"""RetroAchievements cloud-stats sensors (bound to the web coordinator)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry

from mister_fpga import MisterRAWebStats

from .ra_web_coordinator import MisterRAWebCoordinator
from .ra_web_entity import MisterRAWebEntity


@dataclass(frozen=True, kw_only=True)
class RAWebSensorDescription(SensorEntityDescription):
    value_fn: Callable[[MisterRAWebStats], object]
    attr_fn: Callable[[MisterRAWebStats], dict] = lambda _s: {}


def _current_game_attrs(s: MisterRAWebStats) -> dict:
    g = s.current_game
    if g is None:
        return {}
    return {
        "earned": g.num_achieved,
        "possible": g.num_possible,
        "percent": g.percent,
        "console": g.console,
        "last_played": g.last_played,
    }


def _last_achievement_attrs(s: MisterRAWebStats) -> dict:
    a = s.last_achievement
    if a is None:
        return {}
    return {
        "game": a.game_title,
        "points": a.points,
        "date": a.date,
        "badge_url": a.badge_url,
    }


def _recent_games_attrs(s: MisterRAWebStats) -> dict:
    return {
        "games": [
            {
                "title": g.title,
                "console": g.console,
                "earned": g.num_achieved,
                "possible": g.num_possible,
                "percent": g.percent,
                "last_played": g.last_played,
            }
            for g in s.recent_games
        ]
    }


RA_WEB_SENSORS: tuple[RAWebSensorDescription, ...] = (
    RAWebSensorDescription(
        key="ra_hardcore_points",
        translation_key="ra_hardcore_points",
        icon="mdi:trophy",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda s: s.hardcore_points,
    ),
    RAWebSensorDescription(
        key="ra_softcore_points",
        translation_key="ra_softcore_points",
        icon="mdi:trophy-outline",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda s: s.softcore_points,
    ),
    RAWebSensorDescription(
        key="ra_rank",
        translation_key="ra_rank",
        icon="mdi:podium",
        value_fn=lambda s: s.rank,
        attr_fn=lambda s: {"total_ranked": s.total_ranked}
        if s.total_ranked is not None
        else {},
    ),
    RAWebSensorDescription(
        key="ra_current_game",
        translation_key="ra_current_game",
        icon="mdi:gamepad-variant",
        value_fn=lambda s: s.current_game.title if s.current_game else None,
        attr_fn=_current_game_attrs,
    ),
    RAWebSensorDescription(
        key="ra_last_achievement",
        translation_key="ra_last_achievement",
        icon="mdi:medal",
        value_fn=lambda s: s.last_achievement.title if s.last_achievement else None,
        attr_fn=_last_achievement_attrs,
    ),
    RAWebSensorDescription(
        key="ra_recent_games",
        translation_key="ra_recent_games",
        icon="mdi:history",
        value_fn=lambda s: s.recent_games[0].title if s.recent_games else None,
        attr_fn=_recent_games_attrs,
    ),
)


class MisterRAWebSensor(MisterRAWebEntity, SensorEntity):
    entity_description: RAWebSensorDescription

    def __init__(
        self,
        coordinator: MisterRAWebCoordinator,
        entry: ConfigEntry,
        description: RAWebSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self):
        data = self.coordinator.data
        return None if data is None else self.entity_description.value_fn(data)

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        return {} if data is None else self.entity_description.attr_fn(data)
