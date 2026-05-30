"""Diagnostics support for the MiSTer FPGA integration."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import MisterDataUpdateCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: MisterDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "status": asdict(coordinator.data) if coordinator.data else None,
        "systems_count": len(coordinator.systems),
    }
