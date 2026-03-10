"""Tests for weather_calculator.py — core calculation logic."""

import math
from datetime import datetime

import pytest

from weathersense.weather_calculator import (
    STANDARD_PRESSURE,
    apply_pressure_correction,
    apply_solar_correction,
    apply_wind_direction_correction,
    calculate_feels_like,
    calculate_heat_index,
    calculate_indoor_feels_like,
    calculate_steadman_apparent_temp,
    calculate_wind_chill,
    determine_indoor_comfort,
    determine_outdoor_comfort,
)


# ---------------------------------------------------------------------------
# calculate_heat_index
# ---------------------------------------------------------------------------


class TestCalculateHeatIndex:
    """Tests for Heat Index (Rothfusz / NWS)."""

    def test_hot_humid_uses_rothfusz(self):
        """35°C / 80% → should use full Rothfusz and be hotter than air temp."""
        hi = calculate_heat_index(35, 80)
        assert hi > 35, "Heat index should exceed actual temp at high humidity"

    def test_moderate_conditions_simple_formula(self):
        """27°C / 30% → rh < 40 triggers simple formula branch."""
        hi = calculate_heat_index(27, 30)
        # Result should be close to actual temperature
        assert 20 < hi < 40

    def test_returns_float(self):
        assert isinstance(calculate_heat_index(30, 50), float)

    def test_sanity_cap_at_70(self):
        """Extremely high HI should be capped to temp + 25."""
        hi = calculate_heat_index(50, 100)
        assert hi <= 50 + 25

    def test_low_humidity_high_temp_adjustment(self):
        """10% humidity, ~38°C (100°F): should apply the low-humidity adjustment."""
        hi = calculate_heat_index(38, 10)
        assert isinstance(hi, float)

    def test_high_humidity_moderate_temp_adjustment(self):
        """90% humidity, ~30°C (86°F): should apply high-humidity adjustment."""
        hi = calculate_heat_index(30, 90)
        assert hi > 30  # High humidity makes it feel hotter

    def test_known_reference_value(self):
        """NWS reference: 33°C (91.4°F) + 60% RH → HI ≈ 38°C (100°F)."""
        hi = calculate_heat_index(33, 60)
        assert 35 < hi < 45, f"Expected ~38°C, got {hi}"

    def test_extreme_heat(self):
        """50°C + 50% humidity — extreme but valid input."""
        hi = calculate_heat_index(50, 50)
        assert hi <= 75  # Sanity cap: temp + 25

    def test_zero_humidity(self):
        """0% humidity — dry heat, should still work."""
        hi = calculate_heat_index(35, 0)
        assert isinstance(hi, float)


# ---------------------------------------------------------------------------
# calculate_wind_chill
# ---------------------------------------------------------------------------


class TestCalculateWindChill:
    """Tests for Wind Chill (NWS/Environment Canada)."""

    def test_cold_windy(self):
        """-10°C + 5 m/s wind → should feel colder."""
        wct = calculate_wind_chill(-10, 5)
        assert wct < -10

    def test_calm_wind_uses_minimum(self):
        """Very low wind is clamped to 4.828 km/h minimum."""
        wct_calm = calculate_wind_chill(-10, 0)
        wct_min = calculate_wind_chill(-10, 1.34)  # 4.828 km/h ≈ 1.34 m/s
        assert abs(wct_calm - wct_min) < 0.5

    def test_returns_float(self):
        assert isinstance(calculate_wind_chill(0, 3), float)

    def test_known_reference(self):
        """-20°C + 30 km/h (8.33 m/s) → WCT ≈ -33°C (NWS chart)."""
        wct = calculate_wind_chill(-20, 8.33)
        assert -40 < wct < -25, f"Expected ~-33°C, got {wct}"

    def test_zero_celsius(self):
        """0°C + moderate wind."""
        wct = calculate_wind_chill(0, 5)
        assert wct < 0

    def test_high_wind(self):
        """Extreme wind speed should increase chill further."""
        wct_low = calculate_wind_chill(-10, 5)
        wct_high = calculate_wind_chill(-10, 20)
        assert wct_high < wct_low


# ---------------------------------------------------------------------------
# calculate_steadman_apparent_temp
# ---------------------------------------------------------------------------


class TestCalculateSteadmanApparentTemp:
    """Tests for Steadman Apparent Temperature."""

    def test_moderate_conditions(self):
        """20°C, 50% RH, 2 m/s wind — typical moderate weather."""
        at = calculate_steadman_apparent_temp(20, 50, 2)
        assert 10 < at < 30

    def test_wind_cools(self):
        """Higher wind should lower apparent temperature."""
        at_calm = calculate_steadman_apparent_temp(20, 50, 0)
        at_windy = calculate_steadman_apparent_temp(20, 50, 10)
        assert at_windy < at_calm

    def test_humidity_warms(self):
        """Higher humidity should raise apparent temperature."""
        at_dry = calculate_steadman_apparent_temp(25, 20, 2)
        at_humid = calculate_steadman_apparent_temp(25, 90, 2)
        assert at_humid > at_dry

    def test_returns_float(self):
        assert isinstance(calculate_steadman_apparent_temp(15, 60, 3), float)


# ---------------------------------------------------------------------------
# apply_solar_correction
# ---------------------------------------------------------------------------


class TestApplySolarCorrection:
    """Tests for solar radiation correction."""

    def test_noon_increases_feels_like(self):
        """Solar noon should add the most heat."""
        noon = datetime(2024, 6, 21, 13, 0)
        corrected = apply_solar_correction(25.0, noon, cloudiness=0)
        assert corrected > 25.0

    def test_midnight_cooling(self):
        """Midnight should apply slight cooling."""
        midnight = datetime(2024, 6, 21, 0, 0)
        corrected = apply_solar_correction(25.0, midnight, cloudiness=0)
        assert corrected < 25.0

    def test_full_cloudiness_removes_solar_gain(self):
        """100% cloud cover → no solar warming during day."""
        noon = datetime(2024, 6, 21, 13, 0)
        corrected = apply_solar_correction(25.0, noon, cloudiness=100)
        assert corrected == pytest.approx(25.0, abs=0.01)

    def test_evening_hours_apply_nighttime_cooling(self):
        """Hours 19-21 should apply nighttime cooling (-0.5)."""
        for hour in (19, 20, 21):
            evening = datetime(2024, 6, 21, hour, 0)
            corrected = apply_solar_correction(25.0, evening, cloudiness=0)
            assert corrected < 25.0, f"Hour {hour} should apply nighttime cooling"

    def test_hour_5_gap(self):
        """Hour 5 is between nighttime (≤4) and daytime (≥6) → no correction."""
        predawn = datetime(2024, 6, 21, 5, 0)
        corrected = apply_solar_correction(25.0, predawn, cloudiness=0)
        assert corrected == 25.0

    def test_max_solar_correction_hot_day(self):
        """Hot day max correction should be ≤ 2.5°C."""
        noon = datetime(2024, 6, 21, 13, 0)
        correction = apply_solar_correction(30.0, noon, cloudiness=0) - 30.0
        assert correction <= 2.5

    def test_max_solar_correction_cold_day(self):
        """Cold day max correction should be ≤ 1.0°C."""
        noon = datetime(2024, 1, 15, 13, 0)
        correction = apply_solar_correction(0.0, noon, cloudiness=0) - 0.0
        assert correction <= 1.0

    def test_default_time_is_now(self):
        """When time_of_day is None, function should not crash."""
        result = apply_solar_correction(20.0)
        assert isinstance(result, float)

    @pytest.mark.parametrize("hour", range(7, 18))
    def test_all_daytime_hours_positive(self, hour):
        """Daytime hours 7-17 should add solar correction (clear sky).

        Hours 6 and 18 are boundary: sin(0)=0 and sin(π)=0, so correction is 0.
        """
        t = datetime(2024, 6, 21, hour, 0)
        correction = apply_solar_correction(20.0, t, cloudiness=0) - 20.0
        assert correction > 0

    def test_sunrise_sunset_boundary_zero(self):
        """At exactly hour 6 and 18 solar intensity is sin(0)=0 → no correction."""
        for hour in (6, 18):
            t = datetime(2024, 6, 21, hour, 0)
            corrected = apply_solar_correction(20.0, t, cloudiness=0)
            assert corrected == 20.0


# ---------------------------------------------------------------------------
# apply_pressure_correction
# ---------------------------------------------------------------------------


class TestApplyPressureCorrection:
    """Tests for atmospheric pressure correction."""

    def test_standard_pressure_no_change(self):
        """101.3 kPa → no correction."""
        result = apply_pressure_correction(20.0, STANDARD_PRESSURE)
        assert result == pytest.approx(20.0, abs=0.01)

    def test_low_pressure_increases_feels_like(self):
        """Pressure below standard → positive correction."""
        result = apply_pressure_correction(20.0, 95.0)
        assert result > 20.0

    def test_high_pressure_decreases_feels_like(self):
        """Pressure above standard → negative correction."""
        result = apply_pressure_correction(20.0, 105.0)
        assert result < 20.0

    def test_none_pressure_no_change(self):
        assert apply_pressure_correction(20.0, None) == 20.0

    def test_zero_pressure_no_change(self):
        assert apply_pressure_correction(20.0, 0) == 20.0

    def test_out_of_range_low_no_change(self):
        """Pressure < 80 kPa is rejected."""
        assert apply_pressure_correction(20.0, 70.0) == 20.0

    def test_out_of_range_high_no_change(self):
        """Pressure > 110 kPa is rejected."""
        assert apply_pressure_correction(20.0, 120.0) == 20.0


# ---------------------------------------------------------------------------
# apply_wind_direction_correction
# ---------------------------------------------------------------------------


class TestApplyWindDirectionCorrection:
    """Tests for experimental wind direction correction."""

    def test_north_wind_northern_hemisphere_cools(self):
        """North wind (0°) in Northern Hemisphere → should cool."""
        corrected, correction = apply_wind_direction_correction(20.0, 0, latitude=55.0)
        assert correction < 0
        assert corrected < 20.0

    def test_south_wind_northern_hemisphere_warms(self):
        """South wind (180°) in Northern Hemisphere → should warm."""
        corrected, correction = apply_wind_direction_correction(20.0, 180, latitude=55.0)
        assert correction > 0
        assert corrected > 20.0

    def test_north_wind_southern_hemisphere_warms(self):
        """North wind (0°) in Southern Hemisphere → should warm."""
        corrected, correction = apply_wind_direction_correction(20.0, 0, latitude=-30.0)
        assert correction > 0

    def test_east_west_minimal_correction(self):
        """East (90°) and West (270°) → minimal correction (cos ≈ 0)."""
        _, corr_e = apply_wind_direction_correction(20.0, 90, latitude=55.0)
        _, corr_w = apply_wind_direction_correction(20.0, 270, latitude=55.0)
        assert abs(corr_e) < 0.01
        assert abs(corr_w) < 0.01

    def test_none_direction_no_change(self):
        corrected, correction = apply_wind_direction_correction(20.0, None)
        assert corrected == 20.0
        assert correction == 0.0

    def test_max_correction_respected(self):
        _, correction = apply_wind_direction_correction(20.0, 0, latitude=55.0, max_correction=2.0)
        assert abs(correction) <= 2.0

    def test_default_hemisphere_is_northern(self):
        """latitude=None → default to Northern Hemisphere."""
        _, corr_default = apply_wind_direction_correction(20.0, 0, latitude=None)
        _, corr_north = apply_wind_direction_correction(20.0, 0, latitude=55.0)
        assert corr_default == pytest.approx(corr_north)

    def test_direction_wraps_360(self):
        """360° should behave same as 0°."""
        _, corr_360 = apply_wind_direction_correction(20.0, 360, latitude=55.0)
        _, corr_0 = apply_wind_direction_correction(20.0, 0, latitude=55.0)
        assert corr_360 == pytest.approx(corr_0)

    def test_negative_direction_wraps(self):
        """Negative direction should wrap via modulo."""
        _, corr_neg = apply_wind_direction_correction(20.0, -90, latitude=55.0)
        _, corr_pos = apply_wind_direction_correction(20.0, 270, latitude=55.0)
        assert corr_neg == pytest.approx(corr_pos)


# ---------------------------------------------------------------------------
# calculate_feels_like (integration of all methods)
# ---------------------------------------------------------------------------


class TestCalculateFeelsLike:
    """Integration tests for the main calculate_feels_like function."""

    def test_heat_index_selection(self):
        """Hot + humid → Heat Index method."""
        _, method, _, _ = calculate_feels_like(35, 60, wind_speed=1)
        assert method == "Heat Index"

    def test_wind_chill_selection(self):
        """Cold + windy → Wind Chill method."""
        _, method, _, _ = calculate_feels_like(-5, 50, wind_speed=5)
        assert method == "Wind Chill"

    def test_steadman_selection(self):
        """Moderate conditions → Steadman."""
        _, method, _, _ = calculate_feels_like(20, 50, wind_speed=2)
        assert method == "Steadman Apparent Temperature"

    def test_indoor_model(self):
        """Indoor → Indoor Comfort Model."""
        _, method, _, _ = calculate_feels_like(22, 50, is_outdoor=False)
        assert method == "Indoor Comfort Model"

    def test_returns_four_tuple(self):
        result = calculate_feels_like(20, 50)
        assert len(result) == 4

    def test_wind_direction_correction_disabled_by_default(self):
        """Wind direction correction off → correction = 0."""
        _, _, _, wind_corr = calculate_feels_like(
            20, 50, wind_direction=0, enable_wind_direction_correction=False
        )
        assert wind_corr == 0.0

    def test_wind_direction_correction_enabled(self):
        """Wind direction correction on + direction provided → non-zero correction."""
        _, _, _, wind_corr = calculate_feels_like(
            20, 50, wind_direction=0, latitude=55.0,
            enable_wind_direction_correction=True,
        )
        assert wind_corr != 0.0

    def test_comfort_level_returned(self):
        """All calls should return a valid comfort level string."""
        _, _, comfort, _ = calculate_feels_like(20, 50)
        assert comfort in (
            "extreme_cold", "very_cold", "cold", "cool", "slightly_cool",
            "comfortable", "slightly_warm", "warm", "hot", "very_hot", "extreme_hot",
        )

    def test_pressure_applied_outdoor(self):
        """Pressure correction should change result for outdoor."""
        fl_no_p, _, _, _ = calculate_feels_like(20, 50, pressure=None)
        fl_low_p, _, _, _ = calculate_feels_like(20, 50, pressure=95.0)
        assert fl_no_p != fl_low_p

    def test_solar_correction_applied(self):
        """Solar correction at noon vs midnight should differ."""
        noon = datetime(2024, 6, 21, 13, 0)
        midnight = datetime(2024, 6, 21, 0, 0)
        fl_noon, _, _, _ = calculate_feels_like(20, 50, time_of_day=noon)
        fl_midnight, _, _, _ = calculate_feels_like(20, 50, time_of_day=midnight)
        assert fl_noon > fl_midnight

    def test_wind_chill_boundary_10c(self):
        """At exactly 10°C with wind > 1.34 m/s → should use Wind Chill."""
        _, method, _, _ = calculate_feels_like(10, 50, wind_speed=5)
        assert method == "Wind Chill"

    def test_heat_index_boundary_27c_40pct(self):
        """At exactly 27°C and 40% humidity → should use Heat Index."""
        _, method, _, _ = calculate_feels_like(27, 40, wind_speed=1)
        assert method == "Heat Index"

    def test_moderate_zone(self):
        """15°C, 50%, 1 m/s → Steadman (not cold enough for WC, not hot enough for HI)."""
        _, method, _, _ = calculate_feels_like(15, 50, wind_speed=1)
        assert method == "Steadman Apparent Temperature"


# ---------------------------------------------------------------------------
# calculate_indoor_feels_like
# ---------------------------------------------------------------------------


class TestCalculateIndoorFeelsLike:
    """Tests for indoor comfort model."""

    def test_normal_humidity_no_adjustment(self):
        """30-60% humidity → no humidity factor."""
        fl = calculate_indoor_feels_like(22, 45)
        assert fl == pytest.approx(22.0, abs=0.01)

    def test_low_humidity_cools(self):
        """< 30% humidity → feels cooler."""
        fl = calculate_indoor_feels_like(22, 20)
        assert fl < 22

    def test_high_humidity_warms(self):
        """> 60% humidity → feels warmer."""
        fl = calculate_indoor_feels_like(22, 80)
        assert fl > 22

    def test_exactly_30_pct(self):
        """At 30% boundary → no adjustment."""
        fl = calculate_indoor_feels_like(22, 30)
        assert fl == pytest.approx(22.0, abs=0.01)

    def test_exactly_60_pct(self):
        """At 60% boundary → no adjustment."""
        fl = calculate_indoor_feels_like(22, 60)
        assert fl == pytest.approx(22.0, abs=0.01)


# ---------------------------------------------------------------------------
# determine_outdoor_comfort
# ---------------------------------------------------------------------------


class TestDetermineOutdoorComfort:
    """Tests for outdoor comfort level classification."""

    # Heat Index method thresholds
    @pytest.mark.parametrize(
        "feels_like, expected",
        [
            (55, "extreme_hot"),
            (45, "very_hot"),
            (35, "hot"),
            (28, "warm"),
            (25, "comfortable"),
        ],
    )
    def test_heat_index_levels(self, feels_like, expected):
        assert determine_outdoor_comfort(feels_like, "Heat Index") == expected

    # Wind Chill method thresholds
    @pytest.mark.parametrize(
        "feels_like, expected",
        [
            (-50, "extreme_cold"),
            (-42, "very_cold"),
            (-30, "cold"),
            (-15, "cool"),
            (-5, "slightly_cool"),
            (5, "comfortable"),
        ],
    )
    def test_wind_chill_levels(self, feels_like, expected):
        assert determine_outdoor_comfort(feels_like, "Wind Chill") == expected

    # Steadman method thresholds (full range)
    @pytest.mark.parametrize(
        "feels_like, expected",
        [
            (50, "extreme_hot"),
            (40, "very_hot"),
            (33, "hot"),
            (30, "warm"),
            (27, "slightly_warm"),
            (20, "comfortable"),
            (5, "slightly_cool"),
            (-5, "cool"),
            (-20, "cold"),
            (-35, "very_cold"),
            (-45, "extreme_cold"),
        ],
    )
    def test_steadman_levels(self, feels_like, expected):
        assert determine_outdoor_comfort(feels_like, "Steadman Apparent Temperature") == expected

    def test_extreme_hot_reachable(self):
        """Very high feels_like should return extreme_hot (no cap applied)."""
        assert determine_outdoor_comfort(65, "Heat Index") == "extreme_hot"
        assert determine_outdoor_comfort(50, "Steadman Apparent Temperature") == "extreme_hot"


# ---------------------------------------------------------------------------
# determine_indoor_comfort
# ---------------------------------------------------------------------------


class TestDetermineIndoorComfort:
    """Tests for indoor comfort level classification."""

    @pytest.mark.parametrize(
        "temp, humidity, expected",
        [
            (14, 50, "cold"),
            (17, 50, "cool"),
            (19, 50, "slightly_cool"),
            (22, 50, "comfortable"),
            (22, 20, "slightly_cool"),   # Dry air
            (22, 80, "slightly_warm"),   # Humid air
            (25, 50, "slightly_warm"),
            (27, 50, "warm"),
            (30, 50, "hot"),
        ],
    )
    def test_indoor_levels(self, temp, humidity, expected):
        assert determine_indoor_comfort(temp, humidity) == expected

    def test_boundary_16(self):
        assert determine_indoor_comfort(16, 50) == "cool"

    def test_boundary_24(self):
        assert determine_indoor_comfort(24, 50) == "comfortable"

    def test_boundary_26(self):
        """26°C is ≤ 26, so it falls into slightly_warm, not warm."""
        assert determine_indoor_comfort(26, 50) == "slightly_warm"


# ---------------------------------------------------------------------------
# Edge cases and regression tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and regression tests."""

    def test_zero_wind_speed(self):
        """Zero wind speed should not crash."""
        fl, method, comfort, _ = calculate_feels_like(20, 50, wind_speed=0)
        assert isinstance(fl, float)

    def test_zero_humidity(self):
        fl, _, _, _ = calculate_feels_like(30, 0, wind_speed=2)
        assert isinstance(fl, float)

    def test_100_humidity(self):
        fl, _, _, _ = calculate_feels_like(30, 100, wind_speed=2)
        assert isinstance(fl, float)

    def test_extreme_cold(self):
        """Very cold temperature: -50°C."""
        fl, method, comfort, _ = calculate_feels_like(-50, 50, wind_speed=10)
        assert fl < -50
        assert method == "Wind Chill"

    def test_extreme_hot(self):
        """Very hot temperature: 50°C."""
        fl, method, comfort, _ = calculate_feels_like(50, 80)
        assert method == "Heat Index"

    def test_wind_chill_needs_wind(self):
        """Cold temp but no wind → should use Steadman, not Wind Chill."""
        _, method, _, _ = calculate_feels_like(5, 50, wind_speed=0.5)
        assert method == "Steadman Apparent Temperature"

    def test_wind_chill_needs_cold(self):
        """Warm temp + wind → should use Steadman, not Wind Chill."""
        _, method, _, _ = calculate_feels_like(15, 30, wind_speed=10)
        assert method == "Steadman Apparent Temperature"

    def test_negative_wind_direction(self):
        """Negative wind direction should not crash."""
        fl, _, _, corr = calculate_feels_like(
            20, 50, wind_direction=-45, enable_wind_direction_correction=True,
        )
        assert isinstance(fl, float)

    def test_large_wind_direction(self):
        """Wind direction > 360 should wrap."""
        fl, _, _, corr = calculate_feels_like(
            20, 50, wind_direction=720, enable_wind_direction_correction=True,
        )
        assert isinstance(fl, float)
