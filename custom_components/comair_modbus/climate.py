"""Climate platform for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

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
from .const import VENTILATION_MODES
from .coordinator import ComairModbusCoordinator


class ComairClimate(CoordinatorEntity[ComairModbusCoordinator], ClimateEntity):
    """Climate entity for the ComAir ventilation unit."""

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
        """Available while the unit and the airflow block both answer."""
        return self.coordinator.available("airflow")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode — unit is always running."""
        return HVACMode.FAN_ONLY

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature (extract/indoor air)."""
        return self.coordinator.device.airflow.extract_temp

    @property
    def current_humidity(self) -> float | None:
        """Return the current humidity (extract/indoor air)."""
        return self.coordinator.device.airflow.extract_humidity

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode."""
        return self.coordinator.device.current_mode_name or "Auto"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        device = self.coordinator.device
        airflow = device.airflow

        attrs: dict[str, Any] = {}

        if (intake := airflow.intake_temp) is not None:
            attrs["intake_temperature"] = intake
        if (supply := airflow.supply_temp) is not None:
            attrs["supply_temperature"] = supply
        if (exhaust := airflow.exhaust_temp) is not None:
            attrs["exhaust_temperature"] = exhaust

        duration = device.mode_duration or 0
        attrs["mode_duration_minutes"] = duration
        attrs["mode_duration_text"] = "Indefinite" if duration == 0 else f"{duration} minutes"

        if (power := device.power) is not None:
            attrs["power_consumption"] = power

        if (damper := device.bypass_state_name) is not None:
            attrs["damper_position"] = damper

        return attrs

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode — unit is always running, only FAN_ONLY is valid."""
        return None

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        mode = VENTILATION_MODES.get(preset_mode, 0)
        await self.coordinator.async_set_mode(mode)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComairModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the ComAir climate entity from a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_info = runtime_data.device_info

    async_add_entities([ComairClimate(coordinator, device_info)])