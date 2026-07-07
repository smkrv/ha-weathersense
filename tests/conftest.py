"""Lightweight homeassistant stubs so weathersense modules import and run in tests.

The stubs are real classes/functions (not MagicMock): subclassing a MagicMock
SensorEntity would discard the WeatherSenseSensor class body entirely, making
sensor.py untestable. Unit constants carry the real HA string values so the
conversion branches in sensor.py match against realistic state attributes.
"""

import sys
from datetime import datetime
from types import ModuleType
from unittest.mock import MagicMock

# Fixed "now" for deterministic solar correction (noon, 21 Jun 2024).
FIXED_NOW = datetime(2024, 6, 21, 12, 0, 0)


def _install(name: str) -> ModuleType:
    mod = ModuleType(name)
    sys.modules[name] = mod
    return mod


# --- homeassistant package skeleton -----------------------------------------

ha = _install("homeassistant")
components = _install("homeassistant.components")
sensor_mod = _install("homeassistant.components.sensor")
config_entries_mod = _install("homeassistant.config_entries")
const_mod = _install("homeassistant.const")
core_mod = _install("homeassistant.core")
data_entry_flow_mod = _install("homeassistant.data_entry_flow")
helpers_mod = _install("homeassistant.helpers")
entity_mod = _install("homeassistant.helpers.entity")
entity_platform_mod = _install("homeassistant.helpers.entity_platform")
entity_registry_mod = _install("homeassistant.helpers.entity_registry")
event_mod = _install("homeassistant.helpers.event")
util_mod = _install("homeassistant.util")
dt_mod = _install("homeassistant.util.dt")

# Modules only touched by config_flow.py; MagicMock is fine there because
# nothing subclasses from them in the code under test.
sys.modules["homeassistant.helpers.config_validation"] = MagicMock()
sys.modules["homeassistant.helpers.selector"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"] = MagicMock()


# --- voluptuous (real stub: schemas built in config_flow must be introspectable)


class _VolMarker:
    """vol.Marker stand-in: keeps schema/default/description readable and is
    hashable by the wrapped key so it can be used as a dict key like the real
    thing."""

    def __init__(self, schema, msg=None, default=None, description=None):
        self.schema = schema
        self.msg = msg
        self.default = default
        self.description = description

    def __hash__(self):
        return hash(self.schema)

    def __eq__(self, other):
        return self.schema == getattr(other, "schema", other)

    def __repr__(self):
        return f"{type(self).__name__}({self.schema!r})"


class _VolRequired(_VolMarker):
    pass


class _VolOptional(_VolMarker):
    pass


class _VolSchema:
    def __init__(self, schema, extra=None):
        self.schema = schema
        self.extra = extra


vol_mod = _install("voluptuous")
vol_mod.Marker = _VolMarker
vol_mod.Required = _VolRequired
vol_mod.Optional = _VolOptional
vol_mod.Schema = _VolSchema

ha.components = components
ha.config_entries = config_entries_mod
ha.const = const_mod
ha.core = core_mod
ha.data_entry_flow = data_entry_flow_mod
ha.helpers = helpers_mod
ha.util = util_mod
components.sensor = sensor_mod
helpers_mod.config_validation = sys.modules["homeassistant.helpers.config_validation"]
helpers_mod.entity = entity_mod
helpers_mod.entity_platform = entity_platform_mod
helpers_mod.entity_registry = entity_registry_mod
helpers_mod.event = event_mod
helpers_mod.selector = sys.modules["homeassistant.helpers.selector"]
helpers_mod.update_coordinator = sys.modules["homeassistant.helpers.update_coordinator"]
util_mod.dt = dt_mod


# --- homeassistant.components.sensor -----------------------------------------


class SensorEntity:
    """Minimal Entity/SensorEntity stand-in.

    WeatherSenseSensor never calls super().__init__(), so everything here is
    a class attribute or created lazily. async_write_ha_state records calls
    in write_ha_state_calls so tests can assert state writes happened.
    """

    _attr_available = True
    entity_id = None
    hass = None

    def async_write_ha_state(self) -> None:
        self.__dict__.setdefault("write_ha_state_calls", []).append(True)

    def async_on_remove(self, func) -> None:
        self.__dict__.setdefault("on_remove_callbacks", []).append(func)


class SensorDeviceClass:
    TEMPERATURE = "temperature"


class SensorStateClass:
    MEASUREMENT = "measurement"


sensor_mod.SensorEntity = SensorEntity
sensor_mod.SensorDeviceClass = SensorDeviceClass
sensor_mod.SensorStateClass = SensorStateClass


# --- homeassistant.config_entries --------------------------------------------


class ConfigEntry:
    def __init__(self, entry_id="test_entry", data=None, options=None):
        self.entry_id = entry_id
        self.data = data or {}
        self.options = options or {}


class _FlowHandler:
    """Shared FlowHandler helpers: return FlowResult dicts like real HA and
    record every call so tests can assert on flow outcomes."""

    def async_create_entry(self, *, title=None, data=None, **kwargs):
        result = {"type": "create_entry", "title": title, "data": data, **kwargs}
        self.__dict__.setdefault("created_entries", []).append(result)
        return result

    def async_show_form(self, *, step_id=None, data_schema=None, errors=None, **kwargs):
        result = {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors,
            **kwargs,
        }
        self.__dict__.setdefault("shown_forms", []).append(result)
        return result


class ConfigFlow(_FlowHandler):
    def __init_subclass__(cls, **kwargs):
        pass


class OptionsFlow(_FlowHandler):
    # Deliberately NO config_entry attribute: it only exists on the real base
    # class since HA 2024.12, and the integration must run on 2024.11.
    pass


config_entries_mod.ConfigEntry = ConfigEntry
config_entries_mod.ConfigFlow = ConfigFlow
config_entries_mod.OptionsFlow = OptionsFlow


# --- homeassistant.const (real HA string values) ------------------------------

const_mod.ATTR_UNIT_OF_MEASUREMENT = "unit_of_measurement"


class Platform:
    SENSOR = "sensor"


class UnitOfTemperature:
    CELSIUS = "°C"
    FAHRENHEIT = "°F"
    KELVIN = "K"


class UnitOfSpeed:
    BEAUFORT = "Beaufort"
    FEET_PER_SECOND = "ft/s"
    KILOMETERS_PER_HOUR = "km/h"
    KNOTS = "kn"
    METERS_PER_SECOND = "m/s"
    MILES_PER_HOUR = "mph"


class UnitOfPressure:
    PA = "Pa"
    HPA = "hPa"
    KPA = "kPa"
    BAR = "bar"
    CBAR = "cbar"
    MBAR = "mbar"
    MMHG = "mmHg"
    INHG = "inHg"
    PSI = "psi"


const_mod.Platform = Platform
const_mod.UnitOfTemperature = UnitOfTemperature
const_mod.UnitOfSpeed = UnitOfSpeed
const_mod.UnitOfPressure = UnitOfPressure


# --- homeassistant.core -------------------------------------------------------


class HomeAssistant:
    pass


def callback(func):
    return func


core_mod.HomeAssistant = HomeAssistant
core_mod.callback = callback


# --- homeassistant.data_entry_flow --------------------------------------------

data_entry_flow_mod.FlowResult = dict


# --- homeassistant.helpers.* ---------------------------------------------------

entity_mod.DeviceInfo = dict
entity_platform_mod.AddEntitiesCallback = object


class FakeEntityRegistry:
    """Registry stub: no entries registered by default."""

    def __init__(self):
        self.updated_options = []
        self.entries = []

    def async_get(self, entity_id):
        return None

    def async_update_entity_options(self, entity_id, domain, options):
        self.updated_options.append((entity_id, domain, options))


def _registry_async_get(hass):
    return FakeEntityRegistry()


def async_entries_for_config_entry(registry, config_entry_id):
    return [
        entry
        for entry in getattr(registry, "entries", [])
        if getattr(entry, "config_entry_id", None) == config_entry_id
    ]


entity_registry_mod.FakeEntityRegistry = FakeEntityRegistry
entity_registry_mod.async_get = _registry_async_get
entity_registry_mod.async_entries_for_config_entry = async_entries_for_config_entry


def async_track_state_change_event(hass, entity_ids, action):
    return lambda: None


event_mod.async_track_state_change_event = async_track_state_change_event


# --- homeassistant.util.dt ------------------------------------------------------


def now():
    return FIXED_NOW


dt_mod.FIXED_NOW = FIXED_NOW
dt_mod.now = now
