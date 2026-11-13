"""Diagnostics support: redacted gateway report for issue tracking."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import HbRfEthApiError, HbRfEthClient

# The status endpoints used here carry no credentials; the entries in
# hass.data do (WebUI password). Only whitelisted coordinator data is
# reported, never the config entry data dict.
TO_REDACT: set[str] = set()


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: dict[str, Any]
) -> dict[str, Any]:
    client: HbRfEthClient = hass.data["hb_rf_eth"][entry.entry_id]["client"]
    coordinator = hass.data["hb_rf_eth"][entry.entry_id]["coordinator"]
    diagnostics: dict[str, Any] = {
        "host": entry.data.get("host"),
        "coordinator_data": coordinator.data,
    }
    try:
        diagnostics["live_update_status"] = await client.async_update_status()
    except HbRfEthApiError as err:
        diagnostics["live_update_status"] = {"error": str(err)}
    return diagnostics
