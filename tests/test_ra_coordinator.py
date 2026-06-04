"""Coordinator RA wiring tests."""
import types

import pytest


def _make_coordinator():
    from custom_components.mister_fpga.coordinator import (
        MisterDataUpdateCoordinator,
    )
    coord = MisterDataUpdateCoordinator.__new__(MisterDataUpdateCoordinator)
    coord.ssh = None
    coord.ra = None
    coord.ra_data = None
    coord.ssh_data = {}
    return coord


@pytest.mark.asyncio
async def test_refresh_ssh_populates_ra_data():
    coord = _make_coordinator()

    class _FakeSSH:
        async def async_probe(self):
            return {"active_core": "NES"}

    class _FakeRA:
        async def async_status(self):
            return types.SimpleNamespace(installed=True, cores_on=True)

    coord.ssh = _FakeSSH()
    coord.ra = _FakeRA()
    await coord.async_refresh_ssh()
    assert coord.ssh_data == {"active_core": "NES"}
    assert coord.ra_data.installed is True


@pytest.mark.asyncio
async def test_refresh_ssh_noop_without_ssh():
    coord = _make_coordinator()
    await coord.async_refresh_ssh()
    assert coord.ra_data is None
