"""Tests for the MiSTer FPGA number entities (INI video settings)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

ENTITY = "number.mister_fpga_video_brightness"


async def test_video_number_reads_ini(hass, init_integration):
    entry, coordinator = await init_integration()
    coordinator.active_ini_id = 1
    coordinator.ini_values = {"video_brightness": "60"}
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == "60.0"


async def test_video_number_set_writes_ini(hass, init_integration):
    entry, coordinator = await init_integration()
    coordinator.active_ini_id = 1
    with patch.object(
        coordinator.client, "async_set_ini_values", new=AsyncMock()
    ) as mock:
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": ENTITY, "value": 70},
            blocking=True,
        )
    mock.assert_awaited_once_with(1, {"video_brightness": "70"})
