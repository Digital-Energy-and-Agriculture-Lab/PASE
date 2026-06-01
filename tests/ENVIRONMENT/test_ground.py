"""Tests for pase.ENVIRONMENT.ground — Ground, SlopedGround, DEMGround utilities."""

import math
import numpy as np
import pytest

from pase.ENVIRONMENT.ground import (Ground, SlopedGround, rotation_from_z_to_normal,
                                     ground_from_config)


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
