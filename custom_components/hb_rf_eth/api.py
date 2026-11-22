"""Small async REST client for the HB-RF-ETH-ng firmware.

The device authenticates via POST /login.json and expects subsequent requests
to carry ``Authorization: Token <token>`` (not Bearer). Tokens survive reboots.
"""

from __future__ import annotations

from typing import Any

import aiohttp

# Update installation is asynchronous on the device: POST /api/update/install
# returns immediately and progress arrives via GET /api/update/status
# ("install" block). The same applies to a manual update search.
LOGIN_TIMEOUT_SECONDS = 10
REQUEST_TIMEOUT_SECONDS = 30
# A full settings backup (including certificates) can reach several dozen KiB
# on slow links; give the transfer room without hanging the service call.
TRANSFER_TIMEOUT_SECONDS = 120


class HbRfEthApiError(Exception):
    """Base error."""


class HbRfEthAuthError(HbRfEthApiError):
    """Login failed (401)."""


class HbRfEthConnectionError(HbRfEthApiError):
    """Network-level failure."""


class HbRfEthClient:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._host = host.rstrip("/")
        self._username = username
        self._password = password
        self._base = f"http://{self._host}"
        self._token: str | None = None
        # An external session (the HA shared session) is used but never
        # owned: close() leaves it open. Tests inject the mocked session.
        self._session: aiohttp.ClientSession | None = session
        self._owns_session = session is None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            )
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
        self._session = None if not self._owns_session else self._session

    async def async_login(self) -> str:
        """Authenticate and cache the token."""
        session = await self._ensure_session()
        try:
            async with session.post(
                f"{self._base}/login.json",
                json={"username": self._username, "password": self._password},
                timeout=aiohttp.ClientTimeout(total=LOGIN_TIMEOUT_SECONDS),
            ) as resp:
                if resp.status == 401:
                    raise HbRfEthAuthError("invalid credentials")
                resp.raise_for_status()
                data = await self._json_object(resp)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise HbRfEthConnectionError(str(err)) from err
        token = data.get("token")
        if not isinstance(token, str) or not token:
            raise HbRfEthAuthError("device did not return a token")
        self._token = token
        return token

    @staticmethod
    async def _json_object(response: aiohttp.ClientResponse) -> dict[str, Any]:
        """Decode device JSON regardless of its HTTP content type."""
        try:
            data = await response.json(content_type=None)
        except ValueError as err:
            raise HbRfEthApiError("device returned invalid JSON") from err
        if not isinstance(data, dict):
            raise HbRfEthApiError("device did not return a JSON object")
        return data

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        json_response: bool = True,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
        _retried: bool = False,
    ) -> Any:
        token = self._token if self._token is not None else await self.async_login()
        session = await self._ensure_session()
        try:
            async with session.request(
                method,
                f"{self._base}{path}",
                json=payload,
                headers={"Authorization": f"Token {token}"},
                timeout=aiohttp.ClientTimeout(total=timeout_seconds),
            ) as resp:
                if resp.status != 401:
                    resp.raise_for_status()
                    if not json_response:
                        return await resp.text()
                    return await self._json_object(resp)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise HbRfEthConnectionError(str(err)) from err

        # Release the rejected response before opening another request.
        if self._token == token:
            self._token = None
        if _retried:
            raise HbRfEthAuthError("device rejected the refreshed token")
        return await self._request(
            method,
            path,
            payload=payload,
            json_response=json_response,
            timeout_seconds=timeout_seconds,
            _retried=True,
        )

    async def _get(self, path: str, **kwargs: Any) -> Any:
        return await self._request("GET", path, **kwargs)

    async def _post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return await self._request("POST", path, payload=payload or {})

    # --- Read paths -------------------------------------------------------

    async def async_sysinfo(self) -> dict[str, Any]:
        data = await self._get("/sysinfo.json")
        sysinfo = data.get("sysInfo")
        if not isinstance(sysinfo, dict):
            raise HbRfEthApiError("device did not return sysInfo")
        return sysinfo

    async def async_update_status(self) -> dict[str, Any]:
        return await self._get("/api/update/status")

    async def async_backup(self) -> dict[str, Any]:
        """Fetch the full settings backup (GET /api/backup).

        The response includes credentials and certificates in clear text -
        callers must treat the result as a secret and store it accordingly.
        """
        return await self._get(
            "/api/backup", json_response=True, timeout_seconds=TRANSFER_TIMEOUT_SECONDS
        )

    async def async_download_log(self) -> str:
        """Fetch the complete captured system log as plain text."""
        return await self._get(
            "/api/log/download",
            json_response=False,
            timeout_seconds=TRANSFER_TIMEOUT_SECONDS,
        )

    # --- Write paths ------------------------------------------------------

    async def async_restore(self, backup: dict[str, Any]) -> Any:
        return await self._post("/api/restore", backup)

    async def async_restart(self) -> Any:
        return await self._post("/api/restart")

    async def async_update_check(self, channel: str | None = None) -> Any:
        payload: dict[str, Any] = {}
        if channel in ("stable", "beta"):
            payload["channel"] = channel
        return await self._post("/api/update/check", payload)

    async def async_install(self, target: str) -> Any:
        """Start the device-side online installation ("firmware"/"webui")."""
        if target not in ("firmware", "webui"):
            raise HbRfEthApiError(f"invalid install target: {target}")
        return await self._post("/api/update/install", {"target": target})

    async def async_install_firmware(self) -> Any:
        return await self.async_install("firmware")

    async def async_install_webui(self) -> Any:
        return await self.async_install("webui")
