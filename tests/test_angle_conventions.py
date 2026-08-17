#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Witnesses for PASE's two azimuth frames (issue #301).

See DOCUMENTATION/angle_conventions.md. In the world frame (East = X, North = Y,
Zenith = Z):

    compass azimuth A       0 deg = North, positive clockwise towards East
                            unit vector (sin A, cos A)
    trigonometric azimuth A 0 deg = East, positive counterclockwise towards North
                            unit vector (cos A, sin A)

Reading one as the other swaps the East and North components, which is a
reflection about the NE-SW diagonal — issue #300. These tests assert absolute
directions rather than mutual consistency: a round-trip check is satisfied
equally by both frames and cannot see such a defect, which is exactly how #300
survived in tests/test_conversion_functions.py.
"""

import numpy as np
import pytest

from pase.conversion_functions import (COMPASS, TRIGONOMETRIC,
                                       cart_to_sph,
                                       compass_to_trig,
                                       compass_to_unit_vector,
                                       sph_to_cart,
                                       trig_to_compass,
                                       unit_vector_to_compass_deg)
from pase.ENVIRONMENT.light import get_sun_vector


# ---------------------------------------------------------------------------
# The compass frame, in absolute terms
# ---------------------------------------------------------------------------

CARDINALS = [
    ('North', 0.0, [0.0, 1.0, 0.0]),
    ('East', 90.0, [1.0, 0.0, 0.0]),
    ('South', 180.0, [0.0, -1.0, 0.0]),
    ('West', 270.0, [-1.0, 0.0, 0.0]),
]


@pytest.mark.parametrize('name, az_compass_deg, expected', CARDINALS)
def test_compass_cardinal_directions(name, az_compass_deg, expected):
    """A compass azimuth on the horizon points where its name says."""
    got = compass_to_unit_vector(az_compass_deg, el_deg=0.0)
    np.testing.assert_allclose(np.asarray(got, dtype=float).ravel(), expected,
                               atol=1e-12,
                               err_msg=f"compass azimuth {az_compass_deg} should point {name}")


@pytest.mark.parametrize('az_compass_deg', [0.0, 45.0, 137.5, 270.0])
def test_zenith_is_azimuth_independent(az_compass_deg):
    """At 90 deg elevation the azimuth no longer matters."""
    got = compass_to_unit_vector(az_compass_deg, el_deg=90.0)
    np.testing.assert_allclose(np.asarray(got, dtype=float).ravel(),
                               [0.0, 0.0, 1.0], atol=1e-12)


def test_elevation_and_zenith_angle_agree():
    """el_deg and zenith_deg are two ways of saying the same thing."""
    from_el = compass_to_unit_vector(147.0, el_deg=38.0)
    from_zenith = compass_to_unit_vector(147.0, zenith_deg=52.0)
    np.testing.assert_allclose(np.asarray(from_el, dtype=float).ravel(),
                               np.asarray(from_zenith, dtype=float).ravel(),
                               atol=1e-12)


def test_elevation_and_zenith_angle_are_exclusive():
    """Passing both is a caller error, not a silent preference."""
    with pytest.raises(ValueError):
        compass_to_unit_vector(0.0, el_deg=10.0, zenith_deg=80.0)


def test_compass_to_unit_vector_is_vectorized():
    """The helper takes the whole az/el column of a patch table at once."""
    az = np.array([0.0, 90.0, 180.0, 270.0])
    el = np.zeros(4)
    x, y, z = compass_to_unit_vector(az, el_deg=el)
    np.testing.assert_allclose(x, [0.0, 1.0, 0.0, -1.0], atol=1e-12)
    np.testing.assert_allclose(y, [1.0, 0.0, -1.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(z, np.zeros(4), atol=1e-12)


# ---------------------------------------------------------------------------
# The two frames are told apart explicitly
# ---------------------------------------------------------------------------

def test_the_two_frames_disagree_as_documented():
    """
    Azimuth 0 points North in the compass frame and East in the trigonometric
    one. If this test ever passes with both frames giving the same answer, the
    distinction has been lost.
    """
    compass = sph_to_cart('deg', 0.0, elev=0.0, frame=COMPASS)
    trig = sph_to_cart('deg', 0.0, elev=0.0, frame=TRIGONOMETRIC)
    np.testing.assert_allclose(np.asarray(compass, dtype=float).ravel(),
                               [0.0, 1.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(np.asarray(trig, dtype=float).ravel(),
                               [1.0, 0.0, 0.0], atol=1e-12)


def test_frame_is_mandatory_on_sph_to_cart():
    """An undeclared frame is a TypeError, never a silent default."""
    with pytest.raises(TypeError):
        sph_to_cart('deg', 0.0, elev=0.0)


def test_frame_is_mandatory_on_cart_to_sph():
    with pytest.raises(TypeError):
        cart_to_sph(1.0, 0.0, 0.0)


def test_cart_to_sph_reports_the_requested_frame():
    """Due East is 90 deg compass and 0 deg trigonometric. Returns radians."""
    az_compass, zenith = cart_to_sph(1.0, 0.0, 0.0, frame=COMPASS)
    assert az_compass == pytest.approx(np.pi / 2)
    assert zenith == pytest.approx(np.pi / 2)

    az_trig, _ = cart_to_sph(1.0, 0.0, 0.0, frame=TRIGONOMETRIC)
    assert az_trig == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Properties of the conversion between the frames
# ---------------------------------------------------------------------------

ANGLES = [0.0, 12.5, 45.0, 90.0, 137.5, 180.0, 225.0, 300.0, 359.9]


@pytest.mark.parametrize('a', ANGLES)
def test_compass_to_trig_is_an_involution(a):
    """
    The conversion is a reflection, so applying it twice is the identity. This is
    also why NE (45 deg) and SW (225 deg) are fixed points, and therefore why a
    sun placed there cannot reveal a frame mix-up.
    """
    there_and_back = compass_to_trig(compass_to_trig(a))
    assert (there_and_back - a) % 360.0 == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize('a', ANGLES)
def test_trig_to_compass_is_the_same_map(a):
    """A reflection is its own inverse: both directions are the same formula."""
    assert (trig_to_compass(a) - compass_to_trig(a)) % 360.0 == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize('a', [45.0, 225.0])
def test_the_diagonals_are_fixed_points(a):
    """NE and SW are unchanged by the conversion — the blind spots to avoid in tests."""
    assert compass_to_trig(a) % 360.0 == pytest.approx(a, abs=1e-9)


@pytest.mark.parametrize('az_compass_deg', ANGLES)
@pytest.mark.parametrize('el_deg', [0.0, 25.0, 60.0])
def test_heading_round_trip(az_compass_deg, el_deg):
    """unit_vector_to_compass_deg undoes compass_to_unit_vector."""
    x, y, _ = compass_to_unit_vector(az_compass_deg, el_deg=el_deg)
    assert unit_vector_to_compass_deg(x, y) == pytest.approx(az_compass_deg % 360.0,
                                                            abs=1e-9)


def test_unit_vector_to_compass_deg_is_wrapped_and_vectorized():
    """Headings come back in [0, 360), for arrays as well as scalars."""
    headings = unit_vector_to_compass_deg(np.array([0.0, 1.0, 0.0, -1.0]),
                                          np.array([1.0, 0.0, -1.0, 0.0]))
    np.testing.assert_allclose(headings, [0.0, 90.0, 180.0, 270.0], atol=1e-12)
    assert ((headings >= 0.0) & (headings < 360.0)).all()


# ---------------------------------------------------------------------------
# Cross-module agreement
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('az_compass_deg', [0.0, 37.0, 90.0, 147.67, 213.0, 315.0])
@pytest.mark.parametrize('el_deg', [0.0, 30.0, 71.0])
def test_agrees_with_get_sun_vector(az_compass_deg, el_deg):
    """
    PASE builds compass directions in two independent places: get_sun_vector for
    the sun, and this helper for everything else. They must agree, or the sun and
    the sky it shines on live in different frames — which is the shape issue #300
    took.
    """
    helper = np.asarray(compass_to_unit_vector(az_compass_deg, el_deg=el_deg),
                        dtype=float).ravel()
    sun = get_sun_vector(np.array([el_deg]), np.array([az_compass_deg]))[0]
    np.testing.assert_allclose(helper, sun, atol=1e-12)
