"""Tests for the MiSTer FPGA buttons."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.parametrize(
    ("entity_id", "method"),
    [
        ("button.mister_fpga_reboot", "async_reboot"),
        ("button.mister_fpga_go_to_menu", "async_launch_menu"),
        ("button.mister_fpga_take_screenshot", "async_take_screenshot"),
        ("button.mister_fpga_restart_remote", "async_restart_remote"),
        ("button.mister_fpga_index_games", "async_index_games"),
    ],
)
async def test_button_press(hass, init_integration, entity_id, method):
    entry, coordinator = await init_integration()
    with patch.object(coordinator.client, method, new=AsyncMock()) as mock_call:
        await hass.services.async_call(
            "button", "press", {"entity_id": entity_id}, blocking=True
        )
    mock_call.assert_awaited_once()
