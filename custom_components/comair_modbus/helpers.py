"""Helpers for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

from typing import Any

from modbus_connection import ModbusSerialParams

from homeassistant.const import CONF_HOST, CONF_PORT

from .const import CONF_BAUD_RATE, DEFAULT_BAUD_RATE, DEFAULT_PORT


def create_modbus_params(data: dict[str, Any]) -> ModbusSerialParams:
    """Build the shared-connection parameters for the EW11A gateway.

    The Elfin EW11A is set to transparent transmission ("UART Proto: NONE"),
    so it forwards the RS-485 bytes to the network unchanged. That makes this
    a serial line reached over a socket, not a Modbus TCP gateway: RTU frames
    with their CRC, and no MBAP header.

    This matches the wire format pymodbus produced for this integration
    before it moved onto the shared connection, because a TCP client keeps
    whichever framer it is handed rather than forcing Modbus TCP framing.
    """
    return ModbusSerialParams(
        device=f"socket://{data[CONF_HOST]}:{data.get(CONF_PORT, DEFAULT_PORT)}",
        framer="rtu",
        baudrate=data.get(CONF_BAUD_RATE, DEFAULT_BAUD_RATE),
    )