"""Climate platform for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComairModbusConfigEntry
from .const import MODE_NAMES, VENTILATION_MODES
from .coordinator import ComairModbusCoordinator

_LOGGER = logging.getLogger(__name__)


class ComairClimate(CoordinatorEntity[ComairModbusCoordinator], ClimateEntity):
    """Climate entity for ComAir ventilation unit."""

    _attr_has_entity_name = True
    _attr_translation_key = "ventilation"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.PRESET_MODE
    _attr_hvac_modes = [HVACMode.FAN_ONLY]
    _attr_preset_modes = list(VENTILATION_MODES.keys())
    _attr_icon = "mdi:hvac"

    def __init__(
        self,
        coordinator: ComairModbusCoordinator,
        device_info,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.slave_id}_climate"
        self._attr_device_info = device_info

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.data is not None and super().available

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode — unit is always running."""
        return HVACMode.FAN_ONLY

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature (extract/indoor air)."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("extract_temp")

    @property
    def current_humidity(self) -> float | None:
        """Return the current humidity (extract/indoor air)."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("extract_humidity")

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode."""
        if self.coordinator.data is None:
            return None
        mode = self.coordinator.data.get("current_mode", 0)
        return MODE_NAMES.get(mode, "Auto")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self.coordinator.data is None:
            return {}

        attrs = {}

        # Add intake temperature as attribute
        intake_temp = self.coordinator.data.get("intake_temp")
        if intake_temp is not None:
            attrs["intake_temperature"] = intake_temp

        # Add supply temperature as attribute
        supply_temp = self.coordinator.data.get("supply_temp")
        if supply_temp is not None:
            attrs["supply_temperature"] = supply_temp

        # Add exhaust temperature as attribute
        exhaust_temp = self.coordinator.data.get("exhaust_temp")
        if exhaust_temp is not None:
            attrs["exhaust_temperature"] = exhaust_temp

        # Add mode duration
        mode_duration = self.coordinator.data.get("mode_duration", 0)
        attrs["mode_duration_minutes"] = mode_duration
        if mode_duration == 0:
            attrs["mode_duration_text"] = "Indefinite"
        else:
            attrs["mode_duration_text"] = f"{mode_duration} minutes"

        # Add power consumption
        power = self.coordinator.data.get("power")
        if power is not None:
            attrs["power_consumption"] = power

        return attrs

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode — unit is always running, only FAN_ONLY is valid."""
        _LOGGER.debug("HVAC mode set to FAN_ONLY")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        mode = VENTILATION_MODES.get(preset_mode, 0)
        _LOGGER.debug("Setting preset mode to %s (mode=%d)", preset_mode, mode)
        await self.coordinator.async_write_user_override(mode)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComairModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComAir climate entity from a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_info = runtime_data.device_info

    async_add_entities([ComairClimate(coordinator, device_info)])
