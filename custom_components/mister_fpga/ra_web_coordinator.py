"""Separate slow-poll coordinator for RetroAchievements cloud stats."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from mister_fpga import MisterRAWeb, MisterRAWebStats
from mister_fpga.ra_web import MisterRAWebError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MisterRAWebCoordinator(DataUpdateCoordinator[MisterRAWebStats]):
    """Polls the RetroAchievements.org Web API on its own slow interval."""

    def __init__(
        self, hass: HomeAssistant, web: MisterRAWeb, interval: int
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_ra_web",
            update_interval=timedelta(seconds=interval),
        )
        self.web = web

    async def _async_update_data(self) -> MisterRAWebStats:
        try:
            return await self.web.async_fetch_stats()
        except MisterRAWebError as err:
            raise UpdateFailed(str(err)) from err
