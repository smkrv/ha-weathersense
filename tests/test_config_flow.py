"""Tests for config_flow.py — initial setup flow and options flow.

Covers async_step_user validation, the HA 2024.11 regression (the options flow
must keep its own entry reference and never touch self.config_entry), the
_CLEARABLE_FIELDS write-back-as-None normalization, the display-unit
set->cleared transition that drops the entity-registry unit override, and the
options form build with suggested_value descriptions.
"""

import asyncio

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_registry import FakeEntityRegistry

from weathersense.config_flow import WeatherSenseConfigFlow, WeatherSenseOptionsFlow
from weathersense.const import (
    CONF_DISPLAY_UNIT,
    CONF_HUMIDITY_SENSOR,
    CONF_IS_OUTDOOR,
    CONF_PRESSURE_SENSOR,
    CONF_SMOOTHING_ENABLED,
    CONF_SMOOTHING_FACTOR,
    CONF_SOLAR_RADIATION_SENSOR,
    CONF_TEMPERATURE_SENSOR,
    CONF_WIND_DIRECTION_CORRECTION,
    CONF_WIND_DIRECTION_SENSOR,
    CONF_WIND_SPEED_SENSOR,
    DEFAULT_NAME,
    DEFAULT_SMOOTHING_FACTOR,
)

TEMP = "sensor.outdoor_temperature"
HUM = "sensor.outdoor_humidity"
WIND = "sensor.wind_speed"
PRESSURE = "sensor.pressure"
SOLAR = "sensor.solar_radiation"
WIND_DIR = "sensor.wind_direction"


def run(coro):
    return asyncio.run(coro)


def schema_marker(data_schema, key):
    """Find the vol marker for a config key in a recorded schema."""
    return next(marker for marker in data_schema.schema if marker.schema == key)


def make_options_flow(data=None, options=None, entry_id="test_entry"):
    entry = ConfigEntry(entry_id=entry_id, data=data or {}, options=options or {})
    return WeatherSenseOptionsFlow(entry), entry


class FakeRegistryEntry:
    def __init__(self, entity_id, config_entry_id, options=None):
        self.entity_id = entity_id
        self.config_entry_id = config_entry_id
        self.options = options or {}


# ---------------------------------------------------------------------------
# WeatherSenseConfigFlow.async_step_user
# ---------------------------------------------------------------------------


class TestConfigFlowUserStep:
    """Initial setup: validation errors and entry creation."""

    def test_valid_input_creates_entry_with_name_as_title(self):
        flow = WeatherSenseConfigFlow()
        user_input = {
            "name": "Backyard",
            CONF_TEMPERATURE_SENSOR: TEMP,
            CONF_HUMIDITY_SENSOR: HUM,
        }

        result = run(flow.async_step_user(user_input))

        assert result["type"] == "create_entry"
        assert result["title"] == "Backyard"
        assert result["data"] is user_input

    def test_valid_input_without_name_uses_default_title(self):
        flow = WeatherSenseConfigFlow()

        result = run(flow.async_step_user({
            CONF_TEMPERATURE_SENSOR: TEMP,
            CONF_HUMIDITY_SENSOR: HUM,
        }))

        assert result["type"] == "create_entry"
        assert result["title"] == DEFAULT_NAME

    def test_missing_temperature_shows_form_with_error(self):
        flow = WeatherSenseConfigFlow()

        result = run(flow.async_step_user({CONF_HUMIDITY_SENSOR: HUM}))

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert result["errors"] == {CONF_TEMPERATURE_SENSOR: "temperature_required"}
        assert flow.__dict__.get("created_entries") is None

    def test_missing_humidity_shows_form_with_error(self):
        flow = WeatherSenseConfigFlow()

        result = run(flow.async_step_user({CONF_TEMPERATURE_SENSOR: TEMP}))

        assert result["type"] == "form"
        assert result["errors"] == {CONF_HUMIDITY_SENSOR: "humidity_required"}

    def test_missing_both_reports_both_errors(self):
        flow = WeatherSenseConfigFlow()

        result = run(flow.async_step_user({"name": "X"}))

        assert result["errors"] == {
            CONF_TEMPERATURE_SENSOR: "temperature_required",
            CONF_HUMIDITY_SENSOR: "humidity_required",
        }

    def test_empty_string_sensor_is_rejected(self):
        flow = WeatherSenseConfigFlow()

        result = run(flow.async_step_user({
            CONF_TEMPERATURE_SENSOR: "",
            CONF_HUMIDITY_SENSOR: HUM,
        }))

        assert result["errors"] == {CONF_TEMPERATURE_SENSOR: "temperature_required"}

    def test_no_input_shows_form_without_errors(self):
        flow = WeatherSenseConfigFlow()

        result = run(flow.async_step_user(None))

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    def test_user_form_schema_fields(self):
        flow = WeatherSenseConfigFlow()

        result = run(flow.async_step_user(None))

        schema = result["data_schema"].schema
        name_marker = schema_marker(result["data_schema"], "name")
        assert isinstance(name_marker, vol.Required)
        assert name_marker.default == DEFAULT_NAME
        assert isinstance(schema_marker(result["data_schema"], CONF_TEMPERATURE_SENSOR), vol.Required)
        assert isinstance(schema_marker(result["data_schema"], CONF_HUMIDITY_SENSOR), vol.Required)
        for optional_key in (
            CONF_WIND_SPEED_SENSOR, CONF_PRESSURE_SENSOR, CONF_SOLAR_RADIATION_SENSOR,
            CONF_WIND_DIRECTION_SENSOR, CONF_WIND_DIRECTION_CORRECTION,
            CONF_SMOOTHING_ENABLED, CONF_SMOOTHING_FACTOR, CONF_IS_OUTDOOR,
            CONF_DISPLAY_UNIT,
        ):
            assert isinstance(schema_marker(result["data_schema"], optional_key), vol.Optional)
        assert len(schema) == 12


# ---------------------------------------------------------------------------
# WeatherSenseOptionsFlow — entry reference (HA 2024.11 regression)
# ---------------------------------------------------------------------------


class TestOptionsFlowEntryReference:
    """Regression: OptionsFlow.config_entry only exists since HA 2024.12;
    on 2024.11 any self.config_entry access raises AttributeError. The flow
    must keep its own reference in self._entry."""

    def test_init_stores_entry_as_private_attribute(self):
        flow, entry = make_options_flow()

        assert flow._entry is entry
        assert "config_entry" not in vars(flow)

    def test_async_get_options_flow_returns_wired_flow(self):
        entry = ConfigEntry(entry_id="abc")

        flow = WeatherSenseConfigFlow.async_get_options_flow(entry)

        assert isinstance(flow, WeatherSenseOptionsFlow)
        assert flow._entry is entry

    def test_both_steps_run_without_config_entry_property(self):
        # The conftest OptionsFlow base deliberately has no config_entry
        # attribute (mirrors HA 2024.11), so touching self.config_entry in
        # either path would raise AttributeError here.
        flow, _ = make_options_flow(data={CONF_TEMPERATURE_SENSOR: TEMP,
                                          CONF_HUMIDITY_SENSOR: HUM})

        form = run(flow.async_step_init(None))
        submit = run(flow.async_step_init({CONF_TEMPERATURE_SENSOR: TEMP,
                                           CONF_HUMIDITY_SENSOR: HUM}))

        assert form["type"] == "form"
        assert submit["type"] == "create_entry"


# ---------------------------------------------------------------------------
# WeatherSenseOptionsFlow — submit normalization (_CLEARABLE_FIELDS)
# ---------------------------------------------------------------------------


class TestOptionsFlowSubmit:
    """Cleared optional fields must be written back as explicit None, or the
    {**data, **options} merge in async_setup_entry resurrects the old value."""

    def test_cleared_fields_written_back_as_none(self):
        flow, _ = make_options_flow(data={
            CONF_TEMPERATURE_SENSOR: TEMP,
            CONF_HUMIDITY_SENSOR: HUM,
            CONF_WIND_SPEED_SENSOR: WIND,
            CONF_PRESSURE_SENSOR: PRESSURE,
            CONF_SOLAR_RADIATION_SENSOR: SOLAR,
            CONF_WIND_DIRECTION_SENSOR: WIND_DIR,
        })
        user_input = {
            CONF_TEMPERATURE_SENSOR: TEMP,
            CONF_HUMIDITY_SENSOR: HUM,
            CONF_IS_OUTDOOR: True,
        }

        result = run(flow.async_step_init(user_input))

        assert result["type"] == "create_entry"
        assert result["title"] == ""
        data = result["data"]
        assert data[CONF_WIND_SPEED_SENSOR] is None
        assert data[CONF_PRESSURE_SENSOR] is None
        assert data[CONF_SOLAR_RADIATION_SENSOR] is None
        assert data[CONF_WIND_DIRECTION_SENSOR] is None
        assert data[CONF_DISPLAY_UNIT] is None
        assert data[CONF_TEMPERATURE_SENSOR] == TEMP
        assert data[CONF_IS_OUTDOOR] is True

    def test_provided_fields_are_not_overwritten(self):
        flow, _ = make_options_flow(data={
            CONF_TEMPERATURE_SENSOR: TEMP,
            CONF_HUMIDITY_SENSOR: HUM,
        })
        user_input = {
            CONF_TEMPERATURE_SENSOR: TEMP,
            CONF_HUMIDITY_SENSOR: HUM,
            CONF_WIND_SPEED_SENSOR: "sensor.new_wind",
            CONF_DISPLAY_UNIT: "°F",
        }

        result = run(flow.async_step_init(user_input))

        assert result["data"][CONF_WIND_SPEED_SENSOR] == "sensor.new_wind"
        assert result["data"][CONF_DISPLAY_UNIT] == "°F"


# ---------------------------------------------------------------------------
# WeatherSenseOptionsFlow — display unit transitions
# ---------------------------------------------------------------------------


class TestDisplayUnitTransitions:
    """_clear_unit_override runs only on the set -> cleared transition."""

    BASE = {CONF_TEMPERATURE_SENSOR: TEMP, CONF_HUMIDITY_SENSOR: HUM}

    def submit(self, flow, display_unit):
        user_input = dict(self.BASE)
        if display_unit is not None:
            user_input[CONF_DISPLAY_UNIT] = display_unit
        calls = []
        flow._clear_unit_override = lambda: calls.append(True)
        run(flow.async_step_init(user_input))
        return calls

    def test_set_to_cleared_clears_the_override(self):
        flow, _ = make_options_flow(data={**self.BASE, CONF_DISPLAY_UNIT: "°C"})

        assert self.submit(flow, None) == [True]

    def test_set_in_options_to_cleared_clears_the_override(self):
        # The current unit may live in entry.options rather than entry.data.
        flow, _ = make_options_flow(data=self.BASE,
                                    options={CONF_DISPLAY_UNIT: "°F"})

        assert self.submit(flow, None) == [True]

    def test_set_to_set_does_not_clear(self):
        flow, _ = make_options_flow(data={**self.BASE, CONF_DISPLAY_UNIT: "°C"})

        assert self.submit(flow, "°F") == []

    def test_none_to_set_does_not_clear(self):
        flow, _ = make_options_flow(data=self.BASE)

        assert self.submit(flow, "°C") == []

    def test_none_to_none_does_not_clear(self):
        flow, _ = make_options_flow(data=self.BASE)

        assert self.submit(flow, None) == []


# ---------------------------------------------------------------------------
# WeatherSenseOptionsFlow._clear_unit_override
# ---------------------------------------------------------------------------


class TestClearUnitOverride:
    """Dropping the registry unit override keeps the other sensor options."""

    def make_registry(self, monkeypatch, entries):
        registry = FakeEntityRegistry()
        registry.entries = entries
        seen_hass = []

        def fake_async_get(hass):
            seen_hass.append(hass)
            return registry

        monkeypatch.setattr("weathersense.config_flow.er.async_get", fake_async_get)
        return registry, seen_hass

    def test_removes_unit_but_preserves_other_options(self, monkeypatch):
        flow, _ = make_options_flow(entry_id="entry_1")
        flow.hass = object()
        registry, seen_hass = self.make_registry(monkeypatch, [
            FakeRegistryEntry(
                "sensor.feels_like", "entry_1",
                options={"sensor": {"unit_of_measurement": "°F",
                                    "display_precision": 1}},
            ),
        ])

        flow._clear_unit_override()

        assert registry.updated_options == [
            ("sensor.feels_like", "sensor", {"display_precision": 1}),
        ]
        assert seen_hass == [flow.hass]

    def test_entry_without_override_is_left_alone(self, monkeypatch):
        flow, _ = make_options_flow(entry_id="entry_1")
        flow.hass = object()
        registry, _ = self.make_registry(monkeypatch, [
            FakeRegistryEntry(
                "sensor.feels_like", "entry_1",
                options={"sensor": {"display_precision": 2}},
            ),
        ])

        flow._clear_unit_override()

        assert registry.updated_options == []

    def test_other_config_entries_are_not_touched(self, monkeypatch):
        flow, _ = make_options_flow(entry_id="entry_1")
        flow.hass = object()
        registry, _ = self.make_registry(monkeypatch, [
            FakeRegistryEntry(
                "sensor.other_integration", "entry_2",
                options={"sensor": {"unit_of_measurement": "°F"}},
            ),
        ])

        flow._clear_unit_override()

        assert registry.updated_options == []

    def test_entry_with_no_sensor_options_is_left_alone(self, monkeypatch):
        flow, _ = make_options_flow(entry_id="entry_1")
        flow.hass = object()
        registry, _ = self.make_registry(monkeypatch, [
            FakeRegistryEntry("sensor.feels_like", "entry_1", options={}),
        ])

        flow._clear_unit_override()

        assert registry.updated_options == []


# ---------------------------------------------------------------------------
# WeatherSenseOptionsFlow — form build
# ---------------------------------------------------------------------------


class TestOptionsForm:
    """The options form pre-fills clearable fields via suggested_value so the
    user can clear them, and uses default= for the always-present fields."""

    def test_form_result_shape(self):
        flow, _ = make_options_flow(data={CONF_TEMPERATURE_SENSOR: TEMP,
                                          CONF_HUMIDITY_SENSOR: HUM})

        result = run(flow.async_step_init(None))

        assert result["type"] == "form"
        assert result["step_id"] == "init"
        assert isinstance(result["data_schema"], vol.Schema)

    def test_suggested_values_for_set_and_unset_clearable_fields(self):
        flow, _ = make_options_flow(data={
            CONF_TEMPERATURE_SENSOR: TEMP,
            CONF_HUMIDITY_SENSOR: HUM,
            CONF_WIND_SPEED_SENSOR: WIND,
            CONF_DISPLAY_UNIT: "°C",
        })

        result = run(flow.async_step_init(None))

        schema = result["data_schema"]
        assert schema_marker(schema, CONF_WIND_SPEED_SENSOR).description == {
            "suggested_value": WIND,
        }
        assert schema_marker(schema, CONF_DISPLAY_UNIT).description == {
            "suggested_value": "°C",
        }
        # Unset clearable fields get no suggestion at all.
        assert schema_marker(schema, CONF_PRESSURE_SENSOR).description is None
        assert schema_marker(schema, CONF_SOLAR_RADIATION_SENSOR).description is None
        assert schema_marker(schema, CONF_WIND_DIRECTION_SENSOR).description is None

    def test_required_and_defaulted_fields_use_current_config(self):
        flow, _ = make_options_flow(data={
            CONF_TEMPERATURE_SENSOR: TEMP,
            CONF_HUMIDITY_SENSOR: HUM,
            CONF_SMOOTHING_FACTOR: 0.5,
            CONF_IS_OUTDOOR: False,
        })

        result = run(flow.async_step_init(None))

        schema = result["data_schema"]
        temp_marker = schema_marker(schema, CONF_TEMPERATURE_SENSOR)
        assert isinstance(temp_marker, vol.Required)
        assert temp_marker.default == TEMP
        assert schema_marker(schema, CONF_HUMIDITY_SENSOR).default == HUM
        assert schema_marker(schema, CONF_SMOOTHING_FACTOR).default == 0.5
        assert schema_marker(schema, CONF_IS_OUTDOOR).default is False
        assert schema_marker(schema, CONF_SMOOTHING_ENABLED).default is False

    def test_smoothing_factor_falls_back_to_default(self):
        flow, _ = make_options_flow(data={CONF_TEMPERATURE_SENSOR: TEMP,
                                          CONF_HUMIDITY_SENSOR: HUM})

        result = run(flow.async_step_init(None))

        marker = schema_marker(result["data_schema"], CONF_SMOOTHING_FACTOR)
        assert marker.default == DEFAULT_SMOOTHING_FACTOR

    def test_options_override_data_in_prefill(self):
        flow, _ = make_options_flow(
            data={CONF_TEMPERATURE_SENSOR: TEMP,
                  CONF_HUMIDITY_SENSOR: HUM,
                  CONF_WIND_SPEED_SENSOR: "sensor.wind_old"},
            options={CONF_WIND_SPEED_SENSOR: "sensor.wind_new"},
        )

        result = run(flow.async_step_init(None))

        marker = schema_marker(result["data_schema"], CONF_WIND_SPEED_SENSOR)
        assert marker.description == {"suggested_value": "sensor.wind_new"}

    def test_cleared_field_stored_as_none_gets_no_suggestion(self):
        # After a previous clear, options hold an explicit None; the form must
        # treat it as unset, not suggest None back.
        flow, _ = make_options_flow(
            data={CONF_TEMPERATURE_SENSOR: TEMP,
                  CONF_HUMIDITY_SENSOR: HUM,
                  CONF_WIND_SPEED_SENSOR: WIND},
            options={CONF_WIND_SPEED_SENSOR: None},
        )

        result = run(flow.async_step_init(None))

        marker = schema_marker(result["data_schema"], CONF_WIND_SPEED_SENSOR)
        assert marker.description is None
