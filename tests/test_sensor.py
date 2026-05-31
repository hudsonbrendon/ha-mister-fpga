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
