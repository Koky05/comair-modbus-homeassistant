"""Sensor platform for the ComAir HRUC-Plus Modbus integration."""
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
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)

# UnitOfRatio replaced CONCENTRATION_PARTS_PER_MILLION, which HA deprecated and
# removes in Core 2027.8.  Both resolve to "ppm", so fall back on older cores
# that predate the enum rather than raising the minimum HA version.
try:
    from homeassistant.const import UnitOfRatio

    PARTS_PER_MILLION = UnitOfRatio.PARTS_PER_MILLION
except ImportError:  # HA Core older than the UnitOfRatio enum
    from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION as PARTS_PER_MILLION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComairModbusConfigEntry
from .coordinator import ComairModbusCoordinator
from .library import ComairHruC


@dataclass(frozen=True, kw_only=True)
class ComairSensorEntityDescription(SensorEntityDescription):
    """Describes a ComAir sensor backed by a device attribute."""

    value_fn: Callable[[ComairHruC], float | int | str | None]
    #: Sub-system this value comes from. The entity goes unavailable when
    #: that sub-system failed, while the rest of the unit carries on.
    report_name: str
    #: Optional extra attributes, e.g. the meaning of each active fault code.
    attrs_fn: Callable[[ComairHruC], dict | None] | None = None


def _code_attrs(kind: str) -> Callable[[ComairHruC], dict | None]:
    """Expose active codes and their meanings as attributes.

    The state stays the compact code list ("W-12, W-15") so automations and
    history keep working; the human-readable meaning and the raw 32-bit mask
    go in attributes.
    """

    # The property on the device renders the codes for display; the raw
    # register word lives on the status component.
    raw_field = {"fault": "faults", "warning": "warnings", "notification": "notifications"}[kind]

    def _attrs(device: ComairHruC) -> dict | None:
        codes = getattr(device, f"{kind}_codes")
        if codes is None:
            return None
        return {
            "codes": codes,
            "descriptions": getattr(device, f"{kind}_details"),
            "raw_mask": getattr(device.status, raw_field),
        }

    return _attrs


SENSOR_DESCRIPTIONS: tuple[ComairSensorEntityDescription, ...] = (
    # =========================================================================
    # Duct temperatures
    # =========================================================================
    ComairSensorEntityDescription(
        key="intake_temp",
        translation_key="intake_temp",
        name="Intake Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        report_name="airflow",
        value_fn=lambda d: d.airflow.intake_temp,
    ),
    ComairSensorEntityDescription(
        key="supply_temp",
        translation_key="supply_temp",
        name="Supply Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        report_name="airflow",
        value_fn=lambda d: d.airflow.supply_temp,
    ),
    ComairSensorEntityDescription(
        key="extract_temp",
        translation_key="extract_temp",
        name="Extract Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        report_name="airflow",
        value_fn=lambda d: d.airflow.extract_temp,
    ),
    ComairSensorEntityDescription(
        key="exhaust_temp",
        translation_key="exhaust_temp",
        name="Exhaust Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        report_name="airflow",
        value_fn=lambda d: d.airflow.exhaust_temp,
    ),
    # =========================================================================
    # Humidity and CO2
    # =========================================================================
    ComairSensorEntityDescription(
        key="intake_humidity",
        translation_key="intake_humidity",
        name="Intake Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        report_name="airflow",
        value_fn=lambda d: d.airflow.intake_humidity,
    ),
    ComairSensorEntityDescription(
        key="extract_humidity",
        translation_key="extract_humidity",
        name="Extract Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        report_name="airflow",
        value_fn=lambda d: d.airflow.extract_humidity,
    ),
    ComairSensorEntityDescription(
        key="intake_co2",
        translation_key="intake_co2",
        name="Intake CO2",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        report_name="airflow",
        value_fn=lambda d: d.airflow.intake_co2,
    ),
    ComairSensorEntityDescription(
        key="extract_co2",
        translation_key="extract_co2",
        name="Extract CO2",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        report_name="airflow",
        value_fn=lambda d: d.airflow.extract_co2,
    ),
    # =========================================================================
    # Fans
    # =========================================================================
    ComairSensorEntityDescription(
        key="supply_fan_rpm",
        translation_key="supply_fan_rpm",
        name="Supply Fan RPM",
        icon="mdi:fan",
        native_unit_of_measurement="rpm",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        report_name="fans_outputs",
        value_fn=lambda d: d.fans.supply_rpm,
    ),
    ComairSensorEntityDescription(
        key="extract_fan_rpm",
        translation_key="extract_fan_rpm",
        name="Extract Fan RPM",
        icon="mdi:fan",
        native_unit_of_measurement="rpm",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        report_name="fans_outputs",
        value_fn=lambda d: d.fans.extract_rpm,
    ),
    ComairSensorEntityDescription(
        key="supply_fan_pct",
        translation_key="supply_fan_pct",
        name="Supply Fan Speed",
        icon="mdi:fan",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        report_name="fans_outputs",
        value_fn=lambda d: d.supply_fan_pct,
    ),
    ComairSensorEntityDescription(
        key="extract_fan_pct",
        translation_key="extract_fan_pct",
        name="Extract Fan Speed",
        icon="mdi:fan",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        report_name="fans_outputs",
        value_fn=lambda d: d.extract_fan_pct,
    ),
    # =========================================================================
    # Power and timers
    # =========================================================================
    ComairSensorEntityDescription(
        key="power",
        translation_key="power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        report_name="status",
        value_fn=lambda d: d.status.power,
    ),
    ComairSensorEntityDescription(
        key="run_time",
        translation_key="run_time",
        name="Run Time",
        icon="mdi:timer",
        native_unit_of_measurement="d",
        state_class=SensorStateClass.TOTAL,
        report_name="status",
        value_fn=lambda d: d.status.run_time,
    ),
    ComairSensorEntityDescription(
        key="service_timer",
        translation_key="service_timer",
        name="Service Timer",
        icon="mdi:wrench-clock",
        native_unit_of_measurement="months",
        report_name="status",
        value_fn=lambda d: d.status.service_timer,
    ),
    ComairSensorEntityDescription(
        key="filter_timer",
        translation_key="filter_timer",
        name="Filter Timer",
        icon="mdi:air-filter",
        native_unit_of_measurement="months",
        report_name="status",
        value_fn=lambda d: d.status.filter_timer,
    ),
    ComairSensorEntityDescription(
        key="heat_recovery_efficiency",
        translation_key="heat_recovery_efficiency",
        name="Heat Recovery Efficiency",
        icon="mdi:heat-wave",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        report_name="airflow",
        value_fn=lambda d: d.heat_recovery_efficiency,
    ),
    # =========================================================================
    # Diagnostics
    # =========================================================================
    ComairSensorEntityDescription(
        key="faults",
        translation_key="faults",
        name="Faults",
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        report_name="status",
        value_fn=lambda d: d.faults,
        attrs_fn=_code_attrs("fault"),
    ),
    ComairSensorEntityDescription(
        key="warnings",
        translation_key="warnings",
        name="Warnings",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        report_name="status",
        value_fn=lambda d: d.warnings,
        attrs_fn=_code_attrs("warning"),
    ),
    ComairSensorEntityDescription(
        key="notifications",
        translation_key="notifications",
        name="Notifications",
        icon="mdi:bell",
        entity_category=EntityCategory.DIAGNOSTIC,
        report_name="status",
        value_fn=lambda d: d.notifications,
        attrs_fn=_code_attrs("notification"),
    ),
    ComairSensorEntityDescription(
        key="bypass_state",
        translation_key="bypass_state",
        name="Damper Position",
        icon="mdi:air-conditioner",
        entity_category=EntityCategory.DIAGNOSTIC,
        report_name="status",
        value_fn=lambda d: d.bypass_state_name,
        attrs_fn=lambda d: {"raw": d.bypass_state},
    ),
)


class ComairSensor(CoordinatorEntity[ComairModbusCoordinator], SensorEntity):
    """A ComAir sensor reading one attribute off the device."""

    _attr_has_entity_name = True
    entity_description: ComairSensorEntityDescription

    def __init__(
        self,
        coordinator: ComairModbusCoordinator,
        description: ComairSensorEntityDescription,
        device_info,
        unique_key: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        key = unique_key or description.key
        self._attr_unique_id = f"{coordinator.slave_id}_{key}"
        self._attr_device_info = device_info

    @property
    def available(self) -> bool:
        """Available while the sub-system this value comes from answers."""
        return self.coordinator.available(self.entity_description.report_name)

    @property
    def native_value(self) -> float | int | str | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.device)

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return extra attributes, for sensors that define them."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.device)


class ComairZoneSensor(ComairSensor):
    """A zone measurement, one entity per measurement the unit reports.

    Entities are created only for measurements that answered during setup,
    so a unit with two zones wired up does not gain 32 entities that can
    never report. Once created an entity stays in the registry and goes
    unavailable rather than disappearing if its register later reads the
    unavailable sentinel.
    """

    def __init__(
        self,
        coordinator: ComairModbusCoordinator,
        device_info,
        zone_index: int,
        field: str,
    ) -> None:
        """Initialize a zone sensor."""
        description = ZONE_SENSOR_DESCRIPTIONS[field]
        super().__init__(
            coordinator,
            description,
            device_info,
            unique_key=f"zone_{zone_index}_{field}",
        )
        self._zone_index = zone_index
        self._field = field

    @property
    def _zone(self):
        """The zone component this sensor reads."""
        return self.coordinator.device.zone_components.get(self._zone_index)

    @property
    def native_value(self) -> float | int | None:
        """Return the zone measurement."""
        zone = self._zone
        return None if zone is None else getattr(zone, self._field)


ZONE_SENSOR_DESCRIPTIONS: dict[str, ComairSensorEntityDescription] = {
    "temperature": ComairSensorEntityDescription(
        key="zone_temperature",
        translation_key="zone_temperature",
        name="Zone Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        report_name="zones",
        value_fn=lambda d: None,
    ),
    "humidity": ComairSensorEntityDescription(
        key="zone_humidity",
        translation_key="zone_humidity",
        name="Zone Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        report_name="zones",
        value_fn=lambda d: None,
    ),
}


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
        self._restored: bool = False

    @property
    def available(self) -> bool:
        """A long-term statistic holds its value across a gap in the link."""
        return True

    async def async_added_to_hass(self) -> None:
        """Restore last known energy value on HA restart."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._total_energy = float(last_state.state)
            except (ValueError, TypeError):
                self._total_energy = 0.0
        self._restored = True

    @property
    def native_value(self) -> float | None:
        """Return accumulated energy in kWh."""
        if not self._restored:
            return None
        return round(self._total_energy, 4)

    def _handle_coordinator_update(self) -> None:
        """Integrate power over time on each coordinator update."""
        now = time.monotonic()

        power = self.coordinator.device.power
        if power is not None and self._last_update is not None:
            elapsed_hours = (now - self._last_update) / 3600.0
            # Cap at 2x scan interval to prevent spikes after long gaps
            if 0 < elapsed_hours < (120 / 3600):
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

    # Zone entities are added as discovery finds them rather than only while
    # this platform sets up. Discovery has to happen on a later poll, because
    # the refresh during setup is kept deliberately cheap to stay inside Home
    # Assistant's bootstrap window, so at this point the zone set is normally
    # still unknown. Entities already created are tracked so a later poll
    # that sees the same zones adds nothing.
    added: set[int] = set()

    def _add_discovered_zones() -> None:
        """Create an entity for each zone measurement not yet created."""
        new: list[SensorEntity] = []
        for zone_index, fields in coordinator.device.zone_measurements.items():
            if zone_index in added:
                continue
            added.add(zone_index)
            new.extend(
                ComairZoneSensor(coordinator, device_info, zone_index, field)
                for field in fields
            )
        if new:
            async_add_entities(new)

    _add_discovered_zones()
    entry.async_on_unload(coordinator.async_add_listener(_add_discovered_zones))