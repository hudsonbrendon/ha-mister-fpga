from unittest.mock import MagicMock

from mister_fpga import MisterRAWebStats

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
