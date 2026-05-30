"""Base entity for the MiSTer FPGA integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MisterDataUpdateCoordinator


class MisterEntity(CoordinatorEntity[MisterDataUpdateCoordinator]):
    """Common device info and coordinator wiring."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MisterDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        data = coordinator.data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="MiSTer-devel",
            model="MiSTer FPGA",
            configuration_url=f"http://{coordinator.client.host}:{coordinator.client.port}",
            sw_version=data.version if data else None,
        )
