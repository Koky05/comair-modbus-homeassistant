"""Register map and code tables for the ComAir HRUC-Plus MVHR.

This module is part of the vendored device library. It imports nothing from
Home Assistant, so the register map can be tested without it.
"""
from __future__ import annotations

from typing import Final

# ============================================================================
# ADDRESSING
#
# Input registers are numbered from 30001 and holding registers from 40001.
# Everything below is 0-based, i.e. the register number minus its base.
# ============================================================================

INPUT_BASE: Final = 30001
HOLDING_BASE: Final = 40001

# --- Input registers (FC04, read only) -------------------------------------
ADDR_RUN_TIME: Final = 0  # 30001, days
ADDR_SERVICE_TIMER: Final = 1  # 30002, months, 0-based on the wire
ADDR_FILTER_TIMER: Final = 2  # 30003, months, 0-based on the wire
ADDR_FAULTS: Final = 3  # 30004-30005, 32-bit bitmask
ADDR_WARNINGS: Final = 5  # 30006-30007, 32-bit bitmask
ADDR_NOTIFICATIONS: Final = 7  # 30008-30009, 32-bit bitmask
ADDR_POWER: Final = 9  # 30010, W
ADDR_BYPASS_STATE: Final = 11  # 30012, damper position
ADDR_SUPPLY_FAN_RPM: Final = 13  # 30014
ADDR_EXTRACT_FAN_RPM: Final = 15  # 30016
ADDR_ATTENTION_LED: Final = 19  # 30020
ADDR_COOLING_ENABLE: Final = 20  # 30021
ADDR_PREHEATER_ENABLE: Final = 21  # 30022
ADDR_CONTROLLED_COOLING: Final = 22  # 30023
ADDR_CONTROLLED_HEATING: Final = 23  # 30024
ADDR_BYPASS_OUTPUT: Final = 24  # 30025, meaning undocumented, see library/device.py
ADDR_INTAKE_TEMP: Final = 99  # 30100
ADDR_INTAKE_HUMIDITY: Final = 100  # 30101
ADDR_INTAKE_CO2: Final = 101  # 30102
ADDR_SUPPLY_TEMP: Final = 109  # 30110
ADDR_EXTRACT_TEMP: Final = 119  # 30120
ADDR_EXTRACT_HUMIDITY: Final = 120  # 30121
ADDR_EXTRACT_CO2: Final = 121  # 30122
ADDR_EXHAUST_TEMP: Final = 129  # 30130

# Zone measurements. Zone N sits at a fixed 10-register stride:
#   temperature = ZONE_TEMP_BASE + N * ZONE_STRIDE
#   humidity    = ZONE_HUM_BASE  + N * ZONE_STRIDE
ADDR_ZONE_TEMP_BASE: Final = 199  # 30200, zone 0
ADDR_ZONE_HUM_BASE: Final = 200  # 30201, zone 0
ZONE_STRIDE: Final = 10
ZONE_COUNT: Final = 16

# --- Holding registers (FC03/06/16, read/write) ---------------------------
ADDR_VIRTUAL_INPUT_BASE: Final = 0  # 40001-40010
VIRTUAL_INPUT_COUNT: Final = 10
ADDR_KEEPALIVE: Final = 19  # 40020, written 0 every poll
ADDR_USER_OVERRIDE: Final = 29  # 40030, MSB = preset, LSB = minutes
ADDR_CLOCK_YEAR: Final = 39  # 40040
ADDR_CLOCK_MONTH_DAY: Final = 40  # 40041, MSB = month, LSB = day
ADDR_CLOCK_HOUR_MINUTE: Final = 41  # 40042, MSB = hour, LSB = minute

# ============================================================================
# SHARED CONSTANTS
# ============================================================================

#: The unit reports this raw word for a measurement it does not implement.
UNAVAILABLE: Final = 0x8000

#: Temperature reads outside this range are rejected as implausible.
TEMP_MIN: Final = -50.0
TEMP_MAX: Final = 80.0

#: Override durations, in minutes, are clamped to these bounds.
OVERRIDE_MIN_MINUTES: Final = 15
OVERRIDE_MAX_MINUTES: Final = 240

# ============================================================================
# VENTILATION MODE / USER OVERRIDE ENCODING
#
# Register 40030 packs the airflow preset in the MSB and the override
# duration in minutes in the LSB.
# ============================================================================

MODE_AUTO: Final = 0
MODE_LOW: Final = 1
MODE_MEDIUM: Final = 2
MODE_HIGH: Final = 3
MODE_BOOST: Final = 4

#: Fixed maximum-airflow preset. The HMI offers it alongside the four
#: stepped fan speeds; it is not one of the 0-4 presets above.
MODE_MAX: Final = 255

#: Presets 5 and 6 exist on the unit but are not documented and not offered.
MODE_HIDDEN: Final = (5, 6)

VENTILATION_MODES: Final[dict[str, int]] = {
    "Auto": MODE_AUTO,
    "Low": MODE_LOW,
    "Medium": MODE_MEDIUM,
    "High": MODE_HIGH,
    "Boost": MODE_BOOST,
    "Max": MODE_MAX,
}

MODE_NAMES: Final[dict[int, str]] = {v: k for k, v in VENTILATION_MODES.items()}

#: Every preset the integration accepts in a write.
VALID_MODES: Final[frozenset[int]] = frozenset(VENTILATION_MODES.values())


def encode_override(mode: int, minutes: int) -> int:
    """Pack an airflow preset and a duration into the 40030 register value."""
    return ((mode & 0xFF) << 8) | (minutes & 0xFF)


def decode_override(value: int) -> tuple[int, int]:
    """Split a 40030 register value into (preset, duration in minutes)."""
    return (value >> 8) & 0xFF, value & 0xFF


def encode_clock(year: int, month: int, day: int, hour: int, minute: int) -> tuple[int, int, int]:
    """Pack a date and time into the three clock registers 40040-40042."""
    return (year, (month << 8) | day, (hour << 8) | minute)


# ============================================================================
# SUMMER BYPASS / DAMPER POSITION (input register 30012)
#
# Reported directly by the unit, so this replaces any inference from the
# duct temperatures.
# ============================================================================

BYPASS_CLOSED: Final = 0
BYPASS_STATE_NAMES: Final[dict[int, str]] = {
    0: "Closed",
    1: "SBP Normal",
    2: "SBP Evening Fresh",
    3: "SBP Nighttime Fresh",
    4: "Anti-frost",
    5: "Diagnostic",
    6: "Service Mode",
    7: "BMS Override",
}

# ============================================================================
# FAN CURVE
#
# Measured RPM -> % points, averaged across the supply and extract fans.
# ============================================================================
FAN_CURVE: Final[list[tuple[int, float]]] = [
    (0, 0.0),
    (817, 8.0),
    (1021, 15.0),
    (1489, 30.0),
    (3347, 100.0),
]

# ============================================================================
# DEVICE IDENTITY
# ============================================================================
MANUFACTURER: Final = "Ventilair/Vent-Axia"
MODEL: Final = "HRUC-Plus 3"