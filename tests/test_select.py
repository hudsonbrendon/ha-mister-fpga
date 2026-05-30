"""Tests for the MiSTer FPGA system select."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

ENTITY = "select.mister_fpga_launch_system"


async def test_options_from_systems(hass, init_integration):
    systems = [
        {"id": "SNES", "name": "Super Nintendo", "category": "Console"},
        {"id": "Genesis", "name": "Sega Genesis", "category": "Console"},
    ]
    await init_integration(systems=systems)
    state = hass.states.get(ENTITY)
    assert state.attributes["options"] == ["Sega Genesis", "Super Nintendo"]
    assert state.state == "Super Nintendo"


async def test_select_launches_system(hass, init_integration):
    systems = [{"id": "Genesis", "name": "Sega Genesis", "category": "Console"}]
    entry, coordinator = await init_integration(systems=systems)
    with patch.object(
        coordinator.client, "async_launch_system", new=AsyncMock()
    ) as mock_launch:
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": ENTITY, "option": "Sega Genesis"},
            blocking=True,
        )
    mock_launch.assert_awaited_once_with("Genesis")
