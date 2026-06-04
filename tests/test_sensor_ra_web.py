from unittest.mock import MagicMock

from mister_fpga import MisterRAWebStats, RAAchievement, RAGameProgress

from custom_components.mister_fpga.sensor_ra_web import (
    RA_WEB_SENSORS,
    MisterRAWebSensor,
)


def _coord(stats, success=True):
    c = MagicMock()
    c.data = stats
    c.last_update_success = success
    return c


def _by_key(key):
    return next(d for d in RA_WEB_SENSORS if d.key == key)


def test_points_and_rank():
    stats = MisterRAWebStats(
        hardcore_points=100, softcore_points=20, rank=5, total_ranked=999
    )
    assert _by_key("ra_hardcore_points").value_fn(stats) == 100
    assert _by_key("ra_softcore_points").value_fn(stats) == 20
    rank_desc = _by_key("ra_rank")
    assert rank_desc.value_fn(stats) == 5
    assert rank_desc.attr_fn(stats) == {"total_ranked": 999}


def test_current_game():
    g = RAGameProgress(
        game_id=1,
        title="Mario",
        console="NES",
        num_achieved=3,
        num_possible=6,
        percent=50.0,
        last_played="2024-01-01 00:00:00",
    )
    stats = MisterRAWebStats(current_game=g)
    desc = _by_key("ra_current_game")
    assert desc.value_fn(stats) == "Mario"
    attrs = desc.attr_fn(stats)
    assert attrs["earned"] == 3
    assert attrs["possible"] == 6
    assert attrs["percent"] == 50.0
    assert attrs["console"] == "NES"


def test_current_game_none():
    stats = MisterRAWebStats(current_game=None)
    desc = _by_key("ra_current_game")
    assert desc.value_fn(stats) is None
    assert desc.attr_fn(stats) == {}


def test_last_achievement():
    a = RAAchievement(
        title="Win",
        description="d",
        points=10,
        game_title="Mario",
        date="2024-01-01 00:00:00",
        badge_url="https://media.retroachievements.org/Badge/1.png",
    )
    stats = MisterRAWebStats(last_achievement=a)
    desc = _by_key("ra_last_achievement")
    assert desc.value_fn(stats) == "Win"
    attrs = desc.attr_fn(stats)
    assert attrs["game"] == "Mario"
    assert attrs["points"] == 10
    assert attrs["badge_url"].endswith("/Badge/1.png")


def test_recent_games():
    g1 = RAGameProgress(game_id=1, title="A", console="NES", percent=10.0)
    g2 = RAGameProgress(game_id=2, title="B", console="SNES", percent=20.0)
    stats = MisterRAWebStats(recent_games=[g1, g2])
    desc = _by_key("ra_recent_games")
    assert desc.value_fn(stats) == "A"
    games = desc.attr_fn(stats)["games"]
    assert len(games) == 2
    assert games[0]["title"] == "A"
    assert games[1]["percent"] == 20.0


def test_entity_availability_and_value():
    stats = MisterRAWebStats(hardcore_points=100)
    entity = MisterRAWebSensor(
        _coord(stats), MagicMock(), _by_key("ra_hardcore_points")
    )
    assert entity.native_value == 100
    entity_down = MisterRAWebSensor(
        _coord(stats, success=False), MagicMock(), _by_key("ra_hardcore_points")
    )
    assert entity_down.available is False
