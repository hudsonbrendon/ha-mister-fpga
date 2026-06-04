"""Background music (BGM) switch for the MiSTer FPGA integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from mister_fpga import MisterConnectionError, MisterRAError

from .const import DOMAIN
from .entity import MisterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [MisterMusicSwitch(coordinator, entry)]
    ra_data = getattr(coordinator, "ra_data", None)
    if ra_data is not None and ra_data.installed:
        entities.append(MisterRACoresSwitch(coordinator, entry))
        entities.append(MisterRAHardcoreSwitch(coordinator, entry))
    async_add_entities(entities)


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


class _MisterRASwitch(MisterEntity, SwitchEntity):
    """Shared availability for RA switches."""

    @property
    def available(self) -> bool:
        ra_data = getattr(self.coordinator, "ra_data", None)
        return bool(ra_data is not None and ra_data.installed)


class MisterRACoresSwitch(_MisterRASwitch):
    """Toggle RetroAchievements cores on/off (applies on next core load)."""

    _attr_translation_key = "ra_cores"
    _attr_icon = "mdi:trophy"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_ra_cores"

    @property
    def is_on(self) -> bool:
        ra_data = getattr(self.coordinator, "ra_data", None)
        return bool(ra_data and ra_data.cores_on)

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.ra.async_cores_on()
        except MisterRAError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.ra.async_cores_off()
        except MisterRAError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


class MisterRAHardcoreSwitch(_MisterRASwitch):
    """Toggle RA hardcore mode (only NES/FDS enforce it upstream)."""

    _attr_translation_key = "ra_hardcore"
    _attr_icon = "mdi:shield-star"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_ra_hardcore"

    @property
    def is_on(self) -> bool:
        ra_data = getattr(self.coordinator, "ra_data", None)
        return bool(ra_data and ra_data.hardcore)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, enabled: bool) -> None:
        try:
            await self.coordinator.ra.async_set_hardcore(enabled)
        except MisterRAError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
