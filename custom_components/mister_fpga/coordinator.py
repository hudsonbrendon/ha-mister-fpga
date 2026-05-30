"""DataUpdateCoordinator for the MiSTer FPGA integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import MisterClient, MisterConnectionError, MisterStatus
from .const import DOMAIN, EVENT_GAME_CHANGED

_LOGGER = logging.getLogger(__name__)


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
        return data

    async def async_refresh_systems(self) -> None:
        """Refresh the systems list (best-effort; errors are swallowed)."""
        try:
            self.systems = await self.client.async_get_systems()
        except MisterConnectionError:
            pass
