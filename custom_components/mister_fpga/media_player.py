"""Media player for the MiSTer FPGA integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MisterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MisterMediaPlayer(coordinator, entry)])


class MisterMediaPlayer(MisterEntity, MediaPlayerEntity):
    """Now-playing view plus launch-system / launch-game controls."""

    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.PLAY_MEDIA
    )

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_media_player"

    @property
    def state(self) -> MediaPlayerState:
        data = self.coordinator.data
        if not data or not data.online:
            return MediaPlayerState.OFF
        return (
            MediaPlayerState.PLAYING
            if data.is_running_game
            else MediaPlayerState.IDLE
        )

    @property
    def media_content_type(self) -> str:
        return MediaType.GAME

    @property
    def media_title(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.game_name or data.core

    @property
    def app_name(self) -> str | None:
        data = self.coordinator.data
        return (data.system_name or data.system) if data else None

    @property
    def source(self) -> str | None:
        data = self.coordinator.data
        return (data.system_name or data.system) if data else None

    @property
    def source_list(self) -> list[str]:
        return sorted(
            s["name"] for s in self.coordinator.systems if s.get("name")
        )

    async def async_select_source(self, source: str) -> None:
        for system in self.coordinator.systems:
            if system.get("name") == source:
                await self.coordinator.client.async_launch_system(system["id"])
                await self.coordinator.async_request_refresh()
                return

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        await self.coordinator.client.async_launch_game(media_id)
        await self.coordinator.async_request_refresh()
