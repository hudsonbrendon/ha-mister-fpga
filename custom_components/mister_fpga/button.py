"""Buttons for the MiSTer FPGA integration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import MisterClient
from .const import DOMAIN, KEYBOARD_NAMES
from .entity import MisterEntity


@dataclass(frozen=True, kw_only=True)
class MisterButtonEntityDescription(ButtonEntityDescription):
    press_fn: Callable[[MisterClient], Awaitable[None]]


BUTTONS: tuple[MisterButtonEntityDescription, ...] = (
    MisterButtonEntityDescription(
        key="reboot", translation_key="reboot", icon="mdi:restart",
        press_fn=lambda c: c.async_reboot(),
    ),
    MisterButtonEntityDescription(
        key="go_to_menu", translation_key="go_to_menu", icon="mdi:home",
        press_fn=lambda c: c.async_launch_menu(),
    ),
    MisterButtonEntityDescription(
        key="take_screenshot", translation_key="take_screenshot", icon="mdi:camera",
        press_fn=lambda c: c.async_take_screenshot(),
    ),
    MisterButtonEntityDescription(
        key="restart_remote", translation_key="restart_remote",
        icon="mdi:restart-alert", press_fn=lambda c: c.async_restart_remote(),
    ),
    MisterButtonEntityDescription(
        key="index_games", translation_key="index_games",
        icon="mdi:database-refresh", press_fn=lambda c: c.async_index_games(),
    ),
    MisterButtonEntityDescription(
        key="music_next", translation_key="music_next",
        icon="mdi:skip-next", press_fn=lambda c: c.async_music_next(),
    ),
    MisterButtonEntityDescription(
        key="clear_wallpaper", translation_key="clear_wallpaper",
        icon="mdi:wallpaper", press_fn=lambda c: c.async_clear_wallpaper(),
    ),
    MisterButtonEntityDescription(
        key="framebuffer_console", translation_key="framebuffer_console",
        icon="mdi:console", press_fn=lambda c: c.async_open_console(),
    ),
    MisterButtonEntityDescription(
        key="kill_script", translation_key="kill_script",
        icon="mdi:stop-circle", press_fn=lambda c: c.async_kill_script(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list = [MisterButton(coordinator, entry, d) for d in BUTTONS]
    entities += [MisterNavButton(coordinator, entry, name) for name in KEYBOARD_NAMES]
    async_add_entities(entities)


class MisterButton(MisterEntity, ButtonEntity):
    entity_description: MisterButtonEntityDescription

    def __init__(self, coordinator, entry, description) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    async def async_press(self) -> None:
        await self.entity_description.press_fn(self.coordinator.client)


class MisterNavButton(MisterEntity, ButtonEntity):
    """Sends a named keyboard control to the MiSTer."""

    def __init__(self, coordinator, entry, key_name: str) -> None:
        super().__init__(coordinator, entry)
        self._key_name = key_name
        self._attr_translation_key = f"nav_{key_name}"
        self._attr_unique_id = f"{entry.entry_id}_nav_{key_name}"

    async def async_press(self) -> None:
        await self.coordinator.client.async_send_keyboard(self._key_name)
