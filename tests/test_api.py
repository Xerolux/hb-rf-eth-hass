"""API client: login, token retry, backup/restore/log and install calls."""

from __future__ import annotations

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.hb_rf_eth.api import (
    HbRfEthApiError,
    HbRfEthAuthError,
    HbRfEthClient,
)

from .conftest import BACKUP_RESPONSE, HOST, LOGIN_RESPONSE, SYSINFO_RESPONSE

HOST_URL = f"http://{HOST}"


@pytest.fixture
def client(hass, aioclient_mock):
    """Client on the mocked HA session (external session: never closed)."""
    return HbRfEthClient(
        HOST, "admin", "pw", session=async_get_clientsession(hass)
    )


async def test_login_caches_token(client, aioclient_mock):
    aioclient_mock.post(f"{HOST_URL}/login.json", json=LOGIN_RESPONSE)
    aioclient_mock.get(
        f"{HOST_URL}/sysinfo.json",
        json=SYSINFO_RESPONSE,
        headers={"Authorization": "Token test-token"},
    )
    token = await client.async_login()
    assert token == "test-token"
    sysinfo = await client.async_sysinfo()
    assert sysinfo["serial"] == "A1B2C3D4E5F6"
    await client.close()


async def test_login_invalid_credentials(client, aioclient_mock):
    aioclient_mock.post(f"{HOST_URL}/login.json", status=401)
    with pytest.raises(HbRfEthAuthError):
        await client.async_login()
    await client.close()


async def test_relogin_after_expired_token(client, aioclient_mock):
    """A stale token triggers relogin; a second 401 surfaces as error."""
    aioclient_mock.post(f"{HOST_URL}/login.json", json=LOGIN_RESPONSE)
    aioclient_mock.get(f"{HOST_URL}/sysinfo.json", status=401)
    client._token = "stale-token"

    from custom_components.hb_rf_eth.api import HbRfEthConnectionError

    with pytest.raises(HbRfEthConnectionError):
        await client.async_sysinfo()

    # Exactly one relogin attempt after the rejected token (zero logins
    # would mean the stale token was never challenged and retried).
    logins = [c for c in aioclient_mock.mock_calls if str(c[1]).endswith("/login.json")]
    assert len(logins) == 1
    await client.close()


async def test_backup_returns_document(client, aioclient_mock):
    aioclient_mock.post(f"{HOST_URL}/login.json", json=LOGIN_RESPONSE)
    aioclient_mock.get(f"{HOST_URL}/api/backup", json=BACKUP_RESPONSE)
    backup = await client.async_backup()
    assert backup["serial"] == "A1B2C3D4E5F6"
    await client.close()


async def test_restore_posts_document(client, aioclient_mock):
    aioclient_mock.post(f"{HOST_URL}/login.json", json=LOGIN_RESPONSE)
    aioclient_mock.post(f"{HOST_URL}/api/restore", json={"success": True})
    result = await client.async_restore(BACKUP_RESPONSE)
    assert result == {"success": True}
    assert aioclient_mock.mock_calls[1][2] == BACKUP_RESPONSE
    await client.close()


async def test_download_log_returns_text(client, aioclient_mock):
    aioclient_mock.post(f"{HOST_URL}/login.json", json=LOGIN_RESPONSE)
    aioclient_mock.get(
        f"{HOST_URL}/api/log/download", text="line1\nline2\n"
    )
    log = await client.async_download_log()
    assert log == "line1\nline2\n"
    await client.close()


async def test_install_rejects_unknown_target(client):
    with pytest.raises(HbRfEthApiError):
        await client.async_install("bootloader")
    await client.close()


async def test_install_posts_target(client, aioclient_mock):
    aioclient_mock.post(f"{HOST_URL}/login.json", json=LOGIN_RESPONSE)
    aioclient_mock.post(f"{HOST_URL}/api/update/install", json={"accepted": True})
    await client.async_install("webui")
    assert aioclient_mock.mock_calls[1][2] == {"target": "webui"}
    await client.close()


async def test_update_check_defaults_to_configured_channel(client, aioclient_mock):
    aioclient_mock.post(f"{HOST_URL}/login.json", json=LOGIN_RESPONSE)
    aioclient_mock.post(f"{HOST_URL}/api/update/check", json={"outcome": "accepted"})
    await client.async_update_check(None)
    # mock_calls: [0] login, [1] check without explicit channel.
    assert aioclient_mock.mock_calls[1][2] == {}
    await client.async_update_check("beta")
    # Token is cached: no second login, [2] is the beta check.
    assert aioclient_mock.mock_calls[2][2] == {"channel": "beta"}
    await client.close()


async def test_restart(client, aioclient_mock):
    aioclient_mock.post(f"{HOST_URL}/login.json", json=LOGIN_RESPONSE)
    aioclient_mock.post(f"{HOST_URL}/api/restart", json={"success": True})
    await client.async_restart()
    await client.close()
