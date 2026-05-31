"""Tests for the MiSTer FPGA coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock

from custom_components.mister_fpga.api import MisterConnectionError, MisterStatus
from custom_components.mister_fpga.const import EVENT_GAME_CHANGED
from custom_components.mister_fpga.coordinator import MisterDataUpdateCoordinator


async def test_update_returns_status(hass):
    client = AsyncMock()
    client.async_get_status.return_value = MisterStatus(online=True, core="SNES")
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    data = await coordinator._async_update_data()
    assert data.online is True
    assert data.core == "SNES"


async def test_update_offline_on_error(hass):
    client = AsyncMock()
    client.async_get_status.side_effect = MisterConnectionError("boom")
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    data = await coordinator._async_update_data()
    assert data.online is False


async def test_fires_event_on_game_change(hass):
    client = AsyncMock()
    client.async_get_status.return_value = MisterStatus(
        online=True, core="SNES", game="/g/a.sfc", game_name="A", system_name="SNES"
    )
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)

    events = []
    hass.bus.async_listen(EVENT_GAME_CHANGED, lambda e: events.append(e))

    await coordinator._async_update_data()
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["game"] == "A"

    # same game again -> no new event
    await coordinator._async_update_data()
    await hass.async_block_till_done()
    assert len(events) == 1


async def test_refresh_systems_swallows_errors(hass):
    client = AsyncMock()
    client.async_get_systems.side_effect = MisterConnectionError("boom")
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    await coordinator.async_refresh_systems()
    assert coordinator.systems == []


async def test_coordinator_collects_extras(hass):
    from unittest.mock import AsyncMock
    client = AsyncMock()
    client.async_get_status.return_value = MisterStatus(online=True, core="SNES")
    client.async_get_music_status.return_value = {
        "running": True, "playing": True, "track": "x.mp3",
        "playlist": "Vidya", "playback": "random",
    }
    client.async_get_wallpapers.return_value = {
        "active": "a.png", "backgroundMode": 2,
        "wallpapers": [{"filename": "a.png"}],
    }
    client.async_get_inis.return_value = {
        "active": 0, "inis": [{"id": 1, "displayName": "Main"}],
    }
    client.async_get_ini_values.return_value = {
        "__ethernetMacAddress": "AA:BB", "video_brightness": "50",
    }
    client.async_get_peers.return_value = [{"ip": "1.2.3.4"}]
    client.async_get_screenshots.return_value = [
        {"core": "SNES", "filename": "s.png", "modified": "2026-01-01"},
    ]
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    await coordinator.async_refresh_extras()
    assert coordinator.music["track"] == "x.mp3"
    assert coordinator.wallpapers["active"] == "a.png"
    assert coordinator.active_ini_id == 1  # active 0 falls back to 1
    assert coordinator.mac_address == "AA:BB"
    assert coordinator.ini_values["video_brightness"] == "50"
    assert coordinator.peers[0]["ip"] == "1.2.3.4"
    assert coordinator.screenshots_count == 1


async def test_coordinator_extras_tolerate_errors(hass):
    from unittest.mock import AsyncMock
    client = AsyncMock()
    client.async_get_status.return_value = MisterStatus(online=True)
    client.async_get_music_status.side_effect = MisterConnectionError("x")
    client.async_get_wallpapers.side_effect = MisterConnectionError("x")
    client.async_get_inis.side_effect = MisterConnectionError("x")
    client.async_get_ini_values.side_effect = MisterConnectionError("x")
    client.async_get_peers.side_effect = MisterConnectionError("x")
    client.async_get_screenshots.side_effect = MisterConnectionError("x")
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    await coordinator.async_refresh_extras()  # must not raise
    assert coordinator.music == {}
    assert coordinator.ini_values == {}
    assert coordinator.screenshots_count == 0


async def test_coordinator_refresh_scripts(hass):
    from unittest.mock import AsyncMock
    client = AsyncMock()
    client.async_get_scripts.return_value = {
        "canLaunch": True, "scripts": [{"name": "a", "filename": "a.sh"}],
    }
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    await coordinator.async_refresh_scripts()
    assert coordinator.scripts[0]["filename"] == "a.sh"
