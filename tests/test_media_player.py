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


async def test_volume_via_ssh(hass, init_integration, mock_ssh):
    from homeassistant.exceptions import HomeAssistantError
    from mister_fpga import MisterMainUnresponsiveError
    import pytest

    from tests.conftest import SSH_OPTIONS

    mock_ssh.async_probe.return_value = {"volume": 7, "muted": False}
    await init_integration(options=SSH_OPTIONS)
    state = hass.states.get(ENTITY)
    assert state.attributes["volume_level"] == 1.0
    assert state.attributes["is_volume_muted"] is False

    await hass.services.async_call(
        "media_player",
        "volume_set",
        {"entity_id": ENTITY, "volume_level": 0.43},
        blocking=True,
    )
    mock_ssh.async_set_volume.assert_awaited_once_with(3)
    await hass.services.async_call(
        "media_player",
        "volume_mute",
        {"entity_id": ENTITY, "is_volume_muted": True},
        blocking=True,
    )
    mock_ssh.async_set_mute.assert_awaited_once_with(True)
    assert hass.states.get(ENTITY).attributes["is_volume_muted"] is True

    mock_ssh.async_set_volume.side_effect = MisterMainUnresponsiveError("full")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "media_player",
            "volume_set",
            {"entity_id": ENTITY, "volume_level": 0.5},
            blocking=True,
        )


async def test_no_volume_without_ssh(hass, init_integration):
    from homeassistant.components.media_player import MediaPlayerEntityFeature

    await init_integration()
    features = hass.states.get(ENTITY).attributes["supported_features"]
    assert not features & MediaPlayerEntityFeature.VOLUME_SET


async def test_title_falls_back_to_sam_game(
    hass, init_integration, make_status, mock_ssh
):
    from tests.conftest import SSH_OPTIONS

    mock_ssh.async_probe.return_value = {
        "sam_active": True,
        "sam_game": "Breakers (neogeo)",
    }
    await init_integration(
        status=make_status(core="NEOGEO", game=None, game_name=None),
        options=SSH_OPTIONS,
    )
    assert hass.states.get(ENTITY).attributes["media_title"] == "Breakers (neogeo)"
