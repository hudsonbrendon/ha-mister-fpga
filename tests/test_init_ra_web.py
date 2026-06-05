from unittest.mock import MagicMock

from custom_components.mister_fpga import _build_ra_web_coordinator
from custom_components.mister_fpga.const import (
    CONF_RA_API_KEY,
    CONF_RA_CLOUD_INTERVAL,
    CONF_RA_USERNAME,
)
from custom_components.mister_fpga.ra_web_coordinator import MisterRAWebCoordinator


def _entry(options):
    e = MagicMock()
    e.options = options
    return e


def test_no_creds_returns_none(hass):
    assert _build_ra_web_coordinator(hass, _entry({}), MagicMock()) is None


def test_partial_creds_returns_none(hass):
    assert (
        _build_ra_web_coordinator(hass, _entry({CONF_RA_USERNAME: "u"}), MagicMock())
        is None
    )


def test_full_creds_builds_coordinator(hass):
    coord = _build_ra_web_coordinator(
        hass,
        _entry(
            {
                CONF_RA_USERNAME: "u",
                CONF_RA_API_KEY: "k",
                CONF_RA_CLOUD_INTERVAL: 120,
            }
        ),
        MagicMock(),
    )
    assert isinstance(coord, MisterRAWebCoordinator)
    assert coord.update_interval.total_seconds() == 120
    assert coord.web.username == "u"
