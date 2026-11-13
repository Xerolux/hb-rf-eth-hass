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
from .coordinator import HbRfEthCoordinator, HbRfEthEntity

SENSORS = (
    SensorEntityDescription(
        key="cpuUsage",
        name="CPU Usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="memoryUsage",
        name="Memory Usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="uptimeSeconds",
        name="Uptime",
        device_class="duration",
        native_unit_of_measurement="s",
        state_class="total_increasing",
    ),
    SensorEntityDescription(
        key="currentVersion",
        name="Firmware Version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="latestVersion",
        name="Latest Firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HbRfEthCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        HbRfEthSensor(coordinator, description) for description in SENSORS
    )


class HbRfEthSensor(HbRfEthEntity, SensorEntity):
    def __init__(self, coordinator: HbRfEthCoordinator, description) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.host}-{description.key}"

    @property
    def native_value(self) -> str | float | None:
        data = self.coordinator.data
        if self.entity_description.key == "latestVersion":
            latest = data.get("update", {}).get("latestFirmware", "")
            return latest or None
        return data.get("sysinfo", {}).get(self.entity_description.key)
