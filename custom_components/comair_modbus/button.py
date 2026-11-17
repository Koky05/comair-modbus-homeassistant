"""Button platform for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComairModbusConfigEntry
from .coordinator import ComairModbusCoordinator

_LOGGER = logging.getLogger(__name__)


class ComairTimeSyncButton(
    CoordinatorEntity[ComairModbusCoordinator], ButtonEntity
):
    """Button to sync the MVHR clock with Home Assistant time."""

    _attr_has_entity_name = True
    _attr_translation_key = "time_sync"
    _attr_icon = "mdi:clock-edit-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: ComairModbusCoordinator,
        device_info,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.slave_id}_time_sync"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        """Sync the MVHR clock to current Home Assistant time."""
        now = dt_util.now()
        if await self.coordinator.async_sync_clock(now):
            _LOGGER.info("MVHR clock synced to %s", now.strftime("%Y-%m-%d %H:%M"))
        else:
            _LOGGER.error("Could not sync the MVHR clock")


class ComairCalibrateModesButton(
    CoordinatorEntity[ComairModbusCoordinator], ButtonEntity
):
    """Button that learns each ventilation mode's power draw."""

    _attr_has_entity_name = True
    _attr_translation_key = "calibrate_modes"
    _attr_icon = "mdi:tune-variant"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: ComairModbusCoordinator,
        device_info,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.slave_id}_calibrate_modes"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        """Run the calibration cycle."""
        result = await self.coordinator.async_calibrate_modes()
        if result is None:
            _LOGGER.error("ComAir: mode power calibration did not complete")
        else:
            _LOGGER.info("ComAir: mode power calibration completed: %s", result)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComairModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComAir buttons from a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_info = runtime_data.device_info

    async_add_entities(
        [
            ComairTimeSyncButton(coordinator, device_info),
            ComairCalibrateModesButton(coordinator, device_info),
        ]
    )