"""Constants for the ComAir HRUC-Plus Modbus integration."""
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
CONF_MAX_RPM: Final = "max_rpm"

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
CONNECT_TIMEOUT: Final = 10
RETRY_COUNT: Final = 3

# Baud rate options
BAUD_RATE_OPTIONS: Final[list[int]] = [9600, 19200, 38400, 57600, 115200]

# Parity options
PARITY_OPTIONS: Final[list[str]] = ["None", "Even", "Odd"]

# Data bits options
DATA_BITS_OPTIONS: Final[list[int]] = [7, 8]

# Stop bits options
STOP_BITS_OPTIONS: Final[list[int]] = [1, 2]

# ============================================================================
# MODBUS REGISTER DEFINITIONS
# Based on MVHR-BMS Modbus Map from Vent-Axia
# ============================================================================

# Input Registers (Function Code 4) - Read Only
# Address is 0-based (register number - 30001)
INPUT_REGISTERS: Final[dict] = {
    # System Status & Timers (30001-30010)
    "run_time": {
        "address": 0,  # Register 30001
        "data_type": "uint16",
        "unit": "d",
        "name": "Run Time",
        "icon": "mdi:timer",
    },
    "service_timer": {
        "address": 1,  # Register 30002
        "data_type": "uint16",
        "unit": "months",
        "name": "Service Timer",
        "icon": "mdi:wrench-clock",
    },
    "filter_timer": {
        "address": 2,  # Register 30003
        "data_type": "uint16",
        "unit": "months",
        "name": "Filter Timer",
        "icon": "mdi:air-filter",
    },
    "faults": {
        "address": 3,  # Register 30004-30005 (32-bit)
        "data_type": "uint32",
        "count": 2,
        "name": "Faults",
        "icon": "mdi:alert-circle",
    },
    "warnings": {
        "address": 5,  # Register 30006-30007 (32-bit)
        "data_type": "uint32",
        "count": 2,
        "name": "Warnings",
        "icon": "mdi:alert",
    },
    "notifications": {
        "address": 7,  # Register 30008-30009 (32-bit)
        "data_type": "uint32",
        "count": 2,
        "name": "Notifications",
        "icon": "mdi:bell",
    },
    "power": {
        "address": 9,  # Register 30010
        "data_type": "uint16",
        "unit": "W",
        "name": "Power",
        "device_class": "power",
    },
    # Fan RPM (30014-30016)
    "supply_fan_rpm": {
        "address": 13,  # Register 30014
        "data_type": "uint16",
        "unit": "rpm",
        "name": "Supply Fan RPM",
        "icon": "mdi:fan",
    },
    "extract_fan_rpm": {
        "address": 15,  # Register 30016
        "data_type": "uint16",
        "unit": "rpm",
        "name": "Extract Fan RPM",
        "icon": "mdi:fan",
    },
    # Binary Status Flags (30020-30024)
    "attention_led": {
        "address": 19,  # Register 30020
        "data_type": "bool",
        "name": "Attention LED",
        "device_class": "problem",
    },
    "cooling_enable": {
        "address": 20,  # Register 30021
        "data_type": "bool",
        "name": "Cooling Enable",
        "icon": "mdi:snowflake",
    },
    "preheater_enable": {
        "address": 21,  # Register 30022
        "data_type": "bool",
        "name": "Preheater Enable",
        "icon": "mdi:heating-coil",
    },
    "controlled_cooling": {
        "address": 22,  # Register 30023
        "data_type": "bool",
        "name": "Controlled Cooling",
        "icon": "mdi:snowflake-thermometer",
    },
    "controlled_heating": {
        "address": 23,  # Register 30024
        "data_type": "bool",
        "name": "Controlled Heating",
        "icon": "mdi:fire",
    },
    # Intake Duct T1 (30100-30102)
    "intake_temp": {
        "address": 99,  # Register 30100
        "data_type": "int16",
        "scale": 0.1,
        "unit": "°C",
        "name": "Intake Temperature",
        "device_class": "temperature",
    },
    "intake_humidity": {
        "address": 100,  # Register 30101
        "data_type": "uint16",
        "unit": "%",
        "name": "Intake Humidity",
        "device_class": "humidity",
    },
    "intake_co2": {
        "address": 101,  # Register 30102
        "data_type": "uint16",
        "unit": "ppm",
        "name": "Intake CO2",
        "device_class": "carbon_dioxide",
    },
    # Supply Duct T2 (30110)
    "supply_temp": {
        "address": 109,  # Register 30110
        "data_type": "int16",
        "scale": 0.1,
        "unit": "°C",
        "name": "Supply Temperature",
        "device_class": "temperature",
    },
    # Extract Duct T3 (30120-30122)
    "extract_temp": {
        "address": 119,  # Register 30120
        "data_type": "int16",
        "scale": 0.1,
        "unit": "°C",
        "name": "Extract Temperature",
        "device_class": "temperature",
    },
    "extract_humidity": {
        "address": 120,  # Register 30121
        "data_type": "uint16",
        "unit": "%",
        "name": "Extract Humidity",
        "device_class": "humidity",
    },
    "extract_co2": {
        "address": 121,  # Register 30122
        "data_type": "uint16",
        "unit": "ppm",
        "name": "Extract CO2",
        "device_class": "carbon_dioxide",
    },
    # Exhaust Duct T4 (30130)
    "exhaust_temp": {
        "address": 129,  # Register 30130
        "data_type": "int16",
        "scale": 0.1,
        "unit": "°C",
        "name": "Exhaust Temperature",
        "device_class": "temperature",
    },
}

# Holding Registers (Function Code 3/6/16) - Read/Write
# Address is 0-based (register number - 40001)
HOLDING_REGISTERS: Final[dict] = {
    # User Override (40030)
    # Format: MSB=preset (0-4), LSB=minutes duration
    "user_override": {
        "address": 29,  # Register 40030
        "data_type": "uint16",
        "name": "User Override",
    },
    # Virtual Inputs (40001-40010) - for future use
    "virtual_input_1": {"address": 0, "data_type": "uint16"},
    "virtual_input_2": {"address": 1, "data_type": "uint16"},
    "virtual_input_3": {"address": 2, "data_type": "uint16"},
    "virtual_input_4": {"address": 3, "data_type": "uint16"},
    "virtual_input_5": {"address": 4, "data_type": "uint16"},
    "virtual_input_6": {"address": 5, "data_type": "uint16"},
    "virtual_input_7": {"address": 6, "data_type": "uint16"},
    "virtual_input_8": {"address": 7, "data_type": "uint16"},
    "virtual_input_9": {"address": 8, "data_type": "uint16"},
    "virtual_input_10": {"address": 9, "data_type": "uint16"},
}

# ============================================================================
# VENTILATION MODE MAPPING
# ============================================================================
# Register 40030 format: MSB=preset (0-4), LSB=minutes
# Mode values for MSB:
#   0 = Auto
#   1 = Low
#   2 = Medium
#   3 = High
#   4 = Boost

VENTILATION_MODES: Final[dict[str, int]] = {
    "Auto": 0,
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Boost": 4,
}

# Reverse mapping for reading current mode
MODE_NAMES: Final[dict[int, str]] = {v: k for k, v in VENTILATION_MODES.items()}

# Common mode values for reference:
# Auto indefinitely:        0 (0x0000)
# Low for 30 min:          286 (0x011E)
# Low for 60 min:          316 (0x013C)
# Medium for 60 min:       572 (0x023C)
# Medium for 120 min:      632 (0x0278)
# High for 30 min:         798 (0x031E)
# High for 60 min:         828 (0x033C)
# Boost for 15 min:       1039 (0x040F)
# Boost for 30 min:       1054 (0x041E)

# ============================================================================
# DEVICE INFO
# ============================================================================
MANUFACTURER: Final = "Ventilair/Vent-Axia"
MODEL: Final = "HRUC-Plus 3 VL"
