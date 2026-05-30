"""Select entity for launching MiSTer systems."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
    async_add_entities([MisterSystemSelect(coordinator, entry)])


class MisterSystemSelect(MisterEntity, SelectEntity):
    """Pick a system to launch on the MiSTer."""

    _attr_translation_key = "launch_system"
    _attr_icon = "mdi:rocket-launch"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_launch_system"

    @property
    def options(self) -> list[str]:
        return sorted(
            s["name"] for s in self.coordinator.systems if s.get("name")
        )

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        name = data.system_name or data.system
        return name if name in self.options else None

    async def async_select_option(self, option: str) -> None:
        for system in self.coordinator.systems:
            if system.get("name") == option:
                await self.coordinator.client.async_launch_system(system["id"])
                await self.coordinator.async_request_refresh()
                return
