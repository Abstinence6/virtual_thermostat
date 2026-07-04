# Virtual Thermostat

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

A smart **virtual climate controller** for Home Assistant that bridges a temperature sensor with a real AC unit.

## Features

- **Smart thermostat logic** — virtual climate entity with its own target temperature
- **Delta AC** — configurable temperature offset between the user-set target and what's actually sent to the real AC
- **Hysteresis** — prevents short cycling of the AC unit
- **Auto shutoff** — turns off the real AC when the measured temperature reaches the user's target
- **Config flow** — easy setup via Home Assistant UI
- **State persistence** — remembers target temperature, hysteresis, and AC state across restarts
- **Custom services** — change delta_ac and hysteresis on the fly via services

## How It Works

```
User sets target 25°C on Virtual Thermostat
         │
         ├── delta_ac = +5  → AC receives target 30°C (cooling mode)
         ├── delta_ac = -5  → AC receives target 20°C (heating mode)
         │
         ├── Temperature sensor is polled continuously
         │
         └── When measured temp reaches 25°C → AC turns OFF
             └── Hysteresis (e.g., 1°C) prevents rapid on/off cycling
```

### Example: Cooling with Boost

| Parameter | Value |
|-----------|-------|
| User target | 25°C |
| delta_ac | +5°C |
| AC setpoint | 30°C |
| Hysteresis | 1°C |

1. Virtual thermostat sends 30°C to the real AC and turns it on
2. Room cools down; when temperature reaches **25°C**, the AC is turned off
3. Room warms up to **26°C** (25 + 1), AC turns back on with 30°C setpoint
4. Cycle repeats

### Example: Heating with Undershoot

| Parameter | Value |
|-----------|-------|
| User target | 25°C |
| delta_ac | -5°C |
| AC setpoint | 20°C |
| Hysteresis | 1°C |

1. Virtual thermostat sends 20°C to the real AC and turns it on
2. Room warms up; when temperature reaches **25°C**, the AC is turned off
3. Room cools to **24°C** (25 - 1), AC turns back on with 20°C setpoint
4. Cycle repeats

## Installation

### Via HACS (recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant
2. Go to HACS → Integrations → Three-dot menu → Custom repositories
3. Add: `https://github.com/abstinence6/virtual_thermostat` with category "Integration"
4. Click Install
5. Restart Home Assistant
6. Go to Settings → Devices & Services → Add Integration → **Virtual Thermostat**

### Manual Installation

1. Copy the `custom_components/virtual_thermostat/` directory to your HA `custom_components/` directory
2. Restart Home Assistant
3. Add the integration via the UI

## Configuration

### Via UI (Config Flow)

When adding the integration via Settings → Devices & Services → Add Integration:

| Field | Description |
|-------|-------------|
| **Name** | Friendly name for the virtual thermostat |
| **Real AC entity** | The real climate entity (e.g., `climate.living_room_ac`) |
| **Temperature sensor** | The temperature sensor entity (e.g., `sensor.living_room_temp`) |
| **Delta AC** | Offset between user target and AC setpoint in °C |
| **Hysteresis** | Deadband to prevent short cycling in °C |
| **Initial target temperature** | Starting target temperature |
| **Min / Max temperature** | Allowed temperature range |

### Via YAML

```yaml
# Example configuration.yaml entry
climate:
  - platform: virtual_thermostat
    name: "Living Room Virtual Thermostat"
    climate_entity: climate.living_room_ac
    sensor_entity: sensor.living_room_temp
    delta_ac: 5
    hysteresis: 1.0
    target_temperature: 24
    min_temp: 16
    max_temp: 35
```

## Services

### `virtual_thermostat.set_ac_offset`

Change the delta_ac value at runtime.

| Field | Description | Range |
|-------|-------------|-------|
| `delta_ac` | Temperature offset in °C | -20 to 20, step 0.5 |

### `virtual_thermostat.set_hysteresis`

Change the hysteresis value at runtime.

| Field | Description | Range |
|-------|-------------|-------|
| `hysteresis` | Hysteresis in °C | 0.1 to 5.0, step 0.1 |

## State Attributes

| Attribute | Description |
|-----------|-------------|
| `ac_target_temperature` | The temperature being sent to the real AC |
| `delta_measured` | Difference between measured and target temperature (measured - target) |
| `hysteresis` | Current hysteresis setting |
| `sensor_entity` | The sensor entity being monitored |
| `climate_entity` | The real AC being controlled |
| `ac_is_running` | Whether the real AC is currently running |

## Requirements

- Home Assistant 2024.1.0 or newer

## License

Apache License 2.0
