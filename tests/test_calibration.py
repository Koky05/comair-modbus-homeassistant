"""Tests for fan-speed-based ventilation mode inference.

The modules are loaded straight from their files so these tests need neither
Home Assistant nor the vendored Modbus dependency installed.
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

_CONST_PATH = _MODULE_PATH.with_name("const.py")
_const_spec = importlib.util.spec_from_file_location("comair_const", _CONST_PATH)
assert _const_spec and _const_spec.loader
const = importlib.util.module_from_spec(_const_spec)
_const_spec.loader.exec_module(const)

infer = calibration.infer_mode_from_fan_speed
UNKNOWN = calibration.UNKNOWN_MODE


def test_only_app_configurable_modes_are_measured():
    assert const.CALIBRATION_MODES == ("Low", "Medium", "High", "Boost")
    assert set(const.CALIBRATION_PRESETS) == set(const.CALIBRATION_MODES)
    assert "Off" not in const.CALIBRATION_PRESETS
    assert "Max" not in const.CALIBRATION_PRESETS


def test_fixed_readings_cover_off_and_max():
    assert const.FIXED_CALIBRATION_READINGS == {
        "Off": {"supply": 0.0, "extract": 0.0},
        "Max": {"supply": 100.0, "extract": 100.0},
    }

# Only Low/Medium/High/Boost are measured; Off and Max are fixed constants.
MAP = {
    "Off": {"supply": 0.0, "extract": 0.0},
    "Low": {"supply": 7.7, "extract": 7.7},
    "Medium": {"supply": 15.2, "extract": 15.0},
    "High": {"supply": 30.0, "extract": 30.0},
    "Boost": {"supply": 100.0, "extract": 100.0},
    "Max": {"supply": 100.0, "extract": 100.0},
}


def test_fixed_off_and_max_are_recognised_without_measurement():
    # The app cannot change Off or Max, so they are seeded into the map.
    fixed = {
        "Off": {"supply": 0.0, "extract": 0.0},
        "Max": {"supply": 100.0, "extract": 100.0},
    }
    assert infer(1.0, 1.0, fixed) == "Off"
    assert infer(100.0, 100.0, fixed) == "Max"


def test_no_calibration_is_unknown():
    assert infer(50.0, 50.0, {}) == UNKNOWN
    assert infer(50.0, 50.0, None) == UNKNOWN


def test_no_fan_reading_is_unknown():
    assert infer(None, None, MAP) == UNKNOWN


def test_exact_match_both_fans_agree():
    assert infer(7.7, 7.7, MAP) == "Low"
    assert infer(30.0, 30.0, MAP) == "High"


def test_within_relative_tolerance():
    # 30% + 10% is inside the +-20% band for High.
    assert infer(33.0, 33.0, MAP) == "High"


def test_outside_tolerance_is_unknown():
    # 30% + 30% matches no mode.
    assert infer(45.0, 45.0, MAP) == UNKNOWN


def test_absolute_floor_matches_calibrated_off():
    # 0% * 20% is 0; the 2-point floor lets a near-stopped fan match Off.
    assert infer(1.5, 1.5, MAP) == "Off"


def test_closest_mode_wins_when_bands_overlap():
    narrow = {
        "Low": {"supply": 20.0, "extract": 20.0},
        "Medium": {"supply": 22.0, "extract": 22.0},
    }
    assert infer(21.0, 21.0, narrow) == "Low"
    assert infer(22.0, 22.0, narrow) == "Medium"


def test_disagreeing_fans_are_unknown():
    assert infer(7.7, 30.0, MAP) == UNKNOWN


def test_single_available_fan_is_used():
    assert infer(7.7, None, MAP) == "Low"
    assert infer(None, 30.0, MAP) == "High"


def test_one_sided_calibration_uses_that_fan_only():
    partial = {
        "Low": {"supply": 7.7},
        "High": {"extract": 30.0},
    }
    assert infer(7.7, None, partial) == "Low"
    assert infer(None, 30.0, partial) == "High"


def test_non_numeric_and_missing_values_are_skipped():
    partial = {
        "Off": {"supply": None, "extract": None},
        "Low": {"supply": "not-a-number", "extract": "not-a-number"},
        "High": {"supply": 30.0, "extract": 30.0},
    }
    assert infer(30.0, 30.0, partial) == "High"


def test_legacy_watts_map_is_ignored():
    legacy = {"Off": 4.0, "Low": 20.0, "High": 60.0}
    assert infer(20.0, 20.0, legacy) == UNKNOWN
