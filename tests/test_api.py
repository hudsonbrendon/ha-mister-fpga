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
