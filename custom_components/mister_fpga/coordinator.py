"""DataUpdateCoordinator for the MiSTer FPGA integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import utcnow

from mister_fpga import MisterClient, MisterConnectionError, MisterStatus

from .const import DOMAIN, EVENT_GAME_CHANGED

_LOGGER = logging.getLogger(__name__)

# Wallpapers, INIs and peers barely move, and the screenshot count costs a full
# listing. They refresh on this slower cadence instead of on every status poll;
# writes call async_request_refresh_full() so the UI still updates immediately.
SLOW_EXTRAS_INTERVAL = timedelta(minutes=5)


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
        self.scripts: list[dict] = []
        self.music: dict = {}
        self.wallpapers: dict = {}
        self.inis: list[dict] = []
        self.active_ini_id: int = 1
        self.ini_values: dict = {}
        self.mac_address: str | None = None
        self.peers: list[dict] = []
        self.screenshots_count: int = 0
        self.menu_path: str | None = None
        self.indexing: bool = False
        self.index_exists: bool = False
        self.websocket = None
        self.ssh = None
        self.ra = None
        self.ra_data = None
        self.ra_web_coordinator = None
        self.ssh_data: dict = {}
        self._slow_extras_at = None

    async def _async_update_data(self) -> MisterStatus:
        """Fetch status; an offline device is not a fatal error."""
        try:
            data = await self.client.async_get_status()
        except MisterConnectionError as err:
            _LOGGER.debug("MiSTer unreachable: %s", err)
            return MisterStatus(online=False)

        current = data.game or data.core
        if data.online and current != self._last_game:
            self.hass.bus.async_fire(
                EVENT_GAME_CHANGED,
                {
                    "core": data.core,
                    "system": data.system_name,
                    "game": data.game_name,
                },
            )
            self._last_game = current
        if data.online:
            await self.async_refresh_extras()
            await self.async_refresh_ssh()
        return data

    async def async_refresh_ssh(self) -> None:
        if self.ssh is None:
            return
        self.ssh_data = await self.ssh.async_probe()
        if self.ra is not None:
            self.ra_data = await self.ra.async_status()

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

    async def async_refresh_scripts(self) -> None:
        """Refresh the Scripts list (best-effort)."""
        data = await self._safe(self.client.async_get_scripts(), {})
        self.scripts = data.get("scripts", []) if isinstance(data, dict) else []

    async def async_refresh_systems(self) -> None:
        """Refresh the systems list (best-effort; errors are swallowed)."""
        try:
            self.systems = await self.client.async_get_systems()
        except MisterConnectionError:
            pass
