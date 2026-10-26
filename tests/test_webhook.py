"""Push updates: the announce_game_url webhook and remote.ini wiring."""
from __future__ import annotations

import subprocess
import sys
from unittest.mock import AsyncMock, patch

from custom_components.mister_fpga import _SET_ANNOUNCE_PY
from custom_components.mister_fpga.const import EVENT_GAME_CHANGED
from tests.conftest import SSH_OPTIONS

ANNOUNCE = {
    "platform": "mister",
    "hostname": "MiSTer",
    "core": "SNES",
    "system": "SNES",
    "systemName": "Super Nintendo",
    "gamePath": "/media/fat/games/SNES/Super Metroid.sfc",
    "gameFilename": "Super Metroid.sfc",
    "gameName": "Super Metroid",
}


async def test_webhook_updates_entities_and_fires_event(hass, init_integration):
    import json

    from homeassistant.components import webhook
    from homeassistant.util.aiohttp import MockRequest

    entry, coordinator = await init_integration()
    events = []
    hass.bus.async_listen(EVENT_GAME_CHANGED, lambda e: events.append(e))

    request = MockRequest(
        json.dumps(ANNOUNCE).encode(), mock_source="test", method="POST"
    )
    resp = await webhook.async_handle_webhook(
        hass, entry.data["webhook_id"], request
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    assert hass.states.get("sensor.mister_fpga_game").state == "Super Metroid"
    game = hass.states.get("sensor.mister_fpga_game")
    assert game.attributes["game_path"] == ANNOUNCE["gamePath"]
    assert len(events) == 1
    assert events[0].data["game"] == "Super Metroid"


async def test_webhook_unregistered_on_unload(hass, init_integration):
    from homeassistant.components import webhook

    entry, coordinator = await init_integration()
    webhook_id = entry.data["webhook_id"]
    assert webhook_id in hass.data[webhook.DOMAIN]
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert webhook_id not in hass.data[webhook.DOMAIN]


async def test_push_updates_writes_remote_ini_and_restarts(
    hass, init_integration, mock_ssh
):
    mock_ssh.async_run.return_value = (0, "changed\n")
    with patch(
        "custom_components.mister_fpga.get_url", return_value="http://ha.lan:8123"
    ), patch(
        "mister_fpga.client.MisterClient.async_restart_remote", new=AsyncMock()
    ) as restart:
        entry, coordinator = await init_integration(options=SSH_OPTIONS)
        await hass.async_block_till_done()
    cmd = mock_ssh.async_run.await_args_list[-1].args[0]
    assert "/media/fat/Scripts/remote.ini" in cmd
    assert f"http://ha.lan:8123/api/webhook/{entry.data['webhook_id']}" in cmd
    restart.assert_awaited_once()


async def test_push_updates_unchanged_does_not_restart(
    hass, init_integration, mock_ssh
):
    with patch(
        "custom_components.mister_fpga.get_url", return_value="http://ha.lan:8123"
    ), patch(
        "mister_fpga.client.MisterClient.async_restart_remote", new=AsyncMock()
    ) as restart:
        await init_integration(options=SSH_OPTIONS)
        await hass.async_block_till_done()
    restart.assert_not_called()


async def test_push_updates_off_leaves_remote_ini_alone(
    hass, init_integration, mock_ssh
):
    with patch(
        "custom_components.mister_fpga.get_url", return_value="http://ha.lan:8123"
    ):
        await init_integration(options={**SSH_OPTIONS, "push_updates": False})
        await hass.async_block_till_done()
    mock_ssh.async_run.assert_not_called()


def _run_script(path, url):
    out = subprocess.run(
        [sys.executable, "-c", _SET_ANNOUNCE_PY, str(path), url],
        capture_output=True, text=True, check=True,
    )
    return out.stdout


def test_announce_script_preserves_keys_and_is_idempotent(tmp_path):
    ini = tmp_path / "remote.ini"
    ini.write_text("[remote]\nmdns = yes\nsync_ssh_keys = no\n")
    assert _run_script(ini, "http://ha:8123/api/webhook/x") == "changed\n"
    text = ini.read_text()
    assert "mdns = yes" in text
    assert "announce_game_url = http://ha:8123/api/webhook/x" in text
    assert _run_script(ini, "http://ha:8123/api/webhook/x") == ""


def test_announce_script_creates_missing_file(tmp_path):
    ini = tmp_path / "remote.ini"
    assert _run_script(ini, "http://ha/api/webhook/y") == "changed\n"
    assert "[remote]" in ini.read_text()
