"""Support for UltraSync alarm control panels."""

import logging
from typing import Any, Optional

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from ultrasync import AlarmScene
from ultrasync.common import AreaStatus

from .const import DATA_COORDINATOR, DEFAULT_NAME, DOMAIN
from .coordinator import UltraSyncDataUpdateCoordinator
from .entity import UltraSyncEntity

_LOGGER = logging.getLogger(__name__)

# Area status text that means the alarm is going off
TRIGGERED_STATUS = (
    AreaStatus.ALARM_FIRE,
    AreaStatus.ALARM_BURGLAR,
    AreaStatus.ALARM_PANIC,
    AreaStatus.ALARM_MEDICAL,
)

# Area status text for the countdown after arming (it can carry a suffix such
# as " - Night")
EXIT_DELAY_STATUS = (AreaStatus.DELAY_EXIT_1, AreaStatus.DELAY_EXIT_2)

# How the panel's arm mode maps onto Home Assistant's alarm states
ARM_STATE_MAP = {
    AlarmScene.AWAY: AlarmControlPanelState.ARMED_AWAY,
    AlarmScene.STAY: AlarmControlPanelState.ARMED_HOME,
    AlarmScene.DISARMED: AlarmControlPanelState.DISARMED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one UltraSync alarm control panel for each area."""
    coordinator: UltraSyncDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ][DATA_COORDINATOR]

    # The first poll has already run, so the panel's areas are known
    entry_name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    async_add_entities(
        UltraSyncAlarmControlPanel(coordinator, entry.entry_id, entry_name, area)
        for area in coordinator.areas
    )


class UltraSyncAlarmControlPanel(UltraSyncEntity, AlarmControlPanelEntity):
    """Representation of one UltraSync area as an alarm control panel."""

    # The panel login already carries the PIN, so no code is asked for
    _attr_code_arm_required = False
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
    )

    def __init__(
        self,
        coordinator: UltraSyncDataUpdateCoordinator,
        entry_id: str,
        entry_name: str,
        area: dict[str, Any],
    ) -> None:
        """Initialize the alarm control panel for one area."""

        # The area's position on the panel (starting at 0)
        self._bank = area["bank"]
        self._attr_unique_id = f"{entry_id}_alarm_{self._bank}"

        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            entry_name=entry_name,
            name=f"{entry_name} {area['name']}",
        )

    @property
    def _area(self) -> Optional[dict[str, Any]]:
        """Return this area from the latest poll, if the panel still has it."""
        # Look the area up by bank; the list is rebuilt on every poll
        return next(
            (a for a in self.coordinator.areas if a["bank"] == self._bank), None
        )

    @property
    def alarm_state(self) -> Optional[AlarmControlPanelState]:
        """Return the current state of the alarm."""
        area = self._area
        if area is None:
            # The area vanished from the panel; report its state as unknown
            return None

        # The status text is what the keypad shows.  Only plain strings are
        # compared, since a few sensor status values are not strings.
        status = area.get("status")
        status = status if isinstance(status, str) else ""

        # An alarm going off wins over everything else
        if status in TRIGGERED_STATUS:
            return AlarmControlPanelState.TRIGGERED

        # Someone came in while armed; the alarm goes off unless disarmed
        if status == AreaStatus.DELAY_ENTRY:
            return AlarmControlPanelState.PENDING

        # The countdown to leave after arming
        if status.startswith(EXIT_DELAY_STATUS):
            return AlarmControlPanelState.ARMING

        # Otherwise the panel's own arm flags decide.  The status text can't
        # be used here: it reads "Ready", "Not Ready" or "Sensor Bypass" in
        # several arm modes.
        return ARM_STATE_MAP.get(area.get("arm_state"))

    def _set_alarm(self, state: str) -> bool:
        """Send an arm mode to this area only, between polls."""
        # Areas are numbered from 1 when sending, but banks start at 0
        with self.coordinator.hub_lock:
            return self.coordinator.hub.set_alarm(areas=self._bank + 1, state=state)

    async def _async_send(self, state: str) -> None:
        """Send an arm mode and refresh, raising an error if the panel refused."""
        if not await self.hass.async_add_executor_job(self._set_alarm, state):
            # Let the user see the failure instead of a silently unchanged panel
            raise HomeAssistantError(
                f"UltraSync could not set {self.name} to {state}"
            )

        # Show the new state as soon as the panel reports it
        await self.coordinator.async_request_refresh()

    async def async_alarm_disarm(self, code: Optional[str] = None) -> None:
        """Send disarm command."""
        await self._async_send(AlarmScene.DISARMED)

    async def async_alarm_arm_home(self, code: Optional[str] = None) -> None:
        """Send arm home (stay) command."""
        await self._async_send(AlarmScene.STAY)

    async def async_alarm_arm_away(self, code: Optional[str] = None) -> None:
        """Send arm away command."""
        await self._async_send(AlarmScene.AWAY)
