"""Fault, warning and notification code tables for the ComAir HRUC-Plus.

The unit publishes each class as a 32-bit bitmask. Bits are sparse: the code
IDs are not consecutive, and Vent-Axia keeps adding them as the firmware
grows. Every one of the 32 positions is therefore accounted for here --
either as a code the manuals name, or as an open position -- so a new bit
shows up as an explicit "bit N" rather than disappearing into the mask.
"""
from __future__ import annotations

from typing import Final

# ============================================================================
# CODE TABLES
#
# Taken from the manufacturer's own manuals, which do not cover the same set:
#   NL = "Installatie en gebruikershandleiding", Comair HRUC-Plus (Dutch)
#        - has F-8, W-18, W-19, W-20, N-3, N-4, N-5; omits W-8 and W-9
#   PL = "COMAIR HRUC-Plus instrukcja 01/2024" (Polish)
#        - has W-8 and W-9; omits the codes listed above
# Together they cover every code the decoder can produce.
#
# Where the two editions disagree, the disagreement is noted rather than
# silently resolved.
# ============================================================================

#: bit position -> code ID. Codes are not always sequential.
FAULT_BITS: Final[dict[int, str]] = {
    0: "F-1",
    1: "F-2",
    2: "F-3",
    3: "F-4",
    7: "F-8",
    31: "F-32",
}

WARNING_BITS: Final[dict[int, str]] = {
    0: "W-1",
    1: "W-2",
    2: "W-3",
    3: "W-4",
    4: "W-5",
    5: "W-6",
    6: "W-7",
    7: "W-8",
    8: "W-9",
    9: "W-10",
    10: "W-11",
    11: "W-12",
    12: "W-13",
    13: "W-14",
    14: "W-15",
    17: "W-18",
    18: "W-19",
    19: "W-20",
}

NOTIFICATION_BITS: Final[dict[int, str]] = {
    0: "N-1",
    1: "N-2",
    2: "N-3",
    3: "N-4",
    4: "N-5",
}

# ============================================================================
# DESCRIPTIONS
# ============================================================================

FAULT_DESCRIPTIONS: Final[dict[str, str]] = {
    # NL calls F-1 the supply thermistor, PL the inlet thermistor.
    "F-1": "Supply air thermistor",
    "F-2": "Extract air thermistor",
    "F-3": "Supply fan",
    "F-4": "Extract fan",
    "F-8": "Supply air too cold",
    "F-32": "HMI communication lost",
}

WARNING_DESCRIPTIONS: Final[dict[str, str]] = {
    "W-1": "Supply air temperature",
    # NL calls W-2 the exhaust temperature, PL the extract temperature.
    "W-2": "Exhaust air temperature",
    "W-3": "Preheated air temperature",
    "W-4": "Intake air humidity",
    "W-5": "Extract air humidity",
    "W-6": "Supply air flow",
    "W-7": "Extract air flow",
    "W-8": "Left filter sensor",
    "W-9": "Right filter sensor",
    "W-10": "System overpressure",
    "W-11": "Preheater activated",
    "W-12": "Filter cleaning or replacement overdue",
    "W-13": "Service interval overdue",
    "W-14": "Lost connection to sensors or controllers",
    "W-15": "BMS offline",
    "W-18": "Bypass or heat exchanger efficiency",
    "W-19": "Preheater IO offline",
    "W-20": "Cooling unit offline",
}

NOTIFICATION_DESCRIPTIONS: Final[dict[str, str]] = {
    "N-1": "Filter cleaning or replacement due soon",
    "N-2": "Service due soon",
    "N-3": "Device offline",
    "N-4": "Cooling suspended",
    "N-5": "Cooling insufficient",
}

CODE_DESCRIPTIONS: Final[dict[str, str]] = {
    **FAULT_DESCRIPTIONS,
    **WARNING_DESCRIPTIONS,
    **NOTIFICATION_DESCRIPTIONS,
}

# ============================================================================
# CLEARING BEHAVIOUR
#
# Per the Dutch manual:
#   W-1..W-7, W-10, W-11, W-20 - clear once the unit recovers and is power cycled
#   W-12, W-13               - clear once the filter/service values are reset
# ============================================================================
POWER_CYCLE_CLEARS: Final[frozenset[str]] = frozenset(
    {"W-1", "W-2", "W-3", "W-4", "W-5", "W-6", "W-7", "W-10", "W-11", "W-20"}
)
TIMER_RESET_CLEARS: Final[frozenset[str]] = frozenset({"W-12", "W-13"})

#: Width of the published bitmask, in bits.
BITMASK_WIDTH: Final = 32


def decode_bitmask(value: int | None, bits: dict[int, str]) -> list[str]:
    """Decode a 32-bit mask into code IDs, naming every position.

    All 32 positions are walked. A position the tables do not name is
    reported as ``bit N``, so a newly assigned fault is visible in the UI
    instead of vanishing into the unused part of the mask. A code with no
    description (the manual has not caught up yet) is still reported by ID.
    """
    if not value:
        return []
    codes: list[str] = []
    for bit in range(BITMASK_WIDTH):
        if not value & (1 << bit):
            continue
        codes.append(bits.get(bit, f"bit {bit}"))
    return codes


def describe_codes(codes: list[str]) -> list[str]:
    """Pair each code ID with its meaning from the manufacturer's manuals.

    Undocumented codes are passed through unchanged so an unnamed bit is
    still visible rather than silently dropped.
    """
    return [f"{code}: {CODE_DESCRIPTIONS[code]}" if code in CODE_DESCRIPTIONS else code for code in codes]


def format_codes(codes: list[str]) -> str:
    """Render a code list for the sensor state, or ``OK`` when clear."""
    return ", ".join(codes) or "OK"