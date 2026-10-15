"""ComAir HRUC-Plus Modbus integration for Home Assistant."""
from __future__ import annotations

from dataclasses import dataclass
import logging

from modbus_connection import ModbusUnit

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    CONF_BAUD_RATE,
    CONF_DATA_BITS,
    CONF_PARITY,
    CONF_SLAVE_ID,
    CONF_STOP_BITS,
    CONNECT_TIMEOUT,
    DEFAULT_BAUD_RATE,
    DEFAULT_DATA_BITS,
    DEFAULT_PARITY,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DEFAULT_STOP_BITS,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    PLATFORMS,
)
from .coordinator import ComairModbusCoordinator
from .helpers import create_modbus_params

_LOGGER = logging.getLogger(__name__)


@dataclass
class ComairModbusRuntimeData:
    """Runtime data for ComAir Modbus integration."""

    unit: ModbusUnit
    coordinator: ComairModbusCoordinator
    device_info: DeviceInfo


ComairModbusConfigEntry = ConfigEntry[ComairModbusRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant, entry: ComairModbusConfigEntry
) -> bool:
    """Set up ComAir Modbus from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    slave_id = entry.data.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)

    # Kept in the log for reference: these describe the RS-485 line behind the
    # EW11A, which the gateway terminates. Only the baud rate reaches the
    # client, as RTU frame spacing.
    baud_rate = entry.data.get(CONF_BAUD_RATE, DEFAULT_BAUD_RATE)
    data_bits = entry.data.get(CONF_DATA_BITS, DEFAULT_DATA_BITS)
    parity = entry.data.get(CONF_PARITY, DEFAULT_PARITY)
    stop_bits = entry.data.get(CONF_STOP_BITS, DEFAULT_STOP_BITS)

    _LOGGER.info(
        "Setting up ComAir Modbus: %s:%d, Slave ID: %d, Serial: %d %d%s%d",
        host,
        port,
        slave_id,
        baud_rate,
        data_bits,
        parity[0] if parity != "None" else "N",
        stop_bits,
    )

    # Ask `modbus` for a unit on the connection it shares between consumers,
    # instead of opening our own socket. Asking performs no I/O, so a powered
    # down unit does not block setup: the coordinator's first refresh opens
    # the link and turns an unreachable unit into ConfigEntryNotReady.
    unit = async_get_unit(hass, entry, create_modbus_params(entry.data), slave_id)
    unit.require_timeout(CONNECT_TIMEOUT)

    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{host}_{slave_id}")},
        name=f"ComAir HRUC-Plus ({host})",
        manufacturer=MANUFACTURER,
        model=MODEL,
        configuration_url=f"http://{host}",
    )

    coordinator = ComairModbusCoordinator(hass, entry, unit, slave_id)

    # The first refresh also runs the device's one-time setup, which probes
    # which zone measurements the unit is configured for, and doubles as the
    # connection test. There is no separate probe to keep in step with it.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = ComairModbusRuntimeData(
        unit=unit,
        coordinator=coordinator,
        device_info=device_info,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("ComAir Modbus setup complete for %s", host)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ComairModbusConfigEntry
) -> bool:
    """Unload a config entry."""
    # No teardown to register: the connection belongs to `modbus`, which closes
    # it when the last entry holding a unit on it unloads.
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)