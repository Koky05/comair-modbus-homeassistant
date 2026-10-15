"""Modelling components for the ComAir HRUC-Plus register map.

Each component is one sub-system of the unit. Grouping registers by function
keeps a sub-system able to refresh on its own, so a block that stops
answering does not take the rest of the unit with it.
"""
from __future__ import annotations

from modbus_connection.model import Component, gauge, integer, uint32

from .const import (
    ADDR_ATTENTION_LED,
    ADDR_BYPASS_OUTPUT,
    ADDR_BYPASS_STATE,
    ADDR_CLOCK_HOUR_MINUTE,
    ADDR_CLOCK_MONTH_DAY,
    ADDR_CLOCK_YEAR,
    ADDR_CONTROLLED_COOLING,
    ADDR_CONTROLLED_HEATING,
    ADDR_COOLING_ENABLE,
    ADDR_EXHAUST_TEMP,
    ADDR_EXTRACT_CO2,
    ADDR_EXTRACT_FAN_RPM,
    ADDR_EXTRACT_HUMIDITY,
    ADDR_EXTRACT_TEMP,
    ADDR_FAULTS,
    ADDR_FILTER_TIMER,
    ADDR_INTAKE_CO2,
    ADDR_INTAKE_HUMIDITY,
    ADDR_INTAKE_TEMP,
    ADDR_NOTIFICATIONS,
    ADDR_POWER,
    ADDR_PREHEATER_ENABLE,
    ADDR_RUN_TIME,
    ADDR_SERVICE_TIMER,
    ADDR_SUPPLY_FAN_RPM,
    ADDR_SUPPLY_TEMP,
    ADDR_USER_OVERRIDE,
    ADDR_VIRTUAL_INPUT_BASE,
    ADDR_WARNINGS,
    ADDR_ZONE_HUM_BASE,
    ADDR_ZONE_TEMP_BASE,
    FAN_CURVE,
    TEMP_MAX,
    TEMP_MIN,
    UNAVAILABLE,
    VIRTUAL_INPUT_COUNT,
)


def in_range(value: float | None) -> float | None:
    """Drop a temperature outside the range the unit can physically report."""
    if value is None or TEMP_MIN <= value <= TEMP_MAX:
        return value
    return None


class Status(Component):
    """Run hours, service timers, active codes and power.

    Input registers 30001-30012. Adding the damper position here keeps it in
    the same contiguous read as the run counters.
    """

    register_space = "input"

    run_time = integer(ADDR_RUN_TIME, signed=False, unit="d")
    # The unit reports both timers 0-based; the manual counts from 1.
    service_timer = integer(ADDR_SERVICE_TIMER, signed=False, offset=1, unit="months")
    filter_timer = integer(ADDR_FILTER_TIMER, signed=False, offset=1, unit="months")
    faults = uint32(ADDR_FAULTS)
    warnings = uint32(ADDR_WARNINGS)
    notifications = uint32(ADDR_NOTIFICATIONS)
    power = integer(ADDR_POWER, signed=False, unit="W")
    bypass_state = integer(ADDR_BYPASS_STATE, signed=False)


class Fans(Component):
    """Supply and extract fan speed. Input registers 30014 and 30016."""

    register_space = "input"

    supply_rpm = integer(ADDR_SUPPLY_FAN_RPM, signed=False, nan=UNAVAILABLE, unit="rpm")
    extract_rpm = integer(ADDR_EXTRACT_FAN_RPM, signed=False, nan=UNAVAILABLE, unit="rpm")

    @staticmethod
    def rpm_to_pct(rpm: int | None) -> float | None:
        """Convert RPM to a fan speed percentage by interpolating the curve."""
        if rpm is None:
            return None
        if rpm <= FAN_CURVE[0][0]:
            return FAN_CURVE[0][1]
        if rpm >= FAN_CURVE[-1][0]:
            return FAN_CURVE[-1][1]
        for (rpm_lo, pct_lo), (rpm_hi, pct_hi) in zip(FAN_CURVE, FAN_CURVE[1:]):
            if rpm_lo <= rpm <= rpm_hi:
                ratio = (rpm - rpm_lo) / (rpm_hi - rpm_lo)
                return round(pct_lo + ratio * (pct_hi - pct_lo), 1)
        return 0.0


class Outputs(Component):
    """Relay output states. Input registers 30020-30025.

    These are read as plain integers and coerced with ``bool()`` rather than
    through a boolean field: the unit has been seen to hold a non-0/1 word on
    a healthy output, and any non-zero reading has always meant "on" here.
    """

    register_space = "input"

    _attention_led = integer(ADDR_ATTENTION_LED, signed=False, nan=UNAVAILABLE)
    _cooling_enable = integer(ADDR_COOLING_ENABLE, signed=False, nan=UNAVAILABLE)
    _preheater_enable = integer(ADDR_PREHEATER_ENABLE, signed=False, nan=UNAVAILABLE)
    _controlled_cooling = integer(ADDR_CONTROLLED_COOLING, signed=False, nan=UNAVAILABLE)
    _controlled_heating = integer(ADDR_CONTROLLED_HEATING, signed=False, nan=UNAVAILABLE)
    _bypass_output = integer(ADDR_BYPASS_OUTPUT, signed=False, nan=UNAVAILABLE)

    @property
    def attention_led(self) -> bool | None:
        """Whether the attention LED is lit."""
        return None if self._attention_led is None else bool(self._attention_led)

    @property
    def cooling_enable(self) -> bool | None:
        """Whether the cooling circuit is enabled."""
        return None if self._cooling_enable is None else bool(self._cooling_enable)

    @property
    def preheater_enable(self) -> bool | None:
        """Whether the preheater is enabled."""
        return None if self._preheater_enable is None else bool(self._preheater_enable)

    @property
    def controlled_cooling(self) -> bool | None:
        """Whether the unit is controlling cooling."""
        return None if self._controlled_cooling is None else bool(self._controlled_cooling)

    @property
    def controlled_heating(self) -> bool | None:
        """Whether the unit is controlling heating."""
        return None if self._controlled_heating is None else bool(self._controlled_heating)

    @property
    def bypass_output(self) -> bool | None:
        """State of register 30025.

        "Other output sources... TODO/TBC" in the official map. Tested
        2026-08-14 on an HRUC-Plus 3 VR and a Sentinel Econiq SC: it sits
        permanently at 1 on both while the real summer bypass opens and
        closes, so it is NOT the bypass damper output. Its meaning is still
        unknown; kept only because the block already covers it.
        """
        return None if self._bypass_output is None else bool(self._bypass_output)


class Airflow(Component):
    """Duct temperatures, humidity and CO2. Input registers 30100-30130."""

    register_space = "input"

    _intake_temp = gauge(ADDR_INTAKE_TEMP, 0.1, nan=UNAVAILABLE, unit="°C")
    intake_humidity = integer(ADDR_INTAKE_HUMIDITY, signed=False, nan=UNAVAILABLE, unit="%")
    intake_co2 = integer(ADDR_INTAKE_CO2, signed=False, nan=UNAVAILABLE, unit="ppm")
    _supply_temp = gauge(ADDR_SUPPLY_TEMP, 0.1, nan=UNAVAILABLE, unit="°C")
    _extract_temp = gauge(ADDR_EXTRACT_TEMP, 0.1, nan=UNAVAILABLE, unit="°C")
    extract_humidity = integer(ADDR_EXTRACT_HUMIDITY, signed=False, nan=UNAVAILABLE, unit="%")
    extract_co2 = integer(ADDR_EXTRACT_CO2, signed=False, nan=UNAVAILABLE, unit="ppm")
    _exhaust_temp = gauge(ADDR_EXHAUST_TEMP, 0.1, nan=UNAVAILABLE, unit="°C")

    @property
    def intake_temp(self) -> float | None:
        """Outdoor (intake) air temperature."""
        return in_range(self._intake_temp)

    @property
    def supply_temp(self) -> float | None:
        """Air leaving the unit into the supply duct."""
        return in_range(self._supply_temp)

    @property
    def extract_temp(self) -> float | None:
        """Indoor (extract) air temperature."""
        return in_range(self._extract_temp)

    @property
    def exhaust_temp(self) -> float | None:
        """Air discharged to the outside."""
        return in_range(self._exhaust_temp)


class Zone(Component):
    """One MVHR zone's measured temperature and humidity.

    Placed per zone with ``base_offset=zone * ZONE_STRIDE``. A zone that is
    not configured answers UNAVAILABLE on both fields, which is what
    discovery keys on.
    """

    register_space = "input"

    temperature = gauge(ADDR_ZONE_TEMP_BASE, 0.1, nan=UNAVAILABLE, unit="°C")
    humidity = integer(ADDR_ZONE_HUM_BASE, signed=False, nan=UNAVAILABLE, unit="%")


class Settings(Component):
    """The airflow override register.

    Polled. The virtual inputs live in their own component because they are
    written but never read back, and polling them would cost a request per
    poll for values nothing consumes.
    """

    override = integer(ADDR_USER_OVERRIDE, signed=False, writable=True)


class VirtualInputs(Component):
    """The ten BMS virtual inputs.

    These carry a remote temperature, humidity or CO2 sensor into the unit.
    Their type is fixed in the unit's own BMS setup and cannot be changed
    over Modbus, so this component is written to but never polled.
    """

    virtual_input_1 = integer(ADDR_VIRTUAL_INPUT_BASE + 0, signed=False, writable=True)
    virtual_input_2 = integer(ADDR_VIRTUAL_INPUT_BASE + 1, signed=False, writable=True)
    virtual_input_3 = integer(ADDR_VIRTUAL_INPUT_BASE + 2, signed=False, writable=True)
    virtual_input_4 = integer(ADDR_VIRTUAL_INPUT_BASE + 3, signed=False, writable=True)
    virtual_input_5 = integer(ADDR_VIRTUAL_INPUT_BASE + 4, signed=False, writable=True)
    virtual_input_6 = integer(ADDR_VIRTUAL_INPUT_BASE + 5, signed=False, writable=True)
    virtual_input_7 = integer(ADDR_VIRTUAL_INPUT_BASE + 6, signed=False, writable=True)
    virtual_input_8 = integer(ADDR_VIRTUAL_INPUT_BASE + 7, signed=False, writable=True)
    virtual_input_9 = integer(ADDR_VIRTUAL_INPUT_BASE + 8, signed=False, writable=True)
    virtual_input_10 = integer(ADDR_VIRTUAL_INPUT_BASE + 9, signed=False, writable=True)


__all__ = [
    "Airflow",
    "Fans",
    "Outputs",
    "Settings",
    "Status",
    "VirtualInputs",
    "Zone",
    "VIRTUAL_INPUT_COUNT",
    "ADDR_CLOCK_YEAR",
    "ADDR_CLOCK_MONTH_DAY",
    "ADDR_CLOCK_HOUR_MINUTE",
]