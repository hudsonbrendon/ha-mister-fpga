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


async def test_run_script_select(hass, init_integration):
    entry, coordinator = await init_integration()
    coordinator.scripts = [{"name": "update_all", "filename": "update_all.sh"}]
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()
    state = hass.states.get("select.mister_fpga_run_script")
    assert "update_all" in state.attributes["options"]
    with patch.object(
        coordinator.client, "async_launch_script", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": "select.mister_fpga_run_script", "option": "update_all"},
            blocking=True,
        )
    mock.assert_awaited_once_with("update_all.sh")


async def test_background_mode_select(hass, init_integration):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client, "async_set_background_mode", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": "select.mister_fpga_background_mode", "option": "Wallpaper"},
            blocking=True,
        )
    mock.assert_awaited_once_with(2)


async def test_active_ini_select(hass, init_integration):
    entry, coordinator = await init_integration()
    coordinator.inis = [
        {"id": 1, "displayName": "Main"},
        {"id": 2, "displayName": "exam"},
    ]
    coordinator.active_ini_id = 1
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()
    with patch.object(
        coordinator.client, "async_set_active_ini", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": "select.mister_fpga_active_ini", "option": "exam"},
            blocking=True,
        )
    mock.assert_awaited_once_with(2)
