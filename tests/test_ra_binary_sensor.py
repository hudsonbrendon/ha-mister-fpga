"""RA supported-game binary sensor tests."""
import types

from custom_components.mister_fpga.binary_sensor import MisterRAGameSupportedSensor


def _coord(core=None, running=True, installed=True):
    return types.SimpleNamespace(
        data=types.SimpleNamespace(
            online=True, version="x", core=core,
            is_running_game=running,
        ),
        ra_data=(
            types.SimpleNamespace(installed=installed)
            if installed is not None
            else None
        ),
        client=types.SimpleNamespace(host="h", port=8182),
    )


def _sensor(coord):
    s = MisterRAGameSupportedSensor.__new__(MisterRAGameSupportedSensor)
    s.coordinator = coord
    return s


def test_on_when_supported_core_running():
    assert _sensor(_coord(core="NES", running=True)).is_on is True


def test_off_when_unsupported_core():
    assert _sensor(_coord(core="Amiga", running=True)).is_on is False


def test_off_when_in_menu():
    assert _sensor(_coord(core="NES", running=False)).is_on is False


def test_unavailable_when_not_installed():
    assert _sensor(_coord(core="NES", installed=False)).available is False
