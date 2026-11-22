"""Binary sensors: Ethernet and CCU relay connectivity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HbRfEthCoordinator, HbRfEthEntity, services_only

SENSORS = (
    BinarySensorEntityDescription(
        key="ethernet_connected",
        translation_key="ethernet",
        device_class="connectivity",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="ccu_connected",
        translation_key="ccu_relay",
        device_class="connectivity",
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
        HbRfEthBinarySensor(coordinator, description) for description in SENSORS
    )


class HbRfEthBinarySensor(HbRfEthEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: HbRfEthCoordinator, description) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.original_host}-{description.key}"

    @property
    def is_on(self) -> bool | None:
        info = self.coordinator.data.get("sysinfo", {})
        if self.entity_description.key == "ethernet_connected":
            return bool(info.get("ethernetConnected"))
        if self.entity_description.key == "ccu_connected":
            return bool(info.get("rawUartRemoteAddress"))
        return None
