"""Select platform for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComairModbusConfigEntry
from .const import MODE_NAMES, VENTILATION_MODES
from .coordinator import ComairModbusCoordinator

_LOGGER = logging.getLogger(__name__)


class ComairVentilationModeSelect(
    CoordinatorEntity[ComairModbusCoordinator], SelectEntity
):
    """Select entity for ventilation mode."""

    _attr_has_entity_name = True
    _attr_name = "Ventilation Mode"
    _attr_icon = "mdi:fan"
    _attr_options = list(VENTILATION_MODES.keys())

    def __init__(
        self,
        coordinator: ComairModbusCoordinator,
        device_info,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.slave_id}_ventilation_mode"
        self._attr_device_info = device_info

    @property
    def current_option(self) -> str | None:
        """Return current selected option."""
        if self.coordinator.data is None:
            return None
        mode = self.coordinator.data.get("current_mode", 0)
        return MODE_NAMES.get(mode, "Auto")

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        mode = VENTILATION_MODES.get(option, 0)
        _LOGGER.debug("Setting ventilation mode to %s (mode=%d)", option, mode)
        # Set mode indefinitely (duration=0)
        await self.coordinator.async_write_user_override(mode, 0)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComairModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComAir select entities from a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_info = runtime_data.device_info

    async_add_entities([ComairVentilationModeSelect(coordinator, device_info)])
