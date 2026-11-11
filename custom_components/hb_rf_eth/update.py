"""Update entity: firmware updates with one-click install."""

from __future__ import annotations

from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import HbRfEthApiError
from .const import DOMAIN
from .coordinator import HbRfEthCoordinator, HbRfEthEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HbRfEthCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([HbRfEthUpdateEntity(coordinator)])


class HbRfEthUpdateEntity(HbRfEthEntity, UpdateEntity):
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_supported_features = UpdateEntityFeature.INSTALL
    _attr_title = "HB-RF-ETH Firmware"

    def __init__(self, coordinator: HbRfEthCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.host}-firmware"

    @property
    def installed_version(self) -> str | None:
        return self.coordinator.data.get("sysinfo", {}).get("currentVersion")

    @property
    def latest_version(self) -> str | None:
        latest = self.coordinator.data.get("update", {}).get("latestFirmware", "")
        return latest or self.installed_version

    @property
    def release_url(self) -> str | None:
        return self.coordinator.data.get("update", {}).get("notesUrl") or None

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Trigger the device-side online installation."""
        await self.coordinator.client.async_install_firmware()
        # Installation ends in a device restart; the coordinator's next poll
        # picks up the new version once it is back.
        await self.coordinator.async_request_refresh()
