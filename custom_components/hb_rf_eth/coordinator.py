"""DataUpdateCoordinator for the HB-RF-ETH gateway."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import HbRfEthApiError, HbRfEthAuthError, HbRfEthClient
from .const import DOMAIN, POLL_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class HbRfEthCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, client: HbRfEthClient, host: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {host}",
            update_interval=timedelta(seconds=POLL_INTERVAL_SECONDS),
        )
        self.client = client
        self.host = host

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
            "identifiers": {(DOMAIN, self.coordinator.host)},
            "name": info.get("hostname", self.coordinator.host),
            "manufacturer": "Xerolux",
            "model": "HB-RF-ETH-ng",
            "sw_version": info.get("currentVersion"),
            "hw_version": info.get("boardRevision"),
        }
