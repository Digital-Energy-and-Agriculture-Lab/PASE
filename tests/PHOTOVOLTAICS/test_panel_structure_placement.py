"""Placement of PV panels relative to their supporting structure.

Regression coverage for issue #299: the call to ``compute_flush_panel_offset``
in ``PVConfiguration3D._build_panels_for_central`` was overwritten by a constant
lookup, which sank every panel into the rafters without raising anything. A unit
test of ``compute_flush_panel_offset`` alone cannot detect that -- the function
stayed correct, only its call site was lost -- so these tests assert the
resulting geometry instead.
"""

import numpy as np
import pytest

from pase.PHOTOVOLTAICS.configuration import PVConfiguration3D
from pase.PHOTOVOLTAICS.structure import compute_flush_panel_offset

# Center-hinge structures, i.e. the ones panels rest flush on.
FLUSH_STRUCTURE_TYPES = ["PV Table", "HSATS"]

# Panel coordinates are stored as float32 by VTK; observed residuals are ~1e-7.
FLUSH_TOLERANCE = 1e-5


def _panel_normal(tilt_deg: float, azimuth_deg: float) -> np.ndarray:
    """Return the outward normal of a center-hinge panel.

    Panels are built flat, rotated by ``rotate_y(tilt)`` then
    ``rotate_z(-azimuth)``, so their normal is the zenith vector put through the
    same two rotations.

    Parameters
    ----------
    tilt_deg : float
        Panel tilt around the Y axis, in degrees.
    azimuth_deg : float
        Central azimuth, in degrees.

    Returns
    -------
    numpy.ndarray, shape (3,)
        Unit normal of the panel plane.
    """
    tilt = np.radians(tilt_deg)
    azimuth = np.radians(-azimuth_deg)

    tilted = np.array([np.sin(tilt), 0.0, np.cos(tilt)])
    rotation_z = np.array([[np.cos(azimuth), -np.sin(azimuth), 0.0],
                           [np.sin(azimuth), np.cos(azimuth), 0.0],
                           [0.0, 0.0, 1.0]])

    return rotation_z @ tilted


def _per_block_gaps(config: dict) -> dict:
    """Measure the panel-to-structure gap of every block along the panel normal.

    The gap is a separating-axis measurement, not an axis-aligned one: the
    bounding box of a tilted rafter engulfs the panels even when the geometry is
    correct, so an AABB overlap test would report a false negative here.

    The measurement is per block. A panel belonging to one block projects well
    below the structure of another block, so a plant-wide min/max comparison is
    meaningless as soon as there is more than one block.

    Parameters
    ----------
    config : dict
        Aggregated PV + structure inputs, as passed to ``create_regular_central``.

    Returns
    -------
    dict
        Mapping ``(Block_X, Block_Y)`` -> signed gap in meters. Negative means the
        panels dip into the structure, positive means they float above it.
    """
    central = PVConfiguration3D()
    central.create_regular_central(config)

    normal = _panel_normal(float(config["TiltY"]),
                           float(config.get("CentralAzimut", 0.0)))

    gaps = {}
    for block in sorted(set(zip(central.df["Block_X"], central.df["Block_Y"]))):
        block_x, block_y = block
        selector = {"Block_X": [block_x], "Block_Y": [block_y]}

        panels = central.polydata_by_property({**selector, "Type": ["PV"]})
        structure = central.polydata_by_property(
            {**selector, "Type": ["Structure block"]}
        )

        gaps[block] = float((panels.points @ normal).min()
                            - (structure.points @ normal).max())

    return gaps


@pytest.mark.parametrize("structure_type", FLUSH_STRUCTURE_TYPES)
@pytest.mark.parametrize(
    "config_overrides",
    [
        {},
        pytest.param({"PanelThickness": 0.05}, id="3D-panels"),
        pytest.param({"CentralAzimut": 45.0}, id="rotated-central"),
        pytest.param({"NumberOfPVBlocksX": 2, "NumberOfPVBlocksY": 2},
                     id="multi-block"),
    ],
)
def test_panels_rest_flush_on_structure(structure_inputs, structure_type,
                                        config_overrides):
    """Panel back faces must be tangent to the purlin top faces.

    ``compute_flush_panel_offset`` offsets panels by
    ``dim_rafter + 2 * dim_purlin + thickness / 2``, which makes the two surfaces
    coincident. Losing that offset -- issue #299 -- drives the gap to about
    -0.17 m, well outside the tolerance.
    """
    config = structure_inputs(StructureType=structure_type, **config_overrides)

    gaps = _per_block_gaps(config)

    assert gaps, "No block was built; the test would be vacuous."

    for block, gap in gaps.items():
        assert gap >= -FLUSH_TOLERANCE, (
            f"{structure_type} block {block}: panels sink {abs(gap):.4f} m into "
            f"the structure instead of resting on it."
        )
        assert gap <= FLUSH_TOLERANCE, (
            f"{structure_type} block {block}: panels float {gap:.4f} m above the "
            f"structure instead of resting on it."
        )


@pytest.mark.parametrize("structure_type", FLUSH_STRUCTURE_TYPES)
def test_panel_placement_follows_structure_cross_section(structure_inputs,
                                                         structure_type):
    """Panel elevation must track the purlin cross-section.

    Pins the dependency itself, so a call site returning any constant -- rather
    than the specific 0.0 of issue #299 -- is caught too.
    """
    thin = structure_inputs(StructureType=structure_type,
                            PurlinShape="square", PurlinSide=0.1)
    thick = structure_inputs(StructureType=structure_type,
                             PurlinShape="square", PurlinSide=0.3)

    def _panel_z_min(config):
        central = PVConfiguration3D()
        central.create_regular_central(config)
        return float(central.polydata_by_property({"Type": ["PV"]}).bounds[4])

    # Offset grows by 2 * dim_purlin, i.e. 2 * (side / 2), projected on the tilt.
    expected_rise = 2 * (0.3 - 0.1) / 2 * np.cos(np.radians(thin["TiltY"]))

    measured_rise = _panel_z_min(thick) - _panel_z_min(thin)

    assert measured_rise == pytest.approx(expected_rise, abs=1e-4), (
        f"{structure_type}: panel elevation does not follow the purlin section "
        f"(expected +{expected_rise:.4f} m, measured {measured_rise:+.4f} m)."
    )


def test_flush_offset_is_zero_without_center_hinge_structure(structure_inputs):
    """Fences and structure-less centrals get no flush offset.

    ``AgrivoltaicFence`` hangs its panels on a top hinge and lets them straddle
    the horizontal bars on purpose, so the flush invariant asserted above does
    not apply to it.
    """
    fence = structure_inputs(StructureType="Agrivoltaic fence")
    assert compute_flush_panel_offset(fence, thickness=0.05) == 0.0

    no_structure = structure_inputs()
    no_structure.pop("StructureType", None)
    assert compute_flush_panel_offset(no_structure, thickness=0.05) == 0.0
