from unittest.mock import AsyncMock, MagicMock, patch

from mister_fpga import MisterRAWebStats, MisterStatus

from custom_components.mister_fpga.diagnostics import _ra_web_diagnostics


def test_ra_web_diagnostics_none():
    coord = MagicMock()
    coord.ra_web_coordinator = None
    assert _ra_web_diagnostics(coord) is None


def test_ra_web_diagnostics_dump():
    coord = MagicMock()
    coord.ra_web_coordinator.data = MisterRAWebStats(hardcore_points=42)
    dump = _ra_web_diagnostics(coord)
    assert dump["hardcore_points"] == 42


async def test_diagnostics_redacts_ra_api_key(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.mister_fpga.const import DOMAIN
    from custom_components.mister_fpga.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "MiSTer FPGA", "host": "192.168.31.77", "port": 8182},
        options={
            "ra_username": "hudsonbrendon",
            "ra_api_key": "secret123",
        },
        entry_id="mister_ra_key_test",
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
    assert diag["entry"]["options"]["ra_api_key"] == "**REDACTED**"
    assert diag["entry"]["options"]["ra_username"] == "hudsonbrendon"
