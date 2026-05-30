"""Tests for the MiSTer FPGA sensors."""
from __future__ import annotations


async def test_sensors_report_status(hass, init_integration):
    await init_integration()
    assert hass.states.get("sensor.mister_fpga_core").state == "SNES"
    assert hass.states.get("sensor.mister_fpga_system").state == "Super Nintendo"
    assert hass.states.get("sensor.mister_fpga_game").state == "Chrono Trigger"
    assert hass.states.get("sensor.mister_fpga_version").state == "240101"
    assert hass.states.get("sensor.mister_fpga_hostname").state == "MiSTer"
    assert hass.states.get("sensor.mister_fpga_ip_address").state == "192.168.31.77"


async def test_sensor_unknown_when_no_game(hass, init_integration, make_status):
    await init_integration(status=make_status(game_name=None))
    assert hass.states.get("sensor.mister_fpga_game").state == "unknown"
