"""Switch platform for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComairModbusConfigEntry
from .coordinator import ComairModbusCoordinator
from .library.const import VIRTUAL_INPUT_COUNT

_LOGGER = logging.getLogger(__name__)


class ComairVirtualInputSwitch(
    CoordinatorEntity[ComairModbusCoordinator], RestoreEntity, SwitchEntity
):
    """A BMS virtual input.

    Virtual inputs exist to carry a remote temperature, humidity or CO2
    sensor into the unit. The type is fixed in the unit's own BMS setup and
    cannot be changed from here, so these are hidden by default: an
    integration that offers a switch for something the user cannot
    meaningfully toggle in Home Assistant is worse than one that offers
    nothing. They remain available to enable from the entity registry.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:toggle-switch"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: ComairModbusCoordinator,
        device_info,
        index: int,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.slave_id}_virtual_input_{index}"
        self._attr_device_info = device_info
        self._attr_translation_key = f"virtual_input_{index}"
        self._attr_name = f"Virtual Input {index}"
        self._index = index
        self._is_on = False

    async def async_added_to_hass(self) -> None:
        """Show the last known state until the next write."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._is_on = last_state.state == "on"

    @property
    def is_on(self) -> bool:
        """Return true if the virtual input is driven."""
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Drive the virtual input high."""
        await self._async_write(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Drive the virtual input low."""
        await self._async_write(False)

    async def _async_write(self, value: bool) -> None:
        """Write the virtual input and reflect the result."""
        if not await self.coordinator.async_set_virtual_input(self._index, value):
            _LOGGER.error(
                "Failed to write virtual input %s", self._index
            )
            return
        self._is_on = value
        self.async_write_ha_state()
        _LOGGER.debug(
            "Virtual input %s turned %s", self._index, "ON" if value else "OFF"
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComairModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComAir virtual input switches from a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_info = runtime_data.device_info

    async_add_entities(
        ComairVirtualInputSwitch(coordinator, device_info, index)
        for index in range(1, VIRTUAL_INPUT_COUNT + 1)
    )