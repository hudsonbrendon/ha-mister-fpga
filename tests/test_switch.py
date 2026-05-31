"""Tests for the MiSTer FPGA background music switch."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

ENTITY = "switch.mister_fpga_background_music"


async def test_switch_turn_on(hass, init_integration):
    with patch(
        "mister_fpga.client.MisterClient.async_get_music_status",
        new=AsyncMock(return_value={"playing": False}),
    ):
        entry, coordinator = await init_integration()
        with patch.object(
            coordinator.client, "async_music_play", new=AsyncMock()
        ) as mock_play:
            await hass.services.async_call(
                "switch", "turn_on", {"entity_id": ENTITY}, blocking=True
            )
    mock_play.assert_awaited_once()
    assert hass.states.get(ENTITY).state == "on"


async def test_switch_turn_off(hass, init_integration):
    with patch(
        "mister_fpga.client.MisterClient.async_get_music_status",
        new=AsyncMock(return_value={"playing": False}),
    ):
        entry, coordinator = await init_integration()
        with patch.object(
            coordinator.client, "async_music_stop", new=AsyncMock()
        ) as mock_stop:
            await hass.services.async_call(
                "switch", "turn_off", {"entity_id": ENTITY}, blocking=True
            )
    mock_stop.assert_awaited_once()
    assert hass.states.get(ENTITY).state == "off"
