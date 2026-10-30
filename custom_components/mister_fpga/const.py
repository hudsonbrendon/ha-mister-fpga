"""Constants for the MiSTer FPGA integration."""

from __future__ import annotations

# Re-export protocol constants from the library so platform modules can keep
# their existing `from .const import ...` imports unchanged.
from mister_fpga import (  # noqa: F401
    BACKGROUND_MODES,
    DEFAULT_PORT,
    DEFAULT_SSH_PORT,
    DEFAULT_SSH_USERNAME,
    GAMEPAD_ACTIONS,
    GAMEPAD_BUTTONS,
    INI_VIDEO_KEYS,
    KEYBOARD_NAMES,
    MDNS_SERVICE_TYPE,
    WS_PATH,
)

DOMAIN = "mister_fpga"

DEFAULT_NAME = "MiSTer FPGA"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 15
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 600

CONF_RA_API_KEY = "ra_api_key"
CONF_RA_USERNAME = "ra_username"
CONF_RA_CLOUD_INTERVAL = "ra_cloud_interval"
DEFAULT_RA_CLOUD_INTERVAL = 300
MIN_RA_CLOUD_INTERVAL = 60
MAX_RA_CLOUD_INTERVAL = 3600

EVENT_GAME_CHANGED = "mister_fpga_game_changed"
EVENT_MAIN_UNRESPONSIVE = "mister_fpga_main_unresponsive"
EVENT_RETROACHIEVEMENTS = "mister_fpga_retroachievements"

CONF_SSH_ENABLED = "ssh_enabled"
CONF_SSH_USERNAME = "ssh_username"
CONF_SSH_PASSWORD = "ssh_password"
CONF_SSH_PORT = "ssh_port"

CONF_GAMEPAD_ENABLED = "gamepad_enabled"
CONF_PUSH_UPDATES = "push_updates"
CONF_WEBHOOK_ID = "webhook_id"

# Buttons exposed as entities when the Companion Remote daemon answers.
GAMEPAD_ENTITY_BUTTONS = ("start", "select", "a", "b", "home")
