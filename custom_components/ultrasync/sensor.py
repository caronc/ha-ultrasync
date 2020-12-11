"""Monitor the Interlogix/Hills ComNav UltraSync Hub."""

import logging
from typing import Callable, List

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType

from . import UltraSyncEntity
from .const import ZONE_LISTENER, DATA_COORDINATOR, DOMAIN
from .coordinator import UltraSyncDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SENSORS = {
    "area01_state": "Area1State",
    "area02_state": "Area2State",
    "area03_state": "Area3State",
    "area04_state": "Area4State",
}


async def async_setup_entry(
    hass: HomeAssistantType,
    entry: ConfigEntry,
    async_add_entities: Callable[[List[Entity], bool], None],
) -> None:
    """Set up UltraSync sensor based on a config entry."""
    coordinator: UltraSyncDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    sensors = []

    for sensor_type, sensor_name in SENSORS.items():
        sensors.append(
            UltraSyncSensor(
                coordinator,
                entry.entry_id,
                entry.data[CONF_NAME],
                sensor_type,
                sensor_name,
            )
        )

    async_add_entities(sensors)

    _zones = {}

    @callback
    def _prepare_zone_sensors(zones: dict) -> None:
        """Dynamically create sensors based on detected zones."""

        # our list of zones to add
        sensors = []

        for meta in zones:
            bank_no = meta['bank']
            if bank_no not in _zones:
                # hash our entry
                _zones[bank_no] = UltraSyncSensor(
                    coordinator,
                    entry.entry_id,
                    entry.data[CONF_NAME],
                    "zone{:0>2}_state".format(bank_no + 1),
                    "Zone{}State".format(bank_no + 1),
                )
                # Add our bank
                sensors.append(_zones[bank_no])

        if sensors:
            async_add_entities(sensors)

    # register our callback which will be called the second we make a
    # connection to our panel
    async_dispatcher_connect(hass, ZONE_LISTENER, _prepare_zone_sensors)


class UltraSyncSensor(UltraSyncEntity):
    """Representation of a UltraSync sensor."""

    def __init__(
        self,
        coordinator: UltraSyncDataUpdateCoordinator,
        entry_id: str,
        entry_name: str,
        sensor_type: str,
        sensor_name: str,
    ):
        """Initialize a new UltraSync sensor."""

        self._sensor_type = sensor_type
        self._unique_id = f"{entry_id}_{sensor_type}"

        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            name=f"{entry_name} {sensor_name}",
        )

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        value = self.coordinator.data.get(self._sensor_type)
        if value is None:
            _LOGGER.warning("Unable to locate value for %s", self._sensor_type)
            return None

        return value
