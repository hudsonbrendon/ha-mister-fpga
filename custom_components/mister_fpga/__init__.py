"""The MiSTer FPGA integration."""

from __future__ import annotations

import logging
import shlex

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.typing import ConfigType

from mister_fpga import (
    MisterClient,
    MisterConnectionError,
    MisterGamepad,
    MisterRA,
    MisterRAWeb,
    MisterSSH,
)

from .const import (
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
)
from .coordinator import MisterDataUpdateCoordinator
from .ra_web_coordinator import MisterRAWebCoordinator
from .services import async_setup_services
from .websocket import MisterWebSocket

_LOGGER = logging.getLogger(__name__)

type MisterConfigEntry = ConfigEntry[MisterDataUpdateCoordinator]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

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


def _build_ra_web_coordinator(hass, entry, session):
    """Build the RA web coordinator when username + api key are configured."""
    user = entry.options.get(CONF_RA_USERNAME)
    key = entry.options.get(CONF_RA_API_KEY)
    if not user or not key:
        return None
    web = MisterRAWeb(user, key, session=session)
    interval = entry.options.get(CONF_RA_CLOUD_INTERVAL, DEFAULT_RA_CLOUD_INTERVAL)
    return MisterRAWebCoordinator(hass, web, interval)


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
    except Exception as err:
        _LOGGER.warning("MiSTer push updates: %s", err)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register actions; entries are set up by async_setup_entry."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MisterConfigEntry) -> bool:
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

    entry.runtime_data = coordinator
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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MisterConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = entry.runtime_data
    if coordinator.websocket is not None:
        await coordinator.websocket.stop()
    if coordinator.ssh is not None:
        await coordinator.ssh.async_close()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
