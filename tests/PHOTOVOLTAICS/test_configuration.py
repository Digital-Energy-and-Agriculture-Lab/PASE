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

from pase.ENVIRONMENT.ground import Ground, SlopedGround
from pase.PHOTOVOLTAICS.configuration import PVConfiguration3D


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
