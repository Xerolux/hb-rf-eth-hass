"""Device services: backup, restore, log download, restart, update search.

These cover the operations MQTT cannot transport sensibly (full settings
backup incl. certificates, log download) plus the everyday actions for
installations that run the integration without MQTT.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.service import async_extract_config_entry_ids

from .api import HbRfEthApiError, HbRfEthClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

BACKUP_DIR = "hb_rf_eth_backups"

SERVICE_BACKUP = "backup"
SERVICE_RESTORE = "restore"
SERVICE_DOWNLOAD_LOG = "download_log"
SERVICE_RESTART = "restart"
SERVICE_UPDATE_CHECK = "update_check"

RESTORE_SCHEMA = vol.Schema(
    {
        vol.Required("filename"): str,
    },
    # Targeting keys (device_id/entity_id) ride along in service_data.
    extra=vol.ALLOW_EXTRA,
)
UPDATE_CHECK_SCHEMA = vol.Schema(
    {
        vol.Optional("channel", default=None): vol.In(["stable", "beta"]),
    },
    extra=vol.ALLOW_EXTRA,
)


def _backup_dir(hass: HomeAssistant) -> Path:
    path = Path(hass.config.path(BACKUP_DIR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_backup_name(filename: str) -> Path:
    """Reject path traversal; only plain names inside the backup folder."""
    name = os.path.basename(filename)
    if not name or name != filename or not name.endswith(".json"):
        raise ServiceValidationError(
            "filename must be a plain .json file name inside the backup folder",
            translation_domain=DOMAIN,
            translation_key="invalid_filename",
        )
    return Path(name)


async def _client_from_call(
    hass: HomeAssistant, call: ServiceCall
) -> tuple[ConfigEntry, HbRfEthClient]:
    entry_ids = [
        entry_id
        for entry_id in await async_extract_config_entry_ids(call)
        if (data := hass.data.get(DOMAIN, {}).get(entry_id)) and "client" in data
    ]
    if not entry_ids:
        raise ServiceValidationError(
            "no HB-RF-ETH device matched the service target",
            translation_domain=DOMAIN,
            translation_key="no_target",
        )
    entry = hass.config_entries.async_get_entry(entry_ids[0])
    assert entry is not None
    return entry, hass.data[DOMAIN][entry.entry_id]["client"]


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register the domain services (idempotent across config entries)."""
    if hass.services.has_service(DOMAIN, SERVICE_BACKUP):
        return

    async def handle_backup(call: ServiceCall) -> ServiceResponse:
        entry, client = await _client_from_call(hass, call)
        try:
            backup = await client.async_backup()
        except HbRfEthApiError as err:
            raise ServiceValidationError(str(err)) from err
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        # The device backup JSON is flat and carries no serial; take it from
        # the coordinator's sysinfo (with the hostname as fallback).
        sysinfo = hass.data[DOMAIN][entry.entry_id]["coordinator"].data.get(
            "sysinfo", {}
        )
        serial = str(
            sysinfo.get("serial") or sysinfo.get("hostname") or "device"
        )
        target = _backup_dir(hass) / f"{serial}-{stamp}.json"
        await hass.async_add_executor_job(_write_json, target, backup)
        _LOGGER.info("Backup written to %s", target)
        return {"filename": target.name, "path": str(target)}

    async def handle_restore(call: ServiceCall) -> ServiceResponse:
        _entry, client = await _client_from_call(hass, call)
        name = _safe_backup_name(call.data["filename"])
        path = _backup_dir(hass) / name
        if not await hass.async_add_executor_job(path.is_file):
            raise ServiceValidationError(
                f"backup file not found: {name}",
                translation_domain=DOMAIN,
                translation_key="file_not_found",
            )
        backup = json.loads(await hass.async_add_executor_job(path.read_text, "utf-8"))
        try:
            await client.async_restore(backup)
        except HbRfEthApiError as err:
            raise ServiceValidationError(str(err)) from err
        _LOGGER.info("Restored backup %s", name)
        return {"filename": name.name, "restored": True}

    async def handle_download_log(call: ServiceCall) -> ServiceResponse:
        entry, client = await _client_from_call(hass, call)
        try:
            log = await client.async_download_log()
        except HbRfEthApiError as err:
            raise ServiceValidationError(str(err)) from err
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        serial = entry.data.get("host", "device")
        target = _backup_dir(hass) / f"{serial}-log-{stamp}.txt"
        await hass.async_add_executor_job(_write_text, target, log)
        return {"filename": target.name, "path": str(target), "bytes": len(log)}

    async def handle_restart(call: ServiceCall) -> None:
        _entry, client = await _client_from_call(hass, call)
        try:
            await client.async_restart()
        except HbRfEthApiError as err:
            raise ServiceValidationError(str(err)) from err

    async def handle_update_check(call: ServiceCall) -> ServiceResponse:
        _entry, client = await _client_from_call(hass, call)
        channel = call.data.get("channel")
        try:
            await client.async_update_check(channel)
        except HbRfEthApiError as err:
            raise ServiceValidationError(str(err)) from err
        return {"accepted": True, "channel": channel or "configured"}

    hass.services.async_register(
        DOMAIN, SERVICE_BACKUP, handle_backup, supports_response=SupportsResponse.ONLY
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESTORE, handle_restore, supports_response=SupportsResponse.ONLY
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DOWNLOAD_LOG,
        handle_download_log,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, SERVICE_RESTART, handle_restart)
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_CHECK,
        handle_update_check,
        schema=UPDATE_CHECK_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


def _write_json(path: Path, data: Any) -> None:
    # The backup contains credentials and certificates: restrict to owner.
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.chmod(path, 0o600)


def _write_text(path: Path, data: str) -> None:
    path.write_text(data, encoding="utf-8")
    os.chmod(path, 0o600)
