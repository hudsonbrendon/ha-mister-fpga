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
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from mister_fpga import MisterMainUnresponsiveError

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

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_media_player"
        self._attr_supported_features = (
            MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.PLAY_MEDIA
        )
        if coordinator.ssh is not None:  # volume goes through Main's FIFO
            self._attr_supported_features |= (
                MediaPlayerEntityFeature.VOLUME_SET
                | MediaPlayerEntityFeature.VOLUME_MUTE
            )

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
        ssh = self.coordinator.ssh_data
        # The Remote never reports what SAM is showing.
        sam_game = ssh.get("sam_game") if ssh.get("sam_active") else None
        return data.game_name or sam_game or data.core

    @property
    def volume_level(self) -> float | None:
        volume = self.coordinator.ssh_data.get("volume")
        return volume / 7 if volume is not None else None

    @property
    def is_volume_muted(self) -> bool | None:
        return self.coordinator.ssh_data.get("muted")

    async def async_set_volume_level(self, volume: float) -> None:
        level = round(volume * 7)
        await self._ssh_call(self.coordinator.ssh.async_set_volume(level))
        self.coordinator.ssh_data["volume"] = level
        self.async_write_ha_state()

    async def async_mute_volume(self, mute: bool) -> None:
        await self._ssh_call(self.coordinator.ssh.async_set_mute(mute))
        self.coordinator.ssh_data["muted"] = mute
        self.async_write_ha_state()

    async def _ssh_call(self, coro) -> None:
        try:
            await coro
        except MisterMainUnresponsiveError as err:
            raise HomeAssistantError(f"MiSTer Main is not responding: {err}") from err

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
                await self.coordinator.async_request_refresh_full()
                return

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        await self.coordinator.client.async_launch_game(media_id)
        await self.coordinator.async_request_refresh_full()
