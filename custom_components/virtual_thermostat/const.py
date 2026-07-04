"""Constants for the Virtual Thermostat component."""

DOMAIN = "virtual_thermostat"
PLATFORMS = ["climate"]

CONF_CLIMATE = "climate_entity"
CONF_SENSOR = "sensor_entity"
CONF_DELTA_AC = "delta_ac"
CONF_HYSTERESIS = "hysteresis"
CONF_TARGET_TEMP = "target_temperature"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"

DEFAULT_DELTA_AC = 0
DEFAULT_HYSTERESIS = 1.0
DEFAULT_TARGET_TEMP = 22.0
DEFAULT_MIN_TEMP = 16
DEFAULT_MAX_TEMP = 35

ATTR_AC_TEMPERATURE = "ac_target_temperature"
ATTR_DELTA_MEASURED = "delta_measured"
ATTR_HYSTERESIS = "hysteresis"
ATTR_SENSOR_ENTITY = "sensor_entity"
ATTR_CLIMATE_ENTITY = "climate_entity"
