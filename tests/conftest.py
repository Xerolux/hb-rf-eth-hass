"""Shared fixtures: custom-integration loader and device API mocks."""

from __future__ import annotations

import pytest

from custom_components.hb_rf_eth.const import DOMAIN

HOST = "10.0.0.42"
SERIAL = "A1B2C3D4E5F6"

LOGIN_RESPONSE = {"isAuthenticated": True, "token": "test-token", "passwordChanged": True}

SYSINFO_RESPONSE = {
    "sysInfo": {
        "serial": SERIAL,
        "hostname": "hb-rf-eth-test",
        "currentVersion": "2.4.0",
        "boardRevision": "REV 1.10 (PUB)",
        "uptimeSeconds": 1234,
        "cpuUsage": 12.5,
        "memoryUsage": 45.3,
        "ethernetConnected": True,
        "ethernetSpeed": 100,
        "rawUartRemoteAddress": "192.168.1.50:2001",
        "radioModuleType": "RPI-RF-MOD",
    }
}

UPDATE_STATUS_RESPONSE = {
    "state": "idle",
    "everChecked": True,
    "channel": "stable",
    "runningFirmware": "2.4.0",
    "runningWebui": "1.0.0",
    "latestFirmware": "2.4.1",
    "latestWebui": "1.0.0",
    "firmwareUpdateAvailable": True,
    "webuiUpdateAvailable": False,
    "notesUrl": "https://example.com/notes",
    "install": {
        "state": "idle",
        "target": "firmware",
        "progress": 0,
        "version": "",
        "error": "",
    },
}

BACKUP_RESPONSE = {"serial": SERIAL, "settings": {"hostname": "hb-rf-eth-test"}}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading custom_components/hb_rf_eth from the repo checkout."""
    yield


def mock_device_api(aioclient_mock) -> None:
    """Register the endpoints a configured gateway answers."""
    aioclient_mock.post(
        f"http://{HOST}/login.json", json=LOGIN_RESPONSE
    )
    aioclient_mock.get(f"http://{HOST}/sysinfo.json", json=SYSINFO_RESPONSE)
    aioclient_mock.get(f"http://{HOST}/api/update/status", json=UPDATE_STATUS_RESPONSE)


def mock_update_status(aioclient_mock, **install) -> None:
    """Override the install block of /api/update/status."""
    payload = {
        **UPDATE_STATUS_RESPONSE,
        "install": {**UPDATE_STATUS_RESPONSE["install"], **install},
    }
    # The mocker matches the FIRST registration for a URL - never register
    # the status topic twice. Rebuild the whole device mock instead.
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"http://{HOST}/login.json", json=LOGIN_RESPONSE)
    aioclient_mock.get(f"http://{HOST}/sysinfo.json", json=SYSINFO_RESPONSE)
    aioclient_mock.get(f"http://{HOST}/api/update/status", json=payload)


@pytest.fixture
def config_entry(hass, aioclient_mock):
    """A configured gateway with a healthy API mock."""
    from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_device_api(aioclient_mock)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="hb-rf-eth-test",
        data={CONF_HOST: HOST, CONF_USERNAME: "admin", CONF_PASSWORD: "pw"},
        unique_id=SERIAL,
    )
    entry.add_to_hass(hass)
    assert entry.state is not None
    return entry
