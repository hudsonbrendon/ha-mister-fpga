"""Tests for integration setup/unload."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState

from custom_components.mister_fpga.const import DOMAIN


async def test_setup_and_unload(hass, init_integration):
    entry, coordinator = await init_integration()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.entry_id in hass.data[DOMAIN]
    assert coordinator.data.online is True

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_setup_with_offline_device(hass, init_integration, make_status):
    entry, coordinator = await init_integration(status=make_status(online=False))
    assert entry.state is ConfigEntryState.LOADED
    assert coordinator.data.online is False
