"""Ground-awareness tests for PVConfiguration3D.create_regular_central.

Covers the configuration-level integration of the Ground abstraction:

- flat ground (explicit Ground()) reproduces the default (no-ground) geometry;
- on a tilted plane, panels are only translated vertically to the block anchor
  elevation -- never rotated onto the slope -- which encodes the design
  decision that TiltY=0 means horizontal (panel normal points straight up),
  not parallel to the ground.
"""

import numpy as np
import pytest
import pyvista as pv

from pase.ENVIRONMENT.ground import Ground, SlopedGround, DEMGround
from pase.PHOTOVOLTAICS.configuration import (PVConfiguration3D,
                                              _assert_layout_within_ground)


def _flat_dem_ground(extent_x=20.0, extent_y=None, n=21):
    """A small synthetic flat DEMGround spanning [-extent_x, extent_x] x
    [-extent_y, extent_y] (square when ``extent_y`` is omitted)."""
    if extent_y is None:
        extent_y = extent_x
    xs = np.linspace(-extent_x, extent_x, n)
    ys = np.linspace(-extent_y, extent_y, n)
    xx, yy = np.meshgrid(xs, ys)
    zz = np.zeros_like(xx)
    surf = pv.StructuredGrid(xx, yy, zz).extract_surface(algorithm=None).triangulate()
    return DEMGround(surf.compute_normals(consistent_normals=True))


def _base_config(**overrides):
    """Minimal panel-only config accepted by create_regular_central.

    No StructureType -> add_structure is skipped, so every block is a panel and
    the geometry comparison stays panel-only.
    """
    cfg = dict(
        PanelDimensionX=1.6, PanelDimensionY=1.0, PanelThickness=False,
        RepetitionDistanceOfPanelsX=1.8, RepetitionDistanceOfPanelsY=1.2,
        NumberOfPanelsX=2, NumberOfPanelsY=2,
        RepetitionDistanceOfPVBlocksX=3.6, RepetitionDistanceOfPVBlocksY=2.4,
        NumberOfPVBlocksX=1, NumberOfPVBlocksY=1,
        CentralAzimut=0.0, TiltY=10.0, Hinge='center', Height=1.5,
    )
    cfg.update(overrides)
    return cfg


def _block_points(cfg):
    """Return the point array of each block, in block order."""
    return [np.asarray(cfg[i].points, dtype=float) for i in range(cfg.n_blocks)]


def _build(ground=None, **overrides):
    scene = PVConfiguration3D(ground=ground)
    # create_regular_central mutates the dict (setdefault); pass a fresh copy.
    scene.create_regular_central(_base_config(**overrides))
    return scene


def test_flat_ground_matches_default():
    """Explicit Ground() must reproduce the default (no ground argument)."""
    default = _build(ground=None)
    flat = _build(ground=Ground())

    assert default.n_blocks == flat.n_blocks and default.n_blocks > 0
    for pts_d, pts_f in zip(_block_points(default), _block_points(flat)):
        np.testing.assert_allclose(np.sort(pts_d, axis=0),
                                   np.sort(pts_f, axis=0), atol=1e-10)


def test_sloped_single_block_is_pure_z_translation():
    """On a slope, a single block is the flat block shifted by a constant dz.

    The panels keep their world orientation (X/Y unchanged, no rotation onto the
    slope); only Z is lifted to the terrain anchor. A constant per-point dz with
    identical X/Y is the signature of a pure vertical translation.
    """
    slope = SlopedGround(180, 80)  # ~10 deg south-facing slope
    flat = _build(ground=Ground())
    sloped = _build(ground=slope)

    assert flat.n_blocks == sloped.n_blocks and flat.n_blocks > 0
    for pts_f, pts_s in zip(_block_points(flat), _block_points(sloped)):
        # Same point ordering (identical build), so compare row-wise.
        np.testing.assert_allclose(pts_s[:, :2], pts_f[:, :2], atol=1e-9)
        dz = pts_s[:, 2] - pts_f[:, 2]
        np.testing.assert_allclose(dz, dz[0], atol=1e-9)


def test_sloped_block_is_lifted_relative_to_flat():
    """The slope anchor lifts the whole block above its flat-ground position.

    The block is centered at the origin and anchored at the maximum terrain
    elevation over its footprint, which is strictly positive on this slope, so
    every sloped panel point sits above its flat counterpart.
    """
    slope = SlopedGround(180, 80)  # terrain rises northward
    flat = _build(ground=Ground())
    sloped = _build(ground=slope)

    z_flat = np.concatenate([p[:, 2] for p in _block_points(flat)])
    z_sloped = np.concatenate([p[:, 2] for p in _block_points(sloped)])
    assert z_sloped.min() > z_flat.min() + 1e-6


# ── Layout-within-ground coverage check (issue #248) ───────────────────────────

class TestAssertLayoutWithinGround:
    """_assert_layout_within_ground delegates to ground.assert_covers."""

    def test_layout_within_dem_ok(self):
        """A layout well inside the DEM extent must not raise."""
        g = _flat_dem_ground(extent_x=20.0)
        centers = np.array([[0.0, 0.0, 0.0]])
        _assert_layout_within_ground(g, centers, 3.0, 3.0, azimuth_deg=0.0)

    def test_layout_exceeds_dem_raises_actionable(self):
        """A footprint spilling past the DEM raises the actionable error."""
        g = _flat_dem_ground(extent_x=20.0)
        centers = np.array([[0.0, 0.0, 0.0]])
        with pytest.raises(ValueError, match="TerrainExtentRadius"):
            _assert_layout_within_ground(g, centers, 50.0, 3.0, azimuth_deg=0.0)

    def test_azimuth_is_applied_to_footprint(self):
        """The footprint bbox is rotated by the azimuth before the check.

        On a wide-but-shallow DEM (x +/-30, y +/-10), a footprint 25 m long in X
        fits at azimuth 0 but, rotated 90 degrees, its long axis falls along the
        shallow +/-10 Y extent and overruns it. A raise only at 90 degrees proves
        the azimuth is genuinely applied (not ignored).
        """
        g = _flat_dem_ground(extent_x=30.0, extent_y=10.0)
        centers = np.array([[0.0, 0.0, 0.0]])
        # azimuth 0: long axis along X (+/-25 within +/-30), short along Y -> ok.
        _assert_layout_within_ground(g, centers, 25.0, 3.0, azimuth_deg=0.0)
        # azimuth 90: long axis now along Y (+/-25 beyond +/-10) -> raises.
        with pytest.raises(ValueError, match="TerrainExtentRadius"):
            _assert_layout_within_ground(g, centers, 25.0, 3.0, azimuth_deg=90.0)

    def test_unbounded_grounds_are_noop(self):
        """Flat and sloped (infinite) grounds never raise, whatever the layout."""
        centers = np.array([[0.0, 0.0, 0.0]])
        _assert_layout_within_ground(Ground(), centers, 1e6, 1e6, 0.0)
        _assert_layout_within_ground(SlopedGround(180, 80), centers, 1e6, 1e6, 0.0)

    def test_empty_or_none_centers_noop(self):
        """No block centers -> nothing to check, even on a bounded DEM."""
        g = _flat_dem_ground(extent_x=20.0)
        _assert_layout_within_ground(g, None, 3.0, 3.0, 0.0)
        _assert_layout_within_ground(g, np.empty((0, 3)), 3.0, 3.0, 0.0)


# ── End-to-end build on a DEMGround (issue #248) ───────────────────────────────

class TestBuildOnDEMGround:
    """create_regular_central against a bounded DEMGround."""

    def test_build_within_dem_matches_flat(self):
        """A flat DEM (z=0) build reproduces the analytic flat-ground build.

        This exercises the real DEMGround elevation path (vertical ray-cast)
        end to end: querying a z=0 surface must yield the same panel geometry as
        the analytic flat Ground().
        """
        dem = _build(ground=_flat_dem_ground(extent_x=20.0))
        flat = _build(ground=Ground())

        assert dem.n_blocks == flat.n_blocks and dem.n_blocks > 0
        for pts_d, pts_f in zip(_block_points(dem), _block_points(flat)):
            np.testing.assert_allclose(np.sort(pts_d, axis=0),
                                       np.sort(pts_f, axis=0), atol=1e-6)

    def test_build_exceeding_dem_raises_actionable(self):
        """A layout larger than the DEM extent fails fast during the build."""
        with pytest.raises(ValueError, match="TerrainExtentRadius"):
            _build(ground=_flat_dem_ground(extent_x=3.0),
                   NumberOfPVBlocksX=3, NumberOfPVBlocksY=3)
