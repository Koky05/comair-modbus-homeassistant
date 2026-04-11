"""DataUpdateCoordinator for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from pymodbus.client import AsyncModbusTcpClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_MAX_RPM,
    DEFAULT_OVERRIDE_DURATION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    INPUT_REGISTERS,
    MODE_NAMES,
    RETRY_COUNT,
)

# Sentinel value indicating "not available" in HRUC Modbus implementation
UNAVAILABLE_VALUE = 32768  # 0x8000

_LOGGER = logging.getLogger(__name__)


class ComairModbusCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for ComAir Modbus data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: AsyncModbusTcpClient,
        slave_id: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )
        self.client = client
        self.slave_id = slave_id
        self.override_duration: int = DEFAULT_OVERRIDE_DURATION
        self._last_data: dict[str, Any] = {}
        self._failure_count = 0

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from ComAir unit via Modbus."""
        try:
            data: dict[str, Any] = {}

            # Batch 1: Status registers 30001-30010 (addresses 0-9)
            result = await self.client.read_input_registers(
                address=0, count=10, device_id=self.slave_id
            )
            if not result.isError():
                data.update(self._parse_status_registers(result.registers))
            else:
                _LOGGER.debug("Failed to read status registers: %s", result)

            # Batch 2: Fan RPM 30014, 30016 (addresses 13, 15)
            result = await self.client.read_input_registers(
                address=13, count=4, device_id=self.slave_id
            )
            if not result.isError():
                data.update(self._parse_fan_registers(result.registers))
            else:
                _LOGGER.debug("Failed to read fan RPM registers: %s", result)

            # Batch 3: Binary status 30020-30024 (addresses 19-23)
            result = await self.client.read_input_registers(
                address=19, count=5, device_id=self.slave_id
            )
            if not result.isError():
                data.update(self._parse_binary_registers(result.registers))
            else:
                _LOGGER.debug("Failed to read binary registers: %s", result)

            # Batch 3: Intake sensors 30100-30102 (addresses 99-101)
            result = await self.client.read_input_registers(
                address=99, count=3, device_id=self.slave_id
            )
            if not result.isError():
                data["intake_temp"] = self._scale_temp(result.registers[0])
                data["intake_humidity"] = self._if_available(result.registers[1])
                data["intake_co2"] = self._if_available(result.registers[2])
            else:
                _LOGGER.debug("Failed to read intake registers: %s", result)

            # Batch 4: Supply temp 30110 (address 109)
            result = await self.client.read_input_registers(
                address=109, count=1, device_id=self.slave_id
            )
            if not result.isError():
                data["supply_temp"] = self._scale_temp(result.registers[0])
            else:
                _LOGGER.debug("Failed to read supply temp: %s", result)

            # Batch 5: Extract sensors 30120-30122 (addresses 119-121)
            result = await self.client.read_input_registers(
                address=119, count=3, device_id=self.slave_id
            )
            if not result.isError():
                data["extract_temp"] = self._scale_temp(result.registers[0])
                data["extract_humidity"] = self._if_available(result.registers[1])
                data["extract_co2"] = self._if_available(result.registers[2])
            else:
                _LOGGER.debug("Failed to read extract registers: %s", result)

            # Batch 6: Exhaust temp 30130 (address 129)
            result = await self.client.read_input_registers(
                address=129, count=1, device_id=self.slave_id
            )
            if not result.isError():
                data["exhaust_temp"] = self._scale_temp(result.registers[0])
            else:
                _LOGGER.debug("Failed to read exhaust temp: %s", result)

            # Batch 7: User override holding register 40030 (address 29)
            result = await self.client.read_holding_registers(
                address=29, count=1, device_id=self.slave_id
            )
            if not result.isError():
                data["user_override"] = result.registers[0]
                data["current_mode"] = (result.registers[0] >> 8) & 0xFF
                data["mode_duration"] = result.registers[0] & 0xFF
                data["current_mode_name"] = MODE_NAMES.get(
                    data["current_mode"], "Unknown"
                )
            else:
                _LOGGER.debug("Failed to read user override: %s", result)

            # Success - reset failure count and merge data
            self._failure_count = 0
            self._last_data.update(data)
            return self._last_data.copy()

        except Exception as err:
            self._failure_count += 1
            _LOGGER.debug(
                "Transient failure %d/%d: %s",
                self._failure_count,
                RETRY_COUNT,
                err,
            )
            if not self._last_data:
                raise UpdateFailed(
                    f"No data available from ComAir: {err}"
                ) from err
            if self._failure_count >= RETRY_COUNT:
                raise UpdateFailed(
                    f"Error communicating with ComAir after {RETRY_COUNT} attempts: {err}"
                ) from err
            # Return last known data on transient failures
            return self._last_data

    def _parse_status_registers(self, registers: list[int]) -> dict[str, Any]:
        """Parse status registers 30001-30010."""
        data: dict[str, Any] = {}

        if len(registers) >= 10:
            data["run_time"] = registers[0]  # 30001: Run Time (days)
            data["service_timer"] = registers[1] + 1  # 30002: Service Timer (0-based)
            data["filter_timer"] = registers[2] + 1  # 30003: Filter Timer (0-based)
            # 30004-30005: Faults (32-bit)
            data["faults"] = (registers[3] << 16) | registers[4]
            # 30006-30007: Warnings (32-bit)
            data["warnings"] = (registers[5] << 16) | registers[6]
            # 30008-30009: Notifications (32-bit)
            data["notifications"] = (registers[7] << 16) | registers[8]
            data["power"] = registers[9]  # 30010: Power (W)

        return data

    def _parse_fan_registers(self, registers: list[int]) -> dict[str, Any]:
        """Parse fan RPM registers 30014-30017.

        Reading 4 registers starting at address 13:
          [0]=30014 (supply RPM), [1]=30015, [2]=30016 (extract RPM), [3]=30017
        Also calculates fan speed percentage if max_rpm is configured.
        """
        data: dict[str, Any] = {}

        if len(registers) >= 3:
            supply_rpm = self._scale_rpm(registers[0])  # 30014
            extract_rpm = self._scale_rpm(registers[2])  # 30016
            data["supply_fan_rpm"] = supply_rpm
            data["extract_fan_rpm"] = extract_rpm

            # Calculate fan speed percentage from max RPM (set in options)
            max_rpm = self.config_entry.options.get(CONF_MAX_RPM, 0)
            if max_rpm > 0:
                if supply_rpm is not None:
                    data["supply_fan_pct"] = round(
                        min(supply_rpm / max_rpm * 100, 100), 1
                    )
                if extract_rpm is not None:
                    data["extract_fan_pct"] = round(
                        min(extract_rpm / max_rpm * 100, 100), 1
                    )

        return data

    def _parse_binary_registers(self, registers: list[int]) -> dict[str, Any]:
        """Parse binary status registers 30020-30024 (relay output states)."""
        data: dict[str, Any] = {}

        if len(registers) >= 5:
            data["attention_led"] = self._bool_or_none(registers[0])  # 30020
            data["cooling_enable"] = self._bool_or_none(registers[1])  # 30021
            data["preheater_enable"] = self._bool_or_none(registers[2])  # 30022
            data["controlled_cooling"] = self._bool_or_none(registers[3])  # 30023
            data["controlled_heating"] = self._bool_or_none(registers[4])  # 30024

        return data

    def _scale_temp(self, value: int) -> float | None:
        """Scale temperature value (stored as int16 * 10)."""
        if value == UNAVAILABLE_VALUE:
            return None
        # Handle signed int16
        if value >= 32768:
            value -= 65536
        temp = round(value / 10.0, 1)
        if temp < -50 or temp > 80:
            _LOGGER.warning("Temperature out of range: %s", temp)
            return None
        return temp

    def _scale_rpm(self, value: int) -> int | None:
        """Return RPM value (raw register value = RPM, no scaling)."""
        if value == UNAVAILABLE_VALUE:
            return None
        return value

    def _if_available(self, value: int) -> int | None:
        """Return value or None if it's the unavailable sentinel (0x8000)."""
        return None if value == UNAVAILABLE_VALUE else value

    def _bool_or_none(self, value: int) -> bool | None:
        """Return bool or None if value is the unavailable sentinel (0x8000)."""
        if value == UNAVAILABLE_VALUE:
            return None
        return bool(value)


    async def async_write_user_override(
        self, mode: int, duration: int | None = None
    ) -> bool:
        """Write user override register (40030).

        Args:
            mode: Ventilation mode (0=Auto, 1=Low, 2=Medium, 3=High, 4=Boost)
            duration: Duration in minutes (15-240, step 15). If None, uses
                      the current slider value. The MVHR ignores duration=0.

        Returns:
            True if successful, False otherwise
        """
        if duration is None:
            duration = self.override_duration
        # Validate mode (0=Auto, 1=Low, 2=Medium, 3=High, 4=Boost)
        if mode not in range(5):
            _LOGGER.error("Invalid ventilation mode: %d (must be 0-4)", mode)
            return False
        # Duration must be non-zero — MVHR silently ignores writes with duration=0
        if duration <= 0:
            duration = DEFAULT_OVERRIDE_DURATION
        if duration > 240:
            duration = 240
        # Encode: MSB=mode, LSB=duration
        value = ((mode & 0xFF) << 8) | (duration & 0xFF)

        try:
            result = await self.client.write_register(
                address=29, value=value, device_id=self.slave_id
            )
            if not result.isError():
                _LOGGER.debug(
                    "Set ventilation mode to %s for %d minutes (value=%d)",
                    MODE_NAMES.get(mode, "Unknown"),
                    duration,
                    value,
                )
                # Trigger refresh to update entities
                await self.async_request_refresh()
                return True
            else:
                _LOGGER.error("Failed to write user override: %s", result)
                return False
        except Exception as err:
            _LOGGER.exception("Error writing user override: %s", err)
            return False

    async def async_write_raw_override(self, value: int) -> bool:
        """Write raw value to user override register (40030).

        Args:
            value: Raw 16-bit value to write

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.client.write_register(
                address=29, value=value & 0xFFFF, device_id=self.slave_id
            )
            if not result.isError():
                _LOGGER.debug("Set raw user override to %d", value)
                await self.async_request_refresh()
                return True
            else:
                _LOGGER.error("Failed to write raw user override: %s", result)
                return False
        except Exception as err:
            _LOGGER.exception("Error writing raw user override: %s", err)
            return False
