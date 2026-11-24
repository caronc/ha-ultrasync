"""Defines the base UltraSync entity."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

# What the panel's web interface tells us about the hardware family.  These
# are the vendor values reported by the ultrasync library.
PANEL_MODELS = {
    "zerowire": ("Interlogix", "ZeroWire UltraSync"),
    "comnav": ("Hills", "ComNav UltraSync"),
    "xgen": ("Interlogix", "xGen UltraSync"),
    "xgen8": ("Interlogix", "xGen8 UltraSync"),
}


def panel_device_info(coordinator, entry_id: str, entry_name: str) -> DeviceInfo:
    """Describe the panel using what it reported when we logged in."""
    hub = coordinator.hub

    # Only report what the panel actually told us; a panel that was never
    # identified keeps the generic details
    manufacturer, model = PANEL_MODELS.get(hub.vendor, ("UltraSync", None))

    sw_version = None
    if hub.version and hub.version != "0.000":
        sw_version = hub.version
        if hub.release and hub.release != "0":
            sw_version = f"{sw_version}-{hub.release}"

    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=entry_name,
        manufacturer=manufacturer,
        model=model,
        sw_version=sw_version,
        # Adds a "Visit" link to the device page
        configuration_url=hub.url,
    )


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
        self._attr_device_info = panel_device_info(coordinator, entry_id, entry_name)
