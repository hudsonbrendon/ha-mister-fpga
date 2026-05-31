"""Latest-screenshot image entity for the MiSTer FPGA integration."""
from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from mister_fpga import MisterConnectionError

from .const import DOMAIN
from .coordinator import MisterDataUpdateCoordinator
from .entity import MisterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MisterScreenshotImage(hass, coordinator, entry)])


class MisterScreenshotImage(MisterEntity, ImageEntity):
    """Serves the most recent MiSTer screenshot."""

    _attr_translation_key = "latest_screenshot"
    _attr_content_type = "image/png"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: MisterDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        MisterEntity.__init__(self, coordinator, entry)
        ImageEntity.__init__(self, hass)
        self._attr_unique_id = f"{entry.entry_id}_latest_screenshot"
        self._cached: bytes | None = None
        self._current_key: str | None = None
        self._attr_image_last_updated = dt_util.utcnow()

    def _handle_coordinator_update(self) -> None:
        """Mark the image as updated so the frontend re-fetches it."""
        self._attr_image_last_updated = dt_util.utcnow()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        try:
            shots = await self.coordinator.client.async_get_screenshots()
        except MisterConnectionError:
            return self._cached
        if not shots:
            return self._cached
        latest = sorted(shots, key=lambda s: s.get("modified", ""))[-1]
        key = f"{latest.get('core')}/{latest.get('filename')}"
        if key != self._current_key or self._cached is None:
            try:
                self._cached = await self.coordinator.client.async_get_screenshot_image(
                    latest["core"], latest["filename"]
                )
                self._current_key = key
            except MisterConnectionError:
                return self._cached
        return self._cached
