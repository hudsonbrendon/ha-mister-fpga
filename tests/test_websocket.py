"""Tests for the MiSTer FPGA WebSocket message parsing."""
from __future__ import annotations

from custom_components.mister_fpga.api import MisterStatus
from custom_components.mister_fpga.websocket import apply_ws_message


def test_core_running_updates_status():
    status = MisterStatus(online=True, core="MENU")
    new, menu, idx = apply_ws_message("coreRunning:SNES", status, None, (False, False))
    assert new.core == "SNES"


def test_core_running_blank_means_menu():
    status = MisterStatus(online=True, core="SNES", game="x", game_name="X")
    new, menu, idx = apply_ws_message("coreRunning:", status, None, (False, False))
    assert new.core is None
    assert new.game is None


def test_game_running_updates_status():
    status = MisterStatus(online=True, core="SNES")
    new, menu, idx = apply_ws_message(
        "gameRunning:SNES/Chrono.sfc", status, None, (False, False)
    )
    assert new.game == "SNES/Chrono.sfc"
    assert new.game_name == "Chrono"


def test_menu_navigation_sets_path():
    status = MisterStatus(online=True)
    new, menu, idx = apply_ws_message(
        "menuNavigation:_Console/SNES", status, None, (False, False)
    )
    assert menu == "_Console/SNES"


def test_index_status_parsed():
    status = MisterStatus(online=True)
    new, menu, (exists, in_progress) = apply_ws_message(
        "indexStatus:y,n,0,0,", status, None, (False, False)
    )
    assert exists is True
    assert in_progress is False


def test_unknown_message_is_noop():
    status = MisterStatus(online=True, core="SNES")
    new, menu, idx = apply_ws_message(
        "somethingElse:42", status, "_Console", (True, False)
    )
    assert new.core == "SNES"
    assert menu == "_Console"
    assert idx == (True, False)


def test_game_running_preserves_dots_and_spaces():
    status = MisterStatus(online=True, core="PSX")
    new, menu, idx = apply_ws_message(
        "gameRunning:PSX/Crash Bandicoot (USA).chd", status, None, (False, False)
    )
    assert new.game == "PSX/Crash Bandicoot (USA).chd"
    assert new.game_name == "Crash Bandicoot (USA)"


def test_handle_updates_coordinator():
    from unittest.mock import MagicMock

    from custom_components.mister_fpga.websocket import MisterWebSocket

    coordinator = MagicMock()
    coordinator.data = MisterStatus(
        online=True, core="MENU", hostname="MiSTer", version="240101"
    )
    coordinator.menu_path = None
    coordinator.index_exists = False
    coordinator.indexing = False

    ws = MisterWebSocket(MagicMock(), coordinator)

    ws._handle("coreRunning:SNES")
    pushed = coordinator.async_set_updated_data.call_args[0][0]
    assert pushed.core == "SNES"
    assert pushed.online is True
    # other fields preserved through replace
    assert pushed.hostname == "MiSTer"
    assert pushed.version == "240101"

    ws._handle("menuNavigation:_Console/SNES")
    assert coordinator.menu_path == "_Console/SNES"

    ws._handle("indexStatus:y,y,5,2,SNES")
    assert coordinator.index_exists is True
    assert coordinator.indexing is True
