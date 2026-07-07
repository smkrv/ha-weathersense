"""Tests for __init__.py — config entry lifecycle.

Covers async_setup_entry (config merge, platform forwarding, update listener
registration), async_unload_entry (hass.data cleanup on success, retention on
failure), and update_listener (entry reload on options change).
"""

import asyncio

from weathersense import (
    PLATFORMS,
    async_setup_entry,
    async_unload_entry,
    update_listener,
)
from weathersense.const import DOMAIN


class FakeConfigEntries:
    def __init__(self, unload_ok=True):
        self.forwarded = []
        self.unloaded = []
        self.reloaded = []
        self._unload_ok = unload_ok

    async def async_forward_entry_setups(self, entry, platforms):
        self.forwarded.append((entry, platforms))

    async def async_unload_platforms(self, entry, platforms):
        self.unloaded.append((entry, platforms))
        return self._unload_ok

    async def async_reload(self, entry_id):
        self.reloaded.append(entry_id)


class FakeHass:
    def __init__(self, unload_ok=True):
        self.data = {}
        self.config_entries = FakeConfigEntries(unload_ok)


class FakeConfigEntry:
    def __init__(self, entry_id="test_entry", data=None, options=None):
        self.entry_id = entry_id
        self.data = data or {}
        self.options = options or {}
        self.update_listeners = []
        self.on_unload_callbacks = []
        self._remove_listener = lambda: None

    def add_update_listener(self, listener):
        self.update_listeners.append(listener)
        return self._remove_listener

    def async_on_unload(self, func):
        self.on_unload_callbacks.append(func)


class TestAsyncSetupEntry:
    """async_setup_entry wires the entry into hass.data and the sensor platform."""

    def test_returns_true(self):
        hass = FakeHass()
        entry = FakeConfigEntry()

        assert asyncio.run(async_setup_entry(hass, entry)) is True

    def test_stores_merged_data_and_options_in_hass_data(self):
        hass = FakeHass()
        entry = FakeConfigEntry(
            entry_id="abc123",
            data={"temperature_sensor": "sensor.t_old", "humidity_sensor": "sensor.h"},
            options={"temperature_sensor": "sensor.t_new", "smoothing_enabled": True},
        )

        asyncio.run(async_setup_entry(hass, entry))

        # Options override data on key collision.
        assert hass.data[DOMAIN]["abc123"] == {
            "temperature_sensor": "sensor.t_new",
            "humidity_sensor": "sensor.h",
            "smoothing_enabled": True,
        }

    def test_preserves_other_entries_in_domain_data(self):
        hass = FakeHass()
        hass.data[DOMAIN] = {"other_entry": {"kept": True}}
        entry = FakeConfigEntry(entry_id="new_entry")

        asyncio.run(async_setup_entry(hass, entry))

        assert hass.data[DOMAIN]["other_entry"] == {"kept": True}
        assert "new_entry" in hass.data[DOMAIN]

    def test_forwards_to_sensor_platform(self):
        hass = FakeHass()
        entry = FakeConfigEntry()

        asyncio.run(async_setup_entry(hass, entry))

        assert hass.config_entries.forwarded == [(entry, PLATFORMS)]
        assert PLATFORMS == ["sensor"]

    def test_registers_update_listener_and_its_unsubscribe(self):
        hass = FakeHass()
        entry = FakeConfigEntry()

        asyncio.run(async_setup_entry(hass, entry))

        assert entry.update_listeners == [update_listener]
        # The remove-callable from add_update_listener must be handed to
        # async_on_unload, or the listener leaks across reloads.
        assert entry.on_unload_callbacks == [entry._remove_listener]


class TestAsyncUnloadEntry:
    """async_unload_entry pops hass.data only when the platforms unloaded."""

    def test_success_pops_entry_data_and_returns_true(self):
        hass = FakeHass(unload_ok=True)
        entry = FakeConfigEntry(entry_id="abc123")
        hass.data[DOMAIN] = {"abc123": {"some": "config"}, "other": {}}

        result = asyncio.run(async_unload_entry(hass, entry))

        assert result is True
        assert "abc123" not in hass.data[DOMAIN]
        assert "other" in hass.data[DOMAIN]
        assert hass.config_entries.unloaded == [(entry, PLATFORMS)]

    def test_failure_keeps_entry_data_and_returns_false(self):
        hass = FakeHass(unload_ok=False)
        entry = FakeConfigEntry(entry_id="abc123")
        hass.data[DOMAIN] = {"abc123": {"some": "config"}}

        result = asyncio.run(async_unload_entry(hass, entry))

        assert result is False
        assert hass.data[DOMAIN]["abc123"] == {"some": "config"}


class TestUpdateListener:
    """update_listener reloads the entry so new options take effect."""

    def test_reloads_the_entry(self):
        hass = FakeHass()
        entry = FakeConfigEntry(entry_id="abc123")

        asyncio.run(update_listener(hass, entry))

        assert hass.config_entries.reloaded == ["abc123"]
