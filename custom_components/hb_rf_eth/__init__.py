"""The HB-RF-ETH integration: setup, unload, options, services."""

from __future__ import annotations

import logging

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import HbRfEthClient
from .const import DOMAIN
from .coordinator import HbRfEthCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ("binary_sensor", "sensor", "update")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    # async_setup is not reliably called for config-flow-only integrations,
    # so the services register here, once, on the first configured gateway.
    await async_setup_services(hass)
    client = HbRfEthClient(
        entry.data[CONF_HOST],
        entry.data.get(CONF_USERNAME, "admin"),
        entry.data[CONF_PASSWORD],
        # One shared session for all entries: fewer sockets, HA-managed
        # lifecycle. The client never closes an external session.
        session=async_get_clientsession(hass),
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
