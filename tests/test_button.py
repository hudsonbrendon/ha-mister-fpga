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


@pytest.mark.parametrize(
    ("entity_id", "method"),
    [
        ("button.mister_fpga_next_track", "async_music_next"),
        ("button.mister_fpga_clear_wallpaper", "async_clear_wallpaper"),
        ("button.mister_fpga_framebuffer_console", "async_open_console"),
        ("button.mister_fpga_kill_script", "async_kill_script"),
    ],
)
async def test_extra_action_buttons(hass, init_integration, entity_id, method):
    entry, coordinator = await init_integration()
    with patch.object(coordinator.client, method, new=AsyncMock()) as mock:
        await hass.services.async_call(
            "button", "press", {"entity_id": entity_id}, blocking=True
        )
    mock.assert_awaited_once()


@pytest.mark.parametrize(
    ("entity_id", "key"),
    [
        ("button.mister_fpga_nav_up", "up"),
        ("button.mister_fpga_nav_down", "down"),
        ("button.mister_fpga_nav_confirm", "confirm"),
        ("button.mister_fpga_nav_back", "back"),
        ("button.mister_fpga_nav_osd", "osd"),
        ("button.mister_fpga_nav_volume_up", "volume_up"),
    ],
)
async def test_navigation_buttons(hass, init_integration, entity_id, key):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client, "async_send_keyboard", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            "button", "press", {"entity_id": entity_id}, blocking=True
        )
    mock.assert_awaited_once_with(key)


async def test_gamepad_buttons_when_daemon_available(hass, init_integration):
    with patch(
        "mister_fpga.gamepad.MisterGamepad.async_available",
        new=AsyncMock(return_value=True),
    ):
        entry, coordinator = await init_integration()
    assert coordinator.gamepad is not None
    with patch.object(coordinator.gamepad, "async_press", new=AsyncMock()) as mock:
        await hass.services.async_call(
            "button", "press",
            {"entity_id": "button.mister_fpga_gamepad_start"}, blocking=True,
        )
    mock.assert_awaited_once_with("start")
    for name in ("select", "a", "b", "home"):
        assert hass.states.get(f"button.mister_fpga_gamepad_{name}") is not None


async def test_no_gamepad_buttons_without_daemon(hass, init_integration):
    await init_integration()
    assert hass.states.get("button.mister_fpga_gamepad_start") is None


async def test_gamepad_option_off_skips_probe(hass, init_integration):
    probe = AsyncMock(return_value=True)
    with patch("mister_fpga.gamepad.MisterGamepad.async_available", new=probe):
        entry, coordinator = await init_integration(
            options={"gamepad_enabled": False}
        )
    probe.assert_not_called()
    assert coordinator.gamepad is None
