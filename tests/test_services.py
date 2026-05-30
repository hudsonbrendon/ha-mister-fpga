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
