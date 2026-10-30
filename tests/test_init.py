"""Tests for integration setup/unload."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState


async def test_setup_and_unload(hass, init_integration):
    entry, coordinator = await init_integration()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is coordinator
    assert coordinator.data.online is True

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    coordinator.websocket.stop.assert_awaited_once()


async def test_setup_with_offline_device(hass, init_integration, make_status):
    entry, coordinator = await init_integration(status=make_status(online=False))
    assert entry.state is ConfigEntryState.LOADED
    assert coordinator.data.online is False


async def test_setup_starts_websocket_and_scripts(
    hass, init_integration, mock_websocket
):
    entry, coordinator = await init_integration()
    assert mock_websocket.called
    mock_websocket.return_value.start.assert_called_once()
    assert entry.runtime_data is coordinator
