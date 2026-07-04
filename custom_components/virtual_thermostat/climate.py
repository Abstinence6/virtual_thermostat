"""Virtual Thermostat climate platform.

A virtual climate entity that:
- Reads a real temperature sensor
- Controls a real AC (climate entity)
- Uses configurable delta between target and AC setpoint
- Uses hysteresis to prevent short cycling
"""

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    STATE_UNAVAILABLE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    ATTR_AC_TEMPERATURE,
    ATTR_CLIMATE_ENTITY,
    ATTR_DELTA_MEASURED,
    ATTR_HYSTERESIS,
    ATTR_SENSOR_ENTITY,
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
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Virtual Thermostat from YAML configuration."""
    _LOGGER.debug("Setting up Virtual Thermostat platform from YAML")
    # discovery_info is not used - we read config directly
    entity = VirtualThermostatClimate(
        hass=hass,
        name=config.get(CONF_NAME, "Virtual Thermostat"),
        climate_entity_id=config[CONF_CLIMATE],
        sensor_entity_id=config[CONF_SENSOR],
        delta_ac=config.get(CONF_DELTA_AC, DEFAULT_DELTA_AC),
        hysteresis=config.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS),
        target_temperature=config.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP),
        min_temp=config.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP),
        max_temp=config.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP),
    )
    async_add_entities([entity])

    # Register entity services
    platform = entity_platform.async_get_current_platform()
    _register_services(platform)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Virtual Thermostat from a config entry (UI)."""
    _LOGGER.debug(
        "Setting up Virtual Thermostat from config entry: %s",
        config_entry.entry_id,
    )
    data = config_entry.data

    entity = VirtualThermostatClimate(
        hass=hass,
        name=data.get(CONF_NAME, "Virtual Thermostat"),
        climate_entity_id=data[CONF_CLIMATE],
        sensor_entity_id=data[CONF_SENSOR],
        delta_ac=data.get(CONF_DELTA_AC, DEFAULT_DELTA_AC),
        hysteresis=data.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS),
        target_temperature=data.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP),
        min_temp=data.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP),
        max_temp=data.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP),
    )
    async_add_entities([entity])

    # Register entity services
    platform = entity_platform.async_get_current_platform()
    _register_services(platform)


class VirtualThermostatClimate(ClimateEntity, RestoreEntity):
    """Virtual thermostat that controls a real AC based on sensor readings."""

    _attr_should_poll = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        climate_entity_id: str,
        sensor_entity_id: str,
        delta_ac: float,
        hysteresis: float,
        target_temperature: float,
        min_temp: float,
        max_temp: float,
    ) -> None:
        """Initialize the virtual thermostat."""
        self.hass = hass
        self._attr_name = name
        self._attr_unique_id = f"virtual_thermostat_{name.lower().replace(' ', '_')}"

        self._climate_entity_id = climate_entity_id
        self._sensor_entity_id = sensor_entity_id
        self._delta_ac = delta_ac
        self._hysteresis = hysteresis
        self._attr_min_temp = min_temp
        self._attr_max_temp = max_temp

        # Initial state
        self._attr_target_temperature = target_temperature
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_hvac_action = HVACAction.OFF

        # Internal state tracking
        self._ac_is_running = False
        self._last_sensor_state: float | None = None

        _LOGGER.debug(
            "Virtual Thermostat '%s' initialized: "
            "climate=%s, sensor=%s, delta_ac=%s, hysteresis=%s",
            name,
            climate_entity_id,
            sensor_entity_id,
            delta_ac,
            hysteresis,
        )

    # ─── Properties ────────────────────────────────────────────────

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature from the sensor."""
        state = self.hass.states.get(self._sensor_entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, "unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        current_temp = self.current_temperature
        ac_temp = self._get_ac_target_temperature()

        delta_measured = None
        if current_temp is not None:
            delta_measured = round(current_temp - self._attr_target_temperature, 1)

        return {
            ATTR_AC_TEMPERATURE: ac_temp,
            ATTR_DELTA_MEASURED: delta_measured,
            ATTR_HYSTERESIS: self._hysteresis,
            ATTR_SENSOR_ENTITY: self._sensor_entity_id,
            ATTR_CLIMATE_ENTITY: self._climate_entity_id,
            "ac_is_running": self._ac_is_running,
        }

    # ─── Temperature / Mode Control ────────────────────────────────

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return

        # Clamp to valid range
        temp = max(self._attr_min_temp, min(self._attr_max_temp, temp))
        self._attr_target_temperature = temp

        _LOGGER.debug(
            "Target temperature set to %s°C on '%s'",
            temp,
            self._attr_name,
        )

        # If the AC should be running, update its target
        if self._hvac_mode != HVACMode.OFF and self._should_ac_run():
            await self._start_ac()
        elif self._hvac_mode != HVACMode.OFF and not self._should_ac_run():
            await self._stop_ac()

        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode (off/cool/heat)."""
        self._attr_hvac_mode = hvac_mode
        _LOGGER.debug("HVAC mode set to %s on '%s'", hvac_mode, self._attr_name)

        if hvac_mode == HVACMode.OFF:
            await self._stop_ac()
            self._attr_hvac_action = HVACAction.OFF
            self._ac_is_running = False
        else:
            if self._should_ac_run():
                await self._start_ac()
            else:
                await self._stop_ac()
                self._attr_hvac_action = (
                    HVACAction.IDLE
                    if hvac_mode == HVACMode.COOL
                    else HVACAction.IDLE
                )

        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn the thermostat on (restore last mode or default to cool)."""
        if self._attr_hvac_mode == HVACMode.OFF:
            await self.async_set_hvac_mode(HVACMode.COOL)

    async def async_turn_off(self) -> None:
        """Turn the thermostat off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    # ─── Custom Services ────────────────────────────────────────────

    async def async_set_ac_offset(self, delta_ac: float) -> None:
        """Service call to set the delta_ac value."""
        self._delta_ac = delta_ac
        _LOGGER.debug(
            "delta_ac set to %s°C on '%s'", delta_ac, self._attr_name
        )
        # Recalculate AC target if running
        if self._ac_is_running:
            await self._start_ac()
        self.async_write_ha_state()

    async def async_set_hysteresis(self, hysteresis: float) -> None:
        """Service call to set the hysteresis value."""
        self._hysteresis = hysteresis
        _LOGGER.debug(
            "hysteresis set to %s°C on '%s'", hysteresis, self._attr_name
        )
        self.async_write_ha_state()

    # ─── Update Logic ───────────────────────────────────────────────

    async def async_update(self) -> None:
        """Poll the sensor and decide if AC should turn on/off."""
        current_temp = self.current_temperature
        if current_temp is None:
            _LOGGER.warning(
                "Sensor '%s' is not available for '%s'",
                self._sensor_entity_id,
                self._attr_name,
            )
            # Fail-safe: if sensor is lost, turn off AC
            if self._ac_is_running:
                await self._stop_ac()
            return

        # Update hvac_action based on AC state
        if self._attr_hvac_mode == HVACMode.OFF:
            self._attr_hvac_action = HVACAction.OFF
        elif self._ac_is_running:
            if self._attr_hvac_mode == HVACMode.COOL:
                self._attr_hvac_action = HVACAction.COOLING
            elif self._attr_hvac_mode == HVACMode.HEAT:
                self._attr_hvac_action = HVACAction.HEATING
        else:
            self._attr_hvac_action = HVACAction.IDLE

        # Check if we need to change AC state based on temperature
        if self._attr_hvac_mode == HVACMode.OFF:
            return  # Nothing to do if thermostat is off

        should_run = self._should_ac_run()

        if should_run and not self._ac_is_running:
            _LOGGER.debug(
                "Starting AC: temp=%s°C, target=%s°C, delta_ac=%s°C",
                current_temp,
                self._attr_target_temperature,
                self._delta_ac,
            )
            await self._start_ac()
        elif not should_run and self._ac_is_running:
            _LOGGER.debug(
                "Stopping AC: temp=%s°C reached target=%s°C",
                current_temp,
                self._attr_target_temperature,
            )
            await self._stop_ac()

        self._last_sensor_state = current_temp
        self.async_write_ha_state()

    def _should_ac_run(self) -> bool:
        """Determine if the AC should be running based on current temperature."""
        current_temp = self.current_temperature
        if current_temp is None:
            return False

        target = self._attr_target_temperature
        hyst = self._hysteresis

        if self._attr_hvac_mode == HVACMode.COOL:
            # In cooling mode:
            # - AC was running: keep running until temp <= target
            # - AC was stopped: start only when temp >= target + hysteresis
            if self._ac_is_running:
                return current_temp > target
            else:
                return current_temp >= target + hyst

        elif self._attr_hvac_mode == HVACMode.HEAT:
            # In heating mode:
            # - AC was running: keep running until temp >= target
            # - AC was stopped: start only when temp <= target - hysteresis
            if self._ac_is_running:
                return current_temp < target
            else:
                return current_temp <= target - hyst

        return False

    # ─── AC Control ────────────────────────────────────────────────

    def _get_ac_target_temperature(self) -> float:
        """Calculate the target temperature to send to the real AC."""
        ac_temp = self._attr_target_temperature + self._delta_ac
        # Clamp to reasonable range
        return round(max(10, min(40, ac_temp)), 1)

    async def _start_ac(self) -> None:
        """Turn on the real AC with the calculated setpoint."""
        ac_temp = self._get_ac_target_temperature()

        _LOGGER.debug(
            "Starting real AC '%s' with target %s°C "
            "(user target: %s°C, delta_ac: %s°C)",
            self._climate_entity_id,
            ac_temp,
            self._attr_target_temperature,
            self._delta_ac,
        )

        # Set the temperature on the real AC
        await self.hass.services.async_call(
            "climate",
            "set_temperature",
            {
                "entity_id": self._climate_entity_id,
                "temperature": ac_temp,
            },
            blocking=True,
        )

        # Set the HVAC mode on the real AC
        await self.hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {
                "entity_id": self._climate_entity_id,
                "hvac_mode": self._attr_hvac_mode,
            },
            blocking=True,
        )

        # Turn on the real AC
        await self.hass.services.async_call(
            "climate",
            "turn_on",
            {"entity_id": self._climate_entity_id},
            blocking=True,
        )

        self._ac_is_running = True
        self.async_write_ha_state()

    async def _stop_ac(self) -> None:
        """Turn off the real AC."""
        _LOGGER.debug(
            "Stopping real AC '%s'",
            self._climate_entity_id,
        )

        await self.hass.services.async_call(
            "climate",
            "turn_off",
            {"entity_id": self._climate_entity_id},
            blocking=True,
        )

        self._ac_is_running = False
        self.async_write_ha_state()

    # ─── Restore State ──────────────────────────────────────────────

    async def async_added_to_hass(self) -> None:
        """Restore last state on HA restart."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            _LOGGER.debug(
                "Restoring state for '%s': %s",
                self._attr_name,
                last_state.state,
            )

            # Restore HVAC mode
            if last_state.state in [
                HVACMode.OFF,
                HVACMode.COOL,
                HVACMode.HEAT,
            ]:
                self._attr_hvac_mode = last_state.state

            # Restore target temperature
            if last_state.attributes.get("temperature") is not None:
                self._attr_target_temperature = float(
                    last_state.attributes["temperature"]
                )

            # Restore hysteresis
            if last_state.attributes.get(ATTR_HYSTERESIS) is not None:
                self._hysteresis = float(last_state.attributes[ATTR_HYSTERESIS])

            # Restore AC state (best-effort, will be corrected on next update)
            if last_state.attributes.get("ac_is_running") is not None:
                self._ac_is_running = last_state.attributes["ac_is_running"] in [
                    True,
                    "True",
                    "true",
                ]


# ─── Service Registration ──────────────────────────────────────────


def _register_services(platform: entity_platform.EntityPlatform) -> None:
    """Register entity services for Virtual Thermostat."""
    platform.async_register_entity_service(
        "set_ac_offset",
        {
            "delta_ac": {
                "selector": {
                    "number": {
                        "min": -20,
                        "max": 20,
                        "step": 0.5,
                        "unit_of_measurement": "°C",
                    }
                }
            }
        },
        "async_set_ac_offset",
    )

    platform.async_register_entity_service(
        "set_hysteresis",
        {
            "hysteresis": {
                "selector": {
                    "number": {
                        "min": 0.1,
                        "max": 5.0,
                        "step": 0.1,
                        "unit_of_measurement": "°C",
                    }
                }
            }
        },
        "async_set_hysteresis",
    )
