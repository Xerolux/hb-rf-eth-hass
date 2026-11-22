"""Sensors: load, memory, uptime, and version diagnostics."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HbRfEthCoordinator, HbRfEthEntity, services_only

SENSORS = (
    SensorEntityDescription(
        key="cpuUsage",
        translation_key="cpu_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class="measurement",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="memoryUsage",
        translation_key="memory_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class="measurement",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="uptimeSeconds",
        translation_key="uptime",
        device_class="duration",
        native_unit_of_measurement="s",
        state_class="total_increasing",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="currentVersion",
        translation_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="latestVersion",
        translation_key="latest_firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    if services_only(entry):
        return
    coordinator: HbRfEthCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        HbRfEthSensor(coordinator, description) for description in SENSORS
    )


class HbRfEthSensor(HbRfEthEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: HbRfEthCoordinator, description) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.original_host}-{description.key}"

    @property
    def native_value(self) -> str | float | None:
        data = self.coordinator.data
        if self.entity_description.key == "latestVersion":
            update = data.get("update", {})
            if update.get("lastError") or update.get("lastSkipReason"):
                return None
            return update.get("latestFirmware") or None
        return data.get("sysinfo", {}).get(self.entity_description.key)
