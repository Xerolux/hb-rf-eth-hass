"""Config flow: setup, auth errors, duplicates and reauth."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hb_rf_eth.const import DOMAIN

from .conftest import HOST, LOGIN_RESPONSE, SERIAL, SYSINFO_RESPONSE, mock_device_api

USER_INPUT = {CONF_HOST: HOST, CONF_USERNAME: "admin", CONF_PASSWORD: "pw"}


async def test_user_flow_creates_entry(hass, aioclient_mock):
    mock_device_api(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "hb-rf-eth-test"
    assert result["data"] == USER_INPUT
    assert result["context"]["unique_id"] == SERIAL


async def test_user_flow_invalid_auth(hass, aioclient_mock):
    aioclient_mock.post(f"http://{HOST}/login.json", status=401)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_duplicate_aborts(hass, aioclient_mock):
    mock_device_api(aioclient_mock)
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, unique_id=SERIAL)
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_updates_password(hass, aioclient_mock, config_entry):
    """A rejected password surfaces as reauth; a new one reloads the entry."""
    from homeassistant.const import CONF_HOST

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Password changed on the device: every login with the old one fails.
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"http://{config_entry.data[CONF_HOST]}/login.json", status=401)

    result = await config_entry.start_reauth_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    # The new password works again.
    aioclient_mock.clear_requests()
    aioclient_mock.post(
        f"http://{config_entry.data[CONF_HOST]}/login.json", json=LOGIN_RESPONSE
    )
    aioclient_mock.get(f"http://{config_entry.data[CONF_HOST]}/sysinfo.json", json=SYSINFO_RESPONSE)
    aioclient_mock.get(
        f"http://{config_entry.data[CONF_HOST]}/api/update/status", json={"state": "idle"}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new-pw"}
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PASSWORD] == "new-pw"
