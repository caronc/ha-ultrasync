"""Defines the base UltraSync entity."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class UltraSyncEntity(CoordinatorEntity):
    """Base class for a UltraSync entity."""

    def __init__(
        self,
        *,
        coordinator,
        entry_id: str,
        entry_name: str,
        name: str,
    ) -> None:
        """Initialize the UltraSync entity."""

        super().__init__(coordinator)

        self._entry_id = entry_id
        self._attr_name = name

        # Group every entity of this integration under one device, named after
        # what the user called the integration when setting it up
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=entry_name,
            manufacturer="UltraSync",
        )
