"""Buttons for the MiSTer FPGA integration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import MisterClient
from .const import DOMAIN
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
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(MisterButton(coordinator, entry, d) for d in BUTTONS)


class MisterButton(MisterEntity, ButtonEntity):
    entity_description: MisterButtonEntityDescription

    def __init__(self, coordinator, entry, description) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    async def async_press(self) -> None:
        await self.entity_description.press_fn(self.coordinator.client)
