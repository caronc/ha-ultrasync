"""Config flow for the Interlogix/Hills ComNav UltraSync Hub."""
import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType
import ultrasync
import voluptuous as vol

from .const import DEFAULT_NAME, DEFAULT_SCAN_INTERVAL
from .const import DOMAIN  # pylint: disable=unused-import

_LOGGER = logging.getLogger(__name__)


class AuthFailureException(IOError):
    """A general exception we can use to track Authentication failures."""


def validate_input(hass: HomeAssistant, data: dict) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""

    usync = ultrasync.UltraSync(
        host=data[CONF_HOST], user=data[CONF_USERNAME], pin=data[CONF_PIN]
    )

    # validate by attempting to authenticate with the host

    if not usync.login():
        # report our connection issue
        raise AuthFailureException()

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
            # ---- PIN validation ----
            pin = user_input.get(CONF_PIN, "")
            if not isinstance(pin, str):
                pin = str(pin)
            if not pin.isdigit():
                errors["pin"] = "invalid_pin"
            elif not (4 <= len(pin) <= 8):
                errors["pin"] = "invalid_pin_length"

            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Optional(CONF_NAME, default=user_input.get(CONF_NAME, DEFAULT_NAME)): str,
                            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
                            vol.Required(CONF_USERNAME, default=user_input.get(CONF_USERNAME, "")): str,
                            vol.Required(CONF_PIN, default=user_input.get(CONF_PIN, "")): TextSelector(
                                TextSelectorConfig(type=TextSelectorType.PASSWORD)
                            ),
                        }
                    ),
                    errors=errors,
                )
            # ------------------------

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
                    vol.Required(CONF_PIN): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )


class UltraSyncOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle UltraSync client options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: Optional[ConfigType] = None):
        """Manage UltraSync options."""

        current_data = {
            **self._config_entry.data,
            **self._config_entry.options,
        }

        if user_input is not None:
            # ---- PIN validation ----
            errors = {}
            pin = user_input.get(CONF_PIN, "")
            if pin:
                if not isinstance(pin, str):
                    pin = str(pin)
                if not pin.isdigit():
                    errors["pin"] = "invalid_pin"
                elif not (4 <= len(pin) <= 8):
                    errors["pin"] = "invalid_pin_length"

            if errors:
                return self.async_show_form(
                    step_id="init",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, current_data.get(CONF_HOST, ""))): str,
                            vol.Required(CONF_USERNAME, default=user_input.get(CONF_USERNAME, current_data.get(CONF_USERNAME, ""))): str,
                            vol.Required(CONF_PIN, default=user_input.get(CONF_PIN, current_data.get(CONF_PIN, ""))): TextSelector(
                                TextSelectorConfig(type=TextSelectorType.PASSWORD)
                            ),
                            vol.Optional(
                                CONF_SCAN_INTERVAL,
                                default=user_input.get(CONF_SCAN_INTERVAL, current_data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
                            ): int,
                        }
                    ),
                    errors=errors,
                )
            # ------------------------

            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_data.get(CONF_HOST, "")): str,
                vol.Required(CONF_USERNAME, default=current_data.get(CONF_USERNAME, "")): str,
                vol.Required(CONF_PIN, default=current_data.get(CONF_PIN, "")): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current_data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): int,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)