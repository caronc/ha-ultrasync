"""Config flow for the Interlogix/Hills ComNav UltraSync Hub."""
import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.typing import ConfigType
import ultrasync
import voluptuous as vol

from .const import DEFAULT_NAME, DEFAULT_SCAN_INTERVAL
from .const import DOMAIN  # pylint: disable=unused-import

_LOGGER = logging.getLogger(__name__)

# The PIN field hides what is typed, like a password box.
PIN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

# Details needed to log in to the panel. Used when changing them later.
RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PIN): PIN_SELECTOR,
    }
)


class AuthFailureException(IOError):
    """A general exception we can use to track Authentication failures."""


def validate_input(hass: HomeAssistant, data: dict) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""

    usync = ultrasync.UltraSync(
        host=data[CONF_HOST], user=data[CONF_USERNAME], pin=data[CONF_PIN]
    )

    # validate by attempting to authenticate with our hub
    try:
        if not usync.login():
            # report our connection issue
            raise AuthFailureException()

    finally:
        # Log the test session off again, so it does not stay open on the
        # panel next to the one the integration uses.
        usync.logout()

    return True


class UltraSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """UltraSync config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return UltraSyncOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: Optional[ConfigType] = None
    ) -> Dict[str, Any]:
        """Handle user flow."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}

        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(
                    validate_input, self.hass, user_input
                )

            except AuthFailureException:
                errors["base"] = "cannot_connect"

            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                return self.async_abort(reason="unknown")
            else:
                return self.async_create_entry(
                    title=user_input[CONF_HOST],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PIN): PIN_SELECTOR,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: Optional[ConfigType] = None
    ) -> Dict[str, Any]:
        """Change the host, username or PIN of an existing setup."""
        entry = self._get_reconfigure_entry()
        errors = {}

        if user_input is not None:
            # Only save the new details once they can log in to the panel.
            try:
                await self.hass.async_add_executor_job(
                    validate_input, self.hass, user_input
                )

            except AuthFailureException:
                # The panel refused the details or could not be reached.
                errors["base"] = "cannot_connect"

            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                return self.async_abort(reason="unknown")

            else:
                # The entry is named after the host when it is first set up.
                # Follow a new host, unless the user renamed the entry.
                title = (
                    user_input[CONF_HOST]
                    if entry.title == entry.data[CONF_HOST]
                    else entry.title
                )

                # A running integration reloads itself when its details
                # change. One that failed to start (for example because
                # the panel was offline) is started again here, even if
                # the details stayed the same. The state is read first,
                # because saving starts the reload straight away.
                was_loaded = entry.state is ConfigEntryState.LOADED
                self.hass.config_entries.async_update_entry(
                    entry, title=title, data={**entry.data, **user_input}
                )
                if not was_loaded:
                    self.hass.config_entries.async_schedule_reload(entry.entry_id)

                return self.async_abort(reason="reconfigure_successful")

        # Fill the form with what is saved today (or what was just typed).
        # The PIN is left blank, so it is never sent back to the browser.
        suggested = {
            key: value
            for key, value in (user_input or entry.data).items()
            if key != CONF_PIN
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                RECONFIGURE_SCHEMA, suggested
            ),
            errors=errors,
        )


class UltraSyncOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle UltraSync client options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        # Newer Home Assistant sets self.config_entry itself and does not
        # allow it to be assigned, so keep our own reference.
        self._entry = config_entry

    async def async_step_init(self, user_input: Optional[ConfigType] = None):
        """Manage UltraSync options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self._entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
                # From one second up to one day. Zero or less would poll
                # non-stop, and very large numbers stop the setup loading.
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=86400)),
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
