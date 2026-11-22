"""DataUpdateCoordinator for the HB-RF-ETH gateway."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import HbRfEthApiError, HbRfEthAuthError, HbRfEthClient
from .const import DEFAULT_POLL_INTERVAL_SECONDS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HbRfEthCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: HbRfEthClient,
        host: str,
        poll_interval: int = DEFAULT_POLL_INTERVAL_SECONDS,
        *,
        config_entry: ConfigEntry,
        original_host: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN} {host}",
            update_interval=timedelta(seconds=poll_interval),
            always_update=False,
        )
        self.client = client
        self.host = host
        self.original_host = original_host

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            sysinfo = await self.client.async_sysinfo()
        except HbRfEthAuthError as err:
            # Credentials were valid at setup but the device rejects them
            # now (password changed): hand over to the reauth flow.
            raise ConfigEntryAuthFailed(str(err)) from err
        except HbRfEthApiError as err:
            raise UpdateFailed(str(err)) from err
        update_status: dict[str, Any] = {}
        try:
            update_status = await self.client.async_update_status()
        except HbRfEthApiError as err:
            _LOGGER.debug("update status unavailable: %s", err)
        return {"sysinfo": sysinfo, "update": update_status}


class HbRfEthEntity(CoordinatorEntity[HbRfEthCoordinator]):
    """Shared device info for all entities of one gateway."""

    def __init__(self, coordinator: HbRfEthCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def device_info(self) -> dict[str, Any]:
        info = self.coordinator.data.get("sysinfo", {})
        return {
            "identifiers": {(DOMAIN, self.coordinator.original_host)},
            "name": info.get("hostname", self.coordinator.host),
            "manufacturer": "Xerolux",
            "model": "HB-RF-ETH-ng",
            "sw_version": info.get("currentVersion"),
            "hw_version": info.get("boardRevision"),
        }


def services_only(entry) -> bool:
    """True when the entry runs in services-only coexistence mode.

    Used by installations that take their entities from the firmware's
    native MQTT/HA auto-discovery: the integration then registers no
    entities and only provides its services (backup/restore/log/...).
    """
    from .const import CONF_SERVICES_ONLY, DEFAULT_OPTIONS

    options = {**DEFAULT_OPTIONS, **(entry.options or {})}
    return bool(options.get(CONF_SERVICES_ONLY, False))
