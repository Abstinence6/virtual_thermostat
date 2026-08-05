"""Tests for the Virtual Thermostat config and options flows."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_NAME, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.virtual_thermostat import _async_options_updated
from custom_components.virtual_thermostat.const import (
    CONF_CLIMATE,
    CONF_DELTA_AC,
    CONF_HYSTERESIS,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_SENSOR,
    CONF_TARGET_TEMP,
    DOMAIN,
)


ENTRY_DATA = {
    CONF_NAME: "Living room",
    CONF_CLIMATE: "climate.real_ac",
    CONF_SENSOR: "sensor.room_temperature",
    CONF_DELTA_AC: 2.0,
    CONF_HYSTERESIS: 1.0,
    CONF_TARGET_TEMP: 22.0,
    CONF_MIN_TEMP: 16,
    CONF_MAX_TEMP: 35,
}


@pytest.mark.asyncio
async def test_options_flow_updates_all_runtime_settings(hass: HomeAssistant) -> None:
    """Options flow stores every editable setup value in entry options."""
    hass.states.async_set("sensor.room_temperature", "21.0")
    hass.states.async_set("climate.real_ac", STATE_ON)
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, unique_id="vt_test")
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    updated = {**ENTRY_DATA, CONF_NAME: "Bedroom", CONF_DELTA_AC: -3.0}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], updated
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == updated


@pytest.mark.asyncio
async def test_options_flow_rejects_missing_entities(hass: HomeAssistant) -> None:
    """Options flow validates replacement entities before saving."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, unique_id="vt_test")
    entry.add_to_hass(hass)
    hass.states.async_set("climate.real_ac", STATE_ON)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    invalid = {**ENTRY_DATA, CONF_SENSOR: "sensor.missing"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], invalid
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "sensor_not_found"}
    assert entry.options == {}


@pytest.mark.asyncio
async def test_options_update_reloads_entry(hass: HomeAssistant) -> None:
    """Saving options triggers a config-entry reload."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, unique_id="vt_test")
    reload_entry = AsyncMock()
    with patch.object(hass.config_entries, "async_reload", reload_entry):
        await _async_options_updated(hass, entry)
    reload_entry.assert_awaited_once_with(entry.entry_id)
