"""Update entities: firmware and WebUI with one-click install."""

from __future__ import annotations

from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HbRfEthCoordinator, HbRfEthEntity, services_only

INSTALL_ACTIVE_STATES = {"preparing", "downloading", "verifying", "finalizing"}


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    if services_only(entry):
        return
    coordinator: HbRfEthCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [
            HbRfEthUpdateEntity(coordinator, "firmware"),
            HbRfEthUpdateEntity(coordinator, "webui"),
        ]
    )


class HbRfEthUpdateEntity(HbRfEthEntity, UpdateEntity):
    """One installable target ("firmware" or "webui")."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    # PROGRESS makes HA honour the in_progress/update_percentage properties
    # for the state attributes; without it the internal flag is used.
    _attr_supported_features = UpdateEntityFeature.INSTALL | UpdateEntityFeature.PROGRESS

    def __init__(self, coordinator: HbRfEthCoordinator, target: str) -> None:
        super().__init__(coordinator)
        self._target = target
        self._attr_unique_id = f"{coordinator.host}-{target}-update"
        self._attr_title = "HB-RF-ETH Firmware" if target == "firmware" else "HB-RF-ETH WebUI"

    # Installed/latest -----------------------------------------------------

    @property
    def installed_version(self) -> str | None:
        key = "runningFirmware" if self._target == "firmware" else "runningWebui"
        return self.coordinator.data.get("update", {}).get(key) or None

    @property
    def latest_version(self) -> str | None:
        update = self.coordinator.data.get("update", {})
        key = "latestFirmware" if self._target == "firmware" else "latestWebui"
        if update.get("lastError") or update.get("lastSkipReason"):
            return None
        return update.get(key) or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        update = self.coordinator.data.get("update", {})
        if not update:
            return {"update_check_status": "unavailable"}
        if update.get("lastError"):
            return {"update_check_status": "failed", "update_check_reason": update["lastError"]}
        if update.get("lastSkipReason"):
            return {"update_check_status": "skipped", "update_check_reason": update["lastSkipReason"]}
        return {"update_check_status": "checked" if update.get("everChecked") else "not_checked"}

    @property
    def release_url(self) -> str | None:
        return self.coordinator.data.get("update", {}).get("notesUrl") or None

    # Install progress ------------------------------------------------------

    def _install_block(self) -> dict[str, Any]:
        return self.coordinator.data.get("update", {}).get("install") or {}

    @property
    def in_progress(self) -> bool | int:
        install = self._install_block()
        # HA's update.install service requires False (not None) when idle.
        if (
            install.get("target") == self._target
            and install.get("state") in INSTALL_ACTIVE_STATES
        ):
            if install.get("state") == "downloading":
                return int(install.get("progress") or 0)
            return True
        return False

    @property
    def update_percentage(self) -> int | None:
        install = self._install_block()
        if (
            install.get("target") == self._target
            and install.get("state") == "downloading"
        ):
            return int(install.get("progress") or 0)
        return None

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Trigger the device-side online installation."""
        await self.coordinator.client.async_install(self._target)
        # Installation is asynchronous on the device and ends in a restart
        # (firmware) or remount (WebUI); the next polls pick up the result.
        await self.coordinator.async_request_refresh()
