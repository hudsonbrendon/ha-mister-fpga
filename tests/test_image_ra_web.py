from unittest.mock import AsyncMock, MagicMock

from mister_fpga import MisterRAWebStats, RAAchievement

from custom_components.mister_fpga.image import MisterRABadgeImage


def _coord(badge_url):
    ach = (
        RAAchievement(
            title="Win",
            description="d",
            points=10,
            game_title="G",
            badge_url=badge_url,
        )
        if badge_url
        else None
    )
    c = MagicMock()
    c.data = MisterRAWebStats(last_achievement=ach)
    c.last_update_success = True
    c.web = MagicMock()
    c.web.async_get_badge_image = AsyncMock(return_value=b"PNGBYTES")
    return c


async def test_badge_image_fetches_and_caches(hass):
    coord = _coord("https://media.retroachievements.org/Badge/1.png")
    entity = MisterRABadgeImage(hass, coord, MagicMock())
    data = await entity.async_image()
    assert data == b"PNGBYTES"
    coord.web.async_get_badge_image.assert_awaited_once()
    # second call with same url: cached, no re-fetch
    await entity.async_image()
    coord.web.async_get_badge_image.assert_awaited_once()


async def test_badge_image_none_when_no_achievement(hass):
    coord = _coord(None)
    entity = MisterRABadgeImage(hass, coord, MagicMock())
    assert await entity.async_image() is None
