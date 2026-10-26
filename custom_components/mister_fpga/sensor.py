"""Sensors for the MiSTer FPGA integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from mister_fpga import MisterStatus

from .const import DOMAIN
from .coordinator import MisterDataUpdateCoordinator
from .entity import MisterEntity


@dataclass(frozen=True, kw_only=True)
class MisterSensorEntityDescription(SensorEntityDescription):
    value_fn: (
        Callable[[MisterStatus], str | int | float | None] | None
    ) = None
    coordinator_fn: (
        Callable[[MisterDataUpdateCoordinator], str | int | float | None] | None
    ) = None
    attrs_fn: Callable[[MisterDataUpdateCoordinator], dict] | None = None


def _ts_to_datetime(ts):
    if not ts:
        return None
    import datetime as _dt
    return _dt.datetime.fromtimestamp(ts, tz=_dt.UTC)


def _disk_usage(status: MisterStatus) -> float | None:
    if not status.disk_total:
        return None
    return round(status.disk_used / status.disk_total * 100, 1)


def _disk_free_gib(status: MisterStatus) -> float | None:
    return round(status.disk_free / (1024 ** 3), 1) if status.disk_free else None


SENSORS: tuple[MisterSensorEntityDescription, ...] = (
    MisterSensorEntityDescription(
        key="core",
        translation_key="core",
        icon="mdi:chip",
        value_fn=lambda s: s.core,
        attrs_fn=lambda c: {
            "core_session_time": c.data.core_session_time if c.data else None
        },
    ),
    MisterSensorEntityDescription(
        key="system",
        translation_key="system",
        icon="mdi:gamepad-variant",
        value_fn=lambda s: s.system_name or s.system,
    ),
    MisterSensorEntityDescription(
        key="game",
        translation_key="game",
        icon="mdi:disc",
        value_fn=lambda s: s.game_name,
        attrs_fn=lambda c: {
            "game_session_time": c.data.game_session_time if c.data else None,
            "game_path": c.game_path,
        },
    ),
    MisterSensorEntityDescription(
        key="remote_version",
        translation_key="remote_version",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.version,
    ),
    MisterSensorEntityDescription(
        key="hostname",
        translation_key="hostname",
        icon="mdi:server-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.hostname,
    ),
    MisterSensorEntityDescription(
        key="ip_address",
        translation_key="ip_address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.ip,
    ),
    MisterSensorEntityDescription(
        key="dns_name",
        translation_key="dns_name",
        icon="mdi:dns",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.dns,
    ),
    MisterSensorEntityDescription(
        key="disk_free",
        translation_key="disk_free",
        icon="mdi:micro-sd",
        native_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_disk_free_gib,
    ),
    MisterSensorEntityDescription(
        key="disk_usage",
        translation_key="disk_usage",
        icon="mdi:harddisk",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_disk_usage,
    ),
    MisterSensorEntityDescription(
        key="last_updated",
        translation_key="last_updated",
        icon="mdi:update",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.updated,
    ),
    MisterSensorEntityDescription(
        key="mac_address",
        translation_key="mac_address",
        icon="mdi:network-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        coordinator_fn=lambda c: c.mac_address,
    ),
    MisterSensorEntityDescription(
        key="music_track",
        translation_key="music_track",
        icon="mdi:music-note",
        coordinator_fn=lambda c: c.music.get("track") or None,
    ),
    MisterSensorEntityDescription(
        key="music_playlist",
        translation_key="music_playlist",
        icon="mdi:playlist-music",
        coordinator_fn=lambda c: c.music.get("playlist") or None,
    ),
    MisterSensorEntityDescription(
        key="peers",
        translation_key="peers",
        icon="mdi:lan",
        entity_category=EntityCategory.DIAGNOSTIC,
        coordinator_fn=lambda c: len(c.peers),
    ),
    MisterSensorEntityDescription(
        key="screenshots",
        translation_key="screenshots",
        icon="mdi:image-multiple",
        entity_category=EntityCategory.DIAGNOSTIC,
        coordinator_fn=lambda c: c.screenshots_count,
    ),
    MisterSensorEntityDescription(
        key="menu_position",
        translation_key="menu_position",
        icon="mdi:menu",
        coordinator_fn=lambda c: c.menu_path,
    ),
    MisterSensorEntityDescription(
        key="active_core",
        translation_key="active_core",
        icon="mdi:chip",
        coordinator_fn=lambda c: c.ssh_data.get("active_core"),
    ),
    MisterSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="s",
        coordinator_fn=lambda c: c.ssh_data.get("uptime_seconds"),
    ),
    MisterSensorEntityDescription(
        key="cpu_load",
        translation_key="cpu_load",
        icon="mdi:cpu-32-bit",
        state_class=SensorStateClass.MEASUREMENT,
        coordinator_fn=lambda c: c.ssh_data.get("cpu_load_1m"),
    ),
    MisterSensorEntityDescription(
        key="memory_used",
        translation_key="memory_used",
        icon="mdi:memory",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        coordinator_fn=lambda c: c.ssh_data.get("memory_used_percent"),
    ),
    MisterSensorEntityDescription(
        key="firmware_date",
        translation_key="firmware_date",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        coordinator_fn=lambda c: _ts_to_datetime(c.ssh_data.get("firmware_timestamp")),
    ),
)


# Only meaningful with SSH: Main health, SAM and the loaded game's ID.
SSH_SENSORS: tuple[MisterSensorEntityDescription, ...] = (
    MisterSensorEntityDescription(
        key="main_open_fds",
        translation_key="main_open_fds",
        icon="mdi:file-multiple",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        coordinator_fn=lambda c: c.ssh_data.get("main_open_fds"),
    ),
    MisterSensorEntityDescription(
        key="sam_game",
        translation_key="sam_game",
        icon="mdi:television-play",
        coordinator_fn=lambda c: c.ssh_data.get("sam_game"),
    ),
    MisterSensorEntityDescription(
        key="game_id",
        translation_key="game_id",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        coordinator_fn=lambda c: c.ssh_data.get("game_id"),
    ),
)


def _playlog(c, key):
    return c.playlog.get(key) if c.playlog else None


def _top_game(c):
    top = _playlog(c, "topGames") or []
    if not top or not isinstance(top[0], dict):
        return None
    return top[0].get("name") or top[0].get("gameName") or top[0].get("game")


def _duration(key, translation_key, icon, value_fn, suggested_unit):
    return MisterSensorEntityDescription(
        key=key,
        translation_key=translation_key,
        icon=icon,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=suggested_unit,
        state_class=SensorStateClass.TOTAL_INCREASING,
        coordinator_fn=value_fn,
    )


PLAYLOG_SENSORS: tuple[MisterSensorEntityDescription, ...] = (
    _duration(
        "playtime_today", "playtime_today", "mdi:timer-play",
        lambda c: c.playlog_today, UnitOfTime.MINUTES,
    ),
    _duration(
        "playtime_total", "playtime_total", "mdi:timer-sand-complete",
        lambda c: _playlog(c, "totalTime"), UnitOfTime.HOURS,
    ),
    MisterSensorEntityDescription(
        key="games_played",
        translation_key="games_played",
        icon="mdi:gamepad-square",
        state_class=SensorStateClass.TOTAL,
        coordinator_fn=lambda c: _playlog(c, "gamesPlayed"),
    ),
    MisterSensorEntityDescription(
        key="play_sessions",
        translation_key="play_sessions",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL,
        coordinator_fn=lambda c: _playlog(c, "sessions"),
    ),
    MisterSensorEntityDescription(
        key="current_streak",
        translation_key="current_streak",
        icon="mdi:fire",
        native_unit_of_measurement=UnitOfTime.DAYS,
        coordinator_fn=lambda c: _playlog(c, "currentStreak"),
    ),
    MisterSensorEntityDescription(
        key="longest_streak",
        translation_key="longest_streak",
        icon="mdi:trophy-award",
        native_unit_of_measurement=UnitOfTime.DAYS,
        coordinator_fn=lambda c: _playlog(c, "longestStreak"),
    ),
    MisterSensorEntityDescription(
        key="top_game",
        translation_key="top_game",
        icon="mdi:star",
        coordinator_fn=_top_game,
        attrs_fn=lambda c: {
            "top_games": _playlog(c, "topGames") or [],
            "top_systems": _playlog(c, "topSystems") or [],
        },
    ),
)


def _ra(coordinator):
    return getattr(coordinator, "ra_data", None)


RA_SENSORS: tuple[MisterSensorEntityDescription, ...] = (
    MisterSensorEntityDescription(
        key="ra_mode",
        translation_key="ra_mode",
        icon="mdi:trophy",
        entity_category=EntityCategory.DIAGNOSTIC,
        coordinator_fn=lambda c: (
            None if _ra(c) is None else ("RA cores" if _ra(c).cores_on else "Stock")
        ),
    ),
    MisterSensorEntityDescription(
        key="ra_binary",
        translation_key="ra_binary",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        coordinator_fn=lambda c: (
            None if _ra(c) is None
            else ("RA (odelot)" if _ra(c).binary_ra else "Stock")
        ),
    ),
    MisterSensorEntityDescription(
        key="ra_user",
        translation_key="ra_user",
        icon="mdi:account",
        entity_category=EntityCategory.DIAGNOSTIC,
        coordinator_fn=lambda c: None if _ra(c) is None else _ra(c).username,
    ),
    MisterSensorEntityDescription(
        key="ra_active_cores",
        translation_key="ra_active_cores",
        icon="mdi:trophy-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        coordinator_fn=lambda c: (
            None if _ra(c) is None
            else f"{_ra(c).cores_active}/{_ra(c).cores_total}"
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    descriptions = list(SENSORS)
    if coordinator.ssh is not None:
        descriptions.extend(SSH_SENSORS)
    if coordinator.playlog is not None:
        descriptions.extend(PLAYLOG_SENSORS)
    ra_data = getattr(coordinator, "ra_data", None)
    if ra_data is not None and ra_data.installed:
        descriptions.extend(RA_SENSORS)
    async_add_entities(MisterSensor(coordinator, entry, d) for d in descriptions)

    ra_web_coordinator = getattr(coordinator, "ra_web_coordinator", None)
    if ra_web_coordinator is not None:
        from .sensor_ra_web import RA_WEB_SENSORS, MisterRAWebSensor

        async_add_entities(
            MisterRAWebSensor(ra_web_coordinator, entry, d) for d in RA_WEB_SENSORS
        )


class MisterSensor(MisterEntity, SensorEntity):
    entity_description: MisterSensorEntityDescription

    def __init__(self, coordinator, entry, description) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self):
        desc = self.entity_description
        if desc.coordinator_fn is not None:
            return desc.coordinator_fn(self.coordinator)
        if self.coordinator.data is None:
            return None
        return desc.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict | None:
        fn = self.entity_description.attrs_fn
        return fn(self.coordinator) if fn is not None else None
