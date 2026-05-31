"""WebSocket listener for real-time MiSTer Remote updates."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import replace

import aiohttp

from .api import MisterStatus
from .const import WS_PATH

_LOGGER = logging.getLogger(__name__)

_RECONNECT_DELAY = 5


def apply_ws_message(
    message: str,
    status: MisterStatus,
    menu_path: str | None,
    index_state: tuple[bool, bool],
) -> tuple[MisterStatus, str | None, tuple[bool, bool]]:
    """Pure reducer: apply one WS text frame to (status, menu_path, index_state)."""
    prefix, _, rest = message.partition(":")
    if prefix == "coreRunning":
        core = rest.strip() or None
        if core is None:
            return (
                replace(status, core=None, game=None, game_name=None),
                menu_path,
                index_state,
            )
        return replace(status, core=core), menu_path, index_state
    if prefix == "gameRunning":
        rest = rest.strip()
        if not rest:
            return replace(status, game=None, game_name=None), menu_path, index_state
        _, _, name = rest.partition("/")
        game_name = name.rsplit(".", 1)[0] if name else None
        return replace(status, game=rest, game_name=game_name), menu_path, index_state
    if prefix == "menuNavigation":
        return status, rest.strip() or None, index_state
    if prefix == "indexStatus":
        parts = rest.split(",")
        exists = len(parts) > 0 and parts[0] == "y"
        in_progress = len(parts) > 1 and parts[1] == "y"
        return status, menu_path, (exists, in_progress)
    return status, menu_path, index_state


class MisterWebSocket:
    """Maintains a WS connection and pushes updates into the coordinator."""

    def __init__(self, hass, coordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._task: asyncio.Task | None = None
        self._stop = False

    @property
    def _url(self) -> str:
        client = self.coordinator.client
        return f"ws://{client.host}:{client.port}{WS_PATH}"

    def start(self) -> None:
        self._stop = False
        self._task = self.hass.async_create_background_task(
            self._run(), name="mister_fpga_ws"
        )

    async def stop(self) -> None:
        self._stop = True
        if self._task:
            self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        session = async_get_clientsession(self.hass)
        while not self._stop:
            try:
                async with session.ws_connect(self._url, heartbeat=30) as ws:
                    _LOGGER.debug("MiSTer WS connected: %s", self._url)
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            self._handle(msg.data)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
            except (aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.debug("MiSTer WS error: %s", err)
            if self._stop:
                break
            await asyncio.sleep(_RECONNECT_DELAY)

    def _handle(self, message: str) -> None:
        status = self.coordinator.data or MisterStatus(online=True)
        new_status, menu_path, index_state = apply_ws_message(
            message,
            status,
            self.coordinator.menu_path,
            (self.coordinator.index_exists, self.coordinator.indexing),
        )
        new_status = replace(new_status, online=True)
        self.coordinator.menu_path = menu_path
        self.coordinator.index_exists, self.coordinator.indexing = index_state
        self.coordinator.async_set_updated_data(new_status)
