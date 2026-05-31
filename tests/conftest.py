"""Shared fixtures for the MiSTer FPGA tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mister_fpga.api import MisterStatus
from custom_components.mister_fpga.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of the custom integration in every test."""
    yield


@pytest.fixture(autouse=True)
def mock_clientsession():
    """Replace async_get_clientsession with a fake to avoid lingering threads."""
    session = MagicMock()
    patchers = []
    for target in (
        "custom_components.mister_fpga.async_get_clientsession",
        "custom_components.mister_fpga.config_flow.async_get_clientsession",
    ):
        try:
            p = patch(target, return_value=session)
            p.start()
            patchers.append(p)
        except (AttributeError, ModuleNotFoundError):
            # Module/attribute not present yet (created in a later task).
            continue
    yield session
    for p in patchers:
        p.stop()


@pytest.fixture(autouse=True)
def mock_websocket():
    """Prevent the real WebSocket background task from starting in tests."""
    with patch("custom_components.mister_fpga.MisterWebSocket") as ws_cls:
        instance = ws_cls.return_value
        instance.start = MagicMock()
        instance.stop = AsyncMock()
        yield ws_cls


@pytest.fixture(autouse=True)
def mock_refresh_systems():
    """Stop setup from making a real /systems call; tests set systems manually."""
    target = (
        "custom_components.mister_fpga.coordinator."
        "MisterDataUpdateCoordinator.async_refresh_systems"
    )
    p = patch(target, new=AsyncMock(return_value=None))
    p.start()
    yield
    p.stop()


@pytest.fixture
def make_status():
    """Factory for a fully-populated MisterStatus, overridable per test."""

    def _make(**overrides) -> MisterStatus:
        defaults = dict(
            online=True,
            core="SNES",
            system="SNES",
            system_name="Super Nintendo",
            game="/games/SNES/Chrono.sfc",
            game_name="Chrono Trigger",
            hostname="MiSTer",
            version="240101",
            ip="192.168.31.77",
            ips=["192.168.31.77"],
            updated="2026-05-30",
        )
        defaults.update(overrides)
        return MisterStatus(**defaults)

    return _make


@pytest.fixture
def init_integration(hass, make_status):
    """Set up the integration with a patched client status.

    Returns (entry, coordinator).
    """

    async def _init(status=None, systems=None):
        if status is None:
            status = make_status()
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="MiSTer FPGA",
            data={"name": "MiSTer FPGA", "host": "192.168.31.77", "port": 8182},
            entry_id="mister_test",
        )
        entry.add_to_hass(hass)
        with patch(
            "custom_components.mister_fpga.api.MisterClient.async_get_status",
            new=AsyncMock(return_value=status),
        ), patch(
            "custom_components.mister_fpga.api.MisterClient.async_get_music_status",
            new=AsyncMock(return_value={"playing": False}),
        ), patch(
            "custom_components.mister_fpga.api.MisterClient.async_get_wallpapers",
            new=AsyncMock(return_value={}),
        ), patch(
            "custom_components.mister_fpga.api.MisterClient.async_get_inis",
            new=AsyncMock(return_value={"active": 0, "inis": []}),
        ), patch(
            "custom_components.mister_fpga.api.MisterClient.async_get_ini_values",
            new=AsyncMock(return_value={}),
        ), patch(
            "custom_components.mister_fpga.api.MisterClient.async_get_peers",
            new=AsyncMock(return_value=[]),
        ), patch(
            "custom_components.mister_fpga.api.MisterClient.async_get_screenshots",
            new=AsyncMock(return_value=[]),
        ), patch(
            "custom_components.mister_fpga.api.MisterClient.async_get_scripts",
            new=AsyncMock(return_value={"scripts": []}),
        ):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
        coordinator = hass.data[DOMAIN][entry.entry_id]
        if systems is not None:
            coordinator.systems = systems
            coordinator.async_set_updated_data(coordinator.data)
            await hass.async_block_till_done()
        return entry, coordinator

    return _init
