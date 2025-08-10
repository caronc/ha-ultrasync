"""Provides the UltraSync DataUpdateCoordinator."""
from datetime import timedelta
import logging

from async_timeout import timeout
from homeassistant.const import CONF_HOST, CONF_PIN, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import ultrasync

from .const import DOMAIN, SENSOR_UPDATE_LISTENER

_LOGGER = logging.getLogger(__name__)


class UltraSyncDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching UltraSync data."""

    def __init__(self, hass: HomeAssistant, *, config: dict, options: dict):
        """Initialize global UltraSync data updater."""
        self.hub = ultrasync.UltraSync(
            user=config[CONF_USERNAME],
            pin=config[CONF_PIN],
            host=config[CONF_HOST],
        )

        self._init = False

        # Used to track delta (for change tracking)
        self._area_delta = {}
        self._zone_delta = {}
        self._output_delta = {}
        self._history_delta = {}

        update_interval = timedelta(seconds=options[CONF_SCAN_INTERVAL])

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from UltraSync Hub."""

        # initialize our response
        response = {}

        # The hub can sometimes take a very long time to respond; wait
        async with timeout(10):
            details = await self.hass.async_add_executor_job(lambda: self.hub.details(max_age_sec=0))

        # Update our details
        if details:
            async_dispatcher_send(
                self.hass,
                SENSOR_UPDATE_LISTENER,
                details["areas"],
                details["zones"],
                details["outputs"],
                details["historyData"]
            )

            # Process zone data
            for zone in details["zones"]:
                if self._zone_delta.get(zone["bank"]) != zone["sequence"]:
                    self.hass.bus.fire(
                        "ultrasync_zone_update",
                        {
                            "sensor": zone["bank"] + 1,
                            "name": zone["name"],
                            "status": zone["status"],
                        },
                    )

                    # Update our sequence
                    self._zone_delta[zone["bank"]] = zone["sequence"]

                # Set our state:
                response["zone{:0>2}_state".format(zone["bank"] + 1)] = zone[
                    "status"
                ]

            # Process history data (if present)
            for history in details["historyData"]:
                history_name = history["area_name"]
                sensor_id = "history_name{}state".format(history_name)
                state_value = "{} by {} at {}".format(history["action"], history["user"], history["timestamp"])
                response[sensor_id] = state_value

                # Fire event to get initial state
                self.hass.bus.fire(
                    "ultrasync_history_update",
                    {
                        "name": history_name,
                        "status": history["action"],
                        "timestamp": history["timestamp"],
                        "user": history["user"],
                    },
                )

            # Process area data
            for area in details["areas"]:
                area_changed = self._area_delta.get(area["bank"]) != area["sequence"]
                if area_changed:
                    self.hass.bus.fire(
                        "ultrasync_area_update",
                        {
                            "area": area["bank"] + 1,
                            "name": area["name"],
                            "status": area["status"],
                        },
                    )

                    # Update our sequence
                    self._area_delta[area["bank"]] = area["sequence"]

                    # Update our history when area state changes (if history data is present)
                    if "history" in details and details["historyData"]:
                        for history in details["historyData"]:
                            history_name = history["area_name"]
                            sensor_id = "history_name{}state".format(history_name)
                            state_value = "{} by {} at {}".format(history["action"], history["user"], history["timestamp"])
                            if history_name == area["name"]:
                               self.hass.bus.fire(
                                   "ultrasync_history_update",
                                   {
                                        "name": history_name,
                                        "status": history["action"],
                                        "timestamp": history["timestamp"],
                                        "user": history["user"],
                                   },
                               )
                               self._history_delta[history["area_name"]] = history["action"]
                               response[sensor_id] = state_value

                # Set our state:
                response["area{:0>2}_state".format(area["bank"] + 1)] = area[
                    "status"
                ]

            # Process output data (if present)
            output_index = 1
            for output in details["outputs"]:
                if self._output_delta.get(output["name"]) != output["state"]:
                    self.hass.bus.fire(
                        "ultrasync_output_update",
                        {
                            "name": output["name"],
                            "status": output["state"],
                        },
                    )

                    # Update our sequence
                    self._output_delta[output["name"]] = output["state"]

                # Set our state:
                response["output{}state".format(output_index)] = output[
                    "state"
                ]
                output_index += 1

        self._init = True

        # Return our response
        return response
