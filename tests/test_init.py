"""Setup, entities and the domain services (backup/restore/log/restart)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr

from custom_components.hb_rf_eth.const import DOMAIN

from .conftest import (
    BACKUP_RESPONSE,
    HOST,
    LOGIN_RESPONSE,
    SERIAL,
    SYSINFO_RESPONSE,
)

pytestmark = pytest.mark.usefixtures("config_entry")


async def test_setup_creates_entities(hass, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    expected = {
        ("update", f"{HOST}-firmware-update"),
        ("update", f"{HOST}-webui-update"),
    }
    for platform, unique_id in expected:
        assert registry.async_get_entity_id(platform, DOMAIN, unique_id)
    assert registry.async_get_entity_id("binary_sensor", DOMAIN, f"{HOST}-ethernet_connected")
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{HOST}-cpuUsage")


async def test_unload(hass, config_entry):
    from homeassistant.config_entries import ConfigEntryState

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


def _device_id(hass, entry) -> str:
    registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(registry, entry.entry_id)
    assert devices, "gateway device not found"
    return devices[0].id


async def test_backup_service_writes_file(hass, aioclient_mock, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.get(f"http://{HOST}/api/backup", json=BACKUP_RESPONSE)
    response = await hass.services.async_call(
        DOMAIN,
        "backup",
        {"device_id": _device_id(hass, config_entry)},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    filename = response["filename"]
    assert filename.startswith(SERIAL) and filename.endswith(".json")
    path = Path(hass.config.path("hb_rf_eth_backups")) / filename
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored == BACKUP_RESPONSE
    # The backup contains credentials: it must not be world/group readable.
    assert path.stat().st_mode & 0o077 == 0


async def test_restore_service_roundtrip(hass, aioclient_mock, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.get(f"http://{HOST}/api/backup", json=BACKUP_RESPONSE)
    response = await hass.services.async_call(
        DOMAIN,
        "backup",
        {"device_id": _device_id(hass, config_entry)},
        blocking=True,
        return_response=True,
    )

    aioclient_mock.post(f"http://{HOST}/api/restore", json={"success": True})
    result = await hass.services.async_call(
        DOMAIN,
        "restore",
        {"device_id": _device_id(hass, config_entry), "filename": response["filename"]},
        blocking=True,
        return_response=True,
    )
    assert result == {"filename": response["filename"], "restored": True}


async def test_restore_rejects_path_traversal(hass, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "restore",
            {"device_id": _device_id(hass, config_entry), "filename": "../../etc/passwd.json"},
            blocking=True,
        )


async def test_restore_rejects_missing_file(hass, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "restore",
            {"device_id": _device_id(hass, config_entry), "filename": "nope.json"},
            blocking=True,
        )


async def test_download_log_service(hass, aioclient_mock, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.get(
        f"http://{HOST}/api/log/download", text="Tür geöffnet"
    )
    response = await hass.services.async_call(
        DOMAIN,
        "download_log",
        {"device_id": _device_id(hass, config_entry)},
        blocking=True,
        return_response=True,
    )
    assert response["bytes"] == len("Tür geöffnet".encode())
    path = Path(hass.config.path("hb_rf_eth_backups")) / response["filename"]
    assert path.read_text(encoding="utf-8") == "Tür geöffnet"


async def test_restart_service(hass, aioclient_mock, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.post(f"http://{HOST}/api/restart", json={"success": True})
    await hass.services.async_call(
        DOMAIN, "restart", {"device_id": _device_id(hass, config_entry)}, blocking=True
    )


async def test_update_check_service(hass, aioclient_mock, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.post(f"http://{HOST}/api/update/check", json={"outcome": "accepted"})
    response = await hass.services.async_call(
        DOMAIN,
        "update_check",
        {"device_id": _device_id(hass, config_entry), "channel": "beta"},
        blocking=True,
        return_response=True,
    )
    assert response == {"accepted": True, "channel": "beta"}


async def test_service_requires_target_with_multiple_gateways(
    hass, aioclient_mock, config_entry
):
    """The target-optional fallback only applies to a single gateway."""
    from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Second, fully working gateway on another address.
    aioclient_mock.post("http://10.0.0.43/login.json", json=LOGIN_RESPONSE)
    aioclient_mock.get("http://10.0.0.43/sysinfo.json", json=SYSINFO_RESPONSE)
    aioclient_mock.get(
        "http://10.0.0.43/api/update/status", json={"state": "idle"}
    )
    entry2 = MockConfigEntry(
        domain=DOMAIN,
        title="second",
        data={CONF_HOST: "10.0.0.43", CONF_USERNAME: "admin", CONF_PASSWORD: "pw"},
        unique_id="SECOND8SERIAL",
    )
    entry2.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    for target in ({}, {"device_id": [_device_id(hass, config_entry), _device_id(hass, entry2)]}):
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(DOMAIN, "restart", target, blocking=True)


async def test_service_target_optional_with_single_gateway(
    hass, aioclient_mock, config_entry
):
    """Services-only mode has no entities to target: one gateway = no target."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.post(f"http://{HOST}/api/update/check", json={"outcome": "accepted"})
    response = await hass.services.async_call(
        DOMAIN,
        "update_check",
        {},
        blocking=True,
        return_response=True,
    )
    assert response == {"accepted": True, "channel": "configured"}


async def test_invalid_explicit_target_does_not_restart_single_gateway(
    hass, aioclient_mock, config_entry
):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    aioclient_mock.post(f"http://{HOST}/api/restart", json={"success": True})

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "restart", {"device_id": "no-such-device"}, blocking=True
        )

    assert not any(str(call[1]).endswith("/api/restart") for call in aioclient_mock.mock_calls)
