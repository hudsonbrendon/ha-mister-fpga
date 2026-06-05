"""Config flow for the MiSTer FPGA integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from mister_fpga import MisterClient, MisterConnectionError, MisterRAWeb
from mister_fpga.ra_web import MisterRAWebError

from .const import (
    CONF_RA_API_KEY,
    CONF_RA_CLOUD_INTERVAL,
    CONF_RA_USERNAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_RA_CLOUD_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_RA_CLOUD_INTERVAL,
    MAX_SCAN_INTERVAL,
    MIN_RA_CLOUD_INTERVAL,
    MIN_SCAN_INTERVAL,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class MisterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the MiSTer FPGA config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = MisterClient(
                user_input[CONF_HOST], user_input[CONF_PORT], session=session
            )
            try:
                await client.async_get_status()
            except MisterConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MisterOptionsFlow:
        return MisterOptionsFlow(config_entry)


class MisterOptionsFlow(OptionsFlow):
    """Handle MiSTer FPGA options (scan interval)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        from .const import (
            CONF_SSH_ENABLED,
            CONF_SSH_PASSWORD,
            CONF_SSH_PORT,
            CONF_SSH_USERNAME,
            DEFAULT_SSH_PORT,
            DEFAULT_SSH_USERNAME,
        )

        errors: dict[str, str] = {}
        if user_input is not None:
            ra_user = user_input.get(CONF_RA_USERNAME)
            ra_key = user_input.get(CONF_RA_API_KEY)
            if ra_user and ra_key:
                session = async_get_clientsession(self.hass)
                web = MisterRAWeb(ra_user, ra_key, session=session)
                try:
                    await web.async_validate()
                except MisterRAWebError:
                    errors["base"] = "invalid_auth"
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        opts = self._entry.options
        current = opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                    int, vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                ),
                vol.Optional(
                    CONF_SSH_ENABLED, default=opts.get(CONF_SSH_ENABLED, False)
                ): bool,
                vol.Optional(
                    CONF_SSH_USERNAME,
                    default=opts.get(CONF_SSH_USERNAME, DEFAULT_SSH_USERNAME),
                ): str,
                vol.Optional(
                    CONF_SSH_PASSWORD, default=opts.get(CONF_SSH_PASSWORD, "")
                ): str,
                vol.Optional(
                    CONF_SSH_PORT, default=opts.get(CONF_SSH_PORT, DEFAULT_SSH_PORT)
                ): int,
                vol.Optional(
                    CONF_RA_USERNAME, default=opts.get(CONF_RA_USERNAME, "")
                ): str,
                vol.Optional(
                    CONF_RA_API_KEY, default=opts.get(CONF_RA_API_KEY, "")
                ): str,
                vol.Optional(
                    CONF_RA_CLOUD_INTERVAL,
                    default=opts.get(
                        CONF_RA_CLOUD_INTERVAL, DEFAULT_RA_CLOUD_INTERVAL
                    ),
                ): vol.All(
                    int,
                    vol.Range(min=MIN_RA_CLOUD_INTERVAL, max=MAX_RA_CLOUD_INTERVAL),
                ),
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
