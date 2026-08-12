"""Tests for pase.ENVIRONMENT.ground — Ground, SlopedGround, DEMGround utilities."""

import math
import numpy as np
import pytest

import pyvista as pv

from pase.ENVIRONMENT.ground import (Ground, SlopedGround, DEMGround,
                                     rotation_from_z_to_normal,
                                     ground_from_config, bounds_around,
                                     block_reference_elevation)


def _make_dem_surface(peak_h=10.0, extent=20.0, n=21):
    """Synthetic bumpy terrain: a Gaussian bump peaking at the centre (0, 0)."""
    xs = np.linspace(-extent, extent, n)
    ys = np.linspace(-extent, extent, n)
    xx, yy = np.meshgrid(xs, ys)
    sigma = extent / 4.0
    zz = peak_h * np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma ** 2))
    surf = pv.StructuredGrid(xx, yy, zz).extract_surface().triangulate()
    return surf.compute_normals(consistent_normals=True)


class TestGround:
    def test_elevation_scalar(self):
        g = Ground()
        assert g.elevation(0, 0) == pytest.approx(0.0)
        assert g.elevation(100, -50) == pytest.approx(0.0)

    def test_elevation_array(self):
        g = Ground()
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([0.0, 1.0, 2.0])
        z = g.elevation(x, y)
        np.testing.assert_array_equal(z, np.zeros(3))

    def test_normal(self):
        g = Ground()
        np.testing.assert_array_equal(g.normal(0, 0), [0.0, 0.0, 1.0])

    def test_gradient(self):
        g = Ground()
        assert g.gradient(0, 0) == (0.0, 0.0)

    def test_contains(self):
        g = Ground()
        assert g.contains(0, 0) is True
        assert g.contains(1e9, -1e9) is True

    def test_to_polydata(self):
        import pyvista as pv
        g = Ground()
        mesh = g.to_polydata((-5, 5), (-5, 5), resolution=5.0)
        assert isinstance(mesh, pv.PolyData)
        assert mesh.n_points > 0
        np.testing.assert_array_equal(mesh.points[:, 2], 0.0)


class TestSlopedGround:
    def test_flat_degenerate(self):
        g = SlopedGround(0, 90)  # elevation 90° → perfectly flat
        assert g.elevation(0, 0) == pytest.approx(0.0)
        assert g.elevation(100, 200) == pytest.approx(0.0)

    def test_south_facing_slope(self):
        # Normal azimuth 180° (South), elevation 80° → ~10° slope toward South
        # Going north (positive y) → terrain rises
        g = SlopedGround(180, 80)
        assert g.elevation(0, 100) > 0.0
        assert g.elevation(0, -100) < 0.0

    def test_north_facing_slope(self):
        # Normal azimuth 0° (North), elevation 80° → terrain rises going south
        g = SlopedGround(0, 80)
        assert g.elevation(0, -100) > 0.0
        assert g.elevation(0, 100) < 0.0

    def test_normal_is_unit(self):
        g = SlopedGround(45, 75)
        n = g.normal(0, 0)
        assert np.linalg.norm(n) == pytest.approx(1.0, abs=1e-10)

    def test_normal_has_positive_z(self):
        g = SlopedGround(90, 60)
        n = g.normal(0, 0)
        assert n[2] > 0

    def test_gradient_constant(self):
        g = SlopedGround(180, 80)
        dzdx1, dzdy1 = g.gradient(0, 0)
        dzdx2, dzdy2 = g.gradient(100, 200)
        assert dzdx1 == pytest.approx(dzdx2)
        assert dzdy1 == pytest.approx(dzdy2)

    def test_contains_always_true(self):
        g = SlopedGround(0, 80)
        assert g.contains(0, 0) is True
        assert g.contains(1e9, -1e9) is True

    def test_elevation_pivot_at_origin(self):
        g = SlopedGround(180, 80)
        assert g.elevation(0, 0) == pytest.approx(0.0, abs=1e-12)

    def test_to_polydata(self):
        import pyvista as pv
        g = SlopedGround(180, 80)
        mesh = g.to_polydata((-5, 5), (-5, 5), resolution=2.5)
        assert isinstance(mesh, pv.PolyData)
        assert mesh.n_points > 0
        # All z values should match elevation
        pts = mesh.points
        expected_z = g.elevation(pts[:, 0], pts[:, 1])
        np.testing.assert_allclose(pts[:, 2], expected_z, atol=1e-10)


class TestRotationFromZToNormal:
    def test_identity_for_z(self):
        R = rotation_from_z_to_normal(np.array([0.0, 0.0, 1.0]))
        np.testing.assert_allclose(R, np.eye(3), atol=1e-10)

    def test_maps_z_to_given_normal(self):
        n = np.array([0.5, 0.5, math.sqrt(0.5)])
        n /= np.linalg.norm(n)
        R = rotation_from_z_to_normal(n)
        result = R @ np.array([0.0, 0.0, 1.0])
        np.testing.assert_allclose(result, n, atol=1e-10)

    def test_result_is_rotation_matrix(self):
        n = np.array([0.3, 0.1, math.sqrt(1 - 0.09 - 0.01)])
        R = rotation_from_z_to_normal(n)
        np.testing.assert_allclose(R @ R.T, np.eye(3), atol=1e-10)
        assert abs(np.linalg.det(R) - 1.0) < 1e-10


class TestGroundFromConfig:
    def test_missing_keys_returns_flat_ground(self):
        g = ground_from_config({})
        assert isinstance(g, Ground) and not isinstance(g, SlopedGround)
        assert g.elevation(100, 200) == pytest.approx(0.0)

    def test_zero_angle_returns_flat_ground(self):
        g = ground_from_config({'TerrainSlopeAngle': 0.0, 'TerrainSlopeAspect': 180.0})
        assert isinstance(g, Ground) and not isinstance(g, SlopedGround)

    def test_positive_angle_returns_sloped_ground(self):
        g = ground_from_config({'TerrainSlopeAngle': 10.0, 'TerrainSlopeAspect': 180.0})
        assert isinstance(g, SlopedGround)

    def test_conversion_matches_normal_convention(self):
        # TerrainSlopeAngle=10, TerrainSlopeAspect=180 ≡ SlopedGround(180, 80)
        g = ground_from_config({'TerrainSlopeAngle': 10.0, 'TerrainSlopeAspect': 180.0})
        ref = SlopedGround(terrain_normal_azimuth=180, terrain_normal_elevation=80)
        for x, y in [(0, 0), (10, -20), (-5, 30)]:
            assert g.elevation(x, y) == pytest.approx(ref.elevation(x, y))
        np.testing.assert_allclose(g.gradient(0, 0), ref.gradient(0, 0))

    def test_string_values_are_coerced(self):
        # YAML values may arrive as numbers; ensure float() coercion is robust.
        g = ground_from_config({'TerrainSlopeAngle': '10', 'TerrainSlopeAspect': '180'})
        ref = SlopedGround(terrain_normal_azimuth=180, terrain_normal_elevation=80)
        assert g.elevation(0, 100) == pytest.approx(ref.elevation(0, 100))

    def test_sloped_source_explicit(self):
        # TerrainSource='sloped' must build a SlopedGround even at angle 0.
        g = ground_from_config({'TerrainSource': 'sloped',
                                'TerrainSlopeAngle': 0.0, 'TerrainSlopeAspect': 0.0})
        assert isinstance(g, SlopedGround)

    def test_terrain_keys_read_from_location(self):
        # Keys may live in the location dict, not the central config.
        g = ground_from_config({}, location={'TerrainSlopeAngle': 10.0,
                                             'TerrainSlopeAspect': 180.0})
        assert isinstance(g, SlopedGround)

    def test_srtm_requires_lat_lon(self):
        with pytest.raises(ValueError, match="Latitude"):
            ground_from_config({'TerrainSource': 'srtm'})

    def test_srtm_builds_demground(self, monkeypatch):
        # No network: stub the SRTM pipeline with a synthetic surface.
        surf = _make_dem_surface()
        monkeypatch.setattr(
            'pase.ENVIRONMENT.terrain_pipeline.build_terrain_surface',
            lambda bounds, center_lonlat=None: surf,
        )
        g = ground_from_config(
            {'TerrainSource': 'srtm'},
            location={'Latitude': 45.92, 'Longitude': 6.87, 'TerrainExtentRadius': 100},
        )
        assert isinstance(g, DEMGround)
        assert g.elevation(0.0, 0.0) > 5.0   # near the Gaussian peak


class TestBoundsAround:
    def test_symmetry_and_scale(self):
        # At the equator, 111320 m ≈ 1 degree in both lat and lon.
        west, south, east, north = bounds_around(0.0, 0.0, 111_320.0)
        assert north == pytest.approx(1.0, abs=1e-6)
        assert south == pytest.approx(-1.0, abs=1e-6)
        assert east == pytest.approx(1.0, abs=1e-6)
        assert west == pytest.approx(-1.0, abs=1e-6)

    def test_longitude_widens_with_latitude(self):
        # At 60°N, cos=0.5 → the longitude span is twice the equator span.
        _, _, e0, _ = bounds_around(0.0, 0.0, 1000.0)
        _, _, e60, _ = bounds_around(60.0, 0.0, 1000.0)
        assert e60 == pytest.approx(2.0 * e0, rel=1e-3)


class TestFootprintSamples:
    def test_defaults(self):
        assert Ground().footprint_samples == 2
        assert SlopedGround(180, 80).footprint_samples == 2
        assert DEMGround(_make_dem_surface()).footprint_samples == 5


class TestBlockReferenceElevationSampling:
    def test_samples2_matches_four_corners(self):
        g = DEMGround(_make_dem_surface())
        # Footprint away from the peak so corners are well defined.
        z = block_reference_elevation(g, 5.0, 5.0, 3.0, 3.0, samples=2)
        corners = [g.elevation(x, y) for x in (2.0, 8.0) for y in (2.0, 8.0)]
        assert z == pytest.approx(max(corners), abs=1e-9)

    def test_dense_sampling_captures_interior_peak(self):
        g = DEMGround(_make_dem_surface(peak_h=10.0))
        # Footprint centred on the peak: the 4 corners sit in the valley, the
        # interior holds the maximum.
        z_corners = block_reference_elevation(g, 0.0, 0.0, 12.0, 12.0, samples=2)
        z_dense = block_reference_elevation(g, 0.0, 0.0, 12.0, 12.0, samples=11)
        assert z_dense > z_corners + 1.0


class TestDEMGroundAssertCovers:
    def test_within_bounds_ok(self):
        g = DEMGround(_make_dem_surface(extent=20.0))
        g.assert_covers(-10.0, 10.0, -10.0, 10.0)   # no raise

    def test_out_of_bounds_raises_actionable(self):
        g = DEMGround(_make_dem_surface(extent=20.0))
        with pytest.raises(ValueError, match="TerrainExtentRadius"):
            g.assert_covers(-100.0, 100.0, -10.0, 10.0)

    def test_flat_ground_assert_is_noop(self):
        Ground().assert_covers(-1e9, 1e9, -1e9, 1e9)   # no raise
        SlopedGround(180, 80).assert_covers(-1e9, 1e9, -1e9, 1e9)
