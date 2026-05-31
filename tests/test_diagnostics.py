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
