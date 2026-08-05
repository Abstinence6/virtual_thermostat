"""Config flow for Virtual Thermostat integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_CLIMATE,
    CONF_DELTA_AC,
    CONF_HYSTERESIS,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_SENSOR,
    CONF_TARGET_TEMP,
    DEFAULT_DELTA_AC,
    DEFAULT_HYSTERESIS,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_TARGET_TEMP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def _validate_config(hass: HomeAssistant, data: dict[str, Any]) -> list[str]:
    """Validate the configured entities. Returns a list of errors."""
    errors: list[str] = []

    sensor_state = hass.states.get(data[CONF_SENSOR])
    if sensor_state is None:
        errors.append("sensor_not_found")
    elif sensor_state.state in ("unknown", "unavailable"):
        errors.append("sensor_unavailable")

    climate_state = hass.states.get(data[CONF_CLIMATE])
    if climate_state is None:
        errors.append("climate_not_found")
    elif climate_state.domain != "climate":
        errors.append("climate_not_climate")

    return errors


def _config_schema(values: dict[str, Any] | None = None) -> vol.Schema:
    """Return the shared setup/options schema."""
    values = values or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_NAME,
                default=values.get(CONF_NAME, "Virtual Thermostat"),
            ): selector.TextSelector(),
            vol.Required(
                CONF_CLIMATE,
                default=values.get(CONF_CLIMATE, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate")
            ),
            vol.Required(
                CONF_SENSOR,
                default=values.get(CONF_SENSOR, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(
                CONF_DELTA_AC,
                default=values.get(CONF_DELTA_AC, DEFAULT_DELTA_AC),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-20,
                    max=20,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_HYSTERESIS,
                default=values.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1,
                    max=5.0,
                    step=0.1,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_TARGET_TEMP,
                default=values.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=DEFAULT_MIN_TEMP,
                    max=DEFAULT_MAX_TEMP,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_MIN_TEMP,
                default=values.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5, max=20, step=1, unit_of_measurement="°C"
                )
            ),
            vol.Required(
                CONF_MAX_TEMP,
                default=values.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=25, max=45, step=1, unit_of_measurement="°C"
                )
            ),
        }
    )


def _error_map(errors: list[str] | None) -> dict[str, str] | None:
    """Convert validation errors to the flow error format."""
    if not errors:
        return None
    return {"base": errors[-1]}


class VirtualThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Virtual Thermostat."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self._show_form()

        errors = await _validate_config(self.hass, user_input)
        if errors:
            return self._show_form(user_input, errors)

        unique_id = (
            f"vt_{user_input[CONF_SENSOR]}_{user_input[CONF_CLIMATE]}".replace(
                ".", "_"
            )
        )
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        _LOGGER.debug(
            "Creating entry with data: %s",
            {k: v for k, v in user_input.items() if k != CONF_NAME},
        )
        return self.async_create_entry(
            title=user_input.get(CONF_NAME, "Virtual Thermostat"),
            data=user_input,
        )

    @callback
    def _show_form(
        self,
        user_input: dict[str, Any] | None = None,
        errors: list[str] | None = None,
    ) -> FlowResult:
        """Show the initial configuration form."""
        return self.async_show_form(
            step_id="user",
            data_schema=_config_schema(user_input),
            errors=_error_map(errors),
            description_placeholders={
                "climate": "Real AC entity (e.g., climate.living_room_ac)",
                "sensor": "Temperature sensor (e.g., sensor.living_room_temp)",
                "delta_ac": "Offset between target and AC setpoint. "
                "Positive = cooling boost, Negative = heating boost.",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow shown by HA's Configure button."""
        return VirtualThermostatOptionsFlow(config_entry)


class VirtualThermostatOptionsFlow(config_entries.OptionsFlow):
    """Allow all setup values to be changed after entry creation."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the options form."""
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is None:
            return self._show_form(current)

        errors = await _validate_config(self.hass, user_input)
        if errors:
            return self._show_form({**current, **user_input}, errors)

        return self.async_create_entry(title="", data=user_input)

    @callback
    def _show_form(
        self,
        values: dict[str, Any],
        errors: list[str] | None = None,
    ) -> FlowResult:
        """Show the options form with the current runtime values."""
        return self.async_show_form(
            step_id="init",
            data_schema=_config_schema(values),
            errors=_error_map(errors),
        )
