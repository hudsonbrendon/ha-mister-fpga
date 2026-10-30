"""Actions for the MiSTer FPGA integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import (
    HomeAssistantError,
    ServiceValidationError,
    Unauthorized,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service
import voluptuous as vol

from mister_fpga import MisterGamepadError, MisterMainUnresponsiveError, MisterRAError

from .const import BACKGROUND_MODES, DOMAIN, GAMEPAD_ACTIONS, GAMEPAD_BUTTONS
from .coordinator import MisterDataUpdateCoordinator

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
        vol.Optional("page"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)
SERVICE_SEND_KEYBOARD_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required("key"): cv.string}
)
SERVICE_TAKE_SCREENSHOT_SCHEMA = vol.Schema({vol.Required(ATTR_ENTRY_ID): cv.string})
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
        vol.Required("mode"): vol.All(vol.Coerce(int), vol.In(BACKGROUND_MODES)),
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

SERVICE_DELETE_SCREENSHOT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTRY_ID): cv.string,
        vol.Required("core"): cv.string,
        vol.Required("filename"): cv.string,
    }
)
SERVICE_SEND_COMMAND_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required("command"): cv.string}
)
SERVICE_GAMEPAD_PRESS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTRY_ID): cv.string,
        vol.Required("button"): vol.In(GAMEPAD_BUTTONS),
        vol.Optional("action", default="tap"): vol.In(GAMEPAD_ACTIONS),
    }
)
SERVICE_SET_RA_DEBUG_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required("enabled"): cv.boolean}
)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the MiSTer FPGA actions (called once from async_setup)."""

    def _coordinator(call: ServiceCall) -> MisterDataUpdateCoordinator:
        entry_id = call.data[ATTR_ENTRY_ID]
        entry = hass.config_entries.async_get_entry(entry_id)
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
        ):
            raise ServiceValidationError(f"MiSTer config entry '{entry_id}' not found")
        return entry.runtime_data

    def _ssh(coord):
        if coord.ssh is None:
            raise ServiceValidationError("This action needs SSH enabled in options")
        return coord.ssh

    async def _launch_game(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_launch_game(call.data["path"])
        await coord.async_request_refresh_full()

    async def _launch_system(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_launch_system(call.data["system_id"])
        await coord.async_request_refresh_full()

    async def _search_games(call: ServiceCall) -> dict:
        coord = _coordinator(call)
        return await coord.client.async_search_games(
            call.data["query"], call.data.get("system", "all"), call.data.get("page")
        )

    async def _send_keyboard(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_send_keyboard(call.data["key"])

    async def _take_screenshot(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_take_screenshot()

    async def _delete_screenshot(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_delete_screenshot(
            call.data["core"], call.data["filename"]
        )
        await coord.async_request_refresh_full()

    async def _run_script(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_launch_script(call.data["filename"])

    async def _launch(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_launch_path(call.data["path"])
        await coord.async_request_refresh_full()

    async def _launch_token(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_launch_token(call.data["data"])
        await coord.async_request_refresh_full()

    async def _set_ini_value(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_set_ini_values(
            coord.active_ini_id, {call.data["key"]: call.data["value"]}
        )

    async def _set_wallpaper(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_set_wallpaper(call.data["filename"])
        await coord.async_request_refresh_full()

    async def _set_background_mode(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_set_background_mode(call.data["mode"])
        await coord.async_request_refresh_full()

    async def _send_keyboard_raw(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.client.async_send_keyboard_raw(call.data["code"])

    async def _create_shortcut(call: ServiceCall) -> dict:
        # async_register_admin_service has no supports_response; check inline.
        if call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)
            if user is None or not user.is_admin:
                raise Unauthorized(context=call.context)
        coord = _coordinator(call)
        return await coord.client.async_create_shortcut(
            call.data["game_path"], call.data["folder"], call.data["name"]
        )

    async def _send_command(call: ServiceCall) -> None:
        ssh = _ssh(_coordinator(call))
        try:
            await ssh.async_send_command(call.data["command"])
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        except MisterMainUnresponsiveError as err:
            raise HomeAssistantError(f"MiSTer Main is not responding: {err}") from err

    async def _gamepad_press(call: ServiceCall) -> None:
        coord = _coordinator(call)
        if coord.gamepad is None:
            raise ServiceValidationError(
                "Companion Remote gamepad daemon not available on this MiSTer"
            )
        try:
            await coord.gamepad.async_press(call.data["button"], call.data["action"])
        except MisterGamepadError as err:
            raise HomeAssistantError(str(err)) from err

    async def _set_ra_debug(call: ServiceCall) -> None:
        coord = _coordinator(call)
        _ssh(coord)
        if coord.ra_data is None or not coord.ra_data.installed:
            raise ServiceValidationError("RetroAchievements is not installed")
        try:
            await coord.ra.async_set_debug(call.data["enabled"])
        except MisterRAError as err:
            raise HomeAssistantError(str(err)) from err

    services = (
        ("launch_system", _launch_system, SERVICE_LAUNCH_SYSTEM_SCHEMA),
        ("send_keyboard", _send_keyboard, SERVICE_SEND_KEYBOARD_SCHEMA),
        ("take_screenshot", _take_screenshot, SERVICE_TAKE_SCREENSHOT_SCHEMA),
        ("delete_screenshot", _delete_screenshot, SERVICE_DELETE_SCREENSHOT_SCHEMA),
        ("set_wallpaper", _set_wallpaper, SERVICE_SET_WALLPAPER_SCHEMA),
        ("set_background_mode", _set_background_mode, SERVICE_BACKGROUND_MODE_SCHEMA),
        ("gamepad_press", _gamepad_press, SERVICE_GAMEPAD_PRESS_SCHEMA),
    )
    # Anything that can launch arbitrary files, run code or rewrite config.
    admin_services = (
        ("launch_game", _launch_game, SERVICE_LAUNCH_GAME_SCHEMA),
        ("launch", _launch, SERVICE_LAUNCH_SCHEMA),
        ("launch_token", _launch_token, SERVICE_LAUNCH_TOKEN_SCHEMA),
        ("set_ini_value", _set_ini_value, SERVICE_SET_INI_VALUE_SCHEMA),
        ("run_script", _run_script, SERVICE_RUN_SCRIPT_SCHEMA),
        ("send_command", _send_command, SERVICE_SEND_COMMAND_SCHEMA),
        ("send_keyboard_raw", _send_keyboard_raw, SERVICE_KEYBOARD_RAW_SCHEMA),
        ("set_ra_debug", _set_ra_debug, SERVICE_SET_RA_DEBUG_SCHEMA),
    )
    for name, func, schema in services:
        hass.services.async_register(DOMAIN, name, func, schema)
    for name, func, schema in admin_services:
        async_register_admin_service(hass, DOMAIN, name, func, schema)
    hass.services.async_register(
        DOMAIN,
        "search_games",
        _search_games,
        SERVICE_SEARCH_GAMES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "create_shortcut",
        _create_shortcut,
        SERVICE_CREATE_SHORTCUT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
