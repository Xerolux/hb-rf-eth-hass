"""Small async REST client for the HB-RF-ETH-ng firmware.

The device authenticates via POST /login.json and expects subsequent requests
to carry ``Authorization: Token <token>`` (not Bearer). Tokens survive reboots.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class HbRfEthApiError(Exception):
    """Base error."""


class HbRfEthAuthError(HbRfEthApiError):
    """Login failed (401)."""


class HbRfEthConnectionError(HbRfEthApiError):
    """Network-level failure."""


class HbRfEthClient:
    def __init__(self, host: str, username: str, password: str) -> None:
        self._host = host.rstrip("/")
        self._username = username
        self._password = password
        self._base = f"http://{self._host}"
        self._token: str | None = None
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def async_login(self) -> str:
        """Authenticate and cache the token."""
        session = await self._ensure_session()
        try:
            async with session.post(
                f"{self._base}/login.json",
                json={"username": self._username, "password": self._password},
            ) as resp:
                if resp.status == 401:
                    raise HbRfEthAuthError("invalid credentials")
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientError as err:
            raise HbRfEthConnectionError(str(err)) from err
        token = data.get("token")
        if not token:
            raise HbRfEthAuthError("device did not return a token")
        self._token = token
        return token

    async def _get(self, path: str) -> Any:
        if self._token is None:
            await self.async_login()
        session = await self._ensure_session()
        try:
            async with session.get(
                f"{self._base}{path}",
                headers={"Authorization": f"Token {self._token}"},
            ) as resp:
                if resp.status == 401:
                    # Token rejected (device restarted with a new one): retry once.
                    self._token = None
                    await self.async_login()
                    return await self._get(path)
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise HbRfEthConnectionError(str(err)) from err

    async def _post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        if self._token is None:
            await self.async_login()
        session = await self._ensure_session()
        try:
            async with session.post(
                f"{self._base}{path}",
                json=payload or {},
                headers={"Authorization": f"Token {self._token}"},
            ) as resp:
                if resp.status == 401:
                    self._token = None
                    await self.async_login()
                    return await self._post(path, payload)
                resp.raise_for_status()
                if resp.content_type == "application/json":
                    return await resp.json()
                return None
        except aiohttp.ClientError as err:
            raise HbRfEthConnectionError(str(err)) from err

    async def async_sysinfo(self) -> dict[str, Any]:
        data = await self._get("/sysinfo.json")
        return data.get("sysInfo", {})

    async def async_update_status(self) -> dict[str, Any]:
        return await self._get("/api/update/status")

    async def async_install_firmware(self) -> Any:
        return await self._post("/api/update/install", {"target": "firmware"})
