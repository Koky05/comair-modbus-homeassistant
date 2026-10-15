"""Diagnostics support for the ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

from typing import Any

from modbus_connection import ModbusError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SLAVE_ID
from homeassistant.core import HomeAssistant

from .const import DEFAULT_SCAN_INTERVAL
from .coordinator import ComairModbusCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return the raw register map, for reproducing a reading in an issue.

    The registers are read fresh, so the dump reflects the device at the
    moment it was taken rather than the last cached poll. A snapshot like
    this is what an odd reading needs attached to it: it shows exactly what
    the unit returned, and it replays straight into the library's mock
    backend, so it can back a regression test with no hardware.

    Nothing personal is included. The dump carries only the registers the
    integration reads, which are duct measurements, run counters and the
    active code masks. The clock registers are written directly rather than
    declared as fields, so they are never part of a read.
    """
    coordinator: ComairModbusCoordinator = entry.runtime_data.coordinator
    device = coordinator.device

    payload: dict[str, Any] = {
        "entry": {
            CONF_HOST: entry.data.get(CONF_HOST),
            CONF_PORT: entry.data.get(CONF_PORT),
            CONF_SLAVE_ID: entry.data.get(CONF_SLAVE_ID),
        },
        "scan_interval_seconds": DEFAULT_SCAN_INTERVAL,
        "zone_measurements": {
            str(index): list(fields)
            for index, fields in device.zone_measurements.items()
        },
        "last_update_success": coordinator.last_update_success,
    }

    if coordinator.data is not None:
        payload["updated"] = sorted(coordinator.data.updated)
        payload["failed"] = {
            name: str(err) for name, err in coordinator.data.failed.items()
        }
    else:
        payload["updated"] = []
        payload["failed"] = {"*": "no successful poll yet"}

    try:
        registers = await device.async_read_raw()
    except ModbusError as err:
        # A link that will not answer should still hand back everything the
        # rest of the payload knows, rather than failing the download.
        payload["registers"] = f"could not read the register map: {err}"
    else:
        payload["registers"] = {
            space: {str(address): value for address, value in sorted(words.items())}
            for space, words in registers.items()
        }

    return payload