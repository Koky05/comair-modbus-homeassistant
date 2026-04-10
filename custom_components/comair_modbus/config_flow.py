"""Config flow for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.framer import FramerType

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import (
    BAUD_RATE_OPTIONS,
    CONF_BAUD_RATE,
    CONF_DATA_BITS,
    CONF_PARITY,
    CONF_SLAVE_ID,
    CONF_STOP_BITS,
    CONNECT_TIMEOUT,
    DATA_BITS_OPTIONS,
    DEFAULT_BAUD_RATE,
    DEFAULT_DATA_BITS,
    DEFAULT_PARITY,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DEFAULT_STOP_BITS,
    DOMAIN,
    PARITY_OPTIONS,
    STOP_BITS_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

# Configuration schema matching Vent-Axia app BMS screen settings
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        # Gateway connection (required)
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
        # Modbus settings (from BMS screen)
        vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=247)
        ),
        vol.Optional(CONF_BAUD_RATE, default=DEFAULT_BAUD_RATE): vol.In(
            BAUD_RATE_OPTIONS
        ),
        vol.Optional(CONF_DATA_BITS, default=DEFAULT_DATA_BITS): vol.In(
            DATA_BITS_OPTIONS
        ),
        vol.Optional(CONF_PARITY, default=DEFAULT_PARITY): vol.In(PARITY_OPTIONS),
        vol.Optional(CONF_STOP_BITS, default=DEFAULT_STOP_BITS): vol.In(
            STOP_BITS_OPTIONS
        ),
    }
)


class ComairModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ComAir HRUC-Plus Modbus."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            slave_id = user_input.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)

            # Test connection
            client = AsyncModbusTcpClient(
                host=host,
                port=port,
                framer=FramerType.RTU,
                timeout=CONNECT_TIMEOUT,
            )

            try:
                connected = await client.connect()
                if connected:
                    # Try reading a register to verify communication
                    result = await client.read_input_registers(
                        address=0, count=1, device_id=slave_id
                    )
                    client.close()

                    if not result.isError():
                        # Success - create entry
                        unique_id = f"{host}_{slave_id}"
                        await self.async_set_unique_id(unique_id)
                        self._abort_if_unique_id_configured()

                        return self.async_create_entry(
                            title=f"ComAir HRUC ({host})",
                            data=user_input,
                        )
                    else:
                        _LOGGER.error(
                            "Modbus communication error: %s (Slave ID: %d)",
                            result,
                            slave_id,
                        )
                        errors["base"] = "cannot_communicate"
                else:
                    _LOGGER.error("Cannot connect to %s:%d", host, port)
                    errors["base"] = "cannot_connect"

            except Exception as err:
                _LOGGER.exception("Error connecting to %s:%d - %s", host, port, err)
                errors["base"] = "unknown"
            finally:
                if client.connected:
                    client.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "default_port": str(DEFAULT_PORT),
                "default_slave_id": str(DEFAULT_SLAVE_ID),
                "default_baud": str(DEFAULT_BAUD_RATE),
            },
        )
