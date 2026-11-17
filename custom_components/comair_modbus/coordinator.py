"""DataUpdateCoordinator for the ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
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

from .const import (
    CAL_KEY_CALIBRATED_AT,
    CAL_KEY_MAP,
    CAL_KEY_SCHEMA,
    CONF_MODE_CALIBRATION,
    DEFAULT_OVERRIDE_DURATION,
    DEFAULT_SCAN_INTERVAL,
)
from .library import ComairHruC
from .library.const import (
    AIRFLOW_PRESETS,
    CALIBRATION_DURATION_MINUTES,
    CALIBRATION_PRESETS,
    CALIBRATION_SAMPLE_COUNT,
    CALIBRATION_SAMPLE_GAP_SECONDS,
    CALIBRATION_SCHEMA,
    CALIBRATION_SETTLE_DELTA_PCT,
    CALIBRATION_SETTLE_INITIAL_WAIT_SECONDS,
    CALIBRATION_SETTLE_MAX_SECONDS,
    CALIBRATION_SETTLE_POLL_GAP_SECONDS,
    CALIBRATION_SETTLE_STABLE_READINGS,
    FIXED_CALIBRATION_READINGS,
    MODE_AUTO,
)

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
        self.entry = entry
        self.slave_id = slave_id
        self.device = ComairHruC(unit)
        self.override_duration: int = DEFAULT_OVERRIDE_DURATION
        self._failed: frozenset[str] = frozenset()
        #: True until the refresh that runs during setup has completed.
        self._setup_refresh = True
        #: Calibration temporarily drives the fan; regular polls queue behind
        #: it so a scheduled refresh cannot disturb a power reading.
        self._calibration_lock = asyncio.Lock()
        self._calibration_running = False

    async def _async_update_data(self) -> UpdateReport:
        """Poll, queued behind a calibration run if one is in progress."""
        async with self._calibration_lock:
            return await self._async_poll()

    async def _async_poll(self) -> UpdateReport:
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

    # ------------------------------------------------------------------
    # Fan-speed calibration
    # ------------------------------------------------------------------

    @property
    def calibration(self) -> dict:
        """Persisted calibration options (empty until the first run)."""
        return self.entry.options.get(CONF_MODE_CALIBRATION, {})

    @property
    def calibration_map(self) -> dict[str, dict[str, float | None]]:
        """Learned mode -> {"supply": %, "extract": %} map.

        An old watts-only map has no schema and is treated as uncalibrated so
        stale readings can never be mistaken for fan speeds.
        """
        if self.calibration.get(CAL_KEY_SCHEMA) != CALIBRATION_SCHEMA:
            return {}
        return self.calibration.get(CAL_KEY_MAP, {})

    @property
    def calibration_timestamp(self) -> str | None:
        """UTC timestamp of the last usable calibration run."""
        if self.calibration.get(CAL_KEY_SCHEMA) != CALIBRATION_SCHEMA:
            return None
        return self.calibration.get(CAL_KEY_CALIBRATED_AT)

    async def async_calibrate_modes(self) -> dict[str, dict[str, float | None]] | None:
        """Measure every fixed mode's fan speed and persist the map.

        Each preset runs until the fans settle, two fan-speed reads are
        averaged, and the exact override word in force beforehand is restored.
        Only one map is kept: re-running (e.g. for a new season) overwrites it.
        Returns the new map, or ``None`` if the run failed.
        """
        if self._calibration_running:
            _LOGGER.warning("ComAir: calibration already running, ignoring request")
            return None

        # Queue behind an in-flight poll rather than dropping the press; the
        # flag rejects a second calibration request once the lock is held.
        async with self._calibration_lock:
            if self._calibration_running:
                _LOGGER.warning("ComAir: calibration already running, ignoring request")
                return None
            self._calibration_running = True
            try:
                result = await self._async_run_calibration()
            finally:
                self._calibration_running = False

        if result is not None:
            await self.async_request_refresh()
        return result

    async def _async_run_calibration(self) -> dict[str, dict[str, float | None]] | None:
        """Run the fan-speed calibration cycle. Caller holds the lock."""
        device = self.device
        saved_override = device.override_value
        # Off and Max are fixed in the unit, so seed their known speeds and
        # only drive the fan through the four app-configurable modes.
        measured: dict[str, dict[str, float | None]] = dict(FIXED_CALIBRATION_READINGS)
        restore_ok = False

        try:
            for mode, preset in CALIBRATION_PRESETS.items():
                if not await device.async_set_override(
                    preset, CALIBRATION_DURATION_MINUTES
                ):
                    raise RuntimeError(f"could not select {mode}")

                await self._async_wait_for_fan_settle(mode)

                supply_samples: list[float] = []
                extract_samples: list[float] = []
                for _ in range(CALIBRATION_SAMPLE_COUNT):
                    supply, extract = await self._async_read_fan_speeds()
                    if supply is not None:
                        supply_samples.append(supply)
                    if extract is not None:
                        extract_samples.append(extract)
                    await asyncio.sleep(CALIBRATION_SAMPLE_GAP_SECONDS)

                if not supply_samples and not extract_samples:
                    raise RuntimeError(f"no fan speed reading for {mode}")

                reading: dict[str, float | None] = {
                    "supply": (
                        round(sum(supply_samples) / len(supply_samples), 2)
                        if supply_samples
                        else None
                    ),
                    "extract": (
                        round(sum(extract_samples) / len(extract_samples), 2)
                        if extract_samples
                        else None
                    ),
                }
                measured[mode] = reading
                _LOGGER.debug("ComAir: calibrated %s at %s", mode, reading)
        except asyncio.CancelledError:
            _LOGGER.warning("ComAir: mode calibration cancelled")
            raise
        except Exception as err:  # noqa: BLE001 - report, then restore in finally
            _LOGGER.error("ComAir: mode calibration failed: %s", err)
            return None
        finally:
            try:
                # Shield the hardware write so an HA shutdown or entry unload
                # cannot abort it halfway through a multi-minute calibration.
                restore_ok = await asyncio.shield(
                    device.async_set_raw_override(saved_override)
                )
            except asyncio.CancelledError:
                _LOGGER.warning(
                    "ComAir: calibration cancelled; restore left running in background"
                )
                restore_ok = False
                raise
            except Exception as err:  # noqa: BLE001
                _LOGGER.error(
                    "ComAir: failed to restore mode after calibration: %s", err
                )

        if not restore_ok:
            _LOGGER.error("ComAir: calibration not saved - previous mode was not restored")
            return None

        options = dict(self.entry.options)
        options[CONF_MODE_CALIBRATION] = {
            CAL_KEY_MAP: measured,
            CAL_KEY_CALIBRATED_AT: datetime.now(timezone.utc).isoformat(),
            CAL_KEY_SCHEMA: CALIBRATION_SCHEMA,
        }
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        _LOGGER.info("ComAir: mode fan-speed calibration saved: %s", measured)
        return measured

    async def _async_read_fan_speeds(self) -> tuple[float | None, float | None]:
        """Poll the fan subsystem and return (supply %, extract %)."""
        report = await self.device.async_poll(("fans_outputs",))
        if "fans_outputs" not in report.updated:
            return None, None
        return self.device.supply_fan_pct, self.device.extract_fan_pct

    async def _async_wait_for_fan_settle(self, mode: str) -> None:
        """Wait until both available fans stop changing after a preset switch."""
        loop = asyncio.get_running_loop()
        await asyncio.sleep(CALIBRATION_SETTLE_INITIAL_WAIT_SECONDS)
        deadline = loop.time() + CALIBRATION_SETTLE_MAX_SECONDS
        previous: tuple[float | None, float | None] | None = None
        stable = 0

        while True:
            current = await self._async_read_fan_speeds()
            if previous is not None and any(value is not None for value in current):
                settled = all(
                    before is None
                    or after is None
                    or abs(after - before) <= CALIBRATION_SETTLE_DELTA_PCT
                    for before, after in zip(previous, current)
                )
                stable = stable + 1 if settled else 0
                if stable >= CALIBRATION_SETTLE_STABLE_READINGS:
                    return
            previous = current

            if loop.time() >= deadline:
                _LOGGER.warning(
                    "ComAir: fan did not settle for %s within %.0f s; using current reading",
                    mode,
                    CALIBRATION_SETTLE_MAX_SECONDS,
                )
                return
            await asyncio.sleep(CALIBRATION_SETTLE_POLL_GAP_SECONDS)