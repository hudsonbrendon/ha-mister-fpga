"""Tests for the MiSTer FPGA services."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.mister_fpga.const import DOMAIN


async def test_launch_game_service(hass, init_integration):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client, "async_launch_game", new=AsyncMock()
    ) as mock_launch:
        await hass.services.async_call(
            DOMAIN,
            "launch_game",
            {"entry_id": entry.entry_id, "path": "/games/SNES/Chrono.sfc"},
            blocking=True,
        )
    mock_launch.assert_awaited_once_with("/games/SNES/Chrono.sfc")


async def test_launch_system_service(hass, init_integration):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client, "async_launch_system", new=AsyncMock()
    ) as mock_launch:
        await hass.services.async_call(
            DOMAIN,
            "launch_system",
            {"entry_id": entry.entry_id, "system_id": "Genesis"},
            blocking=True,
        )
    mock_launch.assert_awaited_once_with("Genesis")


async def test_send_keyboard_service(hass, init_integration):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client, "async_send_keyboard", new=AsyncMock()
    ) as mock_key:
        await hass.services.async_call(
            DOMAIN,
            "send_keyboard",
            {"entry_id": entry.entry_id, "key": "up"},
            blocking=True,
        )
    mock_key.assert_awaited_once_with("up")


async def test_search_games_service_returns_response(hass, init_integration):
    entry, coordinator = await init_integration()
    payload = {"data": [{"name": "Chrono Trigger"}], "total": 1}
    with patch.object(
        coordinator.client,
        "async_search_games",
        new=AsyncMock(return_value=payload),
    ):
        response = await hass.services.async_call(
            DOMAIN,
            "search_games",
            {"entry_id": entry.entry_id, "query": "chrono"},
            blocking=True,
            return_response=True,
        )
    assert response["total"] == 1


async def test_service_unknown_entry_raises(hass, init_integration):
    await init_integration()
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "launch_game",
            {"entry_id": "does_not_exist", "path": "/x"},
            blocking=True,
        )


async def test_run_script_service(hass, init_integration):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client, "async_launch_script", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            DOMAIN,
            "run_script",
            {"entry_id": entry.entry_id, "filename": "update_all.sh"},
            blocking=True,
        )
    mock.assert_awaited_once_with("update_all.sh")


async def test_launch_path_service(hass, init_integration):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client, "async_launch_path", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            DOMAIN,
            "launch",
            {"entry_id": entry.entry_id, "path": "/media/fat/menu.rbf"},
            blocking=True,
        )
    mock.assert_awaited_once_with("/media/fat/menu.rbf")


async def test_set_ini_value_service(hass, init_integration):
    entry, coordinator = await init_integration()
    coordinator.active_ini_id = 1
    with patch.object(
        coordinator.client, "async_set_ini_values", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            DOMAIN,
            "set_ini_value",
            {"entry_id": entry.entry_id, "key": "vga_scaler", "value": "1"},
            blocking=True,
        )
    mock.assert_awaited_once_with(1, {"vga_scaler": "1"})


async def test_set_wallpaper_service(hass, init_integration):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client, "async_set_wallpaper", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            DOMAIN,
            "set_wallpaper",
            {"entry_id": entry.entry_id, "filename": "snatcher.png"},
            blocking=True,
        )
    mock.assert_awaited_once_with("snatcher.png")


async def test_send_keyboard_raw_service(hass, init_integration):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client, "async_send_keyboard_raw", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            DOMAIN,
            "send_keyboard_raw",
            {"entry_id": entry.entry_id, "code": 28},
            blocking=True,
        )
    mock.assert_awaited_once_with(28)


async def test_create_shortcut_service_returns_response(hass, init_integration):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client,
        "async_create_shortcut",
        new=AsyncMock(return_value={"path": "/x/Crash.mgl"}),
    ):
        resp = await hass.services.async_call(
            DOMAIN,
            "create_shortcut",
            {
                "entry_id": entry.entry_id,
                "game_path": "/g/Crash.chd",
                "folder": "_@Favorites",
                "name": "Crash",
            },
            blocking=True,
            return_response=True,
        )
    assert resp["path"].endswith("Crash.mgl")


async def test_launch_token_service(hass, init_integration):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client, "async_launch_token", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            DOMAIN,
            "launch_token",
            {"entry_id": entry.entry_id, "data": "bWVudS5yYmY="},
            blocking=True,
        )
    mock.assert_awaited_once_with("bWVudS5yYmY=")


async def test_set_background_mode_service(hass, init_integration):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client, "async_set_background_mode", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            DOMAIN,
            "set_background_mode",
            {"entry_id": entry.entry_id, "mode": 2},
            blocking=True,
        )
    mock.assert_awaited_once_with(2)
