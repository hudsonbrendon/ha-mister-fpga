"""Select entity for launching MiSTer systems."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MisterEntity

BACKGROUND_MODES = {
    "None": 0, "Logo": 1, "Wallpaper": 2, "Custom 1": 3,
    "Custom 2": 4, "Custom 3": 5, "Custom 4": 6, "Custom 5": 7,
}
_BG_BY_VALUE = {v: k for k, v in BACKGROUND_MODES.items()}
MUSIC_PLAYBACK_MODES = ["random", "loop", "disabled"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            MisterSystemSelect(coordinator, entry),
            MisterActiveIniSelect(coordinator, entry),
            MisterBackgroundModeSelect(coordinator, entry),
            MisterWallpaperSelect(coordinator, entry),
            MisterMusicPlaylistSelect(coordinator, entry),
            MisterMusicPlaybackSelect(coordinator, entry),
            MisterRunScriptSelect(coordinator, entry),
        ]
    )


class MisterSystemSelect(MisterEntity, SelectEntity):
    """Pick a system to launch on the MiSTer."""

    _attr_translation_key = "launch_system"
    _attr_icon = "mdi:rocket-launch"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_launch_system"

    @property
    def options(self) -> list[str]:
        return sorted(
            s["name"] for s in self.coordinator.systems if s.get("name")
        )

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        name = data.system_name or data.system
        return name if name in self.options else None

    async def async_select_option(self, option: str) -> None:
        for system in self.coordinator.systems:
            if system.get("name") == option:
                await self.coordinator.client.async_launch_system(system["id"])
                await self.coordinator.async_request_refresh()
                return


class MisterActiveIniSelect(MisterEntity, SelectEntity):
    _attr_translation_key = "active_ini"
    _attr_icon = "mdi:file-cog"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_active_ini"

    @property
    def options(self) -> list[str]:
        return [i.get("displayName", str(i.get("id"))) for i in self.coordinator.inis]

    @property
    def current_option(self) -> str | None:
        for i in self.coordinator.inis:
            if i.get("id") == self.coordinator.active_ini_id:
                return i.get("displayName")
        return None

    async def async_select_option(self, option: str) -> None:
        for i in self.coordinator.inis:
            if i.get("displayName") == option:
                await self.coordinator.client.async_set_active_ini(i["id"])
                await self.coordinator.async_request_refresh()
                return


class MisterBackgroundModeSelect(MisterEntity, SelectEntity):
    _attr_translation_key = "background_mode"
    _attr_icon = "mdi:image-frame"
    _attr_options = list(BACKGROUND_MODES)

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_background_mode"

    @property
    def current_option(self) -> str | None:
        mode = self.coordinator.wallpapers.get("backgroundMode")
        return _BG_BY_VALUE.get(mode)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.async_set_background_mode(
            BACKGROUND_MODES[option]
        )
        await self.coordinator.async_request_refresh()


class MisterWallpaperSelect(MisterEntity, SelectEntity):
    _attr_translation_key = "wallpaper"
    _attr_icon = "mdi:wallpaper"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_wallpaper"

    @property
    def options(self) -> list[str]:
        return [
            w.get("filename")
            for w in self.coordinator.wallpapers.get("wallpapers", [])
            if w.get("filename")
        ]

    @property
    def current_option(self) -> str | None:
        return self.coordinator.wallpapers.get("active") or None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.async_set_wallpaper(option)
        await self.coordinator.async_request_refresh()


class MisterMusicPlaylistSelect(MisterEntity, SelectEntity):
    _attr_translation_key = "music_playlist"
    _attr_icon = "mdi:playlist-music"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_music_playlist"
        self._playlists: list[str] = []

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        from .api import MisterConnectionError
        try:
            self._playlists = await self.coordinator.client.async_get_music_playlists()
        except MisterConnectionError:
            self._playlists = []
        self.async_write_ha_state()

    @property
    def options(self) -> list[str]:
        return self._playlists

    @property
    def current_option(self) -> str | None:
        return self.coordinator.music.get("playlist") or None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.async_set_music_playlist(option)
        await self.coordinator.async_request_refresh()


class MisterMusicPlaybackSelect(MisterEntity, SelectEntity):
    _attr_translation_key = "music_playback"
    _attr_icon = "mdi:repeat"
    _attr_options = MUSIC_PLAYBACK_MODES

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_music_playback"

    @property
    def current_option(self) -> str | None:
        return self.coordinator.music.get("playback") or None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.async_set_music_playback(option)
        await self.coordinator.async_request_refresh()


class MisterRunScriptSelect(MisterEntity, SelectEntity):
    _attr_translation_key = "run_script"
    _attr_icon = "mdi:script-text-play"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_run_script"

    @property
    def options(self) -> list[str]:
        return [s.get("name") for s in self.coordinator.scripts if s.get("name")]

    @property
    def current_option(self) -> str | None:
        return None

    async def async_select_option(self, option: str) -> None:
        for s in self.coordinator.scripts:
            if s.get("name") == option:
                await self.coordinator.client.async_launch_script(s["filename"])
                return
