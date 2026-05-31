"""API client for the MiSTer FPGA Remote (mrext) integration."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .const import (
    HTTP_TIMEOUT,
    PATH_CORE_MENU,
    PATH_GAMES_INDEX,
    PATH_GAMES_LAUNCH,
    PATH_GAMES_SEARCH,
    PATH_INIS,
    PATH_KEYBOARD,
    PATH_KEYBOARD_RAW,
    PATH_LAUNCH,
    PATH_LAUNCH_MENU,
    PATH_LAUNCH_NEW,
    PATH_LAUNCH_TOKEN,
    PATH_MUSIC_NEXT,
    PATH_MUSIC_PLAY,
    PATH_MUSIC_PLAYBACK,
    PATH_MUSIC_PLAYLIST,
    PATH_MUSIC_STATUS,
    PATH_MUSIC_STOP,
    PATH_PEERS,
    PATH_PLAYING,
    PATH_REBOOT,
    PATH_RESTART_REMOTE,
    PATH_SCREENSHOTS,
    PATH_SCRIPTS_CONSOLE,
    PATH_SCRIPTS_KILL,
    PATH_SCRIPTS_LAUNCH,
    PATH_SCRIPTS_LIST,
    PATH_SYSINFO,
    PATH_SYSTEMS,
    PATH_WALLPAPERS,
)

_LOGGER = logging.getLogger(__name__)


class MisterConnectionError(Exception):
    """Raised when the MiSTer Remote API is unreachable or returns an error."""


@dataclass
class MisterStatus:
    """Snapshot of the MiSTer device state."""

    online: bool = False
    core: str | None = None
    system: str | None = None
    system_name: str | None = None
    game: str | None = None
    game_name: str | None = None
    hostname: str | None = None
    version: str | None = None
    ip: str | None = None
    ips: list[str] = field(default_factory=list)
    updated: str | None = None
    dns: str | None = None
    disk_total: int | None = None
    disk_used: int | None = None
    disk_free: int | None = None

    @property
    def is_running_game(self) -> bool:
        """True when a real core/game (not the menu) is running."""
        if not self.online:
            return False
        core = (self.core or "").strip().lower()
        return bool(core) and core not in ("menu", "none")


class MisterClient:
    """Thin async wrapper around the mrext Remote REST API."""

    def __init__(
        self, session: aiohttp.ClientSession, host: str, port: int
    ) -> None:
        self._session = session
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/api"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict | None = None,
        parse_json: bool = True,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT),
            ) as resp:
                resp.raise_for_status()
                if not parse_json:
                    return await resp.read()
                text = await resp.text()
                if not text.strip():
                    return None
                try:
                    return json.loads(text)
                except json.JSONDecodeError as err:
                    raise MisterConnectionError(
                        f"{method} {url} returned invalid JSON: {err}"
                    ) from err
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.debug("Request %s %s failed: %s", method, url, err)
            raise MisterConnectionError(f"{method} {url} failed: {err}") from err

    async def async_get_status(self) -> MisterStatus:
        sysinfo = await self._request("GET", PATH_SYSINFO) or {}
        playing = await self._request("GET", PATH_PLAYING) or {}
        ips = sysinfo.get("ips") or []
        disks = sysinfo.get("disks") or []
        disk = disks[0] if disks else {}
        return MisterStatus(
            online=True,
            core=playing.get("core") or None,
            system=playing.get("system") or None,
            system_name=playing.get("systemName") or None,
            game=playing.get("game") or None,
            game_name=playing.get("gameName") or None,
            hostname=sysinfo.get("hostname"),
            version=sysinfo.get("version"),
            ips=ips,
            ip=ips[0] if ips else None,
            updated=sysinfo.get("updated"),
            dns=sysinfo.get("dns"),
            disk_total=disk.get("total"),
            disk_used=disk.get("used"),
            disk_free=disk.get("free"),
        )

    async def async_get_systems(self) -> list[dict]:
        return await self._request("GET", PATH_SYSTEMS) or []

    async def async_launch_system(self, system_id: str) -> None:
        await self._request("POST", f"{PATH_SYSTEMS}/{system_id}")

    async def async_launch_game(self, path: str) -> None:
        await self._request("POST", PATH_GAMES_LAUNCH, payload={"path": path})

    async def async_launch_menu(self) -> None:
        await self._request("POST", PATH_LAUNCH_MENU)

    async def async_search_games(self, query: str, system: str = "all") -> dict:
        return (
            await self._request(
                "POST", PATH_GAMES_SEARCH, payload={"data": query, "system": system}
            )
            or {}
        )

    async def async_index_games(self) -> None:
        await self._request("POST", PATH_GAMES_INDEX)

    async def async_send_keyboard(self, name: str) -> None:
        await self._request("POST", f"{PATH_KEYBOARD}/{name}")

    async def async_reboot(self) -> None:
        await self._request("POST", PATH_REBOOT)

    async def async_restart_remote(self) -> None:
        await self._request("POST", PATH_RESTART_REMOTE)

    async def async_take_screenshot(self) -> None:
        await self._request("POST", PATH_SCREENSHOTS)

    async def async_get_screenshots(self) -> list[dict]:
        return await self._request("GET", PATH_SCREENSHOTS) or []

    async def async_get_screenshot_image(self, core: str, filename: str) -> bytes:
        return await self._request(
            "GET", f"{PATH_SCREENSHOTS}/{core}/{filename}", parse_json=False
        )

    async def async_get_music_status(self) -> dict:
        return await self._request("GET", PATH_MUSIC_STATUS) or {}

    async def async_music_play(self) -> None:
        await self._request("POST", PATH_MUSIC_PLAY)

    async def async_music_stop(self) -> None:
        await self._request("POST", PATH_MUSIC_STOP)

    async def async_music_next(self) -> None:
        await self._request("POST", PATH_MUSIC_NEXT)

    # --- Wallpapers ---
    async def async_get_wallpapers(self) -> dict:
        return await self._request("GET", PATH_WALLPAPERS) or {}

    async def async_set_wallpaper(self, filename: str) -> None:
        await self._request("POST", f"{PATH_WALLPAPERS}/{filename}")

    async def async_clear_wallpaper(self) -> None:
        await self._request("DELETE", PATH_WALLPAPERS)

    # --- INI files ---
    async def async_get_inis(self) -> dict:
        return await self._request("GET", PATH_INIS) or {}

    async def async_get_ini_values(self, ini_id: int) -> dict:
        return await self._request("GET", f"{PATH_INIS}/{ini_id}") or {}

    async def async_set_active_ini(self, ini_id: int) -> None:
        await self._request("PUT", PATH_INIS, payload={"ini": ini_id})

    async def async_set_ini_values(self, ini_id: int, values: dict) -> None:
        await self._request("PUT", f"{PATH_INIS}/{ini_id}", payload=values)

    async def async_set_background_mode(self, mode: int) -> None:
        await self._request("PUT", PATH_CORE_MENU, payload={"mode": mode})

    # --- Music (extended) ---
    async def async_get_music_playlists(self) -> list[str]:
        return await self._request("GET", PATH_MUSIC_PLAYLIST) or []

    async def async_set_music_playlist(self, name: str) -> None:
        await self._request("POST", f"{PATH_MUSIC_PLAYLIST}/{name}")

    async def async_set_music_playback(self, mode: str) -> None:
        await self._request("POST", f"{PATH_MUSIC_PLAYBACK}/{mode}")

    # --- Scripts ---
    async def async_get_scripts(self) -> dict:
        return await self._request("GET", PATH_SCRIPTS_LIST) or {}

    async def async_launch_script(self, filename: str) -> None:
        await self._request("POST", f"{PATH_SCRIPTS_LAUNCH}/{filename}")

    async def async_open_console(self) -> None:
        await self._request("POST", PATH_SCRIPTS_CONSOLE)

    async def async_kill_script(self) -> None:
        await self._request("POST", PATH_SCRIPTS_KILL)

    # --- Peers ---
    async def async_get_peers(self) -> list[dict]:
        data = await self._request("GET", PATH_PEERS) or {}
        return data.get("peers", [])

    # --- Launchers ---
    async def async_launch_path(self, path: str) -> None:
        await self._request("POST", PATH_LAUNCH, payload={"path": path})

    async def async_launch_token(self, data: str) -> None:
        await self._request("GET", f"{PATH_LAUNCH_TOKEN}/{data}")

    async def async_create_shortcut(
        self, game_path: str, folder: str, name: str
    ) -> dict:
        return await self._request(
            "POST",
            PATH_LAUNCH_NEW,
            payload={"gamePath": game_path, "folder": folder, "name": name},
        ) or {}

    # --- Raw keyboard ---
    async def async_send_keyboard_raw(self, code: int) -> None:
        await self._request("POST", f"{PATH_KEYBOARD_RAW}/{code}")
