"""DataUpdateCoordinator for the ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from modbus_connection import (
    ModbusConnectionError,
    ModbusError,
    ModbusUnit,
)
from modbus_connection.model import UpdateReport

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_OVERRIDE_DURATION, DEFAULT_SCAN_INTERVAL
from .library import ComairHruC
from .library.const import AIRFLOW_PRESETS, MODE_AUTO

_LOGGER = logging.getLogger(__name__)


class ComairModbusCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Poll the device object and track which sub-systems answered."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        unit: ModbusUnit,
        slave_id: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="ComAir HRUC-Plus",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )
        self.unit = unit
        self.slave_id = slave_id
        self.device = ComairHruC(unit)
        self.override_duration: int = DEFAULT_OVERRIDE_DURATION
        self._failed: frozenset[str] = frozenset()
        #: True until the refresh that runs during setup has completed.
        self._setup_refresh = True

    async def _async_update_data(self) -> UpdateReport:
        """Refresh the device and translate failures into UpdateFailed.

        The link reconnects on its own, so a dropped connection is reported
        as a failed update rather than triggering a reload.
        """
        try:
            report = await self.device.async_update_readings(
                # The refresh that runs during setup happens inside Home
                # Assistant's bootstrap window. Leave zone discovery to the
                # next poll so setup is not cancelled by the bootstrap
                # timeout on a restart.
                discover_zones=not self._setup_refresh,
            )
        except ModbusConnectionError as err:
            # The gateway drops the socket between requests now and then. The
            # link is already gone, so retrying reopens it immediately and
            # costs nothing. Without this a dropped socket costs a whole poll
            # cycle, which shows up as every entity briefly unavailable.
            # Skipped during setup: that refresh runs inside Home Assistant's
            # bootstrap window, where a second wait can push the entry past
            # the bootstrap timeout and cancel it.
            if self._setup_refresh:
                raise UpdateFailed(str(err)) from err
            _LOGGER.debug("ComAir: link dropped mid-poll (%s), retrying once", err)
            try:
                report = await self.device.async_update_readings(
                    discover_zones=False,
                )
            except ModbusError as retry_err:
                raise UpdateFailed(str(retry_err)) from retry_err
        except ModbusError as err:
            raise UpdateFailed(str(err)) from err
        self._setup_refresh = False

        if not report.updated:
            errors = list(report.failed.values())
            raise UpdateFailed(
                f"no sub-system answered: {errors[0]}"
            ) from ExceptionGroup("every sub-system failed", errors)

        for name in sorted(report.failed.keys() - self._failed):
            _LOGGER.warning("Failed to fetch %s: %s", name, report.failed[name])
        self._failed = frozenset(report.failed)

        return report

    def available(self, *sub_systems: str) -> bool:
        """Whether the coordinator and the named sub-systems last succeeded."""
        return (
            self.last_update_success
            and (not self.data or all(name in self.data.updated for name in sub_systems))
        )

    # ------------------------------------------------------------------
    # Writes, routed through the device so entities stay thin
    # ------------------------------------------------------------------

    async def async_set_mode(self, mode: str, duration: int | None = None) -> bool:
        """Set the airflow option by name, using the slider duration.

        "Auto" cancels any override rather than selecting a preset: on this
        unit preset 0 is OFF, which would stop the fan instead of returning
        control to the unit's own schedule.
        """
        if mode == MODE_AUTO:
            return await self.device.async_cancel_override()
        preset = AIRFLOW_PRESETS.get(mode)
        if preset is None:
            _LOGGER.error("Unknown ventilation option: %s", mode)
            return False
        if duration is None:
            duration = self.override_duration
        return await self.device.async_set_override(preset, duration)

    async def async_set_raw_mode(self, value: int) -> bool:
        """Write a raw value to the override register."""
        return await self.device.async_set_raw_override(value)

    async def async_sync_clock(self, now) -> bool:
        """Push a datetime to the unit's clock registers."""
        return await self.device.async_set_clock(
            now.year, now.month, now.day, now.hour, now.minute
        )

    async def async_set_virtual_input(self, index: int, value: bool) -> bool:
        """Write one BMS virtual input."""
        return await self.device.async_set_virtual_input(index, value)