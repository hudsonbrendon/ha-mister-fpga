"""Tests for MiSTer FPGA diagnostics."""
from __future__ import annotations

from custom_components.mister_fpga.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics(hass, init_integration):
    entry, coordinator = await init_integration()
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["status"]["online"] is True
    assert diag["status"]["core"] == "SNES"
    assert diag["entry"]["data"]["host"] == "192.168.31.77"
    assert diag["extras"]["screenshots"] == 0
    assert diag["ssh_enabled"] is False


async def test_diagnostics_redacts_ssh_password(hass):
    from unittest.mock import AsyncMock, patch

    from mister_fpga import MisterStatus
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.mister_fpga.const import DOMAIN
    from custom_components.mister_fpga.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "MiSTer FPGA", "host": "192.168.31.77", "port": 8182},
        options={
            "ssh_enabled": True,
            "ssh_username": "root",
            "ssh_password": "1",
            "ssh_port": 22,
        },
        entry_id="mister_ssh_test",
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "mister_fpga.client.MisterClient.async_get_status",
            new=AsyncMock(return_value=MisterStatus(online=True)),
        ),
        patch(
            "mister_fpga.client.MisterClient.async_get_music_status",
            new=AsyncMock(return_value={"playing": False}),
        ),
        patch(
            "mister_fpga.client.MisterClient.async_get_wallpapers",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "mister_fpga.client.MisterClient.async_get_inis",
            new=AsyncMock(return_value={"active": 0, "inis": []}),
        ),
        patch(
            "mister_fpga.client.MisterClient.async_get_ini_values",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "mister_fpga.client.MisterClient.async_get_peers",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "mister_fpga.client.MisterClient.async_get_screenshots",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "mister_fpga.client.MisterClient.async_get_scripts",
            new=AsyncMock(return_value={"scripts": []}),
        ),
        patch(
            "mister_fpga.client.MisterClient.async_get_music_playlists",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "custom_components.mister_fpga.coordinator"
            ".MisterDataUpdateCoordinator.async_refresh_ssh",
            new=AsyncMock(return_value=None),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["options"]["ssh_password"] == "**REDACTED**"
    assert diag["entry"]["options"]["ssh_username"] == "root"
