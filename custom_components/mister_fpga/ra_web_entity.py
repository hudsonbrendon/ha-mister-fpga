"""Base entity for RetroAchievements cloud-stats entities."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .ra_web_coordinator import MisterRAWebCoordinator


class MisterRAWebEntity(CoordinatorEntity[MisterRAWebCoordinator]):
    """Binds to the RA web coordinator, grouped under the existing device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: MisterRAWebCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}
        )
