"""The HB-RF-ETH integration: setup, unload, options, services."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import HbRfEthClient
from .const import (
    CONF_POLL_INTERVAL,
    CONF_SERVICES_ONLY,
    DEFAULT_OPTIONS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DOMAIN,
)
from .coordinator import HbRfEthCoordinator
from .services import async_setup_services

PLATFORMS = ("binary_sensor", "sensor", "update")

# No YAML configuration: setup happens exclusively through the config flow.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def entry_options(entry) -> dict:
    """Effective options: defaults overlaid with the stored options."""
    return {**DEFAULT_OPTIONS, **(entry.options or {})}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def _async_remove_entity_registry_entries(hass: HomeAssistant, entry) -> None:
    """Remove this entry's entities when switching to services-only mode.

    HA keeps registry entries of entities a platform no longer provides
    (they would linger as unavailable). Removing them explicitly gives a
    clean device page with just the integration's services.
    """
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.domain in PLATFORMS and entity.platform == DOMAIN:
            registry.async_remove(entity.entity_id)


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
    options = entry_options(entry)
    coordinator = HbRfEthCoordinator(
        hass,
        client,
        entry.data[CONF_HOST],
        poll_interval=options.get(
            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL_SECONDS
        ),
        config_entry=entry,
    )
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await client.close()
        raise

    if options.get(CONF_SERVICES_ONLY):
        await _async_remove_entity_registry_entries(hass, entry)

    hass.data[DOMAIN][entry.entry_id] = {"client": client, "coordinator": coordinator}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Options changes (services-only mode, poll interval) take effect via a
    # full reload; the entity platform then cleans up registry entries it no
    # longer provides. Note: HA (2026.11+) schedules update listeners as
    # tasks, so this must stay a coroutine function.
    async def _async_reload_on_options(hass: HomeAssistant, updated_entry) -> None:
        await hass.config_entries.async_reload(updated_entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["client"].close()
    return unload_ok
