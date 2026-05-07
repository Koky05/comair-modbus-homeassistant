"""Binary sensor platform for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComairModbusConfigEntry
from .coordinator import ComairModbusCoordinator


@dataclass(frozen=True, kw_only=True)
class ComairBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes ComAir binary sensor entity."""

    value_fn: Callable[[dict], bool | None]


BINARY_SENSOR_DESCRIPTIONS: tuple[ComairBinarySensorEntityDescription, ...] = (
    ComairBinarySensorEntityDescription(
        key="attention_led",
        translation_key="attention_led",
        name="Attention LED",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.get("attention_led"),
    ),
    ComairBinarySensorEntityDescription(
        key="cooling_enable",
        translation_key="cooling_enable",
        name="Cooling Enable",
        icon="mdi:snowflake",
        value_fn=lambda data: data.get("cooling_enable"),
    ),
    ComairBinarySensorEntityDescription(
        key="preheater_enable",
        translation_key="preheater_enable",
        name="Preheater Enable",
        icon="mdi:heating-coil",
        value_fn=lambda data: data.get("preheater_enable"),
    ),
    ComairBinarySensorEntityDescription(
        key="controlled_cooling",
        translation_key="controlled_cooling",
        name="Controlled Cooling",
        icon="mdi:snowflake-thermometer",
        value_fn=lambda data: data.get("controlled_cooling"),
    ),
    ComairBinarySensorEntityDescription(
        key="controlled_heating",
        translation_key="controlled_heating",
        name="Controlled Heating",
        icon="mdi:fire",
        value_fn=lambda data: data.get("controlled_heating"),
    ),
    ComairBinarySensorEntityDescription(
        key="bypass_active",
        translation_key="bypass_active",
        name="Summer Bypass",
        icon="mdi:valve-open",
        value_fn=lambda data: data.get("bypass_active"),
    ),
)


class ComairBinarySensor(
    CoordinatorEntity[ComairModbusCoordinator], BinarySensorEntity
):
    """Representation of a ComAir binary sensor."""

    _attr_has_entity_name = True
    entity_description: ComairBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: ComairModbusCoordinator,
        description: ComairBinarySensorEntityDescription,
        device_info,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.slave_id}_{description.key}"
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComairModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComAir binary sensors from a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_info = runtime_data.device_info

    entities = [
        ComairBinarySensor(coordinator, description, device_info)
        for description in BINARY_SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)
