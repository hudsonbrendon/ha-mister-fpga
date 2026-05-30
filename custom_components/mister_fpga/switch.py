"""Background music (BGM) switch for the MiSTer FPGA integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import MisterConnectionError
from .const import DOMAIN
from .entity import MisterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MisterMusicSwitch(coordinator, entry)])


class MisterMusicSwitch(MisterEntity, SwitchEntity):
    """Controls the MiSTer BGM (menu background music) service."""

    _attr_translation_key = "background_music"
    _attr_icon = "mdi:music"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_background_music"
        self._is_on = False

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data and self.coordinator.data.online)

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        try:
            status = await self.coordinator.client.async_get_music_status()
        except MisterConnectionError:
            return
        if isinstance(status, dict):
            self._is_on = bool(status.get("playing"))
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_music_play()
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_music_stop()
        self._is_on = False
        self.async_write_ha_state()
