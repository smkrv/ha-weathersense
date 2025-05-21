"""Constants for the HA WeatherSense integration."""

DOMAIN = "weathersense"
NAME = "HA WeatherSense"

# Configuration options
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_WIND_SPEED_SENSOR = "wind_speed_sensor"
CONF_PRESSURE_SENSOR = "pressure_sensor"
CONF_IS_OUTDOOR = "is_outdoor"
CONF_SOLAR_RADIATION_SENSOR = "solar_radiation_sensor"
CONF_TIME_OF_DAY = "time_of_day"

# Default values
DEFAULT_NAME = "Feels Like Temperature"
DEFAULT_IS_OUTDOOR = True

# Comfort levels
COMFORT_EXTREME_COLD = "extreme_cold"
COMFORT_VERY_COLD = "very_cold"
COMFORT_COLD = "cold"
COMFORT_COOL = "cool"
COMFORT_SLIGHTLY_COOL = "slightly_cool"
COMFORT_COMFORTABLE = "comfortable"
COMFORT_SLIGHTLY_WARM = "slightly_warm"
COMFORT_WARM = "warm"
COMFORT_HOT = "hot"
COMFORT_VERY_HOT = "very_hot"
COMFORT_EXTREME_HOT = "extreme_hot"

# Comfort level descriptions
COMFORT_DESCRIPTIONS = {
    COMFORT_EXTREME_COLD: "Extreme Cold Stress",
    COMFORT_VERY_COLD: "Very Strong Cold Stress",
    COMFORT_COLD: "Strong Cold Stress",
    COMFORT_COOL: "Moderate Cold Stress",
    COMFORT_SLIGHTLY_COOL: "Slight Cold Stress",
    COMFORT_COMFORTABLE: "No Thermal Stress (Comfort)",
    COMFORT_SLIGHTLY_WARM: "Slight Heat Stress",
    COMFORT_WARM: "Moderate Heat Stress",
    COMFORT_HOT: "Strong Heat Stress",
    COMFORT_VERY_HOT: "Very Strong Heat Stress",
    COMFORT_EXTREME_HOT: "Extreme Heat Stress"
}

# Sensor attributes
ATTR_COMFORT_LEVEL = "comfort_level"
ATTR_COMFORT_DESCRIPTION = "comfort_description"
ATTR_CALCULATION_METHOD = "calculation_method"
ATTR_TEMPERATURE = "temperature"
ATTR_HUMIDITY = "humidity"
ATTR_WIND_SPEED = "wind_speed"
ATTR_PRESSURE = "pressure"
ATTR_IS_OUTDOOR = "is_outdoor"
ATTR_TIME_OF_DAY = "time_of_day"
