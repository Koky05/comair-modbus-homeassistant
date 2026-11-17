"""Fan-speed-based ventilation mode inference.

Deliberately free of Home Assistant imports so the matching rules can be read
and tested on their own, like the rest of :mod:`.library`.
"""
from __future__ import annotations

from typing import Final

#: Reported when measured fan speeds do not match any calibrated mode.
UNKNOWN_MODE: Final = "Unknown"

#: Relative tolerance band around a calibrated fan speed (+-20%).
CALIBRATION_FAN_TOLERANCE: Final = 0.20

#: Absolute floor for the tolerance band, in percentage points. Gives the
#: stopped fan (0%) a usable band and covers small RPM-derived jitter.
CALIBRATION_FAN_ABS_TOLERANCE_PCT: Final = 2.0

#: Keys used inside each per-mode calibration reading.
FAN_SUPPLY: Final = "supply"
FAN_EXTRACT: Final = "extract"


def infer_mode_from_fan_speed(
    supply_pct: float | None,
    extract_pct: float | None,
    calibration: dict | None,
    *,
    tolerance: float = CALIBRATION_FAN_TOLERANCE,
    absolute_tolerance_pct: float = CALIBRATION_FAN_ABS_TOLERANCE_PCT,
) -> str:
    """Return the calibrated mode matching the measured fan speed(s).

    Each available fan is matched independently against the map. When both
    fans answer they must agree on the same mode; with only one available that
    fan decides. :data:`UNKNOWN_MODE` is returned when there is no usable
    reading, no calibration, or no match within tolerance.
    """
    if not calibration:
        return UNKNOWN_MODE

    supply_mode = _match_one_fan(
        supply_pct, calibration, FAN_SUPPLY, tolerance, absolute_tolerance_pct
    )
    extract_mode = _match_one_fan(
        extract_pct, calibration, FAN_EXTRACT, tolerance, absolute_tolerance_pct
    )

    if supply_mode is not None and extract_mode is not None:
        return supply_mode if supply_mode == extract_mode else UNKNOWN_MODE
    if supply_mode is not None:
        return supply_mode
    if extract_mode is not None:
        return extract_mode
    return UNKNOWN_MODE


def _match_one_fan(
    value_pct: float | None,
    calibration: dict,
    key: str,
    tolerance: float,
    absolute_tolerance_pct: float,
) -> str | None:
    """Return the closest matching mode for one fan, or ``None``."""
    if value_pct is None:
        return None

    best_mode: str | None = None
    best_error: float | None = None

    for mode, reading in calibration.items():
        if not isinstance(reading, dict):
            # Ignore legacy watts-only entries (plain numbers).
            continue
        try:
            reference = float(reading[key])
        except (KeyError, TypeError, ValueError):
            continue

        allowed = max(abs(reference) * tolerance, absolute_tolerance_pct)
        error = abs(value_pct - reference)
        if error <= allowed and (best_error is None or error < best_error):
            best_mode = mode
            best_error = error

    return best_mode
