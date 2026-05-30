"""The MiSTer FPGA integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MisterClient
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import MisterDataUpdateCoordinator

# Platforms are appended incrementally as each platform module is implemented
# (binary_sensor, sensor, media_player, button, select, switch, image).
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.MEDIA_PLAYER,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.IMAGE,
]

ATTR_ENTRY_ID = "entry_id"

SERVICE_LAUNCH_GAME_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required("path"): cv.string}
)
SERVICE_LAUNCH_SYSTEM_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required("system_id"): cv.string}
)
SERVICE_SEARCH_GAMES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTRY_ID): cv.string,
        vol.Required("query"): cv.string,
        vol.Optional("system", default="all"): cv.string,
    }
)
SERVICE_SEND_KEYBOARD_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required("key"): cv.string}
)
SERVICE_TAKE_SCREENSHOT_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTRY_ID): cv.string}
)


def _register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "launch_game"):
        return

    def _coordinator(call: ServiceCall):
        entry_id = call.data[ATTR_ENTRY_ID]
        if entry_id not in hass.data.get(DOMAIN, {}):
            raise ServiceValidationError(
                f"MiSTer config entry '{entry_id}' not found"
            )
        return hass.data[DOMAIN][entry_id]

    async def _launch_game(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_launch_game(call.data["path"])
        await coord.async_request_refresh()

    async def _launch_system(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_launch_system(call.data["system_id"])
        await coord.async_request_refresh()

    async def _search_games(call: ServiceCall) -> dict:
        coord = _coordinator(call)
        return await coord.client.async_search_games(
            call.data["query"], call.data.get("system", "all")
        )

    async def _send_keyboard(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_send_keyboard(call.data["key"])

    async def _take_screenshot(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_take_screenshot()

    hass.services.async_register(
        DOMAIN, "launch_game", _launch_game, SERVICE_LAUNCH_GAME_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "launch_system", _launch_system, SERVICE_LAUNCH_SYSTEM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        "search_games",
        _search_games,
        SERVICE_SEARCH_GAMES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, "send_keyboard", _send_keyboard, SERVICE_SEND_KEYBOARD_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "take_screenshot", _take_screenshot, SERVICE_TAKE_SCREENSHOT_SCHEMA
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MiSTer FPGA from a config entry."""
    session = async_get_clientsession(hass)
    client = MisterClient(
        session,
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, DEFAULT_PORT),
    )
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = MisterDataUpdateCoordinator(hass, client, scan_interval)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_refresh_systems()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
