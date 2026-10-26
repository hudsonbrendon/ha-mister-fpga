"""Tests for the MiSTer FPGA sensors."""
from __future__ import annotations


async def test_sensors_report_status(hass, init_integration):
    await init_integration()
    assert hass.states.get("sensor.mister_fpga_core").state == "SNES"
    assert hass.states.get("sensor.mister_fpga_system").state == "Super Nintendo"
    assert hass.states.get("sensor.mister_fpga_game").state == "Chrono Trigger"
    assert hass.states.get("sensor.mister_fpga_remote_version").state == "240101"
    assert hass.states.get("sensor.mister_fpga_hostname").state == "MiSTer"
    assert hass.states.get("sensor.mister_fpga_ip_address").state == "192.168.31.77"


async def test_sensor_unknown_when_no_game(hass, init_integration, make_status):
    await init_integration(status=make_status(game_name=None))
    assert hass.states.get("sensor.mister_fpga_game").state == "unknown"


async def test_disk_and_meta_sensors(hass, init_integration, make_status):
    GIB = 1024 ** 3
    status = make_status(
        disk_total=100 * GIB, disk_used=75 * GIB, disk_free=25 * GIB, dns="MiSTer.local"
    )
    entry, coordinator = await init_integration(status=status)
    assert hass.states.get("sensor.mister_fpga_disk_free").state == "25.0"
    assert hass.states.get("sensor.mister_fpga_disk_usage").state == "75.0"
    assert hass.states.get("sensor.mister_fpga_remote_version").state == "240101"
    assert hass.states.get("sensor.mister_fpga_dns_name").state == "MiSTer.local"


async def test_extras_sensors(hass, init_integration):
    entry, coordinator = await init_integration()
    coordinator.music = {"track": "song.mp3", "playlist": "Vidya", "playback": "random"}
    coordinator.mac_address = "AA:BB:CC"
    coordinator.peers = [{"ip": "1.2.3.4"}]
    coordinator.screenshots_count = 3
    coordinator.menu_path = "_Console/SNES"
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.mister_fpga_music_track").state == "song.mp3"
    assert hass.states.get("sensor.mister_fpga_mac_address").state == "AA:BB:CC"
    assert hass.states.get("sensor.mister_fpga_peers").state == "1"
    assert hass.states.get("sensor.mister_fpga_screenshots").state == "3"
    assert hass.states.get("sensor.mister_fpga_menu_position").state == "_Console/SNES"


async def test_ssh_sensors_present(hass, init_integration):
    entry, coordinator = await init_integration()
    coordinator.ssh_data = {
        "active_core": "SNES",
        "uptime_seconds": 3600,
        "cpu_load_1m": 0.5,
        "memory_used_percent": 42.0,
    }
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.mister_fpga_active_core").state == "SNES"
    assert hass.states.get("sensor.mister_fpga_cpu_load").state == "0.5"
    assert hass.states.get("sensor.mister_fpga_memory_used").state == "42.0"


async def test_session_time_attributes(hass, init_integration, make_status):
    await init_integration(
        status=make_status(core_session_time=600, game_session_time=120)
    )
    core = hass.states.get("sensor.mister_fpga_core")
    game = hass.states.get("sensor.mister_fpga_game")
    assert core.attributes["core_session_time"] == 600
    assert game.attributes["game_session_time"] == 120
    assert game.attributes["game_path"] is None


async def test_ssh_only_sensors(hass, init_integration, mock_ssh):
    from tests.conftest import SSH_OPTIONS

    mock_ssh.async_probe.return_value = {
        "main_open_fds": 42,
        "sam_game": "Breakers (neogeo)",
        "game_id": "A1B2C3D4",
    }
    await init_integration(options=SSH_OPTIONS)
    assert hass.states.get("sensor.mister_fpga_main_open_file_descriptors").state == (
        "42"
    )
    assert hass.states.get("sensor.mister_fpga_sam_game").state == "Breakers (neogeo)"
    assert hass.states.get("sensor.mister_fpga_game_id").state == "A1B2C3D4"


async def test_ssh_only_sensors_absent_without_ssh(hass, init_integration):
    await init_integration()
    assert hass.states.get("sensor.mister_fpga_sam_game") is None
    assert hass.states.get("sensor.mister_fpga_play_time_today") is None


async def test_playlog_sensors(hass, init_integration):
    from unittest.mock import AsyncMock, patch

    async def _summary(top=None, days=None):
        if days == 1:
            return {"days": [{"date": "2026-10-26", "time": 1800}]}
        return {
            "totalTime": 7200,
            "gamesPlayed": 3,
            "sessions": 9,
            "currentStreak": 2,
            "longestStreak": 5,
            "topGames": [{"name": "Chrono Trigger", "time": 5000}],
            "topSystems": [{"name": "SNES", "time": 6000}],
        }

    with patch(
        "mister_fpga.client.MisterClient.async_get_playlog_status",
        new=AsyncMock(return_value={"running": True}),
    ), patch(
        "mister_fpga.client.MisterClient.async_get_playlog_summary",
        new=AsyncMock(side_effect=_summary),
    ):
        await init_integration()

    assert float(hass.states.get("sensor.mister_fpga_play_time_today").state) == 30
    assert float(hass.states.get("sensor.mister_fpga_total_play_time").state) == 2
    assert hass.states.get("sensor.mister_fpga_games_played").state == "3"
    assert hass.states.get("sensor.mister_fpga_play_sessions").state == "9"
    assert hass.states.get("sensor.mister_fpga_current_streak").state == "2"
    assert hass.states.get("sensor.mister_fpga_longest_streak").state == "5"
    top = hass.states.get("sensor.mister_fpga_top_game")
    assert top.state == "Chrono Trigger"
    assert top.attributes["top_games"][0]["time"] == 5000
