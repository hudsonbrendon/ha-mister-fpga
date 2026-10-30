# Changelog

## 0.6.1 - Unreleased

Modernised for Home Assistant 2026.10 / Python 3.14. No functional changes.

- Coordinator stored in `entry.runtime_data` (`MisterConfigEntry`) instead of
  `hass.data[DOMAIN]`.
- Actions moved to `services.py` and registered once from `async_setup`; the
  `entry_id` lookup now resolves loaded config entries.
- Options flow uses `OptionsFlowWithReload` (no update listener).
- Platforms use `AddConfigEntryEntitiesCallback` and declare `PARALLEL_UPDATES`.
- `ZeroconfServiceInfo` imported from `homeassistant.helpers.service_info`.
- `manifest.json`: `loggers`; `quality_scale.yaml` added.
- Tooling: ruff config aligned with the other integrations, tests on Python 3.14
  with `pytest-homeassistant-custom-component` 0.13.375, release workflow on
  manifest version change, HACS floor 2025.8.0.
