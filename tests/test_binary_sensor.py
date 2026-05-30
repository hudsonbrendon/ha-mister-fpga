"""Tests for the MiSTer FPGA binary sensor."""
from __future__ import annotations

BINARY_SENSOR_ENTITY_ID = "binary_sensor.mister_fpga_online"


async def test_online_binary_sensor(hass, init_integration, make_status):
    await init_integration(status=make_status(online=True))
    state = hass.states.get(BINARY_SENSOR_ENTITY_ID)
    assert state is not None
    assert state.state == "on"


async def test_offline_binary_sensor(hass, init_integration, make_status):
    await init_integration(status=make_status(online=False))
    state = hass.states.get(BINARY_SENSOR_ENTITY_ID)
    assert state.state == "off"
