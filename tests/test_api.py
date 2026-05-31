"""Tests for the MiSTer FPGA API client."""
from __future__ import annotations

import aiohttp
import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from custom_components.mister_fpga.api import (
    MisterClient,
    MisterConnectionError,
    MisterStatus,
)

BASE = "http://192.168.31.77:8182/api"


@pytest.fixture
async def client():
    """Return a MisterClient backed by a ClientSession with ThreadedResolver.

    Using aiohttp.ThreadedResolver instead of the default AsyncResolver (aiodns)
    prevents pycares from spawning its ``_run_safe_shutdown_loop`` daemon thread,
    which would trip the HA ``verify_cleanup`` fixture.
    """
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    session = ClientSession(connector=connector)
    try:
        yield MisterClient(session, "192.168.31.77", 8182)
    finally:
        await session.close()


def test_base_url():
    client = MisterClient(None, "1.2.3.4", 8182)
    assert client.base_url == "http://1.2.3.4:8182/api"


def test_status_is_running_game():
    assert MisterStatus(online=True, core="SNES").is_running_game is True
    assert MisterStatus(online=True, core="MENU").is_running_game is False
    assert MisterStatus(online=True, core="").is_running_game is False
    assert MisterStatus(online=False, core="SNES").is_running_game is False


async def test_get_status_merges_endpoints(client):
    with aioresponses() as m:
        m.get(
            f"{BASE}/sysinfo",
            payload={
                "ips": ["192.168.31.77"],
                "hostname": "MiSTer",
                "version": "240101",
                "updated": "2026-05-30",
                "dns": "MiSTer.local",
                "disks": [
                    {
                        "path": "/media/fat",
                        "total": 100,
                        "used": 75,
                        "free": 25,
                        "displayName": "SD card",
                    }
                ],
            },
        )
        m.get(
            f"{BASE}/games/playing",
            payload={
                "core": "SNES",
                "system": "SNES",
                "systemName": "Super Nintendo",
                "game": "/games/SNES/Chrono.sfc",
                "gameName": "Chrono Trigger",
            },
        )
        status = await client.async_get_status()
    assert status.online is True
    assert status.core == "SNES"
    assert status.system_name == "Super Nintendo"
    assert status.game_name == "Chrono Trigger"
    assert status.version == "240101"
    assert status.hostname == "MiSTer"
    assert status.ip == "192.168.31.77"
    assert status.dns == "MiSTer.local"
    assert status.disk_total == 100
    assert status.disk_used == 75
    assert status.disk_free == 25


async def test_get_status_raises_on_error(client):
    with aioresponses() as m:
        m.get(f"{BASE}/sysinfo", status=500)
        with pytest.raises(MisterConnectionError):
            await client.async_get_status()


async def test_get_systems(client):
    with aioresponses() as m:
        m.get(
            f"{BASE}/systems",
            payload=[{"id": "SNES", "name": "Super Nintendo", "category": "Console"}],
        )
        systems = await client.async_get_systems()
    assert systems[0]["id"] == "SNES"


async def test_launch_game_posts_path(client):
    with aioresponses() as m:
        m.post(f"{BASE}/games/launch", status=200)
        await client.async_launch_game("/games/SNES/Chrono.sfc")
        import yarl

        key = ("POST", yarl.URL(f"{BASE}/games/launch"))
        assert m.requests[key][0].kwargs["json"] == {"path": "/games/SNES/Chrono.sfc"}


async def test_launch_system(client):
    with aioresponses() as m:
        m.post(f"{BASE}/systems/SNES", status=200)
        await client.async_launch_system("SNES")


async def test_send_keyboard(client):
    with aioresponses() as m:
        m.post(f"{BASE}/controls/keyboard/up", status=200)
        await client.async_send_keyboard("up")


async def test_reboot(client):
    with aioresponses() as m:
        m.post(f"{BASE}/settings/system/reboot", status=200)
        await client.async_reboot()


async def test_screenshot_image_returns_bytes(client):
    with aioresponses() as m:
        m.get(f"{BASE}/screenshots/SNES/shot.png", body=b"\x89PNG", status=200)
        data = await client.async_get_screenshot_image("SNES", "shot.png")
    assert data == b"\x89PNG"


async def test_music_status(client):
    with aioresponses() as m:
        m.get(f"{BASE}/music/status", payload={"running": True, "playing": True})
        status = await client.async_get_music_status()
    assert status["playing"] is True


@pytest.mark.parametrize(
    ("method_name", "path"),
    [
        ("async_launch_menu", "/launch/menu"),
        ("async_index_games", "/games/index"),
        ("async_restart_remote", "/settings/remote/restart"),
        ("async_take_screenshot", "/screenshots"),
        ("async_music_play", "/music/play"),
        ("async_music_stop", "/music/stop"),
        ("async_music_next", "/music/next"),
    ],
)
async def test_simple_post_methods(client, method_name, path):
    with aioresponses() as m:
        m.post(f"{BASE}{path}", status=200)
        await getattr(client, method_name)()
        assert any(k[0] == "POST" for k in m.requests)


async def test_search_games(client):
    with aioresponses() as m:
        m.post(f"{BASE}/games/search", payload={"data": [], "total": 0})
        result = await client.async_search_games("chrono", "SNES")
    assert result["total"] == 0

    with aioresponses() as m:
        m.post(f"{BASE}/games/search", payload={"data": [], "total": 0})
        await client.async_search_games("chrono", "SNES")
        import yarl

        key = ("POST", yarl.URL(f"{BASE}/games/search"))
        assert m.requests[key][0].kwargs["json"] == {"data": "chrono", "system": "SNES"}


async def test_get_screenshots(client):
    with aioresponses() as m:
        m.get(
            f"{BASE}/screenshots",
            payload=[{"core": "SNES", "filename": "a.png", "modified": "2026-05-30"}],
        )
        screenshots = await client.async_get_screenshots()
    assert isinstance(screenshots, list)
    assert screenshots[0]["filename"] == "a.png"


async def test_get_wallpapers(client):
    with aioresponses() as m:
        m.get(
            f"{BASE}/wallpapers",
            payload={
                "active": "snatcher.png",
                "backgroundMode": 2,
                "wallpapers": [
                    {"name": "snatcher", "filename": "snatcher.png", "active": True}
                ],
            },
        )
        wp = await client.async_get_wallpapers()
    assert wp["active"] == "snatcher.png"
    assert wp["backgroundMode"] == 2


async def test_set_and_clear_wallpaper(client):
    with aioresponses() as m:
        m.post(f"{BASE}/wallpapers/snatcher.png", status=200)
        m.delete(f"{BASE}/wallpapers", status=200)
        await client.async_set_wallpaper("snatcher.png")
        await client.async_clear_wallpaper()


async def test_inis_get_set_active(client):
    import yarl

    with aioresponses() as m:
        m.get(
            f"{BASE}/settings/inis",
            payload={
                "active": 0,
                "inis": [
                    {
                        "id": 1,
                        "displayName": "Main",
                        "filename": "MiSTer.ini",
                        "path": "/x",
                    }
                ],
            },
        )
        m.get(
            f"{BASE}/settings/inis/1",
            payload={"__hostname": "MiSTer", "video_brightness": "50"},
        )
        m.put(f"{BASE}/settings/inis", status=200)
        m.put(f"{BASE}/settings/inis/1", status=200)
        inis = await client.async_get_inis()
        values = await client.async_get_ini_values(1)
        await client.async_set_active_ini(1)
        await client.async_set_ini_values(1, {"video_brightness": "60"})
        put_inis_calls = m.requests[
            ("PUT", yarl.URL(f"{BASE}/settings/inis"))
        ]
        put_inis_1_calls = m.requests[
            ("PUT", yarl.URL(f"{BASE}/settings/inis/1"))
        ]
    assert inis["inis"][0]["displayName"] == "Main"
    assert values["video_brightness"] == "50"
    assert put_inis_calls[0].kwargs["json"] == {"ini": 1}
    assert put_inis_1_calls[0].kwargs["json"] == {"video_brightness": "60"}


async def test_set_background_mode(client):
    import yarl

    with aioresponses() as m:
        m.put(f"{BASE}/settings/core/menu", status=200)
        await client.async_set_background_mode(3)
        put_calls = m.requests[("PUT", yarl.URL(f"{BASE}/settings/core/menu"))]
    assert put_calls[0].kwargs["json"] == {"mode": 3}


async def test_music_playlists_and_playback(client):
    with aioresponses() as m:
        m.get(f"{BASE}/music/playlist", payload=["none", "Vidya"])
        m.post(f"{BASE}/music/playlist/Vidya", status=200)
        m.post(f"{BASE}/music/playback/loop", status=200)
        pls = await client.async_get_music_playlists()
        await client.async_set_music_playlist("Vidya")
        await client.async_set_music_playback("loop")
    assert pls == ["none", "Vidya"]


async def test_scripts_list_launch_kill_console(client):
    with aioresponses() as m:
        m.get(
            f"{BASE}/scripts/list",
            payload={
                "canLaunch": True,
                "scripts": [
                    {"name": "update_all", "filename": "update_all.sh", "path": "/x"}
                ],
            },
        )
        m.post(f"{BASE}/scripts/launch/update_all.sh", status=200)
        m.post(f"{BASE}/scripts/console", status=200)
        m.post(f"{BASE}/scripts/kill", status=200)
        scr = await client.async_get_scripts()
        await client.async_launch_script("update_all.sh")
        await client.async_open_console()
        await client.async_kill_script()
    assert scr["scripts"][0]["filename"] == "update_all.sh"


async def test_peers(client):
    with aioresponses() as m:
        m.get(
            f"{BASE}/settings/remote/peers",
            payload={
                "peers": [
                    {"hostname": "MiSTer.local", "version": "0.4", "ip": "1.2.3.4"}
                ]
            },
        )
        peers = await client.async_get_peers()
    assert peers[0]["ip"] == "1.2.3.4"


async def test_generic_launch_and_token(client):
    with aioresponses() as m:
        m.post(f"{BASE}/launch", status=200)
        m.get(f"{BASE}/l/bWVudS5yYmY=", status=200)
        await client.async_launch_path("/media/fat/menu.rbf")
        await client.async_launch_token("bWVudS5yYmY=")


async def test_create_shortcut(client):
    with aioresponses() as m:
        m.post(
            f"{BASE}/launch/new",
            payload={"path": "/media/fat/_@Favorites/Crash.mgl"},
        )
        result = await client.async_create_shortcut(
            "/g/Crash.chd", "_@Favorites", "Crash"
        )
    assert result["path"].endswith("Crash.mgl")


async def test_send_keyboard_raw(client):
    with aioresponses() as m:
        m.post(f"{BASE}/controls/keyboard-raw/16", status=200)
        await client.async_send_keyboard_raw(16)
