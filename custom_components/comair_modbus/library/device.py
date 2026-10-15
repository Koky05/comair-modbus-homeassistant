"""The ComAir HRUC-Plus as a device object over ``modbus-connection``.

Constructed from a ``ModbusUnit`` supplied by the consumer, which owns and
closes the link. Nothing here imports Home Assistant, so the register map and
the device semantics can be exercised without it.
"""
from __future__ import annotations

from collections.abc import Iterable
import logging
from typing import TYPE_CHECKING

from modbus_connection import ModbusError
from modbus_connection.model import ComponentGroup, Device, Raw, UpdateReport

from .codes import (
    FAULT_BITS,
    NOTIFICATION_BITS,
    WARNING_BITS,
    decode_bitmask,
    describe_codes,
    format_codes,
)
from .components import (
    Airflow,
    Fans,
    Outputs,
    Settings,
    Status,
    VirtualInputs,
    Zone,
)
from .const import (
    ADDR_CLOCK_HOUR_MINUTE,
    ADDR_CLOCK_MONTH_DAY,
    ADDR_CLOCK_YEAR,
    ADDR_KEEPALIVE,
    BYPASS_STATE_NAMES,
    FAN_CURVE,
    MODE_NAMES,
    MODE_AUTO,
    MODE_OFF,
    OVERRIDE_MAX_MINUTES,
    VALID_MODES,
    ZONE_COUNT,
    ZONE_STRIDE,
    decode_override,
    encode_clock,
    encode_override,
)

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

_LOGGER = logging.getLogger(__name__)

#: Sub-systems read on every poll.
READINGS = ("status", "fans_outputs", "airflow", "settings", "zones")

#: Every sub-system, for diagnostics.
ALL = READINGS


class ComairHruC(Device):
    """A ComAir HRUC-Plus MVHR reached through a ``ModbusUnit``."""

    def __init__(self, unit: ModbusUnit) -> None:
        """Build the device around one unit on a shared connection."""
        super().__init__(unit)

        self.status = Status(unit)
        # Fan speeds and relay outputs sit three registers apart, so grouping
        # them pools both into a single request. Over a WiFi gateway that is
        # one less round trip per poll, and a shorter hold on the socket.
        # The members are kept as attributes in their own right, because the
        # group is polled as a unit but each is read on its own by entities.
        self.fans = Fans(unit)
        self.outputs = Outputs(unit)
        self.fans_outputs = ComponentGroup(unit, [self.fans, self.outputs])
        self.airflow = Airflow(unit)
        self.settings = Settings(unit)
        # Written to, never polled: nothing reads a virtual input back.
        self.virtual_inputs = VirtualInputs(unit)

        #: Zones the unit is actually configured for, grouped so their reads
        #: pool. ``None`` when the unit reports no zone measurements at all,
        #: which ``async_poll`` skips.
        self.zones: ComponentGroup | None = None
        #: Zone index -> the component for that zone, so an entity can read
        #: its own zone without the group having to expose its members.
        self.zone_components: dict[int, Zone] = {}
        #: Zone index -> the measurements that answered, as field names.
        #: Detection is per measurement, because a zone can be wired for
        #: temperature only and still report UNAVAILABLE for humidity.
        self.zone_measurements: dict[int, tuple[str, ...]] = {}
        #: Zone indices probed so far.
        self._zone_count_scanned = ZONE_COUNT

        # The unit acknowledges an override by zeroing 40030, so the mode the
        # entity shows is whichever was written most recently.
        self._last_override: int | None = None

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    async def _async_setup(self) -> None:
        """Read what never changes.

        Deliberately does no I/O. Zone discovery is left to the first
        ordinary poll instead of running here, because setup runs inside Home
        Assistant's bootstrap window on a restart, and this unit's gateway is
        slow enough that probing there can be cancelled outright by the
        bootstrap timeout before the integration finishes setting up.
        """

    async def _async_discover_zones(self) -> dict[int, tuple[str, ...]]:
        """Probe zones 0-15 and record the measurements that answer.

        A zone that is not configured does not refuse its registers, it
        answers UNAVAILABLE, so discovery keys on the decoded value rather
        than on the read failing. A measurement reading 0 is a real
        measurement and must not be mistaken for an absent one, which is why
        only the UNAVAILABLE sentinel counts as absent.

        Detection is per measurement: a zone wired for temperature alone
        reports its temperature and UNAVAILABLE for humidity.
        """
        found: dict[int, tuple[str, ...]] = {}
        components: list[Zone] = []
        by_index: dict[int, Zone] = {}
        for index in range(self._zone_count_scanned):
            by_index[index] = Zone(self.modbus_unit, base_offset=index * ZONE_STRIDE)

        # All 16 zones are read as one pooled group rather than one read each.
        # The unit is slow enough over its gateway that sixteen sequential
        # probe reads can outlast Home Assistant's bootstrap window, which
        # cancels the whole integration's setup at startup.
        try:
            await ComponentGroup(
                self.modbus_unit, list(by_index.values())
            ).async_update(notify=False)
        except ModbusError as err:
            _LOGGER.debug("ComAir: zone registers not readable: %s", err)
            self.zone_measurements = {}
            self.zone_components = {}
            self.zones = None
            return {}

        for index, zone in by_index.items():
            live = tuple(
                name
                for name in ("temperature", "humidity")
                if getattr(zone, name) is not None
            )
            if not live:
                continue
            components.append(zone)
            found[index] = live

        self.zone_measurements = found
        self.zone_components = {index: by_index[index] for index in found}
        # Poll only the zones that answered. Grouping them lets the reads
        # pool again rather than costing one request per zone.
        self.zones = ComponentGroup(self.modbus_unit, components) if components else None
        if found:
            _LOGGER.debug("ComAir: zone measurements found: %s", found)
        return found

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def async_update_readings(self, *, discover_zones: bool = True) -> UpdateReport:
        """Refresh everything the unit reports.

        ``discover_zones`` is False for the refresh that happens during
        config-entry setup, to keep that refresh inside the time the host
        allows for startup.
        """
        report = await self.async_poll(("status", "fans_outputs", "airflow"))
        report = await self.async_poll(("zones", "settings"), report)

        # Pick up zones that appeared since they were last looked for.
        # Entities only get created while a platform sets up, so the
        # consumer reloads off the back of this rather than adding them
        # mid-poll.
        if discover_zones and self.zones is None:
            await self._async_discover_zones()
            report = await self.async_poll(("zones",), report)

        await self._async_keepalive()
        return report

    async def async_update(self, *, discover_zones: bool = True) -> UpdateReport:
        """Refresh every sub-system."""
        return await self.async_update_readings(discover_zones=discover_zones)

    async def async_read_raw(self, names: Iterable[str] = ALL) -> Raw:
        """Every register this device reads, undecoded, for diagnostics."""
        return await super().async_read_raw(names)

    async def _async_keepalive(self) -> None:
        """Tell the unit its BMS is still attached.

        Writing 0 to 40020 each cycle suppresses the W-15 "BMS offline"
        warning that the unit raises after a write to the override register.
        A failure here is not worth failing the poll over.
        """
        try:
            await self.modbus_unit.write_register(ADDR_KEEPALIVE, 0)
        except Exception as err:  # noqa: BLE001 - deliberately non-fatal
            _LOGGER.debug("ComAir: BMS keep-alive write failed: %s", err)

    # ------------------------------------------------------------------
    # Derived readings
    # ------------------------------------------------------------------

    @property
    def fault_codes(self) -> list[str]:
        """Active fault code IDs."""
        return decode_bitmask(self.status.faults, FAULT_BITS)

    @property
    def warning_codes(self) -> list[str]:
        """Active warning code IDs."""
        return decode_bitmask(self.status.warnings, WARNING_BITS)

    @property
    def notification_codes(self) -> list[str]:
        """Active notification code IDs."""
        return decode_bitmask(self.status.notifications, NOTIFICATION_BITS)

    @property
    def faults(self) -> str:
        """Active faults, rendered for the sensor state."""
        return format_codes(self.fault_codes)

    @property
    def warnings(self) -> str:
        """Active warnings, rendered for the sensor state."""
        return format_codes(self.warning_codes)

    @property
    def notifications(self) -> str:
        """Active notifications, rendered for the sensor state."""
        return format_codes(self.notification_codes)

    @property
    def fault_details(self) -> list[str]:
        """Active faults paired with their meaning."""
        return describe_codes(self.fault_codes)

    @property
    def warning_details(self) -> list[str]:
        """Active warnings paired with their meaning."""
        return describe_codes(self.warning_codes)

    @property
    def notification_details(self) -> list[str]:
        """Active notifications paired with their meaning."""
        return describe_codes(self.notification_codes)

    # -- summer bypass ---------------------------------------------------

    @property
    def bypass_state(self) -> int | None:
        """Raw damper position from input register 30012."""
        return self.status.bypass_state

    @property
    def bypass_state_name(self) -> str | None:
        """Damper position, named."""
        state = self.bypass_state
        return BYPASS_STATE_NAMES.get(state) if state is not None else None

    @property
    def bypass_active(self) -> bool | None:
        """Whether the summer bypass is engaged.

        The unit publishes its damper position directly, so this no longer
        infers anything from the duct temperatures.
        """
        state = self.bypass_state
        return None if state is None else state != 0

    # -- ventilation mode -----------------------------------------------

    def _override_register(self) -> int:
        """The override register's word, preferring the value just written.

        The unit zeroes 40030 once it has acknowledged an override, so the
        last value written is held here and reported until the unit reports
        something else itself.
        """
        if self._last_override is not None:
            return self._last_override
        return self.settings.override or 0

    @property
    def current_mode(self) -> int | None:
        """Active airflow preset ID, or None when no override is in force."""
        value = self._override_register()
        if not value:
            return None
        return decode_override(value)[0]

    @property
    def current_mode_name(self) -> str | None:
        """Active airflow preset, named.

        A zero duration means the unit is running its own schedule, which is
        what "Auto" means here. Preset 0 with a real duration is the fan being
        stopped, so the two are told apart by the duration, not the preset.
        """
        value = self._override_register()
        if not value:
            return MODE_AUTO
        preset, minutes = decode_override(value)
        if minutes == 0:
            return MODE_AUTO
        return MODE_NAMES.get(preset, "Unknown")

    @property
    def mode_duration(self) -> int | None:
        """Override duration in minutes, or 0 when no override is in force."""
        return decode_override(self._override_register())[1]


    @property
    def power(self) -> int | None:
        """Current power draw in watts."""
        return self.status.power

    # -- derived ventilation figures -------------------------------------

    @property
    def supply_fan_pct(self) -> float | None:
        """Supply fan speed as a percentage."""
        return Fans.rpm_to_pct(self.fans.supply_rpm)

    @property
    def extract_fan_pct(self) -> float | None:
        """Extract fan speed as a percentage."""
        return Fans.rpm_to_pct(self.fans.extract_rpm)

    @property
    def heat_recovery_efficiency(self) -> float | None:
        """Heat exchanger efficiency as a percentage.

        (supply - intake) / (extract - intake). Reported as unavailable
        while the bypass is open, because the air never met the exchanger.
        """
        if self.bypass_active:
            return None
        intake = self.airflow.intake_temp
        supply = self.airflow.supply_temp
        extract = self.airflow.extract_temp
        if intake is None or supply is None or extract is None:
            return None
        spread = extract - intake
        if spread <= 0:
            return None
        return round(min(max((supply - intake) / spread * 100, 0), 100), 0)

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def async_set_override(self, mode: int, minutes: int) -> bool:
        """Write an airflow preset and duration to register 40030.

        ``mode`` is one of :data:`VALID_MODES`, which includes the fixed
        maximum-airflow preset 255 alongside the four stepped speeds.

        ``minutes`` of 0 cancels the override and hands the unit back its own
        schedule. That is how "Auto" is selected: preset 0 with a real
        duration is OFF, which stops the fan rather than returning control.
        """
        if mode not in VALID_MODES:
            _LOGGER.error("Invalid ventilation mode: %s (expected one of %s)", mode, sorted(VALID_MODES))
            return False
        # A zero duration is meaningful -- it cancels the override -- so only
        # the upper bound is clamped.
        if minutes < 0:
            minutes = 0
        if minutes > OVERRIDE_MAX_MINUTES:
            minutes = OVERRIDE_MAX_MINUTES
        return await self._async_write_override(encode_override(mode, minutes), mode, minutes)

    async def async_cancel_override(self) -> bool:
        """Hand the unit back its own schedule, cancelling any override."""
        return await self.async_set_override(MODE_OFF, 0)

    async def async_set_raw_override(self, value: int) -> bool:
        """Write an arbitrary value to the override register."""
        return await self._async_write_override(value & 0xFFFF, None, None)

    async def _async_write_override(
        self, value: int, mode: int | None, minutes: int | None
    ) -> bool:
        """Write 40030 and remember what was asked for."""
        try:
            await self.settings.write("override", value)
        except Exception as err:  # noqa: BLE001 - surfaced to the caller
            _LOGGER.error("ComAir: failed to write user override: %s", err)
            return False

        self._last_override = value
        if mode is not None:
            _LOGGER.debug(
                "ComAir: ventilation mode set to %s for %d minutes (value=%d)",
                MODE_NAMES.get(mode, "Unknown"),
                minutes,
                value,
            )
        else:
            _LOGGER.debug("ComAir: raw user override set to %d", value)
        return True

    async def async_set_virtual_input(self, index: int, value: bool) -> bool:
        """Write one BMS virtual input. ``index`` is 1-based."""
        field = f"virtual_input_{index}"
        if field not in VirtualInputs.declared_fields:
            _LOGGER.error("No virtual input %s", index)
            return False
        try:
            await self.virtual_inputs.write(field, int(value))
        except Exception as err:  # noqa: BLE001 - surfaced to the caller
            _LOGGER.error("ComAir: failed to write virtual input %s: %s", index, err)
            return False
        return True

    async def async_set_clock(self, year: int, month: int, day: int, hour: int, minute: int) -> bool:
        """Write the current date and time to registers 40040-40042."""
        values = encode_clock(year, month, day, hour, minute)
        targets = (
            (ADDR_CLOCK_YEAR, values[0], "year"),
            (ADDR_CLOCK_MONTH_DAY, values[1], f"month={month} day={day}"),
            (ADDR_CLOCK_HOUR_MINUTE, values[2], f"hour={hour} minute={minute}"),
        )
        try:
            for address, value, _ in targets:
                await self.modbus_unit.write_register(address, value)
        except Exception as err:  # noqa: BLE001 - surfaced to the caller
            _LOGGER.error("ComAir: failed to sync clock: %s", err)
            return False
        return True


__all__ = ["ComairHruC", "FAN_CURVE"]