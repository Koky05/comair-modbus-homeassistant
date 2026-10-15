"""Home Assistant wiring for the ComAir HRUC-Plus Modbus integration.

The register map and the device semantics live in :mod:`.library`, which has
no Home Assistant imports. What is left here is what only this side needs:
platforms, config keys and the defaults the config flow offers.
"""
from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

# Domain
DOMAIN: Final = "comair_modbus"

# Platforms
PLATFORMS: Final[list[Platform]] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.CLIMATE,
]

# Configuration keys
CONF_SLAVE_ID: Final = "slave_id"
CONF_BAUD_RATE: Final = "baud_rate"
CONF_DATA_BITS: Final = "data_bits"
CONF_PARITY: Final = "parity"
CONF_STOP_BITS: Final = "stop_bits"

# Default values (matching Vent-Axia BMS settings)
DEFAULT_PORT: Final = 502
DEFAULT_SLAVE_ID: Final = 2
DEFAULT_BAUD_RATE: Final = 115200
DEFAULT_DATA_BITS: Final = 8
DEFAULT_PARITY: Final = "None"
DEFAULT_STOP_BITS: Final = 1
DEFAULT_SCAN_INTERVAL: Final = 30
DEFAULT_OVERRIDE_DURATION: Final = 240  # 4 hours (app uses 15 min steps)

# Connection settings
CONNECT_TIMEOUT: Final = 10.0

# Baud rate options
BAUD_RATE_OPTIONS: Final[list[int]] = [9600, 19200, 38400, 57600, 115200]

# Parity options
PARITY_OPTIONS: Final[list[str]] = ["None", "Even", "Odd"]

# Data bits options
DATA_BITS_OPTIONS: Final[list[int]] = [7, 8]

# Stop bits options
STOP_BITS_OPTIONS: Final[list[int]] = [1, 2]

# Re-exported from the device library so the platforms have one import.
from .library.const import (  # noqa: E402
    MANUFACTURER,
    MODE_NAMES,
    MODEL,
    VENTILATION_MODES,
)

__all__ = [
    "BAUD_RATE_OPTIONS",
    "CONF_BAUD_RATE",
    "CONF_DATA_BITS",
    "CONF_PARITY",
    "CONF_SLAVE_ID",
    "CONF_STOP_BITS",
    "CONNECT_TIMEOUT",
    "DATA_BITS_OPTIONS",
    "DEFAULT_BAUD_RATE",
    "DEFAULT_DATA_BITS",
    "DEFAULT_OVERRIDE_DURATION",
    "DEFAULT_PARITY",
    "DEFAULT_PORT",
    "DEFAULT_SCAN_INTERVAL",
    "DEFAULT_SLAVE_ID",
    "DEFAULT_STOP_BITS",
    "DOMAIN",
    "MANUFACTURER",
    "MODE_NAMES",
    "MODEL",
    "PARITY_OPTIONS",
    "PLATFORMS",
    "STOP_BITS_OPTIONS",
    "VENTILATION_MODES",
]