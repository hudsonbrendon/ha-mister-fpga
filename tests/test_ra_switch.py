"""RA switch entity tests."""
import types

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.mister_fpga.switch import (
    MisterRACoresSwitch,
    MisterRAHardcoreSwitch,
)


async def _noop():
    return None


def _coord(installed=True, cores_on=False, hardcore=False, ra=None):
    ra_data = (
        types.SimpleNamespace(
            installed=installed, cores_on=cores_on, hardcore=hardcore
        )
        if installed is not None
        else None
    )
    return types.SimpleNamespace(
        data=types.SimpleNamespace(online=True, version="x"),
        ra=ra,
        ra_data=ra_data,
        client=types.SimpleNamespace(host="h", port=8182),
        async_request_refresh=_noop,
    )


def test_cores_switch_is_on_reflects_state():
    sw = MisterRACoresSwitch.__new__(MisterRACoresSwitch)
    sw.coordinator = _coord(cores_on=True)
    assert sw.is_on is True
    sw.coordinator = _coord(cores_on=False)
    assert sw.is_on is False


def test_cores_switch_unavailable_when_not_installed():
    sw = MisterRACoresSwitch.__new__(MisterRACoresSwitch)
    sw.coordinator = _coord(installed=False)
    assert sw.available is False


@pytest.mark.asyncio
async def test_cores_turn_on_calls_lib_and_refreshes():
    calls = []

    class _RA:
        async def async_cores_on(self):
            calls.append("on")

        async def async_cores_off(self):
            calls.append("off")

    coord = _coord(ra=_RA())
    sw = MisterRACoresSwitch.__new__(MisterRACoresSwitch)
    sw.coordinator = coord
    sw.async_write_ha_state = lambda: None
    await sw.async_turn_on()
    await sw.async_turn_off()
    assert calls == ["on", "off"]


@pytest.mark.asyncio
async def test_control_error_becomes_homeassistant_error():
    from mister_fpga import MisterRAError

    class _RA:
        async def async_cores_on(self):
            raise MisterRAError("boom")

    coord = _coord(ra=_RA())
    sw = MisterRACoresSwitch.__new__(MisterRACoresSwitch)
    sw.coordinator = coord
    sw.async_write_ha_state = lambda: None
    with pytest.raises(HomeAssistantError):
        await sw.async_turn_on()


@pytest.mark.asyncio
async def test_hardcore_switch_sets_value():
    seen = []

    class _RA:
        async def async_set_hardcore(self, enabled):
            seen.append(enabled)

    coord = _coord(ra=_RA(), hardcore=False)
    sw = MisterRAHardcoreSwitch.__new__(MisterRAHardcoreSwitch)
    sw.coordinator = coord
    sw.async_write_ha_state = lambda: None
    await sw.async_turn_on()
    await sw.async_turn_off()
    assert seen == [True, False]
