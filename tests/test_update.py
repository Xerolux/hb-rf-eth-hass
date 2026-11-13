"""Update entities: versions, progress mapping and install calls."""

from __future__ import annotations

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.hb_rf_eth.const import DOMAIN

from .conftest import HOST, mock_update_status

pytestmark = pytest.mark.usefixtures("config_entry")


def _entity_id(hass, target: str) -> str:
    registry = er.async_get(hass)
    entry_id = registry.async_get_entity_id("update", DOMAIN, f"{HOST}-{target}-update")
    assert entry_id, f"{target} update entity missing"
    return entry_id


async def _firmware_state(hass):
    return hass.states.get(_entity_id(hass, "firmware"))


async def _webui_entity(hass):
    return hass.states.get(_entity_id(hass, "webui"))


async def test_firmware_update_entity_state(hass, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    state = await _firmware_state(hass)
    assert state.attributes["installed_version"] == "2.4.0"
    assert state.attributes["latest_version"] == "2.4.1"


async def test_webui_update_entity_state(hass, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    state = await _webui_entity(hass)
    assert state.attributes["installed_version"] == "1.0.0"
    # latestWebui equals the running version: entity reads "up to date".
    assert state.attributes["latest_version"] == "1.0.0"


async def test_latest_falls_back_to_installed_before_first_search(
    hass, aioclient_mock, config_entry
):
    from .conftest import LOGIN_RESPONSE, SYSINFO_RESPONSE, UPDATE_STATUS_RESPONSE

    payload = {
        **UPDATE_STATUS_RESPONSE,
        "everChecked": False,
        "latestFirmware": "",
        "latestWebui": "",
        "firmwareUpdateAvailable": False,
    }
    # Register the whole device exactly once with the modified status.
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"http://{HOST}/login.json", json=LOGIN_RESPONSE)
    aioclient_mock.get(f"http://{HOST}/sysinfo.json", json=SYSINFO_RESPONSE)
    aioclient_mock.get(f"http://{HOST}/api/update/status", json=payload)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    state = await _firmware_state(hass)
    assert state.attributes["latest_version"] == "2.4.0"


async def test_install_posts_target(hass, aioclient_mock, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.post(f"http://{HOST}/api/update/install", json={"accepted": True})
    registry = er.async_get(hass)
    # The firmware entity has an update available (2.4.1 > 2.4.0), so HA's
    # update.install service accepts the call.
    entry = registry.async_get_entity_id("update", DOMAIN, f"{HOST}-firmware-update")
    await hass.services.async_call(
        "update",
        "install",
        {"entity_id": entry},
        blocking=True,
    )
    # The install call is followed by a coordinator refresh (GET status);
    # match on the URL instead of assuming call order.
    installs = [
        c for c in aioclient_mock.mock_calls if str(c[1]).endswith("/api/update/install")
    ]
    assert installs, "install was not posted"
    assert installs[-1][2] == {"target": "firmware"}


async def test_in_progress_reflects_install_block(hass, aioclient_mock, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Firmware downloading at 42 %: entity properties report the percentage.
    mock_update_status(
        aioclient_mock, state="downloading", target="firmware", progress=42
    )
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    from homeassistant.helpers.entity_component import async_update_entity

    entity_id = _entity_id(hass, "firmware")
    await async_update_entity(hass, entity_id)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.attributes.get("in_progress") is True


async def test_in_progress_ignores_other_target(hass, aioclient_mock, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    mock_update_status(aioclient_mock, state="preparing", target="webui")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    from custom_components.hb_rf_eth.update import HbRfEthUpdateEntity

    # A WebUI install must not mark the firmware entity as installing.
    entity = HbRfEthUpdateEntity(coordinator, "firmware")
    assert entity.in_progress is False
    assert entity.update_percentage is None
