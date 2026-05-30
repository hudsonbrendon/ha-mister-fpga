"""Tests for the MiSTer FPGA screenshot image entity."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from custom_components.mister_fpga.image import MisterScreenshotImage

ENTITY = "image.mister_fpga_latest_screenshot"


async def test_image_entity_created(hass, init_integration):
    await init_integration()
    assert hass.states.get(ENTITY) is not None


async def test_async_image_fetches_latest(hass, init_integration):
    entry, coordinator = await init_integration()
    shots = [
        {"core": "SNES", "filename": "old.png", "modified": "2026-05-01"},
        {"core": "SNES", "filename": "new.png", "modified": "2026-05-30"},
    ]
    image_entity = MisterScreenshotImage(hass, coordinator, entry)
    with patch.object(
        coordinator.client, "async_get_screenshots", new=AsyncMock(return_value=shots)
    ), patch.object(
        coordinator.client,
        "async_get_screenshot_image",
        new=AsyncMock(return_value=b"\x89PNG-new"),
    ) as mock_img:
        data = await image_entity.async_image()
    assert data == b"\x89PNG-new"
    mock_img.assert_awaited_once_with("SNES", "new.png")


async def test_image_last_updated_advances_on_refresh(
    hass, init_integration, make_status
):
    entry, coordinator = await init_integration()
    state_before = hass.states.get(ENTITY).state
    coordinator.async_set_updated_data(make_status(game_name="Other Game"))
    await hass.async_block_till_done()
    state_after = hass.states.get(ENTITY).state
    # The image entity's state is its image_last_updated timestamp; it must
    # change (advance) after a coordinator update so the frontend re-fetches.
    assert state_after != "unknown"
    assert state_after != state_before
