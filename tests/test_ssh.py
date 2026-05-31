"""Tests for the optional SSH telemetry parsing."""
from __future__ import annotations

from custom_components.mister_fpga.ssh import parse_ssh_probe


def test_parse_ssh_probe_full():
    raw = (
        "SNES\n|||\n123456.78 100.0\n|||\n0.50 0.40 0.30 1/98 1234"
        "\n|||\n1048576\n524288\n|||\n1742860800"
    )
    data = parse_ssh_probe(raw)
    assert data["active_core"] == "SNES"
    assert data["uptime_seconds"] == 123456
    assert data["cpu_load_1m"] == 0.50
    assert data["memory_used_percent"] == 50.0
    assert data["firmware_timestamp"] == 1742860800


def test_parse_ssh_probe_partial_is_tolerant():
    raw = "MENU\n|||\n\n|||\n\n|||\n\n|||\n"
    data = parse_ssh_probe(raw)
    assert data["active_core"] == "MENU"
    assert data["uptime_seconds"] is None
    assert data["memory_used_percent"] is None
