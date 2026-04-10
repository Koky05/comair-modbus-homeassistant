"""ComAir HRUC-Plus Modbus integration for Home Assistant."""
from __future__ import annotations

from dataclasses import dataclass
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.framer import FramerType

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
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

_LOGGER = logging.getLogger(__name__)


@dataclass
class ComairModbusRuntimeData:
    """Runtime data for ComAir Modbus integration."""

    client: AsyncModbusTcpClient
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

    # Store serial settings for reference (used by EW11A gateway)
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

    # Create Modbus client for RTU over TCP
    client = AsyncModbusTcpClient(
        host=host,
        port=port,
        framer=FramerType.RTU,  # RTU framing over TCP
        timeout=CONNECT_TIMEOUT,
    )

    # Try to connect
    if not await client.connect():
        raise ConfigEntryNotReady(f"Cannot connect to ComAir gateway at {host}:{port}")

    # Verify communication by reading a register
    try:
        result = await client.read_input_registers(
            address=0, count=1, device_id=slave_id
        )
        if result.isError():
            client.close()
            raise ConfigEntryNotReady(
                f"Cannot communicate with ComAir unit (Slave ID: {slave_id})"
            )
    except Exception as err:
        client.close()
        raise ConfigEntryNotReady(f"Error communicating with ComAir: {err}") from err

    # Create device info
    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{host}_{slave_id}")},
        name=f"ComAir HRUC-Plus ({host})",
        manufacturer=MANUFACTURER,
        model=MODEL,
        configuration_url=f"http://{host}",
    )

    # Create coordinator
    coordinator = ComairModbusCoordinator(hass, entry, client, slave_id)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store runtime data
    entry.runtime_data = ComairModbusRuntimeData(
        client=client,
        coordinator=coordinator,
        device_info=device_info,
    )

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("ComAir Modbus setup complete for %s", host)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ComairModbusConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        runtime_data: ComairModbusRuntimeData = entry.runtime_data
        runtime_data.client.close()
        _LOGGER.info("ComAir Modbus unloaded for %s", entry.data[CONF_HOST])

    return unload_ok
