# HA WeatherSense

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A Home Assistant integration that calculates "Feels Like" temperature based on multiple environmental factors.

## Features

- Calculates perceived temperature using scientifically validated models
- Supports both indoor and outdoor environments
- Takes into account:
  - Temperature
  - Humidity
  - Wind speed (for outdoor)
  - Atmospheric pressure
  - Time of day
- Provides comfort level assessment
- Easy setup through the UI

## Installation

### HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → ⋮ (menu) → Custom repositories
   - Add `https://github.com/smkrv/ha-weathersense` as a repository
   - Select "Integration" as the category
3. Click "Install" on the HA WeatherSense integration
4. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [GitHub repository](https://github.com/smkrv/ha-weathersense)
2. Extract the `weathersense` folder from the `custom_components` directory
3. Copy the folder to your Home Assistant's `custom_components` directory
4. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "Add Integration" and search for "HA WeatherSense"
3. Follow the configuration steps:
   - Select a temperature sensor
   - Select a humidity sensor
   - Optionally select wind speed, pressure, and solar radiation sensors
   - Specify if the sensor is for outdoor or indoor use

## How It Works

HA WeatherSense uses different calculation methods depending on the environment and temperature range:

### Outdoor Calculations

- **Heat Index**: Used when temperature is ≥ 27°C
- **Wind Chill**: Used when temperature is ≤ 10°C
- **Steadman Apparent Temperature**: Used for temperatures between 10°C and 27°C

Additional corrections are applied for:
- Time of day (solar radiation effect)
- Atmospheric pressure variations

### Indoor Calculations

For indoor environments, a simplified thermal comfort model is used that primarily considers temperature and humidity.

## Comfort Levels

The integration provides a comfort assessment with the following levels:

- Extreme Cold Stress
- Very Strong Cold Stress
- Strong Cold Stress
- Moderate Cold Stress
- Slight Cold Stress
- No Thermal Stress (Comfort)
- Slight Heat Stress
- Moderate Heat Stress
- Strong Heat Stress
- Very Strong Heat Stress
- Extreme Heat Stress

## Example Automations

### Adjust HVAC based on feels-like temperature

```yaml
automation:
  - alias: "Adjust HVAC based on feels-like temperature"
    trigger:
      - platform: state
        entity_id: sensor.feels_like_temperature
    condition:
      - condition: numeric_state
        entity_id: sensor.feels_like_temperature
        above: 26
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: 23
