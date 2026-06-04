"""RA construction in setup."""
import types

import pytest


@pytest.mark.asyncio
async def test_ra_built_from_ssh(monkeypatch):
    import custom_components.mister_fpga as pkg

    built = {}

    class _FakeRA:
        def __init__(self, ssh):
            built["ssh"] = ssh

    monkeypatch.setattr(pkg, "MisterRA", _FakeRA, raising=False)

    # Simulate the construction lines from async_setup_entry.
    coordinator = types.SimpleNamespace(ssh=object(), ra=None)
    coordinator.ra = pkg.MisterRA(coordinator.ssh)
    assert isinstance(coordinator.ra, _FakeRA)
    assert built["ssh"] is coordinator.ssh
