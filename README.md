<div align="center">  

# HA WeatherSense – Scientifically[*](#references) Accurate Feels-Like Temp, Comfort Levels & Dynamic Icons

</div>
<div align="center">

![GitHub release](https://img.shields.io/github/v/release/smkrv/ha-weathersense?style=flat-square) ![GitHub last commit](https://img.shields.io/github/last-commit/smkrv/ha-weathersense?style=flat-square) [![License: PolyForm Noncommercial](https://img.shields.io/badge/License-PolyForm%20NC%201.0-lightgrey.svg?style=flat-square)](https://polyformproject.org/licenses/noncommercial/1.0.0) [![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration) ![English](https://img.shields.io/badge/lang-EN-blue?style=flat-square) ![Russian](https://img.shields.io/badge/lang-RU-red?style=flat-square) ![German](https://img.shields.io/badge/lang-DE-black?style=flat-square) ![Spanish](https://img.shields.io/badge/lang-ES-yellow?style=flat-square) ![Hindi](https://img.shields.io/badge/lang-HI-orange?style=flat-square) ![Chinese](https://img.shields.io/badge/lang-ZH--CN-green?style=flat-square) ![Czech](https://img.shields.io/badge/lang-CS-11457E?style=flat-square)

</div>

<div align="center">  

  <img src="https://raw.githubusercontent.com/smkrv/ha-weathersense/main/assets/images/ha-weathersense-screenshot.png" alt="HA WeatherSense – Scientifically Accurate Feels-Like Temp" style="width: 50%; max-width: 512px; max-height: 408px; object-fit: contain;"/>
</div>
<div align="center">  
  
  <img src="https://raw.githubusercontent.com/smkrv/ha-weathersense/main/custom_components/weathersense/icons/icon%402x.png" alt="Logo: HA WeatherSense" style="width: 10%; max-width: 32px; max-height: 32px; aspect-ratio: 1/1; object-fit: contain;"/>

  Plug-and-play “feels-like” readings and an instant **comfy/not-comfy** flag for Home Assistant.
<br />
  No jargon, just data that **works**!

</div>

## Features

- Calculates perceived temperature using scientifically validated models
- Supports both **indoor** and **outdoor** environments
- Takes into account:
  - Temperature
  - Humidity
  - Wind speed (for outdoor)
  - Atmospheric pressure
  - Solar radiation (optional)
  - Time of day
- Provides comfort level assessment with detailed explanations
- Includes comfort status indicator (is_comfortable attribute)
- Dynamic icons that change based on comfort level
- Supports different temperature units (°C/°F)
- Automatic unit conversion for any input sensors
- Easy setup through the UI

## 🎨 Companion Card

Check out the [**WeatherSense Card**](https://github.com/smkrv/ha-weathersense-card) — a beautiful custom Lovelace card with hybrid glass+material design and dynamic comfort level visualization.

<p align="center">
  <a href="https://github.com/smkrv/ha-weathersense-card"><img src="https://raw.githubusercontent.com/smkrv/ha-weathersense-card/main/screenshots/screenshot.webp" alt="WeatherSense Card" style="max-width: 500px;" width="500" /></a>
</p>

**Features:**
- Hybrid glass+material design with comfort-level color glow
- Three size modes: normal, compact, ultra-compact
- Extended metrics: temperature, humidity, wind speed, pressure
- Per-metric unit configuration (°C/°F, m/s/km/h/mph/knots, hPa/mmHg/inHg/kPa)
- 11 dynamic color themes based on comfort levels
- Light/dark theme support with smooth animations
- Multi-language support (EN, RU, DE, ES, HI, ZH-CN, CS)
- [Install via HACS →](https://github.com/smkrv/ha-weathersense-card)

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

1. Download the latest release from the [GitHub repository](https://github.com/smkrv/ha-weathersense/releases)
2. Extract the `weathersense` folder from the `custom_components` directory
3. Copy the folder to your Home Assistant's `custom_components` directory
4. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "Add Integration" and search for "HA WeatherSense"
3. Follow the configuration steps:
   - Enter a name for your sensor
   - Select a temperature sensor
   - Select a humidity sensor
   - Optionally select wind speed sensor
   - Optionally select pressure sensor
   - Optionally select solar radiation sensor
   - Optionally select wind direction sensor
   - Enable/disable wind direction correction (experimental)
   - Enable/disable output smoothing (EMA filter) with configurable responsiveness
   - Specify if the sensor is for outdoor or indoor use
   - Optionally select your preferred temperature display unit

You can add multiple instances of the integration for different locations (e.g., living room, bedroom, outside).

## Sensor Attributes

The integration provides the following attributes:

| Attribute | Description |
|-----------|-------------|
| `comfort_level` | Current comfort level code |
| `comfort_description` | Short description of the comfort level |
| `comfort_explanation` | Detailed explanation of the comfort level |
| `calculation_method` | Method used for calculation (Heat Index, Wind Chill, etc.) |
| `temperature` | Source temperature value (in °C) |
| `humidity` | Source humidity value (%) |
| `wind_speed` | Source wind speed value (in m/s) if available |
| `pressure` | Source pressure value (in kPa) if available |
| `wind_direction` | Source wind direction value (in °) if available |
| `wind_direction_correction_applied` | Wind direction correction value (°C) if enabled |
| `is_outdoor` | Whether this is an outdoor or indoor sensor |
| `time_of_day` | Current time when calculation was performed |
| `is_comfortable` | Boolean indicating if current conditions are comfortable |

> **Note:** `comfort_description`, `comfort_explanation` and `calculation_method` are automatically localized based on your Home Assistant language setting.

## Dynamic Icons

The sensor's icon changes automatically based on the current comfort level:

| Comfort Level | Icon |
|---------------|------|
| `extreme_cold` | mdi:snowflake-alert |
| `very_cold` | mdi:snowflake-thermometer |
| `cold` | mdi:thermometer-low |
| `cool` | mdi:thermometer-minus |
| `slightly_cool` | mdi:thermometer-minus |
| `comfortable` | mdi:hand-okay |
| `slightly_warm` | mdi:thermometer-plus |
| `warm` | mdi:thermometer-high |
| `hot` | mdi:thermometer-alert |
| `very_hot` | mdi:heat-wave |
| `extreme_hot` | mdi:fire-alert |

## How It Works

HA WeatherSense uses different calculation methods depending on the environment and temperature range:

### Outdoor Calculations

- **Heat Index**: Used when temperature is ≥ 27°C and humidity ≥ 40%
- **Wind Chill**: Used when temperature is ≤ 10°C and wind speed > 1.34 m/s
- **Steadman Apparent Temperature**: Used for all other conditions

Additional corrections are applied for:
- Time of day (solar radiation effect)
- Atmospheric pressure variations
- Solar radiation (if sensor provided)

### Indoor Calculations

For indoor environments, a simplified thermal comfort model is used that primarily considers temperature and humidity interactions.

## Comfort Levels

The integration provides a comfort assessment with the following levels:

| Level | Description | Explanation |
|-------|-------------|-------------|
| `extreme_cold` | Extreme Cold Stress | Extreme risk: frostbite possible in less than 5 minutes |
| `very_cold` | Very Strong Cold Stress | High risk: frostbite possible in 5-10 minutes |
| `cold` | Strong Cold Stress | Warning: frostbite possible in 10-30 minutes |
| `cool` | Moderate Cold Stress | Caution: prolonged exposure may cause discomfort |
| `slightly_cool` | Slight Cold Stress | Slightly cool: light discomfort for sensitive individuals |
| `comfortable` | No Thermal Stress | Optimal thermal conditions: most people feel comfortable |
| `slightly_warm` | Slight Heat Stress | Slightly warm: light discomfort for sensitive individuals |
| `warm` | Moderate Heat Stress | Caution: fatigue possible with prolonged exposure |
| `hot` | Strong Heat Stress | Extreme caution: heat exhaustion possible |
| `very_hot` | Very Strong Heat Stress | Danger: heat cramps and exhaustion likely |
| `extreme_hot` | Extreme Heat Stress | Extreme danger: heat stroke imminent |

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

### Send notification when conditions become uncomfortable

```yaml
automation:
  - alias: "Notify when outdoor conditions become uncomfortable"
    trigger:
      - platform: state
        entity_id: sensor.outdoor_feels_like
        attribute: is_comfortable
        from: "true"
        to: "false"
    action:
      - service: notify.mobile_app
        data:
          title: "Weather Alert"
          message: >
            Outdoor conditions are now {{ state_attr('sensor.outdoor_feels_like', 'comfort_description') | lower }}.
            Feels like {{ states('sensor.outdoor_feels_like') }}°.
            {{ state_attr('sensor.outdoor_feels_like', 'comfort_explanation') }}
```

### Display comfort level in dashboard

```yaml
type: entities
entities:
  - entity: sensor.feels_like_temperature
    secondary_info: last-changed
    name: Feels Like Temperature
    icon: mdi:thermometer
    tap_action:
      action: more-info
    footer:
      type: text
      content: "{{ state_attr('sensor.feels_like_temperature', 'comfort_description') }}"
```

## Scientific Background

The calculations used in HA WeatherSense are based on peer-reviewed scientific models and official standards used by meteorological organizations worldwide. All formula coefficients have been verified against original sources.

### Heat Index
The Heat Index formula is the official Rothfusz regression equation from NWS Technical Attachment [SR 90-23](https://www.weather.gov/media/ffc/ta_htindx.PDF), which approximates Steadman's (1979) original heat index table. Low-humidity and high-humidity adjustments follow the [NWS Weather Prediction Center algorithm](https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml). The formula operates in Fahrenheit internally and has been validated through extensive physiological studies measuring human heat stress responses.

### Wind Chill Temperature
The Wind Chill model implements the formula jointly adopted by Environment Canada and the US National Weather Service for the 2001/2002 winter season, developed by Osczevski and Bluestein through the [Joint Action Group for Temperature Indices (JAG/TI)](https://www.weather.gov/ffc/wci). The formula was calibrated using wind tunnel tests with 12 human subjects at DCIEM (Defence and Civil Institute of Environmental Medicine) in Toronto, measuring facial heat loss under controlled conditions.

### Steadman Apparent Temperature
For moderate temperatures, we use Steadman's (1994) Apparent Temperature model: `AT = T + 0.33e − 0.70v − 4.00`, where vapor pressure `e` is calculated via the Tetens equation. This formula has been adopted by the [Australian Bureau of Meteorology](https://www.bom.gov.au/info/thermal_stress/) and other international weather services. It accounts for both humidity and wind effects in a unified equation.

### Solar Radiation Correction
The diurnal solar intensity is modeled using a half-sine function, a well-established approach in solar energy literature following Collares-Pereira & Rabl (1979). A simplified fixed 6:00–18:00 window is used instead of actual sunrise/sunset times.

### Pressure Correction
A simplified linear heuristic `0.1 × (101.3 − pressure)` is applied for atmospheric pressure deviations from the [standard atmosphere](https://en.wikipedia.org/wiki/Standard_atmosphere_(unit)) (101.325 kPa, 10th CGPM 1954). **Note:** this is a custom approximation, not a peer-reviewed formula.

### Indoor Comfort Model
The indoor comfort assessment is based on principles from ISO 7730 (Ergonomics of the thermal environment) and ASHRAE Standard 55 (Thermal Environmental Conditions for Human Occupancy), which define internationally recognized thermal comfort standards.

### References
1. Rothfusz, L.P. (1990). "The Heat Index 'Equation'." NWS Technical Attachment SR/SSD 90-23. [[PDF]](https://www.weather.gov/media/ffc/ta_htindx.PDF)
2. Steadman, R.G. (1994). "Norms of apparent temperature in Australia." *Australian Meteorological Magazine*, 43, 1–16. [[PDF]](http://www.bom.gov.au/jshess/docs/1994/steadman.pdf)
3. Osczevski, R. & Bluestein, M. (2005). "The new wind chill equivalent temperature chart." *Bulletin of the American Meteorological Society*, 86(10), 1453–1458. [DOI: 10.1175/BAMS-86-10-1453](https://doi.org/10.1175/BAMS-86-10-1453)
4. Collares-Pereira, M. & Rabl, A. (1979). "The average distribution of solar radiation — correlations between diffuse and hemispherical and between daily and hourly insolation values." *Solar Energy*, 22, 155–164. [DOI: 10.1016/0038-092X(79)90100-2](https://doi.org/10.1016/0038-092X(79)90100-2)
5. ISO 7730. "Ergonomics of the thermal environment — Analytical determination and interpretation of thermal comfort using calculation of the PMV and PPD indices and local thermal comfort criteria."
6. ASHRAE Standard 55. "Thermal Environmental Conditions for Human Occupancy."
7. NWS Weather Prediction Center. [Heat Index Calculation](https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml), [Wind Chill Chart](https://www.weather.gov/safety/cold-wind-chill-chart).
8. Australian Bureau of Meteorology. [Thermal Comfort observations](https://www.bom.gov.au/info/thermal_stress/).

These models are used daily by meteorological services worldwide to provide accurate "feels like" temperatures to the public, making HA WeatherSense's calculations reliable for both comfort assessment and safety warnings.

## Roadmap

Future improvements planned for this integration:

- More advanced indoor comfort models (PMV/PPD)
- Integration with weather forecasts for predictive comfort
- Custom comfort thresholds configuration
- Dashboard card with visual comfort indicators
- Support for UV index in comfort calculations
- Improved solar radiation modeling

## Troubleshooting

### Common Issues

1. **Unrealistic temperature values**: If you see extremely high or low feels-like temperatures, check that your input sensors are providing reasonable values and have the correct units.

2. **Incorrect comfort level**: The comfort level is determined based on the calculated feels-like temperature. If it seems incorrect, verify that the outdoor/indoor setting matches your sensor's actual location.

3. **Sensor shows "unavailable"**: Ensure all required source sensors are available and providing valid readings.

### Debug Logging

To enable debug logs for troubleshooting:

1. Add the following to your `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.weathersense: debug
   ```
2. Restart Home Assistant
3. Check the logs for detailed information about calculations and conversions

## Legal Disclaimer and Limitation of Liability  

### Software Disclaimer  

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  

IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.  

## 📝 License

Author: SMKRV
[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0) — see [LICENSE](LICENSE) for details.

---

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

<div align="center">

Made with ❤️ for the Home Assistant Community

[Report Bug](https://github.com/smkrv/ha-weathersense/issues) · [Request Feature](https://github.com/smkrv/ha-weathersense/issues)

</div>
