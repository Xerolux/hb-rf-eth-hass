"""Config flow: connect to one HB-RF-ETH gateway."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
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
        password or data[CONF_PASSWORD],
        session=async_get_clientsession(hass),
    )


class HbRfEthConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            client = _make_client(self.hass, user_input)
            try:
                await client.async_login()
                sysinfo = await client.async_sysinfo()
            except HbRfEthAuthError:
                errors["base"] = "invalid_auth"
            except HbRfEthApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    sysinfo.get("serial") or user_input[CONF_HOST]
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=sysinfo.get("hostname", user_input[CONF_HOST]),
                    data=user_input,
                )
            finally:
                await client.close()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
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
                await client.async_login()
                sysinfo = await client.async_sysinfo()
            except HbRfEthAuthError:
                errors["base"] = "invalid_auth"
            except HbRfEthApiError:
                errors["base"] = "cannot_connect"
            else:
                data = {**reauth_entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
                # Keep the title in sync with a possibly renamed device.
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
