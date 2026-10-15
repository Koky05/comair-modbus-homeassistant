"""Binary sensor platform for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComairModbusConfigEntry
from .coordinator import ComairModbusCoordinator
from .library import ComairHruC


@dataclass(frozen=True, kw_only=True)
class ComairBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a ComAir binary sensor backed by a device attribute."""

    value_fn: Callable[[ComairHruC], bool | None]
    #: Sub-system this value comes from.
    report_name: str


BINARY_SENSOR_DESCRIPTIONS: tuple[ComairBinarySensorEntityDescription, ...] = (
    ComairBinarySensorEntityDescription(
        key="attention_led",
        translation_key="attention_led",
        name="Attention LED",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        report_name="fans_outputs",
        value_fn=lambda d: d.outputs.attention_led,
    ),
    ComairBinarySensorEntityDescription(
        key="cooling_enable",
        translation_key="cooling_enable",
        name="Cooling Enable",
        icon="mdi:snowflake",
        report_name="fans_outputs",
        value_fn=lambda d: d.outputs.cooling_enable,
    ),
    ComairBinarySensorEntityDescription(
        key="preheater_enable",
        translation_key="preheater_enable",
        name="Preheater Enable",
        icon="mdi:heating-coil",
        report_name="fans_outputs",
        value_fn=lambda d: d.outputs.preheater_enable,
    ),
    ComairBinarySensorEntityDescription(
        key="controlled_cooling",
        translation_key="controlled_cooling",
        name="Controlled Cooling",
        icon="mdi:snowflake-thermometer",
        report_name="fans_outputs",
        value_fn=lambda d: d.outputs.controlled_cooling,
    ),
    ComairBinarySensorEntityDescription(
        key="controlled_heating",
        translation_key="controlled_heating",
        name="Controlled Heating",
        icon="mdi:fire",
        report_name="fans_outputs",
        value_fn=lambda d: d.outputs.controlled_heating,
    ),
    # The unit publishes its damper position on input register 30012, so this
    # reads it rather than inferring it from the duct temperatures.
    ComairBinarySensorEntityDescription(
        key="bypass_active",
        translation_key="bypass_active",
        name="Summer Bypass",
        icon="mdi:valve-open",
        report_name="status",
        value_fn=lambda d: d.bypass_active,
    ),
)


class ComairBinarySensor(
    CoordinatorEntity[ComairModbusCoordinator], BinarySensorEntity
):
    """A ComAir binary sensor reading one attribute off the device."""

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
    def available(self) -> bool:
        """Available while the sub-system this value comes from answers."""
        return self.coordinator.available(self.entity_description.report_name)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.value_fn(self.coordinator.device)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Name the damper position alongside the on/off state."""
        if self.entity_description.key != "bypass_active":
            return None
        name = self.coordinator.device.bypass_state_name
        return {"damper_position": name} if name else None


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