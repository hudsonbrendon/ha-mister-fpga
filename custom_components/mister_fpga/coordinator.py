"""DataUpdateCoordinator for the MiSTer FPGA integration."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import utcnow

from mister_fpga import (
    MisterClient,
    MisterConnectionError,
    MisterIndexStatus,
    MisterStatus,
    MisterUnsupportedError,
)

from .const import (
    DOMAIN,
    EVENT_GAME_CHANGED,
    EVENT_MAIN_UNRESPONSIVE,
    EVENT_RETROACHIEVEMENTS,
)

_LOGGER = logging.getLogger(__name__)

# Wallpapers, INIs and peers barely move, and the screenshot count costs a full
# listing. They refresh on this slower cadence instead of on every status poll;
# writes call async_request_refresh_full() so the UI still updates immediately.
SLOW_EXTRAS_INTERVAL = timedelta(minutes=5)

# MisterRA.async_read_log returns at most 256 KiB per call; a read that moved
# less than this reached the end of the log.
_RA_LOG_CHUNK = 200_000
_RA_LOG_MAX_READS = 64


def _is_mac_junk(name: str | None) -> bool:
    """MacOS AppleDouble files (``._foo``) copied onto the SD card."""
    return bool(name) and name.startswith("._")


class MisterDataUpdateCoordinator(DataUpdateCoordinator[MisterStatus]):
    """Polls the MiSTer Remote API and exposes a MisterStatus to entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MisterClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.systems: list[dict] = []
        self._last_game: str | None = None
        self._game_seen = False
        self.game_path: str | None = None
        self.scripts: list[dict] = []
        self.music: dict = {}
        self.wallpapers: dict = {}
        self.inis: list[dict] = []
        self.active_ini_id: int = 1
        self.ini_values: dict = {}
        self.mac_address: str | None = None
        self.peers: list[dict] = []
        self.screenshots_count: int = 0
        self.playlog: dict | None = None
        self.playlog_today: int | None = None
        self.menu_path: str | None = None
        self.indexing: bool = False
        self.index_exists: bool = False
        self.index_status: MisterIndexStatus | None = None
        self.websocket = None
        self.gamepad = None
        self.ssh = None
        self.ra = None
        self.ra_data = None
        self.ra_web_coordinator = None
        self.ssh_data: dict = {}
        self.main_unresponsive = False
        self._fifo_pending_prev: int | None = None
        self._ra_log_offset: int | None = None
        self._slow_extras_at = None

    async def _async_update_data(self) -> MisterStatus:
        """Fetch status; an offline device is not a fatal error."""
        try:
            data = await self.client.async_get_status()
        except MisterConnectionError as err:
            _LOGGER.debug("MiSTer unreachable: %s", err)
            return MisterStatus(online=False)

        self.async_check_game_changed(data)
        if data.online:
            await self.async_refresh_extras()
            await self.async_refresh_ssh()
        return data

    @callback
    def async_check_game_changed(
        self, data: MisterStatus, game_path: str | None = None
    ) -> None:
        """Fire EVENT_GAME_CHANGED when core/game moved (poll, WS or webhook).

        The first observation after setup only records the baseline, so a
        restart of Home Assistant does not look like a game change.
        """
        if not data.online:
            return
        current = data.game_name or data.core
        if self._game_seen and current == self._last_game:
            if game_path:  # webhook arriving after the WS already saw the game
                self.game_path = game_path
            return
        first = not self._game_seen
        self._game_seen = True
        self._last_game = current
        self.game_path = game_path
        if first:
            return
        event = {
            "core": data.core,
            "system": data.system_name,
            "game": data.game_name,
        }
        if game_path:
            event["game_path"] = game_path
        self.hass.bus.async_fire(EVENT_GAME_CHANGED, event)

    @callback
    def async_handle_announce(self, payload: dict) -> None:
        """Apply an mrext ``announce_game_url`` push (see the webhook)."""
        data = self.data or MisterStatus(online=True)
        system = payload.get("system") or None
        game_path = payload.get("gamePath") or None
        # With no game mrext sends gameFilename "." (filepath.Base of "").
        filename = payload.get("gameFilename") if game_path else None
        new = replace(
            data,
            online=True,
            core=payload.get("core") or data.core,
            system=system,
            system_name=payload.get("systemName") or None,
            game=f"{system}/{filename}" if system and filename else None,
            game_name=payload.get("gameName") or None,
        )
        self.async_check_game_changed(new, game_path)
        self.async_set_updated_data(new)

    async def async_refresh_ssh(self) -> None:
        if self.ssh is None:
            return
        self.ssh_data = await self.ssh.async_probe()
        self._update_main_health()
        if self.ra is not None:
            self.ra_data = await self.ra.async_status()
            if self.ra_data is not None and self.ra_data.installed:
                await self._async_read_ra_log()

    def _update_main_health(self) -> None:
        """Main is hung when the command FIFO stays non-empty on two probes."""
        pending = self.ssh_data.get("cmd_fifo_pending")
        was = self.main_unresponsive
        # -1 means the FIFO is missing (Main not running), not a backlog.
        prev = self._fifo_pending_prev
        self.main_unresponsive = (pending or 0) > 0 and (prev or 0) > 0
        self._fifo_pending_prev = pending
        if self.main_unresponsive and not was:
            self.hass.bus.async_fire(
                EVENT_MAIN_UNRESPONSIVE,
                {
                    "cmd_fifo_pending": pending,
                    "main_open_fds": self.ssh_data.get("main_open_fds"),
                    "active_core": self.ssh_data.get("active_core"),
                },
            )

    async def _async_read_ra_log(self) -> None:
        """Fire EVENT_RETROACHIEVEMENTS for new RA debug-log lines.

        The first run only skips to the end of the log so old lines don't
        replay after a restart.
        """
        first = self._ra_log_offset is None
        offset = self._ra_log_offset or 0
        try:
            for _ in range(_RA_LOG_MAX_READS):
                new_offset, events = await self.ra.async_read_log(offset)
                advanced = new_offset - offset
                offset = new_offset
                if not first:
                    for event in events:
                        self.hass.bus.async_fire(EVENT_RETROACHIEVEMENTS, event)
                if advanced < _RA_LOG_CHUNK:
                    break
        except Exception as err:
            _LOGGER.debug("RA log read failed: %s", err)
            return
        self._ra_log_offset = offset

    async def _safe(self, coro, default):
        """Await coro, returning default on MisterConnectionError."""
        try:
            return await coro
        except MisterConnectionError as err:
            _LOGGER.debug("MiSTer extra fetch failed: %s", err)
            return default

    async def async_request_refresh_full(self) -> None:
        """Refresh status and every extra now. Use after writing to the device."""
        self._slow_extras_at = None
        await self.async_request_refresh()

    async def async_refresh_extras(self, force: bool = False) -> None:
        """Best-effort refresh of secondary state; never raises.

        Music status is polled every cycle (the track changes on its own);
        the rest is throttled to SLOW_EXTRAS_INTERVAL unless force is set.
        """
        music = await self._safe(self.client.async_get_music_status(), {})
        self.music = music if isinstance(music, dict) else {}

        now = utcnow()
        if (
            not force
            and self._slow_extras_at is not None
            and now - self._slow_extras_at < SLOW_EXTRAS_INTERVAL
        ):
            return
        self._slow_extras_at = now

        wallpapers = await self._safe(self.client.async_get_wallpapers(), {})
        self.wallpapers = wallpapers if isinstance(wallpapers, dict) else {}
        if isinstance(self.wallpapers.get("wallpapers"), list):
            self.wallpapers["wallpapers"] = [
                w
                for w in self.wallpapers["wallpapers"]
                if not _is_mac_junk(w.get("filename"))
            ]
        inis = await self._safe(self.client.async_get_inis(), {})
        self.inis = inis.get("inis", []) if isinstance(inis, dict) else []
        active = inis.get("active", 0) if isinstance(inis, dict) else 0
        self.active_ini_id = active if active else 1
        ini_vals = await self._safe(
            self.client.async_get_ini_values(self.active_ini_id), {}
        )
        self.ini_values = ini_vals if isinstance(ini_vals, dict) else {}
        self.mac_address = self.ini_values.get("__ethernetMacAddress") or None
        peers = await self._safe(self.client.async_get_peers(), [])
        self.peers = peers if isinstance(peers, list) else []
        shots = await self._safe(self.client.async_get_screenshots(), [])
        self.screenshots_count = len(shots) if isinstance(shots, list) else 0
        await self._async_refresh_playlog()

    async def _async_refresh_playlog(self) -> None:
        """PlayLog totals (Remote >= 0.5 with the playlog service running)."""
        try:
            status = await self.client.async_get_playlog_status()
            if not (isinstance(status, dict) and status.get("running")):
                self.playlog = self.playlog_today = None
                return
            summary = await self.client.async_get_playlog_summary(top=5)
            today = await self.client.async_get_playlog_summary(days=1)
        except MisterUnsupportedError:
            self.playlog = self.playlog_today = None
            return
        except MisterConnectionError as err:
            _LOGGER.debug("PlayLog fetch failed: %s", err)
            return
        self.playlog = summary if isinstance(summary, dict) else None
        days = today.get("days") if isinstance(today, dict) else None
        self.playlog_today = sum(
            d.get("time") or 0 for d in days or [] if isinstance(d, dict)
        )

    async def async_refresh_scripts(self) -> None:
        """Refresh the Scripts list (best-effort)."""
        data = await self._safe(self.client.async_get_scripts(), {})
        scripts = data.get("scripts", []) if isinstance(data, dict) else []
        self.scripts = [s for s in scripts if not _is_mac_junk(s.get("filename"))]

    async def async_refresh_systems(self) -> None:
        """Refresh the systems list (best-effort; errors are swallowed)."""
        try:
            self.systems = await self.client.async_get_systems()
        except MisterConnectionError:
            pass
