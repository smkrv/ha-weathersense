# HA WeatherSense

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A Home Assistant integration that calculates "Feels Like" temperature based on multiple environmental factors.

> [!IMPORTANT]
> Please note: As these are the initial release versions, bugs and errors may occur.

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

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=smkrv&repository=ha-weathersense&category=Integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" width="170" height="auto"></a>

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
```

---

## Scientific Background

The calculations used in HA WeatherSense are based on peer-reviewed scientific models and official standards used by meteorological organizations worldwide:

### Heat Index
The Heat Index formula is the official algorithm used by the US National Weather Service (NWS), developed by Rothfusz (1990) and refined by the NWS. It has been validated through extensive physiological studies measuring human heat stress responses.

### Wind Chill Temperature
The Wind Chill model implemented is the standard adopted jointly by Environment Canada and the US National Weather Service in 2001, based on research by Osczevski and Bluestein (2005). It was developed using human trials that measured facial heat loss in wind tunnel tests.

### Steadman Apparent Temperature
For moderate temperatures, we use Steadman's (1994) Apparent Temperature model, which has been adopted by the Australian Bureau of Meteorology and other international weather services. It accounts for both humidity and wind effects in a unified equation.

### Indoor Comfort Model
The indoor comfort assessment is based on principles from ISO 7730:2005 (Ergonomics of the thermal environment) and ASHRAE Standard 55-2020, which define internationally recognized thermal comfort standards.

### References
1. Steadman, R.G. (1994). "Norms of apparent temperature in Australia." Australian Meteorological Magazine, 43, 1-16.
2. Rothfusz, L.P. (1990). "The heat index equation." National Weather Service Technical Attachment (SR 90-23).
3. Osczevski, R., & Bluestein, M. (2005). "The new wind chill equivalent temperature chart." Bulletin of the American Meteorological Society, 86(10), 1453-1458.
4. ISO 7730:2005. "Ergonomics of the thermal environment."
5. ASHRAE Standard 55-2020. "Thermal Environmental Conditions for Human Occupancy."

These models are used daily by meteorological services worldwide to provide accurate "feels like" temperatures to the public, making HA WeatherSense's calculations reliable for both comfort assessment and safety warnings.

## Legal Disclaimer and Limitation of Liability  

### Software Disclaimer  

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  

IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.  

## 📝 License

Author: SMKRV
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) - see [LICENSE](LICENSE) for details.

## 💡 Support the Project

The best support is:
- Sharing feedback
- Contributing ideas
- Recommending to friends
- Reporting issues
- Star the repository

If you want to say thanks financially, you can send a small token of appreciation in USDT:

**USDT Wallet (TRC10/TRC20):**
`TXC9zYHYPfWUGi4Sv4R1ctTBGScXXQk5HZ`

*Open-source is built by community passion!* 🚀

---
