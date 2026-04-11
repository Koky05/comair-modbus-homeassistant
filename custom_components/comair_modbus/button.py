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
    """Button to sync MVHR clock with HA time."""

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
        """Sync MVHR clock to current HA time."""
        now = dt_util.now()

        # Register 40040 (address 39): Year (uint16)
        # Register 40041 (address 40): MSB=month, LSB=day
        # Register 40042 (address 41): MSB=hour, LSB=minute
        year = now.year
        month_day = (now.month << 8) | now.day
        hour_minute = (now.hour << 8) | now.minute

        try:
            # Write all three registers
            for addr, value, desc in [
                (39, year, "year"),
                (40, month_day, f"month={now.month} day={now.day}"),
                (41, hour_minute, f"hour={now.hour} minute={now.minute}"),
            ]:
                result = await self.coordinator.client.write_register(
                    address=addr, value=value, device_id=self.coordinator.slave_id
                )
                if result.isError():
                    _LOGGER.error("Failed to write %s: %s", desc, result)
                    return

            _LOGGER.info(
                "MVHR clock synced to %s",
                now.strftime("%Y-%m-%d %H:%M"),
            )
        except Exception as err:
            _LOGGER.exception("Error syncing MVHR clock: %s", err)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ComairModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComAir buttons from a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_info = runtime_data.device_info

    async_add_entities([ComairTimeSyncButton(coordinator, device_info)])
