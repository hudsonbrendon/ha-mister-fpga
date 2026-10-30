"""Tests for the MiSTer FPGA coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock

from mister_fpga import MisterConnectionError, MisterStatus

from custom_components.mister_fpga.const import EVENT_GAME_CHANGED
from custom_components.mister_fpga.coordinator import MisterDataUpdateCoordinator


async def test_update_returns_status(hass):
    client = AsyncMock()
    client.async_get_status.return_value = MisterStatus(online=True, core="SNES")
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    data = await coordinator._async_update_data()
    assert data.online is True
    assert data.core == "SNES"


async def test_update_offline_on_error(hass):
    client = AsyncMock()
    client.async_get_status.side_effect = MisterConnectionError("boom")
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    data = await coordinator._async_update_data()
    assert data.online is False


async def test_fires_event_on_game_change(hass):
    client = AsyncMock()
    client.async_get_status.return_value = MisterStatus(
        online=True, core="SNES", game="/g/a.sfc", game_name="A", system_name="SNES"
    )
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)

    events = []
    hass.bus.async_listen(EVENT_GAME_CHANGED, lambda e: events.append(e))

    # first refresh after setup only records the baseline
    await coordinator._async_update_data()
    await hass.async_block_till_done()
    assert events == []

    client.async_get_status.return_value = MisterStatus(
        online=True, core="SNES", game="/g/b.sfc", game_name="B", system_name="SNES"
    )
    await coordinator._async_update_data()
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["game"] == "B"

    # same game again -> no new event
    await coordinator._async_update_data()
    await hass.async_block_till_done()
    assert len(events) == 1


async def test_websocket_game_change_fires_event(hass):
    from unittest.mock import MagicMock

    from custom_components.mister_fpga.websocket import MisterWebSocket

    coordinator = MisterDataUpdateCoordinator(hass, AsyncMock(), 15)
    coordinator.async_set_updated_data(MisterStatus(online=True, core="MENU"))
    coordinator.async_check_game_changed(coordinator.data)  # setup baseline
    events = []
    hass.bus.async_listen(EVENT_GAME_CHANGED, lambda e: events.append(e))

    ws = MisterWebSocket(MagicMock(), coordinator)
    ws._handle("coreRunning:SNES")
    ws._handle("gameRunning:SNES/Chrono Trigger.sfc")
    ws._handle("gameRunning:SNES/Chrono Trigger.sfc")
    await hass.async_block_till_done()
    assert [e.data["core"] for e in events] == ["SNES", "SNES"]
    assert events[-1].data["game"] == "Chrono Trigger"


async def test_refresh_systems_swallows_errors(hass):
    client = AsyncMock()
    client.async_get_systems.side_effect = MisterConnectionError("boom")
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    await coordinator.async_refresh_systems()
    assert coordinator.systems == []


async def test_coordinator_collects_extras(hass):
    from unittest.mock import AsyncMock

    client = AsyncMock()
    client.async_get_status.return_value = MisterStatus(online=True, core="SNES")
    client.async_get_music_status.return_value = {
        "running": True,
        "playing": True,
        "track": "x.mp3",
        "playlist": "Vidya",
        "playback": "random",
    }
    client.async_get_wallpapers.return_value = {
        "active": "a.png",
        "backgroundMode": 2,
        "wallpapers": [{"filename": "a.png"}],
    }
    client.async_get_inis.return_value = {
        "active": 0,
        "inis": [{"id": 1, "displayName": "Main"}],
    }
    client.async_get_ini_values.return_value = {
        "__ethernetMacAddress": "AA:BB",
        "video_brightness": "50",
    }
    client.async_get_peers.return_value = [{"ip": "1.2.3.4"}]
    client.async_get_screenshots.return_value = [
        {"core": "SNES", "filename": "s.png", "modified": "2026-01-01"},
    ]
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    await coordinator.async_refresh_extras()
    assert coordinator.music["track"] == "x.mp3"
    assert coordinator.wallpapers["active"] == "a.png"
    assert coordinator.active_ini_id == 1  # active 0 falls back to 1
    assert coordinator.mac_address == "AA:BB"
    assert coordinator.ini_values["video_brightness"] == "50"
    assert coordinator.peers[0]["ip"] == "1.2.3.4"
    assert coordinator.screenshots_count == 1


async def test_coordinator_extras_tolerate_errors(hass):
    from unittest.mock import AsyncMock

    client = AsyncMock()
    client.async_get_status.return_value = MisterStatus(online=True)
    client.async_get_music_status.side_effect = MisterConnectionError("x")
    client.async_get_wallpapers.side_effect = MisterConnectionError("x")
    client.async_get_inis.side_effect = MisterConnectionError("x")
    client.async_get_ini_values.side_effect = MisterConnectionError("x")
    client.async_get_peers.side_effect = MisterConnectionError("x")
    client.async_get_screenshots.side_effect = MisterConnectionError("x")
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    await coordinator.async_refresh_extras()  # must not raise
    assert coordinator.music == {}
    assert coordinator.ini_values == {}
    assert coordinator.screenshots_count == 0


async def test_slow_extras_are_throttled(hass):
    """Music polls every cycle; wallpapers/INIs/peers/screenshots do not."""
    from unittest.mock import AsyncMock

    client = AsyncMock()
    client.async_get_music_status.return_value = {"track": "x.mp3"}
    client.async_get_wallpapers.return_value = {"active": "a.png"}
    client.async_get_inis.return_value = {"inis": [], "active": 1}
    client.async_get_ini_values.return_value = {}
    client.async_get_peers.return_value = []
    client.async_get_screenshots.return_value = []
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)

    await coordinator.async_refresh_extras()
    await coordinator.async_refresh_extras()

    assert client.async_get_music_status.call_count == 2
    assert client.async_get_wallpapers.call_count == 1

    # a write forces the slow set to come back immediately
    await coordinator.async_refresh_extras(force=True)
    assert client.async_get_wallpapers.call_count == 2


async def test_coordinator_refresh_scripts(hass):
    from unittest.mock import AsyncMock

    client = AsyncMock()
    client.async_get_scripts.return_value = {
        "canLaunch": True,
        "scripts": [{"name": "a", "filename": "a.sh"}],
    }
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    await coordinator.async_refresh_scripts()
    assert coordinator.scripts[0]["filename"] == "a.sh"


async def test_screenshots_null_response_counts_zero(hass):
    client = AsyncMock()
    client.async_get_music_status.return_value = {}
    client.async_get_wallpapers.return_value = {}
    client.async_get_inis.return_value = {}
    client.async_get_ini_values.return_value = {}
    client.async_get_peers.return_value = []
    client.async_get_screenshots.return_value = None
    client.async_get_playlog_status.return_value = {}
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    await coordinator.async_refresh_extras()
    assert coordinator.screenshots_count == 0


def _playlog_client(**status):
    client = AsyncMock()
    client.async_get_music_status.return_value = {}
    client.async_get_screenshots.return_value = []
    client.async_get_playlog_status.return_value = status

    async def _summary(top=None, days=None):
        if days == 1:
            return {"days": [{"date": "2026-10-26", "time": 1800}]}
        return {"totalTime": 7200, "gamesPlayed": 3, "topGames": [{"name": "A"}]}

    client.async_get_playlog_summary.side_effect = _summary
    return client


async def test_playlog_fetched_when_running(hass):
    coordinator = MisterDataUpdateCoordinator(hass, _playlog_client(running=True), 15)
    await coordinator.async_refresh_extras()
    assert coordinator.playlog["totalTime"] == 7200
    assert coordinator.playlog_today == 1800


async def test_playlog_skipped_when_not_running_or_unsupported(hass):
    from mister_fpga import MisterUnsupportedError

    client = _playlog_client(running=False)
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    await coordinator.async_refresh_extras()
    assert coordinator.playlog is None
    client.async_get_playlog_summary.assert_not_called()

    client.async_get_playlog_status.side_effect = MisterUnsupportedError("0.4")
    await coordinator.async_refresh_extras(force=True)  # must not raise
    assert coordinator.playlog is None


async def test_main_unresponsive_needs_two_probes_and_fires_once(hass):
    from custom_components.mister_fpga.const import EVENT_MAIN_UNRESPONSIVE

    coordinator = MisterDataUpdateCoordinator(hass, AsyncMock(), 15)
    coordinator.ssh = AsyncMock()
    events = []
    hass.bus.async_listen(EVENT_MAIN_UNRESPONSIVE, lambda e: events.append(e))

    probes = [
        {"cmd_fifo_pending": 12},  # one stuck probe is not enough
        {"cmd_fifo_pending": 0},
        {"cmd_fifo_pending": 12},
        {"cmd_fifo_pending": 24},  # second in a row -> hung
        {"cmd_fifo_pending": 24},  # still hung, no new event
        {"cmd_fifo_pending": 0},
    ]
    seen = []
    for probe in probes:
        coordinator.ssh.async_probe.return_value = probe
        await coordinator.async_refresh_ssh()
        seen.append(coordinator.main_unresponsive)
    await hass.async_block_till_done()
    assert seen == [False, False, False, True, True, False]
    assert len(events) == 1
    assert events[0].data["cmd_fifo_pending"] == 24


async def test_ra_log_events_skip_backlog_then_fire(hass):
    import types

    from custom_components.mister_fpga.const import EVENT_RETROACHIEVEMENTS

    coordinator = MisterDataUpdateCoordinator(hass, AsyncMock(), 15)
    coordinator.ssh = AsyncMock()
    coordinator.ssh.async_probe.return_value = {}
    coordinator.ra = AsyncMock()
    coordinator.ra.async_status.return_value = types.SimpleNamespace(installed=True)
    old = {"type": "achievement", "id": 1, "title": "Old"}
    new = {"type": "achievement", "id": 2, "title": "New"}
    coordinator.ra.async_read_log.side_effect = [(500, [old]), (600, [new])]
    events = []
    hass.bus.async_listen(EVENT_RETROACHIEVEMENTS, lambda e: events.append(e))

    await coordinator.async_refresh_ssh()  # first run: skip to the end
    await coordinator.async_refresh_ssh()
    await hass.async_block_till_done()

    assert [c.args[0] for c in coordinator.ra.async_read_log.call_args_list] == [
        0,
        500,
    ]
    assert [e.data for e in events] == [new]


async def test_announce_updates_status_and_fires_event(hass):
    coordinator = MisterDataUpdateCoordinator(hass, AsyncMock(), 15)
    coordinator.async_set_updated_data(MisterStatus(online=True, core="MENU"))
    coordinator.async_check_game_changed(coordinator.data)
    events = []
    hass.bus.async_listen(EVENT_GAME_CHANGED, lambda e: events.append(e))

    coordinator.async_handle_announce(
        {
            "core": "SNES",
            "system": "SNES",
            "systemName": "Super Nintendo",
            "gamePath": "/media/fat/games/SNES/Chrono Trigger.sfc",
            "gameFilename": "Chrono Trigger.sfc",
            "gameName": "Chrono Trigger",
        }
    )
    await hass.async_block_till_done()
    assert coordinator.data.core == "SNES"
    assert coordinator.data.system_name == "Super Nintendo"
    assert coordinator.data.game_name == "Chrono Trigger"
    assert coordinator.data.game == "SNES/Chrono Trigger.sfc"
    assert coordinator.game_path == "/media/fat/games/SNES/Chrono Trigger.sfc"
    assert len(events) == 1
    assert events[0].data["game_path"].endswith("Chrono Trigger.sfc")


async def test_missing_fifo_is_not_a_hang(hass):
    coordinator = MisterDataUpdateCoordinator(hass, AsyncMock(), 15)
    coordinator.ssh = AsyncMock()
    coordinator.ssh.async_probe.return_value = {"cmd_fifo_pending": -1}
    await coordinator.async_refresh_ssh()
    await coordinator.async_refresh_ssh()
    assert coordinator.main_unresponsive is False


async def test_mac_junk_files_are_hidden(hass):
    client = AsyncMock()
    client.async_get_scripts.return_value = {
        "scripts": [
            {"name": "._bgm", "filename": "._bgm.sh"},
            {"name": "bgm", "filename": "bgm.sh"},
        ],
    }
    coordinator = MisterDataUpdateCoordinator(hass, client, 15)
    await coordinator.async_refresh_scripts()
    assert [s["name"] for s in coordinator.scripts] == ["bgm"]


async def test_core_only_announce_has_no_game(hass):
    coordinator = MisterDataUpdateCoordinator(hass, AsyncMock(), 15)
    coordinator.data = MisterStatus(online=True, core="GBC", game="GBC/a.gbc")
    # mrext sends gameFilename "." (filepath.Base("")) when no game is loaded
    coordinator.async_handle_announce(
        {
            "core": "GBC",
            "system": "GameboyColor",
            "systemName": "Gameboy Color",
            "gamePath": "",
            "gameFilename": ".",
            "gameName": "",
        }
    )
    assert coordinator.data.game is None
    assert coordinator.data.system == "GameboyColor"
