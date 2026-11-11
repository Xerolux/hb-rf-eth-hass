"""The HB-RF-ETH integration: setup, unload, options."""

from __future__ import annotations

import logging

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .api import HbRfEthApiError, HbRfEthClient
from .const import DOMAIN
from .coordinator import HbRfEthCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ("binary_sensor", "sensor", "update")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    client = HbRfEthClient(
        entry.data[CONF_HOST],
        entry.data.get(CONF_USERNAME, "admin"),
        entry.data[CONF_PASSWORD],
    )
    coordinator = HbRfEthCoordinator(hass, client, entry.data[CONF_HOST])
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:  # noqa: BLE001 - surface as config error
        await client.close()
        _LOGGER.exception("initial refresh failed")
        return False

    hass.data[DOMAIN][entry.entry_id] = {"client": client, "coordinator": coordinator}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["client"].close()
    return unload_ok
