"""Mock homeassistant modules so the weathersense package can be imported in tests."""

import sys
from types import ModuleType
from unittest.mock import MagicMock


def _create_mock_module(name: str) -> ModuleType:
    mod = ModuleType(name)
    mod.__dict__.update({k: MagicMock() for k in ["__all__"]})
    return mod


# List of homeassistant submodules that are imported by the integration
_HA_MODULES = [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.sensor",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.data_entry_flow",
    "homeassistant.helpers",
    "homeassistant.helpers.config_validation",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.event",
    "homeassistant.helpers.selector",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.util",
    "homeassistant.util.dt",
    "voluptuous",
]

for mod_name in _HA_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()
