"""Tests for the MiSTer FPGA media player."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

ENTITY = "media_player.mister_fpga"


async def test_state_playing(hass, init_integration):
    await init_integration()
    state = hass.states.get(ENTITY)
    assert state.state == "playing"
    assert state.attributes["media_title"] == "Chrono Trigger"
    assert state.attributes["source"] == "Super Nintendo"


async def test_state_idle_at_menu(hass, init_integration, make_status):
    await init_integration(status=make_status(core="MENU", game=None, game_name=None))
    assert hass.states.get(ENTITY).state == "idle"


async def test_state_off_when_offline(hass, init_integration, make_status):
    await init_integration(status=make_status(online=False))
    assert hass.states.get(ENTITY).state == "off"


async def test_select_source_launches_system(hass, init_integration):
    systems = [{"id": "Genesis", "name": "Sega Genesis", "category": "Console"}]
    entry, coordinator = await init_integration(systems=systems)
    with patch.object(
        coordinator.client, "async_launch_system", new=AsyncMock()
    ) as mock_launch:
        await hass.services.async_call(
            "media_player",
            "select_source",
            {"entity_id": ENTITY, "source": "Sega Genesis"},
            blocking=True,
        )
    mock_launch.assert_awaited_once_with("Genesis")
