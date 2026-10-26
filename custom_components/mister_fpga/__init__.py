"""The MiSTer FPGA integration."""
from __future__ import annotations

import logging
import shlex

import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import (
    HomeAssistantError,
    ServiceValidationError,
    Unauthorized,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.service import async_register_admin_service

from mister_fpga import (
    MisterClient,
    MisterConnectionError,
    MisterGamepad,
    MisterGamepadError,
    MisterMainUnresponsiveError,
    MisterRA,
    MisterRAError,
    MisterRAWeb,
)

from .const import (
    BACKGROUND_MODES,
    CONF_GAMEPAD_ENABLED,
    CONF_PUSH_UPDATES,
    CONF_RA_API_KEY,
    CONF_RA_CLOUD_INTERVAL,
    CONF_RA_USERNAME,
    CONF_SCAN_INTERVAL,
    CONF_SSH_ENABLED,
    CONF_SSH_PASSWORD,
    CONF_SSH_PORT,
    CONF_SSH_USERNAME,
    CONF_WEBHOOK_ID,
    DEFAULT_PORT,
    DEFAULT_RA_CLOUD_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSH_PORT,
    DEFAULT_SSH_USERNAME,
    DOMAIN,
    GAMEPAD_ACTIONS,
    GAMEPAD_BUTTONS,
)
from .coordinator import MisterDataUpdateCoordinator
from .ra_web_coordinator import MisterRAWebCoordinator
from .websocket import MisterWebSocket

_LOGGER = logging.getLogger(__name__)

REMOTE_INI = "/media/fat/Scripts/remote.ini"

# Runs on the MiSTer: set [remote] announce_game_url, keeping the other keys.
# Prints "changed" only when the file was rewritten.
_SET_ANNOUNCE_PY = (
    "import configparser,sys\n"
    "p,u=sys.argv[1],sys.argv[2]\n"
    "c=configparser.ConfigParser(interpolation=None,strict=False)\n"
    "c.optionxform=str\n"
    "c.read(p)\n"
    "if not c.has_section('remote'): c.add_section('remote')\n"
    "if c.get('remote','announce_game_url',fallback=None)==u: sys.exit(0)\n"
    "c.set('remote','announce_game_url',u)\n"
    "f=open(p,'w'); c.write(f); f.close()\n"
    "print('changed')\n"
)

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
        vol.Optional("page"): vol.All(vol.Coerce(int), vol.Range(min=1)),
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


def _build_ra_web_coordinator(hass, entry, session):
    """Build the RA web coordinator when username + api key are configured."""
    user = entry.options.get(CONF_RA_USERNAME)
    key = entry.options.get(CONF_RA_API_KEY)
    if not user or not key:
        return None
    web = MisterRAWeb(user, key, session=session)
    interval = entry.options.get(CONF_RA_CLOUD_INTERVAL, DEFAULT_RA_CLOUD_INTERVAL)
    return MisterRAWebCoordinator(hass, web, interval)


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


def _webhook_handler(coordinator):
    async def _handle(hass, webhook_id, request) -> None:
        try:
            payload = await request.json()
        except ValueError:
            _LOGGER.debug("MiSTer webhook: invalid JSON")
            return
        if isinstance(payload, dict):
            coordinator.async_handle_announce(payload)

    return _handle


async def _async_setup_push_updates(hass, coordinator, webhook_id: str) -> None:
    """Point mrext's announce_game_url at our webhook (best-effort)."""
    try:
        url = get_url(hass, allow_external=False, prefer_external=False)
    except NoURLAvailableError:
        _LOGGER.warning("MiSTer push updates: Home Assistant has no internal URL")
        return
    url = f"{url}{webhook.async_generate_path(webhook_id)}"
    cmd = f"python3 -c {shlex.quote(_SET_ANNOUNCE_PY)} {REMOTE_INI} {shlex.quote(url)}"
    try:
        rc, out = await coordinator.ssh.async_run(cmd)
        if rc != 0:
            _LOGGER.warning("MiSTer push updates: remote.ini update failed: %s", out)
            return
        if "changed" in out:
            _LOGGER.info("MiSTer push updates: announce_game_url set, restarting")
            await coordinator.client.async_restart_remote()
    except MisterConnectionError as err:
        # Restarting the Remote drops the connection mid-request.
        _LOGGER.debug("MiSTer push updates: restart_remote: %s", err)
    except Exception as err:  # noqa: BLE001 - SSH is best-effort
        _LOGGER.warning("MiSTer push updates: %s", err)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MiSTer FPGA from a config entry."""
    if CONF_WEBHOOK_ID not in entry.data:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_WEBHOOK_ID: webhook.async_generate_id()}
        )
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

    if entry.options.get(CONF_GAMEPAD_ENABLED, True):
        gamepad = MisterGamepad(entry.data[CONF_HOST], session=session)
        if await gamepad.async_available():
            coordinator.gamepad = gamepad

    ra_web_coordinator = _build_ra_web_coordinator(hass, entry, session)
    if ra_web_coordinator is not None:
        # async_refresh (not first_refresh): a cloud failure must NOT abort setup.
        await ra_web_coordinator.async_refresh()
    coordinator.ra_web_coordinator = ra_web_coordinator

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _register_services(hass)
    websocket = MisterWebSocket(hass, coordinator)
    websocket.start()
    coordinator.websocket = websocket

    webhook_id = entry.data[CONF_WEBHOOK_ID]
    webhook.async_register(
        hass,
        DOMAIN,
        entry.title,
        webhook_id,
        _webhook_handler(coordinator),
        local_only=True,
    )
    entry.async_on_unload(lambda: webhook.async_unregister(hass, webhook_id))
    if coordinator.ssh is not None and entry.options.get(CONF_PUSH_UPDATES, True):
        entry.async_create_task(
            hass, _async_setup_push_updates(hass, coordinator, webhook_id)
        )

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
