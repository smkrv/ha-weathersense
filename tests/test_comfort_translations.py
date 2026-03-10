"""Tests for comfort_translations.py — localized descriptions and methods."""

import pytest

from weathersense.comfort_translations import (
    COMFORT_DESCRIPTIONS_I18N,
    COMFORT_EXPLANATIONS_I18N,
    CALCULATION_METHOD_I18N,
    get_comfort_description,
    get_comfort_explanation,
    get_calculation_method,
)
from weathersense.const import (
    COMFORT_EXTREME_COLD, COMFORT_VERY_COLD, COMFORT_COLD,
    COMFORT_COOL, COMFORT_SLIGHTLY_COOL, COMFORT_COMFORTABLE,
    COMFORT_SLIGHTLY_WARM, COMFORT_WARM, COMFORT_HOT,
    COMFORT_VERY_HOT, COMFORT_EXTREME_HOT,
)

ALL_COMFORT_LEVELS = [
    COMFORT_EXTREME_COLD, COMFORT_VERY_COLD, COMFORT_COLD,
    COMFORT_COOL, COMFORT_SLIGHTLY_COOL, COMFORT_COMFORTABLE,
    COMFORT_SLIGHTLY_WARM, COMFORT_WARM, COMFORT_HOT,
    COMFORT_VERY_HOT, COMFORT_EXTREME_HOT,
]

ALL_METHODS = [
    "Heat Index", "Wind Chill",
    "Steadman Apparent Temperature", "Indoor Comfort Model",
]

SUPPORTED_LANGUAGES = ["en", "ru", "de", "es", "hi", "zh-CN", "cs"]


class TestComfortDescriptions:
    """All languages must have all comfort levels translated."""

    @pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
    def test_all_levels_present(self, lang):
        descs = COMFORT_DESCRIPTIONS_I18N[lang]
        for level in ALL_COMFORT_LEVELS:
            assert level in descs, f"Missing {level} in {lang} descriptions"
            assert descs[level], f"Empty {level} in {lang} descriptions"

    @pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
    def test_explanations_all_levels_present(self, lang):
        expls = COMFORT_EXPLANATIONS_I18N[lang]
        for level in ALL_COMFORT_LEVELS:
            assert level in expls, f"Missing {level} in {lang} explanations"
            assert expls[level], f"Empty {level} in {lang} explanations"


class TestCalculationMethodTranslations:
    """All languages must have all methods translated."""

    @pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
    def test_all_methods_present(self, lang):
        methods = CALCULATION_METHOD_I18N[lang]
        for method in ALL_METHODS:
            assert method in methods, f"Missing '{method}' in {lang}"
            assert methods[method], f"Empty '{method}' in {lang}"


class TestGetFunctions:
    """Test helper functions with fallback behavior."""

    def test_english_fallback(self):
        """Unknown language falls back to English."""
        desc = get_comfort_description(COMFORT_COMFORTABLE, "xx")
        assert desc == "No Thermal Stress (Comfort)"

    def test_russian(self):
        desc = get_comfort_description(COMFORT_COMFORTABLE, "ru")
        assert "комфорт" in desc.lower()

    def test_czech(self):
        desc = get_comfort_description(COMFORT_COMFORTABLE, "cs")
        assert "komfort" in desc.lower()

    def test_explanation_fallback(self):
        expl = get_comfort_explanation(COMFORT_HOT, "unknown")
        assert "heat exhaustion" in expl.lower()

    def test_method_translation(self):
        method = get_calculation_method("Heat Index", "ru")
        assert method == "Индекс жары"

    def test_method_fallback(self):
        method = get_calculation_method("Heat Index", "unknown_lang")
        assert method == "Heat Index"

    def test_method_unknown_method_returns_original(self):
        method = get_calculation_method("Unknown Method", "en")
        assert method == "Unknown Method"

    def test_language_normalization(self):
        """zh_CN should match zh-CN."""
        desc = get_comfort_description(COMFORT_COMFORTABLE, "zh_CN")
        assert desc  # Should not be empty (found zh-CN)

    @pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
    def test_descriptions_differ_from_english(self, lang):
        """Non-English languages should have different descriptions."""
        if lang == "en":
            return
        en_desc = get_comfort_description(COMFORT_COMFORTABLE, "en")
        lang_desc = get_comfort_description(COMFORT_COMFORTABLE, lang)
        assert lang_desc != en_desc, f"{lang} description should differ from English"
