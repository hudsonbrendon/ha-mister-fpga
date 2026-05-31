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


async def test_bgm_and_game_and_indexing_binary_sensors(
    hass, init_integration, make_status
):
    entry, coordinator = await init_integration(
        status=make_status(core="SNES", game="x", game_name="X")
    )
    coordinator.music = {"running": True}
    coordinator.indexing = True
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.mister_fpga_game_running").state == "on"
    bgm = hass.states.get("binary_sensor.mister_fpga_background_music_active")
    assert bgm.state == "on"
    assert hass.states.get("binary_sensor.mister_fpga_indexing").state == "on"


async def test_game_running_off_in_menu(hass, init_integration, make_status):
    entry, coordinator = await init_integration(
        status=make_status(core="MENU", game=None, game_name=None)
    )
    assert hass.states.get("binary_sensor.mister_fpga_game_running").state == "off"
