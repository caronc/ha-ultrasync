"""Provides the UltraSync DataUpdateCoordinator."""
from datetime import timedelta
import logging
import threading

try:
    # Python 3.11+ has this built in; newer Home Assistant no longer ships
    # the async_timeout package
    from asyncio import timeout

except ImportError:
    from async_timeout import timeout

from homeassistant.const import CONF_HOST, CONF_PIN, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import ultrasync

from .const import DOMAIN, SENSOR_UPDATE_LISTENER
from .history import fetch_history

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

        # Polls and alarm panel commands run in different worker threads, but
        # share one panel session; this lock makes them take turns
        self.hub_lock = threading.Lock()

        # The areas from the last successful poll (used by the alarm panels)
        self.areas = []

        # Used to track delta (for change tracking)
        self._area_delta = {}
        self._zone_delta = {}
        self._output_delta = {}
        self._history_delta = {}
        self._last_history_key = None
        self._last_disarmed_by = None
        self._last_armed_by = None

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
            details = await self.hass.async_add_executor_job(self._details)

        # Update our details
        if details:
            # Keep the latest areas for the alarm panels
            self.areas = details["areas"]

            async_dispatcher_send(
                self.hass,
                SENSOR_UPDATE_LISTENER,
                details["areas"],
                details["zones"],
                details["outputs"],
                details["history_data"]
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

            # Only announce new history records. Do not replay the latest
            # historical event on Home Assistant startup.
            for history in details["history_data"]:
                history_name = history.get("area_name") or "System"
                sensor_id = "history_name{}state".format(history_name)
                state_value = "{} by {} at {}".format(history["action"], history["user"], history["timestamp"])
                response[sensor_id] = state_value

                key = (history.get("record"), history.get("raw"))
                if self._last_history_key is not None and key != self._last_history_key:
                    self.hass.bus.fire(
                        "ultrasync_history_update",
                        {
                            "name": history_name,
                            "status": history["action"],
                            "timestamp": history["timestamp"],
                            "user": history["user"],
                            "record": history.get("record"),
                            "details": history.get("details", []),
                        },
                    )
                if key != self._last_history_key:
                    action = history["action"].casefold()
                    user = history.get("user")
                    if user and action == "turn off":
                        self._last_disarmed_by = user
                    elif user and action == "turn on":
                        self._last_armed_by = user
                self._last_history_key = key

            response["last_disarmed_by"] = self._last_disarmed_by
            response["last_armed_by"] = self._last_armed_by

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

    def _details(self) -> dict:
        """Read the panel details, waiting for any alarm command to finish."""
        with self.hub_lock:
            details = self.hub.details(max_age_sec=0)
            if not details:
                return details
            # The library's legacy history.htm parser cannot see all ComNav
            # XML events. Only use XML when this panel exposes ComNav history.
            if details.get("history_data"):
                latest = fetch_history(self.hub)
                if latest:
                    details["history_data"] = [latest]
            return details
