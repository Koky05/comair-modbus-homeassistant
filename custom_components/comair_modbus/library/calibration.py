"""Power-based ventilation mode inference.

Deliberately free of Home Assistant imports so the matching rules can be read
and tested on their own, like the rest of :mod:`.library`.
"""
from __future__ import annotations

from typing import Final

#: Reported when measured power does not match any calibrated mode.
UNKNOWN_MODE: Final = "Unknown"

#: Relative tolerance band around a calibrated power value (+-15%).
CALIBRATION_TOLERANCE: Final = 0.15

#: Absolute floor for the tolerance band, in watts. Keeps the band sensible
#: for the near-zero "Off" reading, where 15% would be a fraction of a watt,
#: and covers a stopped fan reporting 0 W after being calibrated a few watts.
CALIBRATION_ABS_TOLERANCE_W: Final = 5.0


def infer_mode_from_power(
    power_w: float | None,
    calibration: dict[str, float] | None,
    *,
    tolerance: float = CALIBRATION_TOLERANCE,
    absolute_tolerance_w: float = CALIBRATION_ABS_TOLERANCE_W,
) -> str:
    """Return the calibrated mode whose power matches ``power_w``.

    A mode matches when the difference is within ``tolerance`` of its
    calibrated value, with ``absolute_tolerance_w`` as a floor. When several
    modes match, the closest one wins. Returns :data:`UNKNOWN_MODE` when no
    calibration exists, power is unavailable, or nothing is within tolerance.
    """
    if power_w is None or not calibration:
        return UNKNOWN_MODE

    best_mode: str | None = None
    best_error: float | None = None

    for mode, watts in calibration.items():
        if watts is None:
            continue
        try:
            reference = float(watts)
        except (TypeError, ValueError):
            continue

        allowed = max(reference * tolerance, absolute_tolerance_w)
        error = abs(power_w - reference)
        if error <= allowed and (best_error is None or error < best_error):
            best_mode = mode
            best_error = error

    return best_mode if best_mode is not None else UNKNOWN_MODE
