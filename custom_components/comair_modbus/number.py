"""Number platform for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComairModbusConfigEntry
from .coordinator import ComairModbusCoordinator

_LOGGER = logging.getLogger(__name__)


class ComairModeDurationNumber(
    CoordinatorEntity[ComairModbusCoordinator], NumberEntity
):
    """Number entity for mode duration in minutes."""

    _attr_has_entity_name = True
    _attr_translation_key = "mode_duration"
    _attr_icon = "mdi:timer"
    _attr_native_min_value = 15
    _attr_native_max_value = 240
    _attr_native_step = 15
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
        """Return the current override duration setting."""
        return self.coordinator.override_duration

    async def async_set_native_value(self, value: float) -> None:
        """Set override duration. The next mode change will use this duration."""
        duration = int(value)
        self.coordinator.override_duration = duration
        _LOGGER.debug("Override duration set to %d minutes", duration)
        self.async_write_ha_state()


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
