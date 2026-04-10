"""Sensor platform for ComAir HRUC-Plus Modbus integration."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    EntityCategory,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComairModbusConfigEntry
from .coordinator import ComairModbusCoordinator


@dataclass(frozen=True, kw_only=True)
class ComairSensorEntityDescription(SensorEntityDescription):
    """Describes ComAir sensor entity."""

    value_fn: Callable[[dict], float | int | str | None]


def _calc_heat_recovery(data: dict) -> float | None:
    """Calculate heat recovery efficiency: (supply - intake) / (extract - intake) * 100."""
    intake = data.get("intake_temp")
    supply = data.get("supply_temp")
    extract = data.get("extract_temp")
    if intake is None or supply is None or extract is None:
        return None
    diff = extract - intake
    if diff <= 0:
        return None
    efficiency = ((supply - intake) / diff) * 100
    return round(min(max(efficiency, 0), 100), 0)


SENSOR_DESCRIPTIONS: tuple[ComairSensorEntityDescription, ...] = (
    # =========================================================================
    # Temperature Sensors
    # =========================================================================
    ComairSensorEntityDescription(
        key="intake_temp",
        translation_key="intake_temp",
        name="Intake Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("intake_temp"),
    ),
    ComairSensorEntityDescription(
        key="supply_temp",
        translation_key="supply_temp",
        name="Supply Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("supply_temp"),
    ),
    ComairSensorEntityDescription(
        key="extract_temp",
        translation_key="extract_temp",
        name="Extract Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("extract_temp"),
    ),
    ComairSensorEntityDescription(
        key="exhaust_temp",
        translation_key="exhaust_temp",
        name="Exhaust Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("exhaust_temp"),
    ),
    # =========================================================================
    # Humidity Sensors
    # =========================================================================
    ComairSensorEntityDescription(
        key="intake_humidity",
        translation_key="intake_humidity",
        name="Intake Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("intake_humidity"),
    ),
    ComairSensorEntityDescription(
        key="extract_humidity",
        translation_key="extract_humidity",
        name="Extract Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("extract_humidity"),
    ),
    # =========================================================================
    # CO2 Sensors
    # =========================================================================
    ComairSensorEntityDescription(
        key="intake_co2",
        translation_key="intake_co2",
        name="Intake CO2",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("intake_co2"),
    ),
    ComairSensorEntityDescription(
        key="extract_co2",
        translation_key="extract_co2",
        name="Extract CO2",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("extract_co2"),
    ),
    # =========================================================================
    # Fan RPM Sensors
    # =========================================================================
    ComairSensorEntityDescription(
        key="supply_fan_rpm",
        translation_key="supply_fan_rpm",
        name="Supply Fan RPM",
        icon="mdi:fan",
        native_unit_of_measurement="rpm",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get("supply_fan_rpm"),
    ),
    ComairSensorEntityDescription(
        key="extract_fan_rpm",
        translation_key="extract_fan_rpm",
        name="Extract Fan RPM",
        icon="mdi:fan",
        native_unit_of_measurement="rpm",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get("extract_fan_rpm"),
    ),
    # =========================================================================
    # Fan Speed Percentage (calculated from RPM / max RPM, configured in options)
    # =========================================================================
    ComairSensorEntityDescription(
        key="supply_fan_pct",
        translation_key="supply_fan_pct",
        name="Supply Fan Speed",
        icon="mdi:fan",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("supply_fan_pct"),
    ),
    ComairSensorEntityDescription(
        key="extract_fan_pct",
        translation_key="extract_fan_pct",
        name="Extract Fan Speed",
        icon="mdi:fan",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("extract_fan_pct"),
    ),
    # =========================================================================
    # Power Sensor
    # =========================================================================
    ComairSensorEntityDescription(
        key="power",
        translation_key="power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("power"),
    ),
    # =========================================================================
    # Timer Sensors
    # =========================================================================
    ComairSensorEntityDescription(
        key="run_time",
        translation_key="run_time",
        name="Run Time",
        icon="mdi:timer",
        native_unit_of_measurement="d",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.get("run_time"),
    ),
    ComairSensorEntityDescription(
        key="service_timer",
        translation_key="service_timer",
        name="Service Timer",
        icon="mdi:wrench-clock",
        native_unit_of_measurement="months",
        value_fn=lambda data: data.get("service_timer"),
    ),
    ComairSensorEntityDescription(
        key="filter_timer",
        translation_key="filter_timer",
        name="Filter Timer",
        icon="mdi:air-filter",
        native_unit_of_measurement="months",
        value_fn=lambda data: data.get("filter_timer"),
    ),
    # =========================================================================
    # Heat Recovery Efficiency
    # =========================================================================
    ComairSensorEntityDescription(
        key="heat_recovery_efficiency",
        translation_key="heat_recovery_efficiency",
        name="Heat Recovery Efficiency",
        icon="mdi:heat-wave",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: _calc_heat_recovery(data),
    ),
    # =========================================================================
    # Diagnostic Sensors
    # =========================================================================
    ComairSensorEntityDescription(
        key="faults",
        translation_key="faults",
        name="Faults",
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("faults"),
    ),
    ComairSensorEntityDescription(
        key="warnings",
        translation_key="warnings",
        name="Warnings",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("warnings"),
    ),
    ComairSensorEntityDescription(
        key="notifications",
        translation_key="notifications",
        name="Notifications",
        icon="mdi:bell",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("notifications"),
    ),
)


class ComairSensor(CoordinatorEntity[ComairModbusCoordinator], SensorEntity):
    """Representation of a ComAir sensor."""

    _attr_has_entity_name = True
    entity_description: ComairSensorEntityDescription

    def __init__(
        self,
        coordinator: ComairModbusCoordinator,
        description: ComairSensorEntityDescription,
        device_info,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.slave_id}_{description.key}"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float | int | str | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


class ComairEnergySensor(
    CoordinatorEntity[ComairModbusCoordinator], RestoreEntity, SensorEntity
):
    """Energy sensor that integrates power over time (Riemann sum)."""

    _attr_has_entity_name = True
    _attr_translation_key = "energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:lightning-bolt"

    def __init__(
        self,
        coordinator: ComairModbusCoordinator,
        device_info,
    ) -> None:
        """Initialize the energy sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.slave_id}_energy"
        self._attr_device_info = device_info
        self._total_energy: float = 0.0
        self._last_update: float | None = None

    async def async_added_to_hass(self) -> None:
        """Restore last known energy value on HA restart."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._total_energy = float(last_state.state)
            except (ValueError, TypeError):
                self._total_energy = 0.0

    @property
    def native_value(self) -> float | None:
        """Return accumulated energy in kWh."""
        return round(self._total_energy, 4)

    def _handle_coordinator_update(self) -> None:
        """Integrate power over time on each coordinator update."""
        now = time.monotonic()

        if self.coordinator.data is not None:
            power = self.coordinator.data.get("power")
            if power is not None and self._last_update is not None:
                elapsed_hours = (now - self._last_update) / 3600.0
                self._total_energy += (power / 1000.0) * elapsed_hours

        self._last_update = now
        super()._handle_coordinator_update()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComairModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComAir sensors from a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_info = runtime_data.device_info

    entities: list[SensorEntity] = [
        ComairSensor(coordinator, description, device_info)
        for description in SENSOR_DESCRIPTIONS
    ]
    entities.append(ComairEnergySensor(coordinator, device_info))

    async_add_entities(entities)
