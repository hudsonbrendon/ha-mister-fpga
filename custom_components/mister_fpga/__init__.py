"""The MiSTer FPGA integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from mister_fpga import MisterClient, MisterRA

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SSH_ENABLED,
    CONF_SSH_PASSWORD,
    CONF_SSH_PORT,
    CONF_SSH_USERNAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSH_PORT,
    DEFAULT_SSH_USERNAME,
    DOMAIN,
)
from .coordinator import MisterDataUpdateCoordinator
from .websocket import MisterWebSocket

# Platforms are appended incrementally as each platform module is implemented
# (binary_sensor, sensor, media_player, button, select, switch, image).
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.IMAGE,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
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
SERVICE_RUN_SCRIPT_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required("filename"): cv.string}
)
SERVICE_LAUNCH_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required("path"): cv.string}
)
SERVICE_LAUNCH_TOKEN_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required("data"): cv.string}
)
SERVICE_SET_INI_VALUE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTRY_ID): cv.string,
        vol.Required("key"): cv.string,
        vol.Required("value"): cv.string,
    }
)
SERVICE_SET_WALLPAPER_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required("filename"): cv.string}
)
SERVICE_BACKGROUND_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTRY_ID): cv.string,
        vol.Required("mode"): vol.All(int, vol.Range(min=0, max=7)),
    }
)
SERVICE_KEYBOARD_RAW_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required("code"): int}
)
SERVICE_CREATE_SHORTCUT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTRY_ID): cv.string,
        vol.Required("game_path"): cv.string,
        vol.Required("folder"): cv.string,
        vol.Required("name"): cv.string,
    }
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

    async def _run_script(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_launch_script(call.data["filename"])

    async def _launch(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_launch_path(call.data["path"])
        await coord.async_request_refresh()

    async def _launch_token(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_launch_token(call.data["data"])
        await coord.async_request_refresh()

    async def _set_ini_value(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_set_ini_values(
            coord.active_ini_id, {call.data["key"]: call.data["value"]}
        )

    async def _set_wallpaper(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_set_wallpaper(call.data["filename"])
        await coord.async_request_refresh()

    async def _set_background_mode(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_set_background_mode(call.data["mode"])
        await coord.async_request_refresh()

    async def _send_keyboard_raw(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_send_keyboard_raw(call.data["code"])

    async def _create_shortcut(call: ServiceCall) -> dict:
        coord = _coordinator(call)
        return await coord.client.async_create_shortcut(
            call.data["game_path"], call.data["folder"], call.data["name"]
        )

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
    hass.services.async_register(
        DOMAIN, "run_script", _run_script, SERVICE_RUN_SCRIPT_SCHEMA
    )
    hass.services.async_register(DOMAIN, "launch", _launch, SERVICE_LAUNCH_SCHEMA)
    hass.services.async_register(
        DOMAIN, "launch_token", _launch_token, SERVICE_LAUNCH_TOKEN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "set_ini_value", _set_ini_value, SERVICE_SET_INI_VALUE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "set_wallpaper", _set_wallpaper, SERVICE_SET_WALLPAPER_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        "set_background_mode",
        _set_background_mode,
        SERVICE_BACKGROUND_MODE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, "send_keyboard_raw", _send_keyboard_raw, SERVICE_KEYBOARD_RAW_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        "create_shortcut",
        _create_shortcut,
        SERVICE_CREATE_SHORTCUT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MiSTer FPGA from a config entry."""
    session = async_get_clientsession(hass)
    client = MisterClient(
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, DEFAULT_PORT),
        session=session,
    )
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = MisterDataUpdateCoordinator(hass, client, scan_interval)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_refresh_systems()
    await coordinator.async_refresh_scripts()

    if entry.options.get(CONF_SSH_ENABLED) and entry.options.get(CONF_SSH_PASSWORD):
        from mister_fpga import MisterSSH
        coordinator.ssh = MisterSSH(
            entry.data[CONF_HOST],
            entry.options.get(CONF_SSH_PORT, DEFAULT_SSH_PORT),
            entry.options.get(CONF_SSH_USERNAME, DEFAULT_SSH_USERNAME),
            entry.options[CONF_SSH_PASSWORD],
        )
        coordinator.ra = MisterRA(coordinator.ssh)
        await coordinator.async_refresh_ssh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _register_services(hass)
    websocket = MisterWebSocket(hass, coordinator)
    websocket.start()
    coordinator.websocket = websocket
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator is not None and getattr(coordinator, "websocket", None) is not None:
        await coordinator.websocket.stop()
    if getattr(coordinator, "ssh", None) is not None:
        await coordinator.ssh.async_close()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
