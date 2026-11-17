"""Tests for power-based ventilation mode inference.

The module is loaded straight from its file so these tests need neither Home
Assistant nor the vendored Modbus dependency installed.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "comair_modbus"
    / "library"
    / "calibration.py"
)
_spec = importlib.util.spec_from_file_location("comair_calibration", _MODULE_PATH)
assert _spec and _spec.loader
calibration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(calibration)

infer = calibration.infer_mode_from_power
UNKNOWN = calibration.UNKNOWN_MODE

MAP = {"Off": 4.0, "Low": 20.0, "Medium": 35.0, "High": 60.0, "Boost": 110.0, "Max": 150.0}


def test_no_calibration_is_unknown():
    assert infer(50.0, {}) == UNKNOWN
    assert infer(50.0, None) == UNKNOWN


def test_no_power_is_unknown():
    assert infer(None, MAP) == UNKNOWN


def test_exact_match():
    assert infer(35.0, MAP) == "Medium"


def test_within_relative_tolerance():
    # 60 W + 10% is inside the +-15% band.
    assert infer(66.0, MAP) == "High"


def test_outside_tolerance_is_unknown():
    # 60 W + 25% matches no mode.
    assert infer(75.0, MAP) == UNKNOWN


def test_absolute_floor_covers_off_reading():
    # 4 W * 15% is only 0.6 W; the 5 W floor still matches 6 W to "Off".
    assert infer(6.0, MAP) == "Off"


def test_zero_watts_matches_calibrated_off():
    # A stopped fan may report 0 W even when Off calibrated a few watts.
    assert infer(0.0, MAP) == "Off"


def test_closest_mode_wins_when_bands_overlap():
    narrow = {"Low": 20.0, "Medium": 22.0}
    assert infer(21.0, narrow) == "Low"
    assert infer(22.0, narrow) == "Medium"


def test_non_numeric_and_none_values_are_skipped():
    partial = {"Off": None, "Low": "not-a-number", "High": 60.0}
    assert infer(60.0, partial) == "High"
