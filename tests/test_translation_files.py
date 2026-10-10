"""All translation files must expose identical key structures.

Regression (Devin Review): config_flow sets ``errors["base"] = "same_sensor"``
in the options step, which resolves ``options.error.same_sensor`` — a key that
only existed under ``config.error``. Missing keys render as raw identifiers,
so every locale must carry the same flattened key set.
"""

import json
import glob
import os

TRANSLATIONS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "custom_components", "weathersense", "translations"
)


def _flatten(d, prefix=""):
    keys = set()
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys |= _flatten(v, path)
        else:
            keys.add(path)
    return keys


def _load_all():
    files = sorted(glob.glob(os.path.join(TRANSLATIONS_DIR, "*.json")))
    return {os.path.basename(f): _flatten(json.load(open(f))) for f in files}


def test_all_locales_cover_every_language_in_integration():
    locales = _load_all()
    assert len(locales) == 7


def test_all_translation_files_have_identical_keys():
    locales = _load_all()
    reference = locales["en.json"]
    for name, keys in locales.items():
        assert keys == reference, (
            f"{name} differs from en.json: "
            f"missing={sorted(reference - keys)} extra={sorted(keys - reference)}"
        )


def test_error_keys_exist_for_config_and_options():
    """same_sensor is raised in both the user step (config.error) and the
    options step (options.error); both paths must resolve."""
    en = json.load(open(os.path.join(TRANSLATIONS_DIR, "en.json")))
    assert "same_sensor" in en["config"]["error"]
    assert "same_sensor" in en["options"]["error"]
