<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/mister_fpga/brand/dark_logo.png">
    <img src="custom_components/mister_fpga/brand/logo.png" alt="MiSTer FPGA" width="420">
  </picture>
</p>

# MiSTer FPGA for Home Assistant

[![Tests](https://github.com/hudsonbrendon/ha-mister-fpga/actions/workflows/tests.yml/badge.svg)](https://github.com/hudsonbrendon/ha-mister-fpga/actions/workflows/tests.yml)
[![Hassfest](https://github.com/hudsonbrendon/ha-mister-fpga/actions/workflows/hassfest.yml/badge.svg)](https://github.com/hudsonbrendon/ha-mister-fpga/actions/workflows/hassfest.yml)
[![Validate](https://github.com/hudsonbrendon/ha-mister-fpga/actions/workflows/validate.yml/badge.svg)](https://github.com/hudsonbrendon/ha-mister-fpga/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/hudsonbrendon/ha-mister-fpga)](https://github.com/hudsonbrendon/ha-mister-fpga/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Monitor and control a network-connected **MiSTer FPGA** from Home Assistant over the
[**mrext "Remote"**](https://github.com/wizzomafizzo/mrext) HTTP API — the running
core/system/game, firmware version, hostname, IP and online status, the latest
screenshot, plus launching any system or game, reboot, return to menu, take a screenshot,
restart the Remote service, re-index games, background music, and keyboard input.

> Talks to the mrext Remote REST API (default port `8182`) at `http://<mister-ip>:8182/api`.
> Everything runs on your LAN — no cloud, no account. Not affiliated with the MiSTer-devel
> project or the mrext developers.

## Features

- 🎮 **Now playing** — a media player showing the running core/game; `idle` in the menu,
  `off` when unreachable. `select_source` launches any installed system; `play_media`
  launches a game by file path.
- 🕹️ **State sensors** — current core, system, game, firmware version, hostname and IP
  address.
- 📡 **Online status** — a connectivity binary sensor that flips off when the MiSTer is
  unreachable (powered off / Remote service down).
- 🚀 **Launch system** — a select entity to start any installed core/system from the
  device's list.
- 🎵 **Background music** — a switch to toggle the MiSTer BGM (menu music) service.
- 🖼️ **Latest screenshot** — an image entity serving the most recent screenshot taken on
  the device, refreshed on each poll.
- 🔘 **Buttons** — Reboot, Go to menu, Take screenshot, Restart Remote service, and
  Re-index games.
- 🛠️ **Services** — `launch_game`, `launch_system`, `search_games` (returns results),
  `send_keyboard`, and `take_screenshot`, each targeting a config entry by `entry_id`.
- 📣 **Events** — fires `mister_fpga_game_changed` on the Home Assistant event bus when the
  running core/game changes, enabling automations.
- 🏠 **Local polling** — no cloud; talks straight to the mrext Remote service on your
  network.
- 🌐 **Localized** — UI and entities translated to English and Português (Brasil).

## Requirements

**On the MiSTer:**

- A MiSTer FPGA on your network (Ethernet or Wi-Fi).
- The **Remote** service from [mrext](https://github.com/wizzomafizzo/mrext) installed and
  running (default port `8182`).
  - Confirm it works by opening `http://<MiSTer_IP>:8182/` in a browser — the Remote web
    panel should load.
- A static / reserved IP for the MiSTer is recommended.

**On Home Assistant:**

- Home Assistant **2024.12** or newer.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hudsonbrendon&repository=ha-mister-fpga&category=integration)

1. In Home Assistant, open **HACS → ⋮ (top right) → Custom repositories**.
2. Add `https://github.com/hudsonbrendon/ha-mister-fpga` and choose the **Integration**
   category — or use the button above.
3. Search for **MiSTer FPGA** in HACS, install it, and **restart Home Assistant**.

### Manual

1. Copy `custom_components/mister_fpga/` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Go to **Settings → Devices & Services → Add Integration → MiSTer FPGA**.
2. Enter the MiSTer's **host (IP address)** and **port** (default `8182`).

You can later change the polling interval via **Configure** (options flow).

## Entities

### Media player

| Entity | Description |
|--------|-------------|
| `media_player.<name>` | MiSTer media player (receiver class). State: `off` when unreachable, `playing` while a core/game runs, `idle` in the menu. `source`/`source_list` are the installed systems; `select_source` launches a system. `play_media` launches a game by absolute path. |

### Binary sensor

| Entity | Description |
|--------|-------------|
| `binary_sensor.<name>_online` | On while the mrext Remote service is reachable; off when the MiSTer is unreachable. |

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.<name>_core` | Running core |
| `sensor.<name>_system` | Running system (friendly name) |
| `sensor.<name>_game` | Running game, or `unknown` in the menu |
| `sensor.<name>_version` | MiSTer firmware/build version |
| `sensor.<name>_hostname` | Device hostname |
| `sensor.<name>_ip_address` | Device IP address |

### Select

| Entity | Description |
|--------|-------------|
| `select.<name>_launch_system` | Options are the installed systems; selecting one launches it on the MiSTer. |

### Switch

| Entity | Description |
|--------|-------------|
| `switch.<name>_background_music` | Toggles the MiSTer BGM (menu background music) service. |

### Buttons

| Entity | Action |
|--------|--------|
| `button.<name>_reboot` | Reboot the MiSTer |
| `button.<name>_go_to_menu` | Return to the main menu |
| `button.<name>_take_screenshot` | Capture a screenshot |
| `button.<name>_restart_remote` | Restart the mrext Remote service |
| `button.<name>_index_games` | Re-index the games database |

### Image

| Entity | Description |
|--------|-------------|
| `image.<name>_latest_screenshot` | The most recent screenshot taken on the device. |

## Services

| Service | Description |
|---------|-------------|
| `mister_fpga.launch_game` | Launch a game by its absolute file path on the MiSTer. |
| `mister_fpga.launch_system` | Launch a core/system by its ID (e.g. `SNES`). |
| `mister_fpga.search_games` | Search indexed games and return the results (response service). |
| `mister_fpga.send_keyboard` | Send a named keyboard key to the MiSTer (e.g. `up`, `enter`, `escape`). |
| `mister_fpga.take_screenshot` | Trigger a screenshot capture on the MiSTer. |

Each service takes an `entry_id` field — the config entry ID of the target MiSTer.

## Events

The integration fires **`mister_fpga_game_changed`** on the Home Assistant event bus
whenever the running core/game changes.

Event data:

```yaml
core: SNES
system: Super Nintendo
game: Chrono Trigger
```

Example automation — notify when a new game starts:

```yaml
automation:
  trigger:
    - platform: event
      event_type: mister_fpga_game_changed
  action:
    - service: notify.mobile_app_my_phone
      data:
        message: "Now playing on MiSTer: {{ trigger.event.data.game }}"
```

## Diagnostics

Download Diagnostics is supported via **Settings → Devices & Services → your MiSTer entry
→ ⋮ → Download diagnostics**. The report includes the current device status and entry
configuration.

## Notes & limitations

- 🌐 **LAN only, no auth** — the mrext Remote HTTP server is unauthenticated by design;
  keep your MiSTer on a trusted network.
- ⚡ **No power-on** — the integration controls a running MiSTer over HTTP; powering the
  device on over the network is out of scope.
- 🖼️ **Screenshots** depend on screenshots existing on the device; the image entity stays
  empty until at least one screenshot has been taken.
- 🧩 **Remote required** — the mrext Remote service must be installed and running; MiSTer's
  stock firmware does not expose this API on its own.

## Credits

REST API by [wizzomafizzo/mrext](https://github.com/wizzomafizzo/mrext). MiSTer-kun logo
by the [MiSTer-devel](https://github.com/MiSTer-devel) project. Integration by
[@hudsonbrendon](https://github.com/hudsonbrendon).

## License

[MIT](LICENSE)
