"""Diagnostics support for the MiSTer FPGA integration."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_SSH_PASSWORD, DOMAIN
from .coordinator import MisterDataUpdateCoordinator

TO_REDACT = {CONF_SSH_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: MisterDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "status": asdict(coordinator.data) if coordinator.data else None,
        "systems_count": len(coordinator.systems),
        "extras": {
            "active_ini_id": coordinator.active_ini_id,
            "mac_address": coordinator.mac_address,
            "music": coordinator.music,
            "wallpapers_active": coordinator.wallpapers.get("active"),
            "background_mode": coordinator.wallpapers.get("backgroundMode"),
            "peers": len(coordinator.peers),
            "screenshots": coordinator.screenshots_count,
            "scripts": [s.get("filename") for s in coordinator.scripts],
            "menu_path": coordinator.menu_path,
            "indexing": coordinator.indexing,
        },
        "ssh_enabled": coordinator.ssh is not None,
        "ssh_data": coordinator.ssh_data,
    }
