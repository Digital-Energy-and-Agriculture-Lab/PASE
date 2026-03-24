#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pytest
from scipy.interpolate import interp1d

from pase.ENVIRONMENT.shading import Horizon
from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.sky_model import ReinhartSky
from pase.ENVIRONMENT.mesh import Mesh
from pase.PHOTOVOLTAICS.configuration import PVConfiguration3D


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_horizon(flat_elevation=5.0):
    """Return a Horizon with a flat synthetic profile (no PVGIS call)."""
    h = Horizon(lat=50.0, lon=4.0)
    azimuths = np.array([0.0, 360.0])
    elevations = np.array([flat_elevation, flat_elevation])
    h.interp_func = interp1d(azimuths, elevations,
                             kind='linear', fill_value="extrapolate")
    return h


def _create_simple_scene():
    """Return a minimal (cfg, mesh, sky) tuple for integration tests."""
    params = dict(
        PanelDimensionX=1.6, PanelDimensionY=1.0, PanelThickness=False,
        RepetitionDistanceOfPanelsX=1.8, RepetitionDistanceOfPanelsY=2.1,
        RepetitionDistanceOfPVBlocksX=3.6, RepetitionDistanceOfPVBlocksY=2.4,
        NumberOfPVBlocksX=1, NumberOfPVBlocksY=1, RotationAxisNumber=0,
        CentralAzimut=0.0, TiltY=10.0, Height=2.0,
        NumberOfPanelsX=2, NumberOfPanelsY=2, Hinge='Center'
    )
    cfg = PVConfiguration3D()
    cfg.create_regular_central(params)

    M = Mesh()
    loc = dict(InterestZoneOrientationMode='custom', InterestZoneCustomAngle=0)
    M.set_interest_zone_orientation(loc, params)
    M.add_rectangular_surface(
        width=2, height=2, density=0.1, name="crop",
        center=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0),
        reference_direction=(1.0, 0.0, 0.0), face_type="rectangle"
    )

    sky = ReinhartSky(MF=1).reinhart_patches
    return cfg, M, sky


# Sun vector with elevation ~26° (el = arcsin(0.5/norm))
_SUN = np.array([[0.0, 1.0, 0.5]])
_SUN = _SUN / np.linalg.norm(_SUN)


# ─────────────────────────────────────────────
# Unit tests — Horizon class
# ─────────────────────────────────────────────

def test_horizon_mask_sun_above():
    """Sun well above horizon → visible."""
    h = _make_horizon(flat_elevation=5.0)
    assert h.is_sun_visible(180, 45) == True


def test_horizon_mask_sun_below():
    """Sun below horizon → not visible."""
    h = _make_horizon(flat_elevation=5.0)
    assert h.is_sun_visible(180, -5) == False


def test_horizon_mask_at_exact_boundary():
    """Sun exactly at horizon elevation → NOT visible (strict >)."""
    h = _make_horizon(flat_elevation=5.0)
    assert h.is_sun_visible(180, 5.0) == False


def test_horizon_mask_just_above_boundary():
    """Sun just above horizon elevation → visible."""
    h = _make_horizon(flat_elevation=5.0)
    assert h.is_sun_visible(180, 5.01) == True


def test_horizon_mask_azimuth_normalization():
    """Azimuths outside [0, 360] are normalized correctly."""
    h = _make_horizon(flat_elevation=5.0)
    # 370° ≡ 10° : sun at el=45 should be visible
    assert h.is_sun_visible(370, 45) == True
    # 370° ≡ 10° : sun at el=2 should be blocked
    assert h.is_sun_visible(370, 2) == False


def test_horizon_mask_no_profile():
    """If no profile is loaded, all positions are assumed visible."""
    h = Horizon(lat=50.0, lon=4.0)
    azimuths = np.array([0.0, 90.0, 180.0, 270.0])
    elevations = np.array([0.0, 0.0, 0.0, 0.0])
    result = h.get_horizon_mask(azimuths, elevations)
    assert np.all(result)


def test_horizon_mask_array_input():
    """Array inputs: mixed visible/blocked positions."""
    h = _make_horizon(flat_elevation=5.0)
    azimuths = np.array([0.0, 90.0, 180.0, 270.0])
    elevations = np.array([10.0, 3.0, 20.0, 1.0])  # above, below, above, below
    result = h.is_sun_visible(azimuths, elevations)
    expected = np.array([True, False, True, False])
    assert np.array_equal(result, expected)


# ─────────────────────────────────────────────
# Integration tests — Horizon + Ray_casting_scene
# ─────────────────────────────────────────────

def test_direct_mask_horizon_blocks_all():
    """Horizon at 89° blocks all sun positions with elevation < 89°."""
    cfg, M, sky = _create_simple_scene()
    h = _make_horizon(flat_elevation=89.0)
    L = Ray_casting_scene(M, cfg, sky, horizon=h)
    direct_mask = L.get_direct_mask(_SUN, cfg)
    assert np.all(direct_mask == 0)


def test_direct_mask_horizon_no_effect():
    """Horizon at -5° (below all sun positions) → same result as without horizon."""
    cfg, M, sky = _create_simple_scene()
    h = _make_horizon(flat_elevation=-5.0)
    L_with = Ray_casting_scene(M, cfg, sky, horizon=h)
    L_without = Ray_casting_scene(M, cfg, sky)
    mask_with = L_with.get_direct_mask(_SUN, cfg)
    mask_without = L_without.get_direct_mask(_SUN, cfg)
    assert np.array_equal(mask_with, mask_without)