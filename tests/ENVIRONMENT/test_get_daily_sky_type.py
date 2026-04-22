#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Tests for Light.get_daily_sky_type
#
# get_daily_sky_type does not read any instance attributes, so we use
# Light.__new__(Light) to get a bare instance — no weather files or
# PVGIS connection needed.

import numpy as np
import pandas as pd
import pytest

from pase.ENVIRONMENT.light import Light, SKY_CATEGORY_LABELS

# Bare Light instance — skips __init__ entirely
light = Light.__new__(Light)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_series(date_str, values, freq='h'):
    """Build a Series with a DatetimeIndex from a list of values for one day."""
    index = pd.date_range(date_str, periods=len(values), freq=freq)
    return pd.Series(values, index=index, dtype=float)


def make_year(year, value, leap=False):
    """Build a full-year hourly Series filled with a constant sky type value."""
    n_days = 366 if leap else 365
    index = pd.date_range(f'{year}-01-01', periods=n_days * 24, freq='h')
    return pd.Series(float(value), index=index)


def sky_type(result, day=0):
    return result['CIE Sky Type'].iloc[day]


def sky_cat(result, day=0):
    return result['Sky Category'].iloc[day]


# ---------------------------------------------------------------------------
# Rounding rules
# ---------------------------------------------------------------------------

def test_decimal_0_1_to_0_4_rounds_down():
    # [2, 2, 2, 3] → mean = 9/4 = 2.25 → decimal 0.25 → floor → 2
    result = light.get_daily_sky_type(make_series('2020-06-01', [2, 2, 2, 3]))
    assert sky_type(result) == 2


def test_decimal_0_6_to_0_9_rounds_up():
    # [2, 3, 3, 3] → mean = 11/4 = 2.75 → decimal 0.75 → ceil → 3
    result = light.get_daily_sky_type(make_series('2020-06-01', [2, 3, 3, 3]))
    assert sky_type(result) == 3


def test_exact_integer_no_rounding():
    # [1, 1, 3, 3] → mean = 8/4 = 2.0 → decimal 0.0 → floor(2.0) = 2
    result = light.get_daily_sky_type(make_series('2020-06-01', [1, 1, 3, 3]))
    assert sky_type(result) == 2


def test_single_daytime_value():
    # One valid hour → result equals that sky type unchanged
    result = light.get_daily_sky_type(make_series('2020-06-01', [7]))
    assert sky_type(result) == 7


# ---------------------------------------------------------------------------
# NaN handling (nighttime hours)
# ---------------------------------------------------------------------------

def test_all_nan_returns_nan():
    # All nighttime → no valid hours → NaN
    result = light.get_daily_sky_type(make_series('2020-06-01', [np.nan, np.nan, np.nan]))
    assert np.isnan(sky_type(result))


def test_nan_hours_are_excluded_from_mean():
    # NaN entries (nighttime) must not pull the mean toward zero
    # valid = [1, 4, 4] → mean = 9/3 = 3.0 → result = 3
    result = light.get_daily_sky_type(
        make_series('2020-06-01', [np.nan, np.nan, 1, 4, 4, np.nan])
    )
    assert sky_type(result) == 3


# ---------------------------------------------------------------------------
# Tiebreak at 0.5
# ---------------------------------------------------------------------------

def test_tiebreak_equal_counts_defaults_to_lower():
    # [2, 2, 3, 3] → mean = 10/4 = 2.5
    # lower(2) count = 2, upper(3) count = 2  →  equal → lower wins → 2
    result = light.get_daily_sky_type(make_series('2020-06-01', [2, 2, 3, 3]))
    assert sky_type(result) == 2


def test_tiebreak_more_lower_values_rounds_down():
    # [1, 2, 2, 2, 3, 5] → mean = 15/6 = 2.5
    # lower(2) count = 3, upper(3) count = 1  →  lower wins → 2
    series = make_series('2020-06-01', [1, 2, 2, 2, 3, 5])
    assert series.mean() == pytest.approx(2.5)
    result = light.get_daily_sky_type(series)
    assert sky_type(result) == 2


def test_tiebreak_more_upper_values_rounds_up():
    # [2, 3, 3, 3, 1, 1, 1, 6] → mean = 20/8 = 2.5
    # lower(2) count = 1, upper(3) count = 3  →  upper wins → 3
    series = make_series('2020-06-01', [2, 3, 3, 3, 1, 1, 1, 6])
    assert series.mean() == pytest.approx(2.5)
    result = light.get_daily_sky_type(series)
    assert sky_type(result) == 3


# ---------------------------------------------------------------------------
# Sky category labels
# ---------------------------------------------------------------------------

def test_known_types_map_to_correct_category():
    expected = {
        1:  'overcast',
        4:  'intermediate overcast',
        7:  'intermediate',
        11: 'intermediate clear',
        13: 'clear',
    }
    for cie_type, label in expected.items():
        result = light.get_daily_sky_type(make_series('2020-06-01', [cie_type] * 6))
        assert sky_cat(result) == label, f"Type {cie_type}: expected '{label}'"


def test_type_5_maps_to_undefined():
    result = light.get_daily_sky_type(make_series('2020-06-01', [5] * 6))
    assert sky_cat(result) == 'undefined'


def test_all_nan_day_maps_to_undefined_category():
    result = light.get_daily_sky_type(make_series('2020-06-01', [np.nan, np.nan]))
    assert sky_cat(result) == 'undefined'


def test_sky_category_labels_constant_covers_all_defined_types():
    assert set(SKY_CATEGORY_LABELS.keys()) == {1, 4, 7, 11, 13}


# ---------------------------------------------------------------------------
# Output shape and structure
# ---------------------------------------------------------------------------

def test_output_is_dataframe_with_correct_columns():
    result = light.get_daily_sky_type(make_series('2020-06-01', [1] * 6))
    assert isinstance(result, pd.DataFrame)
    assert 'CIE Sky Type' in result.columns
    assert 'Sky Category' in result.columns


def test_output_length_is_365_for_regular_year():
    result = light.get_daily_sky_type(make_year(2019, 5, leap=False))
    assert len(result) == 365


def test_output_length_is_366_for_leap_year():
    result = light.get_daily_sky_type(make_year(2020, 5, leap=True))
    assert len(result) == 366


# ---------------------------------------------------------------------------
# Multi-day independence
# ---------------------------------------------------------------------------

def test_days_are_computed_independently():
    # Day 1: all type 1  → mean = 1.0  → result = 1, overcast
    # Day 2: all type 13 → mean = 13.0 → result = 13, clear
    day1 = make_series('2020-06-01', [1] * 12)
    day2 = make_series('2020-06-02', [13] * 12)
    result = light.get_daily_sky_type(pd.concat([day1, day2]))
    assert sky_type(result, day=0) == 1
    assert sky_cat(result,  day=0) == 'overcast'
    assert sky_type(result, day=1) == 13
    assert sky_cat(result,  day=1) == 'clear'


def test_all_15_sky_types_as_constant_days():
    # Each sky type (1-15) used as a constant day → CIE Sky Type must round-trip
    days = [make_series(f'2020-01-{d+1:02d}', [t] * 8)
            for d, t in enumerate(range(1, 16))]
    result = light.get_daily_sky_type(pd.concat(days))
    for i, expected in enumerate(range(1, 16)):
        assert sky_type(result, day=i) == expected, f"Sky type {expected} failed"
