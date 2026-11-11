"""Binary sensors: Ethernet and CCU relay connectivity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HbRfEthCoordinator, HbRfEthEntity

SENSORS = (
    BinarySensorEntityDescription(
        key="ethernet_connected",
        name="Ethernet",
        device_class="connectivity",
    ),
    BinarySensorEntityDescription(
        key="ccu_connected",
        name="CCU Relay",
        device_class="connectivity",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HbRfEthCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        HbRfEthBinarySensor(coordinator, description) for description in SENSORS
    )


class HbRfEthBinarySensor(HbRfEthEntity, BinarySensorEntity):
    def __init__(self, coordinator: HbRfEthCoordinator, description) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.host}-{description.key}"

    @property
    def is_on(self) -> bool | None:
        info = self.coordinator.data.get("sysinfo", {})
        if self.entity_description.key == "ethernet_connected":
            return bool(info.get("ethernetConnected"))
        if self.entity_description.key == "ccu_connected":
            return bool(info.get("rawUartRemoteAddress"))
        return None
