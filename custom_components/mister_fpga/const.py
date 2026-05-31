"""Constants for the MiSTer FPGA integration."""
from __future__ import annotations

DOMAIN = "mister_fpga"

DEFAULT_NAME = "MiSTer FPGA"
DEFAULT_PORT = 8182

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 15
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 600

HTTP_TIMEOUT = 10

EVENT_GAME_CHANGED = "mister_fpga_game_changed"

# mrext Remote API paths (relative to base_url = http://host:port/api)
PATH_PLAYING = "/games/playing"
PATH_SYSINFO = "/sysinfo"
PATH_SYSTEMS = "/systems"
PATH_GAMES_LAUNCH = "/games/launch"
PATH_GAMES_SEARCH = "/games/search"
PATH_GAMES_INDEX = "/games/index"
PATH_LAUNCH_MENU = "/launch/menu"
PATH_KEYBOARD = "/controls/keyboard"
PATH_REBOOT = "/settings/system/reboot"
PATH_RESTART_REMOTE = "/settings/remote/restart"
PATH_SCREENSHOTS = "/screenshots"
PATH_MUSIC_STATUS = "/music/status"
PATH_MUSIC_PLAY = "/music/play"
PATH_MUSIC_STOP = "/music/stop"
PATH_MUSIC_NEXT = "/music/next"
PATH_MUSIC_PLAYLIST = "/music/playlist"
PATH_MUSIC_PLAYBACK = "/music/playback"
PATH_WALLPAPERS = "/wallpapers"
PATH_INIS = "/settings/inis"
PATH_CORE_MENU = "/settings/core/menu"
PATH_SCRIPTS_LIST = "/scripts/list"
PATH_SCRIPTS_LAUNCH = "/scripts/launch"
PATH_SCRIPTS_CONSOLE = "/scripts/console"
PATH_SCRIPTS_KILL = "/scripts/kill"
PATH_PEERS = "/settings/remote/peers"
PATH_LAUNCH = "/launch"
PATH_LAUNCH_TOKEN = "/l"
PATH_LAUNCH_NEW = "/launch/new"
PATH_KEYBOARD_RAW = "/controls/keyboard-raw"
PATH_GENERATE_MAC = "/settings/system/generate-mac"

# WebSocket endpoint (mounted under /api on Remote v0.4)
WS_PATH = "/api/ws"

# MiSTer.ini keys exposed as Number entities (value range 0-100)
INI_VIDEO_KEYS = ("video_brightness", "video_contrast", "video_saturation")

# Keyboard control names accepted by POST /controls/keyboard/{name}
KEYBOARD_NAMES = (
    "up", "down", "left", "right", "confirm", "back", "cancel", "menu",
    "osd", "core_select", "user", "volume_up", "volume_down", "volume_mute",
    "reset", "screenshot", "raw_screenshot", "console", "exit_console",
    "computer_osd", "change_background", "pair_bluetooth", "toggle_core_dates",
)
