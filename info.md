# Virtual Thermostat

A smart climate controller for Home Assistant that bridges a temperature sensor with a real AC unit.

## Features

- **Virtual thermostat** entity with its own target temperature
- **Delta AC** — configurable offset between user-set target and what's sent to the real AC
- **Hysteresis** — prevents short cycling of the AC
- **Auto shutoff** — turns off the real AC when the measured temperature reaches the target
- **Config flow** — easy setup via Home Assistant UI
- **Restore state** — remembers settings across HA restarts

## How it works

```
User sets target 25°C
        │
        ├── delta_ac = +5  → AC receives target 30°C (cooling)
        ├── delta_ac = -5  → AC receives target 20°C (heating)
        │
        ├── Sensor monitors actual temperature
        │
        └── When measured = 25°C → AC turns OFF
            └── Hysteresis prevents rapid on/off cycling
```

## Installation (HACS)

1. Add this repository as a custom repository in HACS
2. Search for "Virtual Thermostat"
3. Install
4. Restart Home Assistant
5. Add the integration via Settings → Devices & Services → Add Integration → Virtual Thermostat

## Manual Installation

Copy the `custom_components/virtual_thermostat/` directory to your HA `custom_components/` directory.
