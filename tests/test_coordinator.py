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
