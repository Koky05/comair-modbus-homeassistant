"""Switch platform for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComairModbusConfigEntry
from .coordinator import ComairModbusCoordinator

_LOGGER = logging.getLogger(__name__)

VIRTUAL_INPUTS = [
    {"key": f"virtual_input_{i}", "name": f"Virtual Input {i}", "address": i - 1}
    for i in range(1, 11)
]


class ComairVirtualInputSwitch(
    CoordinatorEntity[ComairModbusCoordinator], SwitchEntity
):
    """Switch entity for a BMS virtual input."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:toggle-switch"

    def __init__(
        self,
        coordinator: ComairModbusCoordinator,
        device_info,
        key: str,
        name: str,
        address: int,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.slave_id}_{key}"
        self._attr_device_info = device_info
        self._attr_translation_key = key
        self._address = address
        self._attr_name = name
        self._is_on: bool = False

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the virtual input on."""
        try:
            result = await self.coordinator.client.write_register(
                address=self._address, value=1, device_id=self.coordinator.slave_id
            )
            if not result.isError():
                self._is_on = True
                self.async_write_ha_state()
                _LOGGER.debug("Virtual input %s turned ON", self._attr_name)
            else:
                _LOGGER.error("Failed to turn on %s: %s", self._attr_name, result)
        except Exception as err:
            _LOGGER.exception("Error turning on %s: %s", self._attr_name, err)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the virtual input off."""
        try:
            result = await self.coordinator.client.write_register(
                address=self._address, value=0, device_id=self.coordinator.slave_id
            )
            if not result.isError():
                self._is_on = False
                self.async_write_ha_state()
                _LOGGER.debug("Virtual input %s turned OFF", self._attr_name)
            else:
                _LOGGER.error("Failed to turn off %s: %s", self._attr_name, result)
        except Exception as err:
            _LOGGER.exception("Error turning off %s: %s", self._attr_name, err)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComairModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComAir virtual input switches from a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_info = runtime_data.device_info

    entities = [
        ComairVirtualInputSwitch(
            coordinator, device_info,
            vi["key"], vi["name"], vi["address"],
        )
        for vi in VIRTUAL_INPUTS
    ]

    async_add_entities(entities)
