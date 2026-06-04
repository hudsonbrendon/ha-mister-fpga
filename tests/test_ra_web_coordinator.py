import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from mister_fpga import MisterRAWebStats
from mister_fpga.ra_web import MisterRAWebError

from custom_components.mister_fpga.ra_web_coordinator import MisterRAWebCoordinator


class _FakeWeb:
    def __init__(self, stats=None, error=False):
        self._stats = stats or MisterRAWebStats(hardcore_points=42)
        self._error = error

    async def async_fetch_stats(self):
        if self._error:
            raise MisterRAWebError("boom")
        return self._stats


async def test_coordinator_returns_stats(hass):
    coord = MisterRAWebCoordinator(hass, _FakeWeb(), 300)
    data = await coord._async_update_data()
    assert data.hardcore_points == 42


async def test_coordinator_maps_error_to_update_failed(hass):
    coord = MisterRAWebCoordinator(hass, _FakeWeb(error=True), 300)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()
