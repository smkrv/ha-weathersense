"""Tests for sensor.py — WeatherSenseSensor update pipeline.

Covers unit conversion, the attribute contract the companion card depends on
(GitHub issue #10), stale-value resets on unavailable inputs, availability
transitions, EMA smoothing, and the native-value-is-always-Celsius rule.
"""

import asyncio
import inspect
import logging
import math
from unittest.mock import MagicMock

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_registry import FakeEntityRegistry
from homeassistant.util import dt as dt_util

from weathersense.sensor import WeatherSenseSensor, async_setup_entry
from weathersense.weather_calculator import calculate_feels_like

TEMP = "sensor.outdoor_temperature"
HUM = "sensor.outdoor_humidity"
WIND = "sensor.wind_speed"
PRESSURE = "sensor.pressure"
SOLAR = "sensor.solar_radiation"
WIND_DIR = "sensor.wind_direction"

LATITUDE = 55.7

ALL_COMFORT_SLUGS = {
    "extreme_cold", "very_cold", "cold", "cool", "slightly_cool",
    "comfortable", "slightly_warm", "warm", "hot", "very_hot", "extreme_hot",
}


class FakeState:
    def __init__(self, state, unit=None):
        self.state = str(state)
        self.attributes = {"unit_of_measurement": unit} if unit is not None else {}


class FakeStates:
    def __init__(self):
        self._states = {}

    def get(self, entity_id):
        return self._states.get(entity_id)

    def set(self, entity_id, state, unit=None):
        self._states[entity_id] = FakeState(state, unit)

    def remove(self, entity_id):
        self._states.pop(entity_id, None)


class FakeUnits:
    temperature_unit = "°C"


class FakeConfig:
    def __init__(self):
        self.language = "en"
        self.latitude = LATITUDE
        self.units = FakeUnits()


class FakeHass:
    def __init__(self):
        self.states = FakeStates()
        self.config = FakeConfig()


class FakeEvent:
    def __init__(self, entity_id, new_state):
        self.data = {"entity_id": entity_id, "new_state": new_state}


def make_hass(temp=20.0, humidity=50.0, temp_unit="°C"):
    hass = FakeHass()
    hass.states.set(TEMP, temp, temp_unit)
    hass.states.set(HUM, humidity)
    return hass


def make_sensor(hass, **kwargs):
    return WeatherSenseSensor(hass, "test_entry", "Feels Like", TEMP, HUM, **kwargs)


def update(sensor):
    asyncio.run(sensor._update_state())


def expected_feels_like(temperature, humidity, wind_speed=0, pressure=None,
                        cloudiness=0, wind_direction=None,
                        wind_direction_correction=False):
    """Expected native value: the calculator called with converted inputs."""
    feels_like, _, _, _ = calculate_feels_like(
        temperature, humidity, wind_speed, pressure, True,
        dt_util.now(), cloudiness, wind_direction, LATITUDE,
        wind_direction_correction,
    )
    return round(feels_like, 1)


# ---------------------------------------------------------------------------
# Conftest regression: the sensor class must be a real class
# ---------------------------------------------------------------------------


class TestSensorIsRealClass:
    """Regression: MagicMock-based homeassistant stubs made WeatherSenseSensor
    itself a MagicMock subclass, silently discarding its class body."""

    def test_not_a_magicmock_subclass(self):
        assert not issubclass(WeatherSenseSensor, MagicMock)
        assert WeatherSenseSensor.__name__ == "WeatherSenseSensor"

    def test_update_state_is_a_plain_coroutine_function(self):
        assert inspect.iscoroutinefunction(WeatherSenseSensor._update_state)


# ---------------------------------------------------------------------------
# Temperature unit conversion
# ---------------------------------------------------------------------------


class TestTemperatureConversion:
    """Input temperature is converted to Celsius before calculation."""

    def test_fahrenheit_converted_to_celsius(self):
        hass = make_hass(temp=68.0, temp_unit="°F")
        sensor = make_sensor(hass)
        update(sensor)
        attrs = sensor._attr_extra_state_attributes
        assert attrs["temperature"] == pytest.approx(20.0)
        assert attrs["temperature_unit"] == "°C"

    def test_celsius_passthrough(self):
        hass = make_hass(temp=20.0, temp_unit="°C")
        sensor = make_sensor(hass)
        update(sensor)
        assert sensor._attr_extra_state_attributes["temperature"] == 20.0


# ---------------------------------------------------------------------------
# Wind speed unit conversion
# ---------------------------------------------------------------------------


class TestWindSpeedConversion:
    """All supported wind units are converted to m/s."""

    @pytest.mark.parametrize(
        "unit, raw, expected_ms",
        [
            ("km/h", 36.0, 10.0),
            ("mph", 10.0, 4.4704),
            ("kn", 10.0, 5.14444),
            ("ft/s", 10.0, 3.048),
            ("Beaufort", 4.0, 6.688),  # 0.836 * 4^1.5
            ("m/s", 7.5, 7.5),
            (None, 7.5, 7.5),  # no unit attribute → assumed m/s
        ],
    )
    def test_conversion_to_ms(self, unit, raw, expected_ms):
        hass = make_hass()
        hass.states.set(WIND, raw, unit)
        sensor = make_sensor(hass, wind_speed_entity_id=WIND)
        update(sensor)
        attrs = sensor._attr_extra_state_attributes
        assert attrs["wind_speed"] == pytest.approx(expected_ms)
        assert attrs["wind_speed_unit"] == "m/s"

    def test_unknown_unit_assumed_ms_and_warns(self, caplog):
        hass = make_hass()
        hass.states.set(WIND, 5.0, "mach")
        sensor = make_sensor(hass, wind_speed_entity_id=WIND)
        with caplog.at_level(logging.WARNING):
            update(sensor)
        assert sensor._attr_extra_state_attributes["wind_speed"] == 5.0
        assert "unsupported wind speed unit" in caplog.text

    def test_negative_beaufort_clamped_to_zero(self):
        """A glitched negative Beaufort reading must not raise (complex power)."""
        hass = make_hass()
        hass.states.set(WIND, -1.0, "Beaufort")
        sensor = make_sensor(hass, wind_speed_entity_id=WIND)
        update(sensor)
        assert sensor._attr_extra_state_attributes["wind_speed"] == 0.0


# ---------------------------------------------------------------------------
# Pressure unit conversion
# ---------------------------------------------------------------------------


class TestPressureConversion:
    """All supported pressure units are converted to kPa."""

    @pytest.mark.parametrize(
        "unit, raw, expected_kpa",
        [
            ("hPa", 1013.0, 101.3),
            ("mbar", 1013.0, 101.3),
            ("mmHg", 760.0, 101.32),
            ("inHg", 29.92, 101.32),
            ("Pa", 101300.0, 101.3),
            ("bar", 1.013, 101.3),
            ("cbar", 101.3, 101.3),
            ("psi", 14.7, 101.35),
            ("kPa", 101.3, 101.3),
        ],
    )
    def test_conversion_to_kpa(self, unit, raw, expected_kpa):
        hass = make_hass()
        hass.states.set(PRESSURE, raw, unit)
        sensor = make_sensor(hass, pressure_entity_id=PRESSURE)
        update(sensor)
        attrs = sensor._attr_extra_state_attributes
        assert attrs["pressure"] == pytest.approx(expected_kpa)
        assert attrs["pressure_unit"] == "kPa"

    def test_unknown_unit_assumed_kpa_and_warns(self, caplog):
        hass = make_hass()
        hass.states.set(PRESSURE, 101.3, "atm")
        sensor = make_sensor(hass, pressure_entity_id=PRESSURE)
        with caplog.at_level(logging.WARNING):
            update(sensor)
        assert sensor._attr_extra_state_attributes["pressure"] == 101.3
        assert "unsupported pressure unit" in caplog.text


# ---------------------------------------------------------------------------
# Attribute contract (regression net for GitHub issue #10)
# ---------------------------------------------------------------------------


class TestAttributeContract:
    """The companion card reads these exact keys; the state must be the
    feels-like value while the raw input temperature stays in attributes."""

    def test_native_value_is_feels_like_not_input_temp(self):
        hass = make_hass(temp=18.0, humidity=50.0)
        sensor = make_sensor(hass)
        update(sensor)

        # 18°C/50% at fixed noon: Steadman 17.4°C + 2.0°C solar → 19.4°C
        assert sensor._attr_native_value == pytest.approx(19.4)
        assert sensor._attr_native_value == expected_feels_like(18.0, 50.0)
        assert sensor._attr_native_value != 18.0

        attrs = sensor._attr_extra_state_attributes
        assert attrs["temperature"] == 18.0
        assert attrs["temperature_unit"] == "°C"
        assert attrs["humidity"] == 50.0
        assert attrs["humidity_unit"] == "%"

    def test_comfort_level_is_stable_slug_with_localized_twin(self):
        hass = make_hass(temp=18.0, humidity=50.0)
        sensor = make_sensor(hass)
        update(sensor)

        attrs = sensor._attr_extra_state_attributes
        assert attrs["comfort_level"] == "comfortable"
        assert attrs["comfort_level"] in ALL_COMFORT_SLUGS
        assert attrs["comfort_level_localized"] == "Comfortable"
        assert attrs["is_comfortable"] is True

    @pytest.mark.parametrize(
        "temp, humidity, wind_ms, is_outdoor, expected_key",
        [
            (30.0, 70.0, 0.0, True, "heat_index"),
            (-5.0, 50.0, 5.0, True, "wind_chill"),
            (18.0, 50.0, 0.0, True, "steadman"),
            (22.0, 50.0, 0.0, False, "indoor"),
        ],
    )
    def test_calculation_method_key(self, temp, humidity, wind_ms, is_outdoor, expected_key):
        hass = make_hass(temp=temp, humidity=humidity)
        hass.states.set(WIND, wind_ms, "m/s")
        sensor = make_sensor(
            hass, wind_speed_entity_id=WIND, is_outdoor=is_outdoor
        )
        update(sensor)
        attrs = sensor._attr_extra_state_attributes
        assert attrs["calculation_method_key"] == expected_key
        assert attrs["calculation_method_key"] in {
            "heat_index", "wind_chill", "steadman", "indoor"
        }

    def test_wind_direction_correction_attribute_when_enabled(self):
        hass = make_hass(temp=18.0, humidity=50.0)
        hass.states.set(WIND_DIR, 0.0)  # due north → -1.0°C in Northern Hemisphere
        sensor = make_sensor(
            hass,
            wind_direction_entity_id=WIND_DIR,
            wind_direction_correction=True,
        )
        update(sensor)
        attrs = sensor._attr_extra_state_attributes
        assert attrs["wind_direction"] == 0.0
        assert attrs["wind_direction_correction_applied"] == pytest.approx(-1.0)
        assert sensor._attr_native_value == expected_feels_like(
            18.0, 50.0, wind_direction=0.0, wind_direction_correction=True
        )


# ---------------------------------------------------------------------------
# Stale-value resets when an optional input disappears
# ---------------------------------------------------------------------------


class TestStaleValueResets:
    """A vanished optional input must drop its attribute instead of serving
    the previous value, and the calculation must fall back to the default."""

    def test_wind_unavailable_drops_attribute_and_calc_uses_zero(self):
        hass = make_hass(temp=20.0, humidity=50.0)
        hass.states.set(WIND, 15.0, "m/s")
        sensor = make_sensor(hass, wind_speed_entity_id=WIND)
        update(sensor)
        assert sensor._attr_extra_state_attributes["wind_speed"] == 15.0
        value_with_wind = sensor._attr_native_value

        hass.states.set(WIND, "unavailable")
        update(sensor)

        attrs = sensor._attr_extra_state_attributes
        assert "wind_speed" not in attrs
        assert sensor._wind_speed is None
        assert sensor._attr_native_value == expected_feels_like(20.0, 50.0, wind_speed=0)
        # 15 m/s of wind cooled the Steadman result by 10.5°C; without it
        # the value must climb back.
        assert sensor._attr_native_value > value_with_wind

    def test_pressure_unavailable_drops_attribute(self):
        hass = make_hass()
        hass.states.set(PRESSURE, 1013.0, "hPa")
        sensor = make_sensor(hass, pressure_entity_id=PRESSURE)
        update(sensor)
        assert sensor._attr_extra_state_attributes["pressure"] == pytest.approx(101.3)

        hass.states.set(PRESSURE, "unavailable")
        update(sensor)
        assert "pressure" not in sensor._attr_extra_state_attributes
        assert sensor._pressure is None

    def test_wind_direction_unavailable_drops_attribute(self):
        hass = make_hass()
        hass.states.set(WIND_DIR, 180.0)
        sensor = make_sensor(hass, wind_direction_entity_id=WIND_DIR)
        update(sensor)
        assert sensor._attr_extra_state_attributes["wind_direction"] == 180.0

        hass.states.set(WIND_DIR, "unavailable")
        update(sensor)
        assert "wind_direction" not in sensor._attr_extra_state_attributes
        assert sensor._wind_direction is None

    def test_solar_unavailable_resets_cloudiness_to_zero(self):
        hass = make_hass(temp=18.0, humidity=50.0)
        hass.states.set(SOLAR, 800.0)  # → cloudiness 20 → smaller solar gain
        sensor = make_sensor(hass, solar_radiation_entity_id=SOLAR)
        update(sensor)
        assert sensor._solar_radiation == 800.0
        assert sensor._attr_native_value == expected_feels_like(18.0, 50.0, cloudiness=20)

        hass.states.set(SOLAR, "unavailable")
        update(sensor)
        assert sensor._solar_radiation is None
        assert sensor._attr_native_value == expected_feels_like(18.0, 50.0, cloudiness=0)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


class TestAvailability:
    """Missing or non-numeric required inputs flip the entity unavailable."""

    def test_missing_temperature_state_flips_unavailable(self):
        hass = FakeHass()
        hass.states.set(HUM, 50.0)
        sensor = make_sensor(hass)
        update(sensor)
        assert sensor._attr_available is False
        assert len(sensor.write_ha_state_calls) == 1

    def test_unavailable_temperature_string_flips_unavailable(self):
        hass = make_hass()
        hass.states.set(TEMP, "unavailable")
        sensor = make_sensor(hass)
        update(sensor)
        assert sensor._attr_available is False

    def test_missing_humidity_state_flips_unavailable(self):
        hass = FakeHass()
        hass.states.set(TEMP, 20.0, "°C")
        sensor = make_sensor(hass)
        update(sensor)
        assert sensor._attr_available is False

    def test_repeated_failure_writes_state_only_once(self):
        hass = FakeHass()
        sensor = make_sensor(hass)
        update(sensor)
        update(sensor)
        assert len(sensor.write_ha_state_calls) == 1

    def test_recovery_restores_availability(self):
        hass = FakeHass()
        sensor = make_sensor(hass)
        update(sensor)
        assert sensor._attr_available is False

        hass.states.set(TEMP, 20.0, "°C")
        hass.states.set(HUM, 50.0)
        update(sensor)
        assert sensor._attr_available is True
        assert sensor._attr_native_value == expected_feels_like(20.0, 50.0)
        assert len(sensor.write_ha_state_calls) == 2

    def test_handle_state_changes_recomputes_on_unavailable_event(self):
        """Regression: the handler used to return early on unavailable events,
        so a vanished required input never flipped the entity unavailable."""
        hass = make_hass(temp=20.0, humidity=50.0)
        sensor = make_sensor(hass)
        update(sensor)
        assert sensor._attr_available is True

        hass.states.set(TEMP, "unavailable")
        event = FakeEvent(TEMP, FakeState("unavailable"))
        asyncio.run(sensor._handle_state_changes(event))
        assert sensor._attr_available is False


# ---------------------------------------------------------------------------
# EMA smoothing
# ---------------------------------------------------------------------------


class TestSmoothing:
    """EMA smoothing: value = alpha * raw + (1 - alpha) * previous."""

    def test_first_update_stores_raw_value(self):
        hass = make_hass(temp=18.0, humidity=50.0)
        sensor = make_sensor(hass, smoothing_enabled=True, smoothing_factor=0.3)
        update(sensor)
        assert sensor._attr_native_value == expected_feels_like(18.0, 50.0)

    def test_second_update_applies_ema(self):
        hass = make_hass(temp=18.0, humidity=50.0)
        sensor = make_sensor(hass, smoothing_enabled=True, smoothing_factor=0.3)
        update(sensor)
        raw1 = expected_feels_like(18.0, 50.0)

        hass.states.set(TEMP, 10.0, "°C")
        update(sensor)
        raw2 = expected_feels_like(10.0, 50.0)

        assert sensor._attr_native_value == round(0.3 * raw2 + 0.7 * raw1, 1)
        # raw1 = 19.4, raw2 = 9.5 → 0.3*9.5 + 0.7*19.4 = 16.43 → 16.4
        assert sensor._attr_native_value == pytest.approx(16.4)

    def test_disabled_smoothing_tracks_raw_values(self):
        hass = make_hass(temp=18.0, humidity=50.0)
        sensor = make_sensor(hass, smoothing_enabled=False)
        update(sensor)
        hass.states.set(TEMP, 10.0, "°C")
        update(sensor)
        assert sensor._attr_native_value == expected_feels_like(10.0, 50.0)

    def test_smoothing_factor_clamped_low(self):
        sensor = make_sensor(make_hass(), smoothing_enabled=True, smoothing_factor=0.01)
        assert sensor._smoothing_factor == 0.05

    def test_smoothing_factor_clamped_high(self):
        sensor = make_sensor(make_hass(), smoothing_enabled=True, smoothing_factor=0.99)
        assert sensor._smoothing_factor == 0.95


# ---------------------------------------------------------------------------
# Native value stays Celsius regardless of display unit
# ---------------------------------------------------------------------------


class TestNativeValueUnit:
    """The native value is always Celsius; a Fahrenheit display choice is
    expressed via suggested/registry unit, never by converting the value."""

    def test_fahrenheit_display_does_not_convert_native_value(self):
        hass = make_hass(temp=18.0, humidity=50.0)
        sensor_c = make_sensor(hass)
        sensor_f = make_sensor(hass, display_unit="°F")
        update(sensor_c)
        update(sensor_f)

        assert sensor_f._attr_native_value == sensor_c._attr_native_value
        assert sensor_f._attr_native_unit_of_measurement == "°C"
        assert sensor_f._attr_suggested_unit_of_measurement == "°F"

    def test_invalid_display_unit_ignored(self):
        sensor = make_sensor(make_hass(), display_unit="K")
        assert sensor._display_unit is None


# ---------------------------------------------------------------------------
# async_added_to_hass: initial update, listeners, registry unit override
# ---------------------------------------------------------------------------


class FakeRegistryEntry:
    def __init__(self, entity_id, unit=None):
        self.entity_id = entity_id
        self.options = {"sensor": {"unit_of_measurement": unit}} if unit else {}


class TestAsyncAddedToHass:
    """Entity setup: initial calculation, state listeners, and the
    entity-registry unit override for an explicit display unit."""

    def test_initial_update_and_listener_registration(self, monkeypatch):
        hass = make_hass(temp=18.0, humidity=50.0)
        hass.states.set(WIND, 5.0, "m/s")
        hass.states.set(PRESSURE, 101.3, "kPa")
        hass.states.set(SOLAR, 0.0)  # 0 W/m² → cloudiness 100 → no solar gain
        hass.states.set(WIND_DIR, 90.0)
        tracked = {}

        def fake_track(hass_arg, entity_ids, action):
            tracked["entity_ids"] = entity_ids
            return lambda: None

        monkeypatch.setattr(
            "weathersense.sensor.async_track_state_change_event", fake_track
        )
        sensor = make_sensor(
            hass,
            wind_speed_entity_id=WIND,
            pressure_entity_id=PRESSURE,
            solar_radiation_entity_id=SOLAR,
            wind_direction_entity_id=WIND_DIR,
        )
        sensor.entity_id = "sensor.feels_like"
        asyncio.run(sensor.async_added_to_hass())

        assert sensor._attr_native_value == expected_feels_like(
            18.0, 50.0, wind_speed=5.0, pressure=101.3, cloudiness=100
        )
        assert tracked["entity_ids"] == [TEMP, HUM, WIND, PRESSURE, SOLAR, WIND_DIR]
        assert len(sensor.on_remove_callbacks) == 1

    def test_entity_in_two_roles_tracked_once(self, monkeypatch):
        """HA registers one job per listed id: a duplicate would run the
        update twice for a single state change."""
        tracked = {}

        def fake_track(hass_arg, entity_ids, action):
            tracked["entity_ids"] = entity_ids
            return lambda: None

        monkeypatch.setattr(
            "weathersense.sensor.async_track_state_change_event", fake_track
        )
        sensor = make_sensor(
            make_hass(),
            wind_speed_entity_id=WIND,
            wind_direction_entity_id=WIND,
        )
        asyncio.run(sensor.async_added_to_hass())

        assert tracked["entity_ids"] == [TEMP, HUM, WIND]

    def test_display_unit_updates_registry_override(self, monkeypatch):
        registry = FakeEntityRegistry()
        registry.async_get = lambda entity_id: FakeRegistryEntry(
            "sensor.feels_like", "°C"
        )
        monkeypatch.setattr("weathersense.sensor.er.async_get", lambda hass: registry)

        sensor = make_sensor(make_hass(), display_unit="°F")
        sensor.entity_id = "sensor.feels_like"
        asyncio.run(sensor.async_added_to_hass())

        assert registry.updated_options == [
            ("sensor.feels_like", "sensor", {"unit_of_measurement": "°F"})
        ]

    def test_display_unit_already_matching_skips_registry_write(self, monkeypatch):
        registry = FakeEntityRegistry()
        registry.async_get = lambda entity_id: FakeRegistryEntry(
            "sensor.feels_like", "°F"
        )
        monkeypatch.setattr("weathersense.sensor.er.async_get", lambda hass: registry)

        sensor = make_sensor(make_hass(), display_unit="°F")
        sensor.entity_id = "sensor.feels_like"
        asyncio.run(sensor.async_added_to_hass())

        assert registry.updated_options == []

    def test_unregistered_entity_skips_registry_write(self, monkeypatch):
        registry = FakeEntityRegistry()  # async_get returns None by default
        monkeypatch.setattr("weathersense.sensor.er.async_get", lambda hass: registry)

        sensor = make_sensor(make_hass(), display_unit="°F")
        sensor.entity_id = "sensor.feels_like"
        asyncio.run(sensor.async_added_to_hass())

        assert registry.updated_options == []


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    """Platform setup builds the sensor from config entry data + options."""

    def test_builds_sensor_from_entry_data(self):
        hass = make_hass()
        entry = ConfigEntry(
            entry_id="entry_1",
            data={
                "name": "My Feels Like",
                "temperature_sensor": TEMP,
                "humidity_sensor": HUM,
                "wind_speed_sensor": WIND,
            },
        )
        added = []
        asyncio.run(async_setup_entry(hass, entry, added.extend))

        assert len(added) == 1
        sensor = added[0]
        assert isinstance(sensor, WeatherSenseSensor)
        assert sensor._temperature_entity_id == TEMP
        assert sensor._humidity_entity_id == HUM
        assert sensor._wind_speed_entity_id == WIND
        assert sensor._is_outdoor is True

    def test_options_override_entry_data(self):
        hass = make_hass()
        entry = ConfigEntry(
            entry_id="entry_1",
            data={
                "temperature_sensor": TEMP,
                "humidity_sensor": HUM,
                "is_outdoor": True,
                "smoothing_enabled": False,
            },
            options={"is_outdoor": False, "smoothing_enabled": True},
        )
        added = []
        asyncio.run(async_setup_entry(hass, entry, added.extend))

        sensor = added[0]
        assert sensor._is_outdoor is False
        assert sensor._smoothing_enabled is True


# ---------------------------------------------------------------------------
# Diagnostic warnings (GitHub issue #11)
# ---------------------------------------------------------------------------


class TestDiagnosticWarnings:
    """Every warning must say WHICH WeatherSense sensor and WHICH input is
    the problem — a one-tick flicker must be identifiable from the log alone."""

    def test_missing_temperature_names_sensor_and_source(self, caplog):
        hass = FakeHass()
        hass.states.set(HUM, 50.0)
        sensor = make_sensor(hass)
        sensor.entity_id = "sensor.feels_like_wohnen"
        with caplog.at_level(logging.WARNING):
            update(sensor)
        assert "sensor.feels_like_wohnen" in caplog.text
        assert f"temperature source {TEMP} has no state" in caplog.text
        assert sensor._attr_available is False

    def test_missing_both_inputs_names_both(self, caplog):
        sensor = make_sensor(FakeHass())
        with caplog.at_level(logging.WARNING):
            update(sensor)
        assert f"temperature source {TEMP}" in caplog.text
        assert f"humidity source {HUM}" in caplog.text

    def test_unavailable_flicker_names_which_input(self, caplog):
        """The reporter's case: a sub-second unavailable tick must leave a
        log line naming the exact source entity that blinked."""
        hass = make_hass()
        hass.states.set(TEMP, "unavailable")
        sensor = make_sensor(hass)
        sensor.entity_id = "sensor.feels_like_wohnen"
        with caplog.at_level(logging.WARNING):
            update(sensor)
        assert f"temperature source {TEMP} is unavailable" in caplog.text
        assert "humidity" not in caplog.text  # only the flickering input is named
        assert sensor._attr_available is False

    def test_unknown_humidity_named(self, caplog):
        hass = make_hass()
        hass.states.set(HUM, "unknown")
        sensor = make_sensor(hass)
        with caplog.at_level(logging.WARNING):
            update(sensor)
        assert f"humidity source {HUM} is unknown" in caplog.text

    def test_non_numeric_value_names_entity_and_raw_values(self, caplog):
        hass = make_hass()
        hass.states.set(TEMP, "error")
        sensor = make_sensor(hass)
        sensor.entity_id = "sensor.feels_like_wohnen"
        with caplog.at_level(logging.WARNING):
            update(sensor)
        assert "sensor.feels_like_wohnen" in caplog.text
        assert TEMP in caplog.text and "'error'" in caplog.text
        assert sensor._attr_available is False

    def test_falls_back_to_name_without_entity_id(self, caplog):
        hass = FakeHass()
        sensor = make_sensor(hass)
        sensor.entity_id = None  # before platform registration
        with caplog.at_level(logging.WARNING):
            update(sensor)
        assert "Feels Like" in caplog.text


def warning_lines(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]


def _missing_temperature(hass):
    hass.states.remove(TEMP)


def _offline_humidity(hass):
    hass.states.set(HUM, "unknown")


def _non_numeric_temperature(hass):
    hass.states.set(TEMP, "error")


def _unsupported_temperature_unit(hass):
    hass.states.set(TEMP, 20.0, "°R")


def _implausible_temperature(hass):
    hass.states.set(TEMP, 500.0, "°C")


def _humidity_out_of_range(hass):
    hass.states.set(HUM, 100.4)


def _unsupported_wind_unit(hass):
    hass.states.set(WIND, 3.0, "furlong/fortnight")


def _unsupported_pressure_unit(hass):
    hass.states.set(PRESSURE, 1.0, "atm")


class TestWarnOncePerEpisode:
    """_update_state runs on every state change of any tracked input, so a
    condition that persists (humidity stuck at 101% overnight, a dead source)
    must log one WARNING per episode, not one per update. A condition that
    clears and comes back warns again: every flicker from #11 still leaves
    its own line."""

    @pytest.mark.parametrize("break_input", [
        _missing_temperature,
        _offline_humidity,
        _non_numeric_temperature,
        _unsupported_temperature_unit,
        _implausible_temperature,
        _humidity_out_of_range,
        _unsupported_wind_unit,
        _unsupported_pressure_unit,
    ])
    def test_persistent_condition_warns_once(self, caplog, break_input):
        hass = make_hass()
        hass.states.set(WIND, 3.0, "m/s")
        hass.states.set(PRESSURE, 101.3, "kPa")
        break_input(hass)
        sensor = make_sensor(
            hass, wind_speed_entity_id=WIND, pressure_entity_id=PRESSURE
        )
        with caplog.at_level(logging.WARNING):
            for _ in range(5):
                update(sensor)
        assert len(warning_lines(caplog)) == 1

    def test_repeats_are_logged_at_debug(self, caplog):
        sensor = make_sensor(make_hass(humidity=100.4))
        with caplog.at_level(logging.DEBUG):
            update(sensor)
            update(sensor)
        clamp = [r.levelno for r in caplog.records if "outside 0-100" in r.getMessage()]
        assert clamp == [logging.WARNING, logging.DEBUG]

    def test_changing_value_of_same_condition_warns_once(self, caplog):
        """The episode is the condition, not the exact reading: a drifting
        101.2 -> 102.5% is still the same out-of-range humidity."""
        hass = make_hass()
        sensor = make_sensor(hass)
        with caplog.at_level(logging.WARNING):
            for humidity in (100.4, 101.2, 102.5):
                hass.states.set(HUM, humidity)
                update(sensor)
        assert len(warning_lines(caplog)) == 1

    def test_cleared_then_recurring_condition_warns_again(self, caplog):
        hass = make_hass()
        sensor = make_sensor(hass)
        with caplog.at_level(logging.WARNING):
            hass.states.set(TEMP, "unavailable")
            update(sensor)
            update(sensor)  # same flicker seen by a humidity update
            hass.states.set(TEMP, 20.0, "°C")
            update(sensor)  # recovered
            hass.states.set(TEMP, "unavailable")
            update(sensor)  # second flicker
        lines = warning_lines(caplog)
        assert lines == [f"Feels Like: temperature source {TEMP} is unavailable"] * 2

    def test_second_input_failing_while_first_is_invalid_warns(self, caplog):
        """Episodes are per source: humidity breaking while temperature is
        still bad is news; humidity staying bad after temperature recovers
        is not."""
        hass = make_hass()
        sensor = make_sensor(hass)
        with caplog.at_level(logging.WARNING):
            hass.states.set(TEMP, "error")
            update(sensor)
            hass.states.set(HUM, "nan")
            update(sensor)
            hass.states.set(TEMP, 20.0, "°C")
            update(sensor)
        lines = warning_lines(caplog)
        assert len(lines) == 2
        assert "'nan'" in lines[1]

    def test_second_source_going_offline_warns(self, caplog):
        hass = make_hass()
        sensor = make_sensor(hass)
        with caplog.at_level(logging.WARNING):
            hass.states.set(TEMP, "unavailable")
            update(sensor)
            hass.states.set(HUM, "unavailable")
            update(sensor)
            hass.states.set(HUM, 50.0)
            update(sensor)  # temperature is still the same offline episode
        lines = warning_lines(caplog)
        assert len(lines) == 2
        assert f"humidity source {HUM} is unavailable" in lines[1]

    def test_persistent_condition_survives_required_input_flicker(self, caplog):
        """A flicker returns before the humidity and wind checks run; that
        must not end their episodes."""
        hass = make_hass(humidity=101.0)
        hass.states.set(WIND, 3.0, "furlong/fortnight")
        sensor = make_sensor(hass, wind_speed_entity_id=WIND)
        with caplog.at_level(logging.WARNING):
            update(sensor)
            hass.states.set(TEMP, "unavailable")
            update(sensor)
            hass.states.set(TEMP, 20.0, "°C")
            update(sensor)
        lines = warning_lines(caplog)
        assert len(lines) == 3
        assert "outside 0-100" in lines[0]
        assert "unsupported wind speed unit" in lines[1]
        assert "is unavailable" in lines[2]

    def test_optional_input_flicker_keeps_its_unit_episode(self, caplog):
        hass = make_hass()
        hass.states.set(WIND, 3.0, "furlong/fortnight")
        sensor = make_sensor(hass, wind_speed_entity_id=WIND)
        with caplog.at_level(logging.WARNING):
            update(sensor)
            hass.states.set(WIND, "unavailable", "furlong/fortnight")
            update(sensor)
            hass.states.set(WIND, 3.0, "furlong/fortnight")
            update(sensor)
        assert len(warning_lines(caplog)) == 1

    def test_new_condition_warns_while_another_persists(self, caplog):
        hass = make_hass(humidity=100.4)
        hass.states.set(WIND, 3.0, "m/s")
        sensor = make_sensor(hass, wind_speed_entity_id=WIND)
        with caplog.at_level(logging.WARNING):
            update(sensor)
            _unsupported_wind_unit(hass)
            update(sensor)
        lines = warning_lines(caplog)
        assert len(lines) == 2
        assert "outside 0-100" in lines[0]
        assert "unsupported wind speed unit" in lines[1]


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Bad source data must not silently poison the calculation."""

    def test_nan_temperature_flips_unavailable(self):
        hass = make_hass()
        hass.states.set(TEMP, "nan")
        sensor = make_sensor(hass)
        update(sensor)
        assert sensor._attr_available is False

    def test_inf_temperature_flips_unavailable(self):
        hass = make_hass()
        hass.states.set(TEMP, "inf")
        sensor = make_sensor(hass)
        update(sensor)
        assert sensor._attr_available is False

    def test_implausible_temperature_flips_unavailable(self, caplog):
        """500°C cannot be real data; marking unavailable prevents garbage
        (and extreme negatives near -237.7°C crash the vapor-pressure exp)."""
        hass = make_hass(temp=500.0)
        sensor = make_sensor(hass)
        with caplog.at_level(logging.WARNING):
            update(sensor)
        assert sensor._attr_available is False
        assert "implausible temperature" in caplog.text

    def test_extreme_negative_temperature_no_crash(self):
        hass = make_hass(temp=-237.7)
        sensor = make_sensor(hass)
        update(sensor)
        assert sensor._attr_available is False

    def test_kelvin_converted_to_celsius(self):
        hass = make_hass(temp=293.15, temp_unit="K")
        sensor = make_sensor(hass)
        update(sensor)
        assert sensor._attr_extra_state_attributes["temperature"] == pytest.approx(20.0)

    def test_unknown_temperature_unit_warns_and_assumes_celsius(self, caplog):
        hass = make_hass(temp=20.0, temp_unit="°R")
        sensor = make_sensor(hass)
        with caplog.at_level(logging.WARNING):
            update(sensor)
        assert "unsupported temperature unit" in caplog.text
        assert sensor._attr_extra_state_attributes["temperature"] == 20.0

    def test_humidity_over_100_clamped_and_warns(self, caplog):
        hass = make_hass(humidity=140.0)
        sensor = make_sensor(hass)
        with caplog.at_level(logging.WARNING):
            update(sensor)
        assert sensor._attr_extra_state_attributes["humidity"] == 100.0
        assert "outside 0-100" in caplog.text
        assert sensor._attr_available is True

    def test_negative_humidity_clamped_to_zero(self):
        hass = make_hass(humidity=-5.0)
        sensor = make_sensor(hass)
        update(sensor)
        assert sensor._attr_extra_state_attributes["humidity"] == 0.0

    def test_nan_pressure_does_not_poison_native_value(self):
        """Regression: nan <= 0 is False, so a nan pressure flowed into the
        correction and made the whole native value nan."""
        hass = make_hass()
        hass.states.set(PRESSURE, "nan")
        sensor = make_sensor(hass, pressure_entity_id=PRESSURE)
        update(sensor)
        assert "pressure" not in sensor._attr_extra_state_attributes
        assert math.isfinite(sensor._attr_native_value)

    def test_negative_wind_clamped_to_calm(self):
        """Negative wind is sensor noise; clamped to 0 like negative
        Beaufort already was."""
        hass = make_hass()
        hass.states.set(WIND, -3.0, "m/s")
        sensor = make_sensor(hass, wind_speed_entity_id=WIND)
        update(sensor)
        assert sensor._attr_extra_state_attributes["wind_speed"] == 0.0
        assert math.isfinite(sensor._attr_native_value)

    def test_nan_wind_treated_as_invalid(self):
        hass = make_hass()
        hass.states.set(WIND, "nan", "m/s")
        sensor = make_sensor(hass, wind_speed_entity_id=WIND)
        update(sensor)
        assert "wind_speed" not in sensor._attr_extra_state_attributes
        assert math.isfinite(sensor._attr_native_value)

    @pytest.mark.parametrize("state,unit", [
        ("200", "m/s"),      # above every recorded surface wind (~113 m/s gust)
        ("1e308", "m/s"),    # finite, but *3.6 -> inf -> inf-inf -> nan in wind chill
        ("1e300", "mph"),    # conversion product stays finite, still implausible
    ])
    def test_implausible_wind_dropped_not_published_as_nan(self, state, unit):
        """Regression (Devin Review): huge finite wind passed validation and
        overflowed inside calculate_wind_chill, publishing a nan temperature."""
        hass = make_hass(temp=5.0)  # cold day -> wind chill path
        hass.states.set(WIND, state, unit)
        sensor = make_sensor(hass, wind_speed_entity_id=WIND)
        update(sensor)
        assert "wind_speed" not in sensor._attr_extra_state_attributes
        assert math.isfinite(sensor._attr_native_value)

    def test_plausible_high_wind_kept(self):
        hass = make_hass(temp=5.0)
        hass.states.set(WIND, "300", "km/h")  # 83.3 m/s: extreme but real
        sensor = make_sensor(hass, wind_speed_entity_id=WIND)
        update(sensor)
        assert sensor._attr_extra_state_attributes["wind_speed"] == pytest.approx(83.33, rel=0.01)

    def test_huge_beaufort_does_not_abort_update(self):
        """Regression (Devin Review): a huge finite Beaufort value overflows
        the ** 1.5 conversion with OverflowError, which escaped the handler
        and aborted the whole update."""
        hass = make_hass()
        hass.states.set(WIND, "1e300", "Beaufort")
        sensor = make_sensor(hass, wind_speed_entity_id=WIND)
        update(sensor)
        assert "wind_speed" not in sensor._attr_extra_state_attributes
        assert sensor._attr_available is True
        assert math.isfinite(sensor._attr_native_value)

    def test_huge_bar_pressure_not_published_as_infinity(self):
        """Regression (Devin Review): bar * 100 returns inf silently, and the
        attribute used to publish the infinite value."""
        hass = make_hass()
        hass.states.set(PRESSURE, "1e307", "bar")
        sensor = make_sensor(hass, pressure_entity_id=PRESSURE)
        update(sensor)
        assert "pressure" not in sensor._attr_extra_state_attributes
        assert sensor._pressure is None
        assert math.isfinite(sensor._attr_native_value)

    def test_nan_wind_direction_ignored(self):
        hass = make_hass()
        hass.states.set(WIND_DIR, "nan")
        sensor = make_sensor(
            hass, wind_direction_entity_id=WIND_DIR, wind_direction_correction=True
        )
        update(sensor)
        assert "wind_direction" not in sensor._attr_extra_state_attributes
        assert math.isfinite(sensor._attr_native_value)

    def test_nan_solar_radiation_ignored(self):
        hass = make_hass()
        hass.states.set(SOLAR, "nan")
        sensor = make_sensor(hass, solar_radiation_entity_id=SOLAR)
        update(sensor)
        assert sensor._solar_radiation is None
        assert math.isfinite(sensor._attr_native_value)
