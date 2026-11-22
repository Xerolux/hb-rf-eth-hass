"""Zeroconf discovery, reconfigure and options flows."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hb_rf_eth.const import (
    CONF_POLL_INTERVAL,
    CONF_SERVICES_ONLY,
    DOMAIN,
)

from .conftest import HOST, LOGIN_RESPONSE, SERIAL, SYSINFO_RESPONSE

USER_INPUT = {CONF_HOST: HOST, CONF_USERNAME: "admin", CONF_PASSWORD: "pw"}


def _mock_ok(aioclient_mock, host: str = HOST):
    aioclient_mock.post(f"http://{host}/login.json", json=LOGIN_RESPONSE)
    aioclient_mock.get(f"http://{host}/sysinfo.json", json=SYSINFO_RESPONSE)
    aioclient_mock.get(f"http://{host}/api/update/status", json={"state": "idle"})


class FakeZeroconfServiceInfo:
    def __init__(self, host: str = HOST):
        self.host = host
        self.hostname = "hb-rf-eth-a446b8.local."
        self.properties = {
            "serial": SERIAL,
            "version": "2.4.0-Beta.6",
            "board": "REV 1.8 (SK)",
        }


async def test_zeroconf_flow_creates_entry(hass, aioclient_mock):
    _mock_ok(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=FakeZeroconfServiceInfo(),
    )
    # Discovered gateway: only credentials are asked for.
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: "admin", CONF_PASSWORD: "pw"}
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == HOST
    assert result["context"]["unique_id"] == SERIAL


async def test_zeroconf_flow_aborts_for_configured_device(hass, aioclient_mock):
    _mock_ok(aioclient_mock)
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, unique_id=SERIAL)
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=FakeZeroconfServiceInfo(),
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_updates_host(hass, aioclient_mock, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    old_entity = registry.async_get_entity_id("update", DOMAIN, f"{HOST}-firmware-update")
    assert old_entity is not None

    # New IP, same credentials.
    _mock_ok(aioclient_mock, "10.0.0.99")
    result = await config_entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "10.0.0.99", CONF_USERNAME: "admin"},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data[CONF_HOST] == "10.0.0.99"
    assert config_entry.data[CONF_PASSWORD] == "pw"
    assert registry.async_get_entity_id("update", DOMAIN, f"{HOST}-firmware-update") == old_entity
    assert registry.async_get_entity_id("update", DOMAIN, "10.0.0.99-firmware-update") is None
    assert hass.states.get(old_entity).state != "unavailable"


async def test_reconfigure_rejects_different_gateway(hass, aioclient_mock, config_entry):
    host = "10.0.0.99"
    aioclient_mock.post(f"http://{host}/login.json", json=LOGIN_RESPONSE)
    other_gateway = {"sysInfo": {**SYSINFO_RESPONSE["sysInfo"], "serial": "OTHER"}}
    aioclient_mock.get(f"http://{host}/sysinfo.json", json=other_gateway)

    result = await config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: host, CONF_USERNAME: "admin"}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "wrong_gateway"
    assert config_entry.data[CONF_HOST] == HOST


async def test_options_services_only_drops_entities(hass, aioclient_mock, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    assert registry.async_get_entity_id("update", DOMAIN, f"{HOST}-firmware-update")

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SERVICES_ONLY: True, CONF_POLL_INTERVAL: 60},
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Reload happened automatically; the entities are gone, the coordinator
    # (and with it the services) keeps running.
    assert registry.async_get_entity_id("update", DOMAIN, f"{HOST}-firmware-update") is None
    assert hass.data[DOMAIN][config_entry.entry_id]["coordinator"].data["sysinfo"][
        "serial"
    ] == SERIAL

    # And back to full mode the entities return.
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SERVICES_ONLY: False, CONF_POLL_INTERVAL: 30}
    )
    await hass.async_block_till_done()
    assert registry.async_get_entity_id("update", DOMAIN, f"{HOST}-firmware-update")


async def test_options_rejects_out_of_range_interval(hass, config_entry):
    import voluptuous as vol

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    try:
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_SERVICES_ONLY: False, CONF_POLL_INTERVAL: 5},
        )
        raised = False
    except vol.Invalid:
        raised = True
    assert raised, "interval below 10 must be rejected by the schema"
