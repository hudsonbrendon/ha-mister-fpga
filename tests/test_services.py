"""Tests for the MiSTer FPGA services."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.exceptions import ServiceValidationError
import pytest

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
    payload = {
        "data": [{"name": "Chrono Trigger"}],
        "total": 1,
        "pageSize": 50,
        "page": 2,
    }
    with patch.object(
        coordinator.client,
        "async_search_games",
        new=AsyncMock(return_value=payload),
    ) as mock:
        response = await hass.services.async_call(
            DOMAIN,
            "search_games",
            {"entry_id": entry.entry_id, "query": "chrono", "page": 2},
            blocking=True,
            return_response=True,
        )
    assert response["total"] == 1
    assert response["page"] == 2
    mock.assert_awaited_once_with("chrono", "all", 2)


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
    with patch.object(coordinator.client, "async_launch_path", new=AsyncMock()) as mock:
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
            {"entry_id": entry.entry_id, "data": "**random:snes"},
            blocking=True,
        )
    mock.assert_awaited_once_with("**random:snes")


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


async def test_set_background_mode_rejects_invalid_mode(hass, init_integration):
    import voluptuous as vol

    entry, coordinator = await init_integration()
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "set_background_mode",
            {"entry_id": entry.entry_id, "mode": 3},
            blocking=True,
        )


async def test_delete_screenshot_service(hass, init_integration):
    entry, coordinator = await init_integration()
    with patch.object(
        coordinator.client, "async_delete_screenshot", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            DOMAIN,
            "delete_screenshot",
            {"entry_id": entry.entry_id, "core": "SNES", "filename": "a.png"},
            blocking=True,
        )
    mock.assert_awaited_once_with("SNES", "a.png")


async def test_send_command_requires_ssh(hass, init_integration):
    entry, coordinator = await init_integration()
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "send_command",
            {"entry_id": entry.entry_id, "command": "volume 5"},
            blocking=True,
        )


async def test_send_command_service(hass, init_integration, mock_ssh):
    from homeassistant.exceptions import HomeAssistantError
    from mister_fpga import MisterMainUnresponsiveError

    from tests.conftest import SSH_OPTIONS

    entry, coordinator = await init_integration(options=SSH_OPTIONS)
    await hass.services.async_call(
        DOMAIN,
        "send_command",
        {"entry_id": entry.entry_id, "command": "volume 5"},
        blocking=True,
    )
    mock_ssh.async_send_command.assert_awaited_once_with("volume 5")

    mock_ssh.async_send_command.side_effect = MisterMainUnresponsiveError("full")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "send_command",
            {"entry_id": entry.entry_id, "command": "volume 5"},
            blocking=True,
        )


async def test_gamepad_press_service(hass, init_integration):
    entry, coordinator = await init_integration()
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "gamepad_press",
            {"entry_id": entry.entry_id, "button": "start"},
            blocking=True,
        )
    coordinator.gamepad = AsyncMock()
    await hass.services.async_call(
        DOMAIN,
        "gamepad_press",
        {"entry_id": entry.entry_id, "button": "up", "action": "down"},
        blocking=True,
    )
    coordinator.gamepad.async_press.assert_awaited_once_with("up", "down")


async def test_set_ra_debug_service(hass, init_integration, mock_ssh):
    import types

    from tests.conftest import SSH_OPTIONS

    mock_ssh.ra.async_status.return_value = types.SimpleNamespace(
        installed=True,
        cores_on=True,
        hardcore=False,
        binary_ra=True,
        username="u",
        cores_active=1,
        cores_total=2,
    )
    entry, coordinator = await init_integration(options=SSH_OPTIONS)
    await hass.services.async_call(
        DOMAIN,
        "set_ra_debug",
        {"entry_id": entry.entry_id, "enabled": True},
        blocking=True,
    )
    mock_ssh.ra.async_set_debug.assert_awaited_once_with(True)


@pytest.mark.parametrize(
    ("service", "data"),
    [
        ("launch_game", {"path": "/x"}),
        ("launch_token", {"data": "**random:snes"}),
        ("send_command", {"command": "volume 5"}),
        ("send_keyboard_raw", {"code": 28}),
        ("create_shortcut", {"game_path": "/g", "folder": "_@F", "name": "n"}),
    ],
)
async def test_dangerous_services_need_admin(
    hass, init_integration, hass_read_only_user, service, data
):
    from homeassistant.core import Context
    from homeassistant.exceptions import Unauthorized

    entry, coordinator = await init_integration()
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            service,
            {"entry_id": entry.entry_id, **data},
            blocking=True,
            context=Context(user_id=hass_read_only_user.id),
            return_response=service == "create_shortcut",
        )
