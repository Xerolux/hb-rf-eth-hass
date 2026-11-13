"""Diagnostics: device report without credentials."""

from __future__ import annotations

import pytest

from .conftest import HOST

pytestmark = pytest.mark.usefixtures("config_entry")


async def test_diagnostics_report(hass, aioclient_mock, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    from homeassistant.helpers import device_registry as dr

    from custom_components.hb_rf_eth.diagnostics import async_get_device_diagnostics

    registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(registry, config_entry.entry_id)
    assert devices, "gateway device not found"
    device = devices[0]

    report = await async_get_device_diagnostics(hass, config_entry, device)
    assert report["host"] == HOST
    assert report["coordinator_data"]["sysinfo"]["serial"]
    assert "live_update_status" in report
    # The stored WebUI password never leaves the entry data dict.
    assert "pw" not in str(report)
