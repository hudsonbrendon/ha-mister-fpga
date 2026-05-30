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
