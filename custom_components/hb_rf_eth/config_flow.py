"""Config flow: manual setup, zeroconf discovery and reconfiguration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HbRfEthApiError, HbRfEthAuthError, HbRfEthClient
from .const import DEFAULT_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): str,
    }
)


def _make_client(hass, data: dict[str, Any], password: str | None = None) -> HbRfEthClient:
    return HbRfEthClient(
        data[CONF_HOST],
        data.get(CONF_USERNAME, DEFAULT_USERNAME),
        data[CONF_PASSWORD] if password is None else password,
        session=async_get_clientsession(hass),
    )


async def _probe(client: HbRfEthClient) -> dict[str, Any]:
    """Login + sysinfo; raises HbRfEthAuthError / HbRfEthApiError."""
    await client.async_login()
    return await client.async_sysinfo()


class HbRfEthConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for one HB-RF-ETH gateway."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_host: str | None = None
        self._discovered_serial: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            client = _make_client(self.hass, user_input)
            try:
                sysinfo = await _probe(client)
            except HbRfEthAuthError:
                errors["base"] = "invalid_auth"
            except HbRfEthApiError:
                errors["base"] = "cannot_connect"
            else:
                serial = sysinfo.get("serial") or user_input[CONF_HOST]
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=sysinfo.get("hostname", user_input[CONF_HOST]),
                    data=user_input,
                )
            finally:
                await client.close()

        schema = STEP_USER_SCHEMA
        if self._discovered_host:
            schema = self._build_discovered_schema()
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    def _build_discovered_schema(self) -> vol.Schema:
        """Prefill host (and serial-derived hint) after zeroconf discovery."""
        return vol.Schema(
            {
                vol.Required(CONF_HOST, default=self._discovered_host): str,
                vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

    async def async_step_zeroconf(self, discovery_info):
        """Automatic discovery via the firmware's _hb-rf-eth._tcp service."""
        host: str = discovery_info.host or discovery_info.hostname.rstrip(".")
        properties: dict[str, Any] = discovery_info.properties or {}
        serial = str(properties.get("serial") or "").strip()

        if serial:
            await self.async_set_unique_id(serial)
            self._abort_if_unique_id_configured()
        self._discovered_host = host
        self._discovered_serial = serial
        self.context["title_placeholders"] = {
            "host": host,
            "serial": serial or "unknown",
            "version": str(properties.get("version") or ""),
        }
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ):
        """Ask only for credentials after the gateway was discovered."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                CONF_HOST: self._discovered_host,
                CONF_USERNAME: user_input.get(CONF_USERNAME, DEFAULT_USERNAME),
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            client = _make_client(self.hass, data)
            try:
                sysinfo = await _probe(client)
            except HbRfEthAuthError:
                errors["base"] = "invalid_auth"
            except HbRfEthApiError:
                errors["base"] = "cannot_connect"
            else:
                serial = sysinfo.get("serial") or self._discovered_serial
                if serial:
                    await self.async_set_unique_id(serial)
                    self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=sysinfo.get("hostname", self._discovered_host),
                    data=data,
                )
            finally:
                await client.close()

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            description_placeholders={
                "host": self._discovered_host or "?",
                "serial": self._discovered_serial or "?",
            },
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Reconfigure an existing entry: host / user / password."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()
        if user_input is not None:
            data = {**reconfigure_entry.data, **user_input}
            client = _make_client(self.hass, data)
            try:
                sysinfo = await _probe(client)
            except HbRfEthAuthError:
                errors["base"] = "invalid_auth"
            except HbRfEthApiError:
                errors["base"] = "cannot_connect"
            else:
                serial = sysinfo.get("serial")
                if serial:
                    await self.async_set_unique_id(serial)
                    # Abort only when a DIFFERENT entry claims this gateway;
                    # the entry being reconfigured obviously may keep it.
                    for existing in self._async_current_entries():
                        if (
                            existing.unique_id == serial
                            and existing.entry_id != reconfigure_entry.entry_id
                        ):
                            raise self.AbortFlow("already_configured")
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data=data,
                    title=sysinfo.get("hostname", data[CONF_HOST]),
                )
            finally:
                await client.close()

        current = reconfigure_entry.data
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=current.get(CONF_HOST, "")): str,
                    vol.Required(
                        CONF_USERNAME, default=current.get(CONF_USERNAME, DEFAULT_USERNAME)
                    ): str,
                    vol.Required(CONF_PASSWORD, default=current.get(CONF_PASSWORD, "")): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        """Password changed on the device: ask for the new one."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ):
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            client = _make_client(self.hass, reauth_entry.data, user_input[CONF_PASSWORD])
            try:
                sysinfo = await _probe(client)
            except HbRfEthAuthError:
                errors["base"] = "invalid_auth"
            except HbRfEthApiError:
                errors["base"] = "cannot_connect"
            else:
                data = {**reauth_entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
                title = sysinfo.get("hostname", reauth_entry.title)
                return self.async_update_reload_and_abort(reauth_entry, data=data, title=title)
            finally:
                await client.close()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            description_placeholders={"host": reauth_entry.data[CONF_HOST]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HbRfEthOptionsFlowHandler()


class HbRfEthOptionsFlowHandler(config_entries.OptionsFlow):
    """Options: services-only coexistence mode and poll interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            interval = user_input["poll_interval"]
            if not 10 <= interval <= 300:
                errors["base"] = "invalid_interval"
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        from .const import (
            CONF_POLL_INTERVAL,
            CONF_SERVICES_ONLY,
            DEFAULT_OPTIONS,
            DEFAULT_POLL_INTERVAL_SECONDS,
        )

        current = {**DEFAULT_OPTIONS, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SERVICES_ONLY,
                        default=current[CONF_SERVICES_ONLY],
                    ): bool,
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=current.get(
                            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL_SECONDS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                }
            ),
            errors=errors,
        )
