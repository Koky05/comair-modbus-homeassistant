"""Number platform for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComairModbusConfigEntry
from .const import MODE_NAMES
from .coordinator import ComairModbusCoordinator

_LOGGER = logging.getLogger(__name__)


class ComairModeDurationNumber(
    CoordinatorEntity[ComairModbusCoordinator], NumberEntity
):
    """Number entity for mode duration in minutes."""

    _attr_has_entity_name = True
    _attr_name = "Mode Duration"
    _attr_icon = "mdi:timer"
    _attr_native_min_value = 0
    _attr_native_max_value = 255
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: ComairModbusCoordinator,
        device_info,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.slave_id}_mode_duration"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float | None:
        """Return the current duration."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("mode_duration", 0)

    async def async_set_native_value(self, value: float) -> None:
        """Set new duration value."""
        duration = int(value)
        # Get current mode and update with new duration
        current_mode = self.coordinator.data.get("current_mode", 0) if self.coordinator.data else 0
        _LOGGER.debug(
            "Setting mode duration to %d minutes for mode %s",
            duration,
            MODE_NAMES.get(current_mode, "Unknown"),
        )
        await self.coordinator.async_write_user_override(current_mode, duration)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComairModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComAir number entities from a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_info = runtime_data.device_info

    async_add_entities(
        [
            ComairModeDurationNumber(coordinator, device_info),
        ]
    )
