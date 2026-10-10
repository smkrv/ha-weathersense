"""
Sensor platform for HA WeatherSense integration.

@license: PolyForm Noncommercial 1.0.0
@author: SMKRV
@github: https://github.com/smkrv/ha-weathersense
@source: https://github.com/smkrv/ha-weathersense
"""
from __future__ import annotations

import logging
import math
from typing import Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    UnitOfTemperature,
    UnitOfPressure,
    UnitOfSpeed,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    NAME,
    METHOD_KEYS,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_WIND_SPEED_SENSOR,
    CONF_PRESSURE_SENSOR,
    CONF_IS_OUTDOOR,
    CONF_SOLAR_RADIATION_SENSOR,
    CONF_WIND_DIRECTION_SENSOR,
    CONF_WIND_DIRECTION_CORRECTION,
    CONF_SMOOTHING_ENABLED,
    CONF_SMOOTHING_FACTOR,
    DEFAULT_NAME,
    DEFAULT_IS_OUTDOOR,
    DEFAULT_SMOOTHING_FACTOR,
    ATTR_COMFORT_LEVEL,
    ATTR_COMFORT_LEVEL_LOCALIZED,
    ATTR_CALCULATION_METHOD_KEY,
    ATTR_COMFORT_DESCRIPTION,
    ATTR_COMFORT_EXPLANATION,
    ATTR_CALCULATION_METHOD,
    ATTR_TEMPERATURE,
    ATTR_HUMIDITY,
    ATTR_WIND_SPEED,
    ATTR_PRESSURE,
    ATTR_IS_OUTDOOR,
    ATTR_TIME_OF_DAY,
    ATTR_IS_COMFORTABLE,
    ATTR_WIND_DIRECTION,
    ATTR_WIND_DIRECTION_CORRECTION,
    COMFORT_ICONS,
    COMFORT_COMFORTABLE,
    COMFORT_SLIGHTLY_WARM,
    COMFORT_SLIGHTLY_COOL,
    CONF_DISPLAY_UNIT,
)
from .comfort_translations import get_comfort_level, get_comfort_description, get_comfort_explanation, get_calculation_method
from .weather_calculator import calculate_feels_like

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the WeatherSense sensor from config entry."""
    config = {**entry.data, **entry.options}

    name = config.get("name", DEFAULT_NAME)

    sensor = WeatherSenseSensor(
        hass,
        entry.entry_id,
        name,
        config.get(CONF_TEMPERATURE_SENSOR),
        config.get(CONF_HUMIDITY_SENSOR),
        config.get(CONF_WIND_SPEED_SENSOR),
        config.get(CONF_PRESSURE_SENSOR),
        config.get(CONF_SOLAR_RADIATION_SENSOR),
        config.get(CONF_IS_OUTDOOR, DEFAULT_IS_OUTDOOR),
        config.get(CONF_DISPLAY_UNIT),
        config.get(CONF_WIND_DIRECTION_SENSOR),
        config.get(CONF_WIND_DIRECTION_CORRECTION, False),
        config.get(CONF_SMOOTHING_ENABLED, False),
        config.get(CONF_SMOOTHING_FACTOR, DEFAULT_SMOOTHING_FACTOR),
    )

    async_add_entities([sensor])


class WeatherSenseSensor(SensorEntity):
    """Representation of a WeatherSense Sensor."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        temperature_entity_id: str,
        humidity_entity_id: str,
        wind_speed_entity_id: Optional[str] = None,
        pressure_entity_id: Optional[str] = None,
        solar_radiation_entity_id: Optional[str] = None,
        is_outdoor: bool = True,
        display_unit: Optional[str] = None,
        wind_direction_entity_id: Optional[str] = None,
        wind_direction_correction: bool = False,
        smoothing_enabled: bool = False,
        smoothing_factor: float = 0.3,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry_id = entry_id
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{name}"

        self._temperature_entity_id = temperature_entity_id
        self._humidity_entity_id = humidity_entity_id
        self._wind_speed_entity_id = wind_speed_entity_id
        self._pressure_entity_id = pressure_entity_id
        self._solar_radiation_entity_id = solar_radiation_entity_id
        self._wind_direction_entity_id = wind_direction_entity_id
        self._wind_direction_correction_enabled = wind_direction_correction
        self._is_outdoor = is_outdoor

        # The native value is always Celsius; HA converts the displayed state
        # to the system unit. An explicit display unit choice is expressed
        # through the entity-registry unit override (see async_added_to_hass),
        # never by converting the native value.
        if display_unit in [UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT]:
            self._display_unit = display_unit
            self._attr_suggested_unit_of_measurement = display_unit
        else:
            self._display_unit = None

        self._attr_available = True
        self._temperature = None
        self._humidity = None
        self._wind_speed = None
        self._pressure = None
        self._solar_radiation = None
        self._wind_direction = None
        self._wind_direction_correction = 0.0
        self._calculation_method = None
        self._comfort_level = None

        # EMA smoothing
        self._smoothing_enabled = smoothing_enabled
        self._smoothing_factor = max(0.05, min(0.95, smoothing_factor))
        self._previous_smoothed_value = None

        self._attr_icon = "mdi:thermometer"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=NAME,
            manufacturer="HA WeatherSense",
        )

    async def async_added_to_hass(self) -> None:
        """Set up listeners when the entity is added to Home Assistant."""
        # Set up listeners for all relevant entities (deduplicated: the same
        # entity may be configured for more than one role)
        entities_to_track = list(dict.fromkeys([
            self._temperature_entity_id,
            self._humidity_entity_id,
        ]))

        if self._wind_speed_entity_id:
            entities_to_track.append(self._wind_speed_entity_id)
        if self._pressure_entity_id:
            entities_to_track.append(self._pressure_entity_id)
        if self._solar_radiation_entity_id:
            entities_to_track.append(self._solar_radiation_entity_id)
        if self._wind_direction_entity_id:
            entities_to_track.append(self._wind_direction_entity_id)

        # suggested_unit_of_measurement only applies on first registration,
        # so a display unit changed later via the options flow needs the
        # entity-registry override updated explicitly (same mechanism as the
        # UI unit setting).
        if self._display_unit:
            registry = er.async_get(self.hass)
            reg_entry = registry.async_get(self.entity_id)
            if reg_entry and reg_entry.options.get("sensor", {}).get(
                "unit_of_measurement"
            ) != self._display_unit:
                # Merge: async_update_entity_options replaces the whole
                # per-domain dict, and options["sensor"] also carries
                # user-set keys like display_precision.
                registry.async_update_entity_options(
                    reg_entry.entity_id,
                    "sensor",
                    {
                        **reg_entry.options.get("sensor", {}),
                        "unit_of_measurement": self._display_unit,
                    },
                )

        # Initial data fetch
        await self._update_state()

        # Set up state change listeners
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, entities_to_track, self._handle_state_changes
            )
        )

    async def _handle_state_changes(self, event):
        """Handle state changes in the tracked entities."""
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")

        # Recompute even for unavailable/unknown states: a vanished required
        # input must flip this entity to unavailable, and a vanished optional
        # input must drop its stale attribute instead of serving old data.
        if new_state is None or new_state.state in ("unavailable", "unknown"):
            _LOGGER.debug("Entity %s has invalid state: %s", entity_id, new_state)

        await self._update_state()

    def _set_unavailable(self) -> None:
        """Mark the entity unavailable so consumers do not read stale data."""
        if self._attr_available:
            self._attr_available = False
            self.async_write_ha_state()

    def _log_label(self) -> str:
        """Label that identifies this sensor in log lines (issue #11)."""
        return self.entity_id or self._attr_name

    async def _update_state(self) -> None:
        """Update the state of the sensor."""
        label = self._log_label()

        # Get current values from entities
        temp_state = self.hass.states.get(self._temperature_entity_id)
        humidity_state = self.hass.states.get(self._humidity_entity_id)

        # Name exactly which required input has no state at all, so a log line
        # is enough to find the culprit without cross-referencing history.
        missing = [
            f"{kind} source {eid} has no state"
            for kind, state, eid in (
                ("temperature", temp_state, self._temperature_entity_id),
                ("humidity", humidity_state, self._humidity_entity_id),
            )
            if not state
        ]
        if missing:
            _LOGGER.warning("%s: %s", label, "; ".join(missing))
            self._set_unavailable()
            return

        # An unavailable/unknown flicker must also say which input blinked;
        # a generic warning leaves users guessing across many sensors (#11).
        offline = [
            f"{kind} source {eid} is {state.state}"
            for kind, state, eid in (
                ("temperature", temp_state, self._temperature_entity_id),
                ("humidity", humidity_state, self._humidity_entity_id),
            )
            if state.state in ("unavailable", "unknown")
        ]
        if offline:
            _LOGGER.warning("%s: %s", label, "; ".join(offline))
            self._set_unavailable()
            return

        try:
            raw_temperature = float(temp_state.state)
            raw_humidity = float(humidity_state.state)
            if not math.isfinite(raw_temperature) or not math.isfinite(raw_humidity):
                raise ValueError("non-finite value")
        except (ValueError, TypeError):
            _LOGGER.warning(
                "%s: invalid temperature or humidity values "
                "(temperature source %s = %r, humidity source %s = %r)",
                label,
                self._temperature_entity_id, temp_state.state,
                self._humidity_entity_id, humidity_state.state,
            )
            self._set_unavailable()
            return

        # Convert temperature to Celsius if needed
        self._temperature = raw_temperature
        temp_unit = temp_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        if temp_unit == UnitOfTemperature.FAHRENHEIT:
            self._temperature = (self._temperature - 32) * 5/9
            _LOGGER.debug("Converted temperature from %s°F to %s°C",
                         raw_temperature, self._temperature)
        elif temp_unit == UnitOfTemperature.KELVIN:
            self._temperature = self._temperature - 273.15
            _LOGGER.debug("Converted temperature from %sK to %s°C",
                         raw_temperature, self._temperature)
        elif temp_unit not in (None, UnitOfTemperature.CELSIUS):
            _LOGGER.warning(
                "%s: unsupported temperature unit %s on %s; assuming °C",
                label, temp_unit, self._temperature_entity_id,
            )

        # Physically implausible readings mark the sensor unavailable instead
        # of feeding garbage into the calculators (and crashing on extremes).
        if not -80 <= self._temperature <= 80:
            _LOGGER.warning(
                "%s: implausible temperature %.1f°C from %s",
                label, self._temperature, self._temperature_entity_id,
            )
            self._set_unavailable()
            return

        # Humidity outside 0-100% is bad source data; clamp rather than drop,
        # but warn so the user can fix the upstream sensor.
        if raw_humidity < 0 or raw_humidity > 100:
            _LOGGER.warning(
                "%s: humidity %.1f%% from %s outside 0-100, clamped",
                label, raw_humidity, self._humidity_entity_id,
            )
        self._humidity = min(100.0, max(0.0, raw_humidity))

        # Get optional sensor values
        wind_speed = 0
        self._wind_speed = None
        if self._wind_speed_entity_id:
            wind_state = self.hass.states.get(self._wind_speed_entity_id)
            if wind_state:
                try:
                    wind_speed = float(wind_state.state)
                    if not math.isfinite(wind_speed):
                        raise ValueError("non-finite wind speed")
                    # Negative readings are sensor noise: clamp to calm
                    # (same treatment as the negative-Beaufort case below).
                    wind_speed = max(0.0, wind_speed)
                    # Convert to m/s if needed
                    wind_unit = wind_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
                    if wind_unit == UnitOfSpeed.KILOMETERS_PER_HOUR:
                        wind_speed = wind_speed / 3.6
                    elif wind_unit == UnitOfSpeed.MILES_PER_HOUR:
                        wind_speed = wind_speed * 0.44704
                    elif wind_unit == UnitOfSpeed.KNOTS:
                        wind_speed = wind_speed * 0.514444
                    elif wind_unit == UnitOfSpeed.FEET_PER_SECOND:
                        wind_speed = wind_speed * 0.3048
                    elif wind_unit == UnitOfSpeed.BEAUFORT:
                        # Beaufort is not linear: v = 0.836 * B^(3/2) m/s.
                        # Clamp at 0: a negative reading would produce a
                        # complex number and crash the update.
                        wind_speed = 0.836 * max(0.0, wind_speed) ** 1.5
                    elif wind_unit not in (None, UnitOfSpeed.METERS_PER_SECOND):
                        _LOGGER.warning(
                            "%s: unsupported wind speed unit %s on %s; assuming m/s",
                            label, wind_unit, self._wind_speed_entity_id,
                        )
                    if wind_unit != UnitOfSpeed.METERS_PER_SECOND:
                        _LOGGER.debug("Converted wind speed from %s %s to %s m/s",
                                     float(wind_state.state), wind_unit, wind_speed)
                    # Physically impossible readings are bad data: they pass
                    # isfinite but produce inf/nan inside wind chill (v*3.6
                    # overflows; inf - inf = nan). ~150 m/s exceeds every
                    # measured surface wind (~113 m/s record gust).
                    if wind_speed > 150:
                        raise ValueError("implausible wind speed")
                    self._wind_speed = wind_speed
                # OverflowError: a huge finite Beaufort overflows the ** 1.5
                # conversion (raising, not returning inf like * does).
                except (ValueError, TypeError, OverflowError):
                    wind_speed = 0
                    _LOGGER.debug(
                        "%s: invalid wind speed value %r from %s",
                        label, wind_state.state, self._wind_speed_entity_id,
                    )

        self._pressure = None
        if self._pressure_entity_id:
            pressure_state = self.hass.states.get(self._pressure_entity_id)
            if pressure_state:
                try:
                    pressure_value = float(pressure_state.state)
                    if not math.isfinite(pressure_value) or pressure_value <= 0:
                        raise ValueError("invalid pressure")

                    # Convert to kPa if needed
                    pressure_unit = pressure_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
                    if pressure_unit in (UnitOfPressure.HPA, UnitOfPressure.MBAR):
                        # 1 hPa = 1 mbar = 0.1 kPa
                        pressure_value = pressure_value * 0.1
                    elif pressure_unit == UnitOfPressure.MMHG:
                        pressure_value = pressure_value * 0.133322
                    elif pressure_unit == UnitOfPressure.INHG:
                        pressure_value = pressure_value * 3.38639
                    elif pressure_unit == UnitOfPressure.PA:
                        pressure_value = pressure_value * 0.001
                    elif pressure_unit == UnitOfPressure.BAR:
                        pressure_value = pressure_value * 100
                    elif pressure_unit == UnitOfPressure.CBAR:
                        pressure_value = pressure_value * 1.0  # 1 cbar = 1 kPa
                    elif pressure_unit == UnitOfPressure.PSI:
                        pressure_value = pressure_value * 6.89476
                    elif pressure_unit not in (None, UnitOfPressure.KPA):
                        _LOGGER.warning(
                            "%s: unsupported pressure unit %s on %s; assuming kPa",
                            label, pressure_unit, self._pressure_entity_id,
                        )
                    if pressure_unit != UnitOfPressure.KPA:
                        _LOGGER.debug("Converted pressure from %s %s to %s kPa",
                                     float(pressure_state.state), pressure_unit, pressure_value)
                    # Multiplication returns inf silently: a huge bar/psi
                    # reading passes the input check but overflows here.
                    if not math.isfinite(pressure_value):
                        raise ValueError("pressure out of range")
                    self._pressure = pressure_value
                except (ValueError, TypeError, OverflowError):
                    _LOGGER.debug(
                        "%s: invalid pressure value %r from %s",
                        label, pressure_state.state, self._pressure_entity_id,
                    )

        # Get wind direction if configured
        self._wind_direction = None
        if self._wind_direction_entity_id:
            wind_dir_state = self.hass.states.get(self._wind_direction_entity_id)
            if wind_dir_state:
                try:
                    wind_direction = float(wind_dir_state.state)
                    if not math.isfinite(wind_direction):
                        raise ValueError("non-finite wind direction")
                    self._wind_direction = wind_direction
                except (ValueError, TypeError):
                    _LOGGER.debug(
                        "%s: invalid wind direction value %r from %s",
                        label, wind_dir_state.state, self._wind_direction_entity_id,
                    )

        # Get solar radiation if configured (estimate cloudiness from it)
        cloudiness = 0
        self._solar_radiation = None
        if self._solar_radiation_entity_id:
            solar_state = self.hass.states.get(self._solar_radiation_entity_id)
            if solar_state:
                try:
                    solar = float(solar_state.state)
                    if not math.isfinite(solar):
                        raise ValueError("non-finite solar radiation")
                    self._solar_radiation = solar
                    # Estimate cloudiness from solar radiation.
                    # Clear sky ≈ 1000 W/m², full cloud ≈ 0 W/m². A reading of
                    # 0 (e.g. at night) is indistinguishable from full
                    # overcast; harmless, since the nighttime branch of the
                    # solar correction ignores cloudiness anyway.
                    cloudiness = max(0, min(100, 100 * (1 - self._solar_radiation / 1000)))
                except (ValueError, TypeError):
                    _LOGGER.debug(
                        "%s: invalid solar radiation value %r from %s",
                        label, solar_state.state, self._solar_radiation_entity_id,
                    )

        # Calculate feels-like temperature
        current_time = dt_util.now()

        # Get latitude from Home Assistant config for hemisphere detection
        latitude = self.hass.config.latitude

        feels_like, method, comfort, wind_dir_correction = calculate_feels_like(
            self._temperature,
            self._humidity,
            wind_speed,
            self._pressure,
            self._is_outdoor,
            current_time,
            cloudiness,
            self._wind_direction,
            latitude,
            self._wind_direction_correction_enabled,
        )
        self._wind_direction_correction = wind_dir_correction

        # Native value stays in Celsius; HA converts the state to the system
        # unit or the entity-registry override (see async_added_to_hass).
        raw_value = round(feels_like, 1)

        # Apply EMA smoothing if enabled
        if self._smoothing_enabled and self._previous_smoothed_value is not None:
            alpha = self._smoothing_factor
            smoothed = round(alpha * raw_value + (1 - alpha) * self._previous_smoothed_value, 1)
            self._attr_native_value = smoothed
            self._previous_smoothed_value = smoothed
        else:
            self._attr_native_value = raw_value
            self._previous_smoothed_value = raw_value

        self._calculation_method = method
        self._comfort_level = comfort

        self._attr_icon = COMFORT_ICONS.get(self._comfort_level, "mdi:thermometer")

        if self._is_outdoor:
            is_comfortable = comfort in [COMFORT_COMFORTABLE, COMFORT_SLIGHTLY_WARM, COMFORT_SLIGHTLY_COOL]
        else:
            is_comfortable = comfort in [COMFORT_COMFORTABLE, COMFORT_SLIGHTLY_WARM]

        _LOGGER.debug(
            "Calculated feels like: %s°C, method: %s, comfort: %s, is_comfortable: %s",
            round(feels_like, 1),
            method,
            comfort,
            is_comfortable
        )

        self._attr_available = True
        self._attr_extra_state_attributes = {
            # comfort_level is the stable machine-readable key (automations
            # and the companion card depend on it); localized text lives in
            # comfort_level_localized.
            ATTR_COMFORT_LEVEL: self._comfort_level,
            ATTR_COMFORT_LEVEL_LOCALIZED: get_comfort_level(self._comfort_level, self.hass.config.language),
            ATTR_COMFORT_DESCRIPTION: get_comfort_description(self._comfort_level, self.hass.config.language),
            ATTR_COMFORT_EXPLANATION: get_comfort_explanation(self._comfort_level, self.hass.config.language),
            ATTR_CALCULATION_METHOD: get_calculation_method(self._calculation_method, self.hass.config.language),
            ATTR_CALCULATION_METHOD_KEY: METHOD_KEYS.get(self._calculation_method, self._calculation_method),
            ATTR_TEMPERATURE: self._temperature,
            ATTR_HUMIDITY: self._humidity,
            ATTR_IS_OUTDOOR: self._is_outdoor,
            ATTR_TIME_OF_DAY: current_time.strftime("%Y-%m-%d %H:%M:%S"),
            ATTR_IS_COMFORTABLE: is_comfortable,
        }

        self._attr_extra_state_attributes.update({
            f"{ATTR_TEMPERATURE}_unit": UnitOfTemperature.CELSIUS,
            f"{ATTR_HUMIDITY}_unit": "%",
        })

        if self._wind_speed is not None:
            self._attr_extra_state_attributes[ATTR_WIND_SPEED] = self._wind_speed
            self._attr_extra_state_attributes[f"{ATTR_WIND_SPEED}_unit"] = UnitOfSpeed.METERS_PER_SECOND
        if self._pressure is not None:
            self._attr_extra_state_attributes[ATTR_PRESSURE] = round(self._pressure, 2)
            self._attr_extra_state_attributes[f"{ATTR_PRESSURE}_unit"] = UnitOfPressure.KPA
        if self._wind_direction is not None:
            self._attr_extra_state_attributes[ATTR_WIND_DIRECTION] = self._wind_direction
            self._attr_extra_state_attributes[f"{ATTR_WIND_DIRECTION}_unit"] = "°"
        if self._wind_direction_correction_enabled and self._wind_direction_correction != 0.0:
            self._attr_extra_state_attributes[ATTR_WIND_DIRECTION_CORRECTION] = round(self._wind_direction_correction, 2)

        self.async_write_ha_state()
