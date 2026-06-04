"""RA sensor value-function tests."""
import types

from custom_components.mister_fpga.sensor import RA_SENSORS


def _ra(**kw):
    base = dict(
        installed=True, cores_on=True, binary_ra=True,
        hardcore=False, username="hudsonbrendon",
        cores_active=2, cores_total=15,
    )
    base.update(kw)
    return types.SimpleNamespace(ra_data=types.SimpleNamespace(**base))


def _by_key(key):
    return next(d for d in RA_SENSORS if d.key == key)


def test_ra_mode_sensor():
    assert _by_key("ra_mode").coordinator_fn(_ra(cores_on=True)) == "RA cores"
    assert _by_key("ra_mode").coordinator_fn(_ra(cores_on=False)) == "Stock"


def test_ra_binary_sensor():
    assert _by_key("ra_binary").coordinator_fn(_ra(binary_ra=True)) == "RA (odelot)"
    assert _by_key("ra_binary").coordinator_fn(_ra(binary_ra=False)) == "Stock"


def test_ra_user_sensor():
    assert _by_key("ra_user").coordinator_fn(_ra(username="x")) == "x"


def test_ra_active_cores_sensor():
    val = _by_key("ra_active_cores").coordinator_fn(_ra(cores_active=2, cores_total=15))
    assert val == "2/15"


def test_ra_sensor_none_when_no_ra_data():
    coord = types.SimpleNamespace(ra_data=None)
    assert _by_key("ra_mode").coordinator_fn(coord) is None
