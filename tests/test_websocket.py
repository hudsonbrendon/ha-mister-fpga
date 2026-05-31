"""Tests for the MiSTer FPGA WebSocket HA adapter."""
from __future__ import annotations

from mister_fpga import MisterStatus


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
