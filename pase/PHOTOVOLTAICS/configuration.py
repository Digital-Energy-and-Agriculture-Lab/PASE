#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Authors : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com) and Nicolas De Cock (nicolas.decock1@gmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.


from __future__ import annotations

import logging
from typing import Iterable, Union, Dict, List, Any, Tuple, Optional, Sequence
import numpy as np
import pandas as pd
import pyvista as pyv


# ----- Constants -----
EPS = 1e-12
DEFAULT_NORMAL = np.array([0.0, 0.0, 1.0], dtype=float)
DEFAULT_PANEL_THICKNESS = 0.0
DEFAULT_PANEL_Z_DIM = 0.1

logger = logging.getLogger(__name__)


# ----- Utilities -----
def merge_polydata(datasets: List[pyv.PolyData], *, extract_surface: bool = True) -> pyv.PolyData:
    """
    Merge multiple ``pyvista.PolyData`` datasets efficiently.

    Parameters
    ----------
    datasets : list of pyvista.PolyData
        Datasets to merge. Non-PolyData items are ignored.
    extract_surface : bool, default True
        If ``True``, extract the outer surface after merging (useful for
        ray tracing or visualization). If ``False``, return the raw merged
        geometry (which may include volumetric cells).

    Returns
    -------
    pyvista.PolyData
        The merged geometry. If ``datasets`` is empty, returns an empty
        ``pyvista.PolyData``.

    Notes
    -----
    Uses a temporary ``pyvista.MultiBlock`` and ``combine()`` to merge inputs.
    If ``combine()`` returns a non-PolyData dataset, ``extract_geometry()``
    is used before the optional surface extraction.

    Examples
    --------
    >>> merged = merge_polydata([pd1, pd2, pd3], extract_surface=True)
    """
    if not datasets:
        return pyv.PolyData()

    mb = pyv.MultiBlock()
    for d in datasets:
        if isinstance(d, pyv.PolyData):
            mb.append(d)

    merged = mb.combine()
    if isinstance(merged, pyv.PolyData):
        return merged

    geom = merged.extract_geometry()
    return geom.extract_surface() if extract_surface else geom


def name_matches_flag(
    name: Optional[str],
    flags: Sequence[str],
    *,
    exact: bool = False,
    case_sensitive: bool = False
) -> bool:
    """
    Check whether a name matches any of the provided flags.

    Parameters
    ----------
    name : str or None
        Name to test. ``None`` never matches.
    flags : sequence of str
        Candidate flags to match against.
    exact : bool, default False
        If ``True``, require an exact equality; otherwise use substring match.
    case_sensitive : bool, default False
        If ``True``, comparisons are case sensitive; otherwise both the name
        and flags are lowercased prior to comparison.

    Returns
    -------
    bool
        ``True`` if a match is found under the chosen mode, ``False`` otherwise.

    Examples
    --------
    >>> name_matches_flag("PV_12", ["PV"])          # substring
    True
    >>> name_matches_flag("pv_12", ["PV"], case_sensitive=True)
    False
    >>> name_matches_flag("PV", ["PV","INV"], exact=True)
    True
    """
    if name is None:
        return False

    if not case_sensitive:
        name = name.lower()
        flags = [f.lower() for f in flags]

    if exact:
        return name in flags
    return any(flag in name for flag in flags)


def get_block_by_name(mb: pyv.MultiBlock, name: str) -> Optional[pyv.PolyData]:
    """
    Retrieve a child block by its name (O(n)).

    Parameters
    ----------
    mb : pyvista.MultiBlock
        Parent multiblock container.
    name : str
        Name to search for (as returned by ``mb.get_block_name(i)``).

    Returns
    -------
    pyvista.PolyData or None
        The matching block if found and it is a ``PolyData``; otherwise ``None``.

    Notes
    -----
    Iterates linearly over ``mb.n_blocks`` and returns the first name match.
    """
    for i in range(mb.n_blocks):
        if mb.get_block_name(i) == name:
            return mb[i]
    return None


# ----- MultiBlock Extensions -----

class MultiBlockPASE(pyv.MultiBlock):
    """
    PyVista ``MultiBlock`` extension with convenience filters and geometry queries.

    Notes
    -----
    - Treats blocks as PV-like panels by convention but works with any PolyData.
    - Naming-based filters allow selecting subsets without touching underlying data.
    """

    def get_polydata_by_flag(
        self,
        flag: Union[str, Iterable[str]],
        *,
        exact: bool = False,
        case_sensitive: bool = False,
    ) -> "MultiBlockPASE":
        """
        Filter blocks by name using one or multiple flags.

        Parameters
        ----------
        flag : str or Iterable[str]
            Flag(s) to match against block names (e.g., ``"PV"``).
        exact : bool, default False
            If ``True``, require exact equality with the block name; otherwise
            a substring match is used.
        case_sensitive : bool, default False
            If ``True``, comparisons are case sensitive.

        Returns
        -------
        MultiBlockPASE
            A new ``MultiBlockPASE`` containing only matching ``PolyData`` children,
            preserving their original names.

        Examples
        --------
        >>> pv_only = mb.get_polydata_by_flag("PV")
        >>> subset = mb.get_polydata_by_flag(["PV", "INV"], case_sensitive=True)
        """
        flags = [flag] if isinstance(flag, str) else list(flag)
        result = MultiBlockPASE()

        for i in range(self.n_blocks):
            name = self.get_block_name(i)
            if name_matches_flag(name, flags, exact=exact, case_sensitive=case_sensitive):
                child = self[i]
                if isinstance(child, pyv.PolyData):
                    result.append(child, name=name)

        return result

    # ---- Geometry Queries ----

    def get_lowest_corners(self, polydata: pyv.PolyData) -> np.ndarray:
        """
        Return the two lowest (in Z) distinct corners of a rectangular box.

        Parameters
        ----------
        polydata : pyvista.PolyData
            Rectangular parallelepiped (box-like) geometry.

        Returns
        -------
        numpy.ndarray, shape (2, 3)
            Two 3D points at the minimum Z level with different (x, y).

        Raises
        ------
        ValueError
            If the input has no points, if fewer than two lowest points exist,
            or if all lowest points share the same (x, y) (degenerate geometry).

        Notes
        -----
        Points are compared with tolerance ``EPS`` for Z and ``np.allclose`` for (x, y).
        """
        points = np.asarray(polydata.points, dtype=float)
        if points.size == 0:
            raise ValueError("PolyData has no points")

        z = points[:, 2]
        z_min = float(z.min())

        mask_lowest = np.abs(z - z_min) < EPS
        lowest_points = points[mask_lowest]

        if len(lowest_points) < 2:
            raise ValueError("Expected at least 2 points at minimum z for a rectangular box")

        first = lowest_points[0]
        for point in lowest_points[1:]:
            if not np.allclose(point[:2], first[:2], atol=EPS):
                return np.vstack([first, point])

        raise ValueError("All lowest points have same x,y coordinates (degenerate geometry)")

    def get_lowest_corners_multiblock(
        self,
        flag: Union[str, Iterable[str]] = ("PV",)
    ) -> np.ndarray:
        """
        Compute lowest-corner pairs for all blocks matching a flag.

        Parameters
        ----------
        flag : str or Iterable[str], default ("PV",)
            Name filter passed to ``get_polydata_by_flag``.

        Returns
        -------
        numpy.ndarray, shape (N, 2, 3)
            For each matching block, the two lowest corners. If no matches,
            returns an empty array with shape ``(0, 2, 3)``.

        See Also
        --------
        get_lowest_corners : Corner extraction for a single ``PolyData``.
        """
        geometry = self.get_polydata_by_flag(flag)
        corners = [self.get_lowest_corners(g) for g in geometry]
        return np.stack(corners, axis=0) if corners else np.empty((0, 2, 3), float)

    def get_area_multiblock(
        self,
        flag: Union[str, Iterable[str]] = ("PV",)
    ) -> np.ndarray:
        """
        Return surface areas for all blocks matching a flag.

        Parameters
        ----------
        flag : str or Iterable[str], default ("PV",)
            Name filter passed to ``get_polydata_by_flag``.

        Returns
        -------
        numpy.ndarray, shape (N,)
            Areas of each matching ``PolyData`` (as floats). Empty if no matches.
        """
        geometry = self.get_polydata_by_flag(flag)
        return np.array([float(g.area) for g in geometry], dtype=float)

    def get_z_min_multiblock(
        self,
        flag: Union[str, Iterable[str]] = ("PV",)
    ) -> np.ndarray:
        """
        Return minimum Z for all blocks matching a flag.

        Parameters
        ----------
        flag : str or Iterable[str], default ("PV",)
            Name filter passed to ``get_polydata_by_flag``.

        Returns
        -------
        numpy.ndarray, shape (N,)
            Minimum Z (lower bound of ``g.bounds``) per matching dataset.
        """
        geometry = self.get_polydata_by_flag(flag)
        return np.array([float(g.bounds[4]) for g in geometry], dtype=float)

    def get_normal_multiblock(
        self,
        flag: Union[str, Iterable[str]] = ("PV",)
    ) -> np.ndarray:
        """
        Estimate an average outward normal for each matching block.

        Parameters
        ----------
        flag : str or Iterable[str], default ("PV",)
            Name filter passed to ``get_polydata_by_flag``.

        Returns
        -------
        numpy.ndarray, shape (N, 3)
            Unit normals for each matching block. Falls back to
            ``DEFAULT_NORMAL`` when normals cannot be computed.

        Notes
        -----
        - Triangulates the geometry and computes **cell normals** only.
        - Discards invalid/zero-length normals; averages remaining unit normals.
        - Uses ``auto_orient_normals=True`` and ``consistent_normals=True`` for stability.

        Warnings
        --------
        If normal computation fails for a dataset, a warning is logged and
        ``DEFAULT_NORMAL`` is returned for that entry.
        """
        geometry = self.get_polydata_by_flag(flag)
        normals: List[np.ndarray] = []

        for g in geometry:
            try:
                gg = g.triangulate(copy=True).compute_normals(
                    cell_normals=True,
                    point_normals=False,
                    auto_orient_normals=True,
                    consistent_normals=True,
                )

                cell_normals = np.asarray(gg.cell_normals, float)

                if cell_normals.size == 0:
                    normals.append(DEFAULT_NORMAL.copy())
                    continue

                norms = np.linalg.norm(cell_normals, axis=1, keepdims=True)
                valid_mask = (norms[:, 0] > EPS) & np.isfinite(norms[:, 0])

                if not valid_mask.any():
                    normals.append(DEFAULT_NORMAL.copy())
                    continue

                unit_normals = cell_normals[valid_mask] / norms[valid_mask]
                mean_normal = unit_normals.mean(axis=0)
                mean_norm = np.linalg.norm(mean_normal)

                if not np.isfinite(mean_norm) or mean_norm <= EPS:
                    normals.append(DEFAULT_NORMAL.copy())
                else:
                    normals.append((mean_normal / mean_norm).astype(float))

            except Exception as e:
                logger.warning(f"Failed to compute normals for geometry: {e}")
                normals.append(DEFAULT_NORMAL.copy())

        return np.vstack(normals) if normals else np.empty((0, 3), float)


# ----- PV Configuration -----

class PVConfiguration3D(MultiBlockPASE):
    """
    3D PV plant configuration builder.

    Conventions
    -----------
    - Input angles (azimuth, tilt) are in **degrees**.
    - PyVista rotations use degrees internally.
    - Panels are named "PV_<ObjectID>".
    - Azimuth rotates around +Z axis (``rotate_z(-az_deg, ...)``).

    Tracking support
    ----------------
    Provides lazy tracking: you can attach tracker axes/pivots, set angles
    for a time ``t``, and build a merged ``PolyData`` snapshot for ray tracing
    without mutating the base geometry.
    """


    @staticmethod
    def _coerce_thickness(panel_thickness) -> float:
        """
        Normalize 'PanelThickness' to a thickness value in meters.
        Historical behavior:
        - False -> 0.0 (2D panels)
        - True  -> THICKNESS_TRUE_DEFAULT (3D panels with default thickness)
        Also accepts numeric values (float/int).
        """
        # Historical default when PanelThickness is boolean True (meters)
        THICKNESS_TRUE_DEFAULT = 0.10
        import numpy as _np  # local to avoid global dependency here
        if isinstance(panel_thickness, (bool, _np.bool_)) or type(panel_thickness) is bool:
            return float(THICKNESS_TRUE_DEFAULT) if panel_thickness else 0.0
        try:
            t = float(panel_thickness)
        except Exception as e:
            raise TypeError(f"PanelThickness must be bool or float, got {type(panel_thickness).__name__}") from e
        return 0.0 if t < 0 else t

    def __init__(self, **kwargs: Any):
        """
        Initialize an empty PV configuration.

        Parameters
        ----------
        **kwargs : Any
            Forwarded to ``MultiBlockPASE`` constructor.

        Attributes
        ----------
        object_id : int
            Next ObjectID to assign when creating panels.
        central_id : int
            Identifier that increments per generated "central" (grid).
        tracking_state : pandas.DataFrame or None
            Optional tracking state with MultiIndex ``(t, ObjectID) -> angles``.
        df : pandas.DataFrame
            Metadata table indexed by ``ObjectID`` (created in ``_init_dataframe``).
        """
        super().__init__(**kwargs)
        self.object_id: int = 0
        self.central_id: int = 0
        self._name_to_pos: Dict[str, int] = {}
        self._oid_to_pos: Dict[int, int] = {}
        self._poly_cache: Dict[Any, pyv.PolyData] = {}
        self.tracking_state: Optional[pd.DataFrame] = None  # MultiIndex (t, ObjectID) -> angles
        self._init_dataframe()

    # ---- Metadata table ----
    def _init_dataframe(self) -> None:
        """
        Initialize the metadata ``DataFrame`` with standard PV columns.

        Notes
        -----
        The resulting ``self.df`` is indexed by ``ObjectID`` and contains:
        ``Central, Block_X, Block_Y, Module_X, Module_Y, Type, Center, Bounds,
        Area, Azimuth_deg, Tilt_deg, HingePoint, HingeAxis, SecondAxis``.
        """
        self.df = pd.DataFrame(
            columns=[
                "Central",
                "Block_X",
                "Block_Y",
                "Module_X",
                "Module_Y",
                "Type",
                "Center",
                "Bounds",
                "Area",
                "Azimuth_deg",
                "Tilt_deg",
                # Tracking geometry (optional)
                "HingePoint",
                "HingeAxis",
                "SecondAxis",
            ]
        )
        self.df.index.name = "ObjectID"

    # ---- Indexing helpers ----
    def reindex(self) -> None:
        """
        Rebuild internal name and ObjectID position maps.

        Notes
        -----
        Scans all blocks to populate ``_name_to_pos`` and ``_oid_to_pos`` using:
        - block names (``self.get_block_name(i)``), and
        - ``ObjectID`` in block ``field_data``, if present.
        """
        self._name_to_pos.clear()
        self._oid_to_pos.clear()
        for i in range(self.n_blocks):
            name = self.get_block_name(i)
            if name:
                self._name_to_pos[name] = i
            blk = self[i]
            try:
                oid = int(np.asarray(blk.field_data.get("ObjectID"))[0])
                self._oid_to_pos[oid] = i
            except Exception:
                pass

    def get_position_by_oid(self, oid: int) -> Optional[int]:
        """
        Return block position for a given ``ObjectID``.

        Parameters
        ----------
        oid : int
            The panel ObjectID.

        Returns
        -------
        int or None
            The block index in the multiblock, or ``None`` if not found.

        Notes
        -----
        Falls back to scanning all blocks if cached maps miss.
        """
        pos = self._oid_to_pos.get(int(oid))
        if pos is not None:
            return pos
        name = f"PV_{oid}"
        pos = self._name_to_pos.get(name)
        if pos is not None:
            return pos
        # fallback scan
        for i in range(self.n_blocks):
            blk = self[i]
            try:
                if int(np.asarray(blk.field_data.get("ObjectID"))[0]) == oid:
                    return i
            except Exception:
                pass
        return None

    def get_block_by_oid(self, oid: int) -> Optional[pyv.PolyData]:
        """
        Get the ``PolyData`` block associated with an ``ObjectID``.

        Parameters
        ----------
        oid : int
            The panel ObjectID.

        Returns
        -------
        pyvista.PolyData or None
            The corresponding block, or ``None`` if absent.
        """
        pos = self.get_position_by_oid(oid)
        return None if pos is None else self[pos]

    def remove_by_oid(self, oid: int) -> bool:
        """
        Remove a block by ``ObjectID`` and update indices & metadata.

        Parameters
        ----------
        oid : int
            The panel ObjectID to remove.

        Returns
        -------
        bool
            ``True`` if a block was removed, ``False`` otherwise.

        Side Effects
        ------------
        - Rebuilds the multiblock without the removed item.
        - Drops the row from ``self.df`` if present.
        - Calls ``reindex()`` at the end.
        """
        pos = self.get_position_by_oid(oid)
        if pos is None:
            return False
        blocks = []
        names = []
        for i in range(self.n_blocks):
            if i == pos:
                continue
            blocks.append(self[i])
            names.append(self.get_block_name(i))
        self.clear()
        for b, n in zip(blocks, names):
            self.append(b, name=n)
        if oid in self.df.index:
            self.df = self.df.drop(index=oid)
        self.reindex()
        return True

    def assert_consistency(self) -> None:
        """
        Validate consistency between geometry blocks and metadata.

        Raises
        ------
        RuntimeError
            If some ``ObjectID`` in ``self.df`` is missing in blocks, or
            if there are blocks named ``PV_*`` without a matching row in ``self.df``.
        """
        missing = []
        for oid in self.df.index:
            if self.get_position_by_oid(int(oid)) is None:
                missing.append(int(oid))
        orphans = []
        for i in range(self.n_blocks):
            b = self[i]
            name = self.get_block_name(i) or ""
            if name.startswith("PV_"):
                try:
                    oid = int(np.asarray(b.field_data.get("ObjectID"))[0])
                except Exception:
                    oid = None
                if oid is None or oid not in self.df.index:
                    orphans.append((i, name, oid))
        if missing or orphans:
            raise RuntimeError(
                f"Inconsistency: missing_in_blocks={missing}, orphan_blocks={orphans}"
            )

    # ---- Defaults ----
    @staticmethod
    def _apply_defaults(pv_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default configuration values for optional keys.

        Parameters
        ----------
        pv_config : dict
            Input configuration.

        Returns
        -------
        dict
            A shallow copy of ``pv_config`` with defaults applied:
            - ``PanelThickness`` defaults to ``DEFAULT_PANEL_THICKNESS``.
            - ``MeshConfig`` defaults to ``False``.
        """
        config = dict(pv_config)
        config.setdefault("PanelThickness", DEFAULT_PANEL_THICKNESS)
        config.setdefault("MeshConfig", False)
        return config

    # ---- Panel primitives ----
    @staticmethod
    def _create_panel_2d(width: float, height: float, z_position: float = 0.0) -> pyv.PolyData:
        """
        Create a triangulated 2D rectangular panel as ``PolyData``.

        Parameters
        ----------
        width : float
            Panel width (X dimension).
        height : float
            Panel height (Y dimension).
        z_position : float, default=0.0
            Z coordinate of the rectangle plane.

        Returns
        -------
        pyvista.PolyData
            Triangulated rectangle mesh.
        """
        rect = pyv.Rectangle(
            [
                [-width / 2, height / 2, z_position],
                [width / 2, height / 2, z_position],
                [-width / 2, -height / 2, z_position],
            ]
        )
        return rect.triangulate()

    @staticmethod
    def _create_panel_3d(width: float, height: float, thickness: float) -> pyv.PolyData:
        """
        Create a triangulated 3D box panel as ``PolyData``.

        Parameters
        ----------
        width : float
            Panel width (X dimension).
        height : float
            Panel height (Y dimension).
        thickness : float
            Panel thickness (Z dimension).

        Returns
        -------
        pyvista.PolyData
            Triangulated box mesh centered at the origin.
        """
        half_thickness = thickness / 2.0
        box = pyv.Box(
            bounds=(
                -width / 2,
                width / 2,
                -height / 2,
                height / 2,
                -half_thickness,
                half_thickness,
            )
        )
        return box.triangulate()

    # ---- Grid maths ----
    def _compute_panel_grid_positions(
        self,
        num_blocks_x: int,
        num_blocks_y: int,
        panels_per_block_x: int,
        panels_per_block_y: int,
        block_spacing_x: float,
        block_spacing_y: float,
        panel_spacing_x: float,
        panel_spacing_y: float,
        base_height: float,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute panel positions and their parent block centers.

        Parameters
        ----------
        num_blocks_x, num_blocks_y : int
            Number of blocks along X/Y.
        panels_per_block_x, panels_per_block_y : int
            Number of panels per block along X/Y.
        block_spacing_x, block_spacing_y : float
            Center-to-center spacing between blocks along X/Y.
        panel_spacing_x, panel_spacing_y : float
            Center-to-center spacing between panels within a block along X/Y.
        base_height : float
            Base Z elevation for all panels.

        Returns
        -------
        positions : numpy.ndarray, shape (N, 3)
            World coordinates (x, y, z) for each panel instance.
        block_centers : numpy.ndarray, shape (N, 3)
            The corresponding block center (x, y, z) per panel.
        grid_indices : numpy.ndarray, shape (N, 4)
            Integer indices ``[BX, BY, MX, MY]`` for block and module coordinates.

        Notes
        -----
        ``N = num_blocks_x * num_blocks_y * panels_per_block_x * panels_per_block_y``.
        """
        """Compute positions and block centers vectorially."""
        total_span_x = (num_blocks_x - 1) * block_spacing_x + (panels_per_block_x - 1) * panel_spacing_x
        total_span_y = (num_blocks_y - 1) * block_spacing_y + (panels_per_block_y - 1) * panel_spacing_y

        bx = np.arange(num_blocks_x)
        by = np.arange(num_blocks_y)
        mx = np.arange(panels_per_block_x)
        my = np.arange(panels_per_block_y)

        BX, BY, MX, MY = np.meshgrid(bx, by, mx, my, indexing='ij')
        grid_indices = np.column_stack([BX.ravel(), BY.ravel(), MX.ravel(), MY.ravel()])

        offset_x = (
            grid_indices[:, 0] * block_spacing_x + grid_indices[:, 2] * panel_spacing_x - total_span_x / 2.0
        )
        offset_y = (
            grid_indices[:, 1] * block_spacing_y + grid_indices[:, 3] * panel_spacing_y - total_span_y / 2.0
        )
        offset_z = np.full_like(offset_x, base_height, dtype=float)
        positions = np.column_stack([offset_x, offset_y, offset_z])

        block_center_x = (
            grid_indices[:, 0] * block_spacing_x + (
                panels_per_block_x - 1) * panel_spacing_x / 2.0 - total_span_x / 2.0
        )
        block_center_y = (
            grid_indices[:, 1] * block_spacing_y + (
                panels_per_block_y - 1) * panel_spacing_y / 2.0 - total_span_y / 2.0
        )
        block_center_z = np.full_like(block_center_x, base_height, dtype=float)
        block_centers = np.column_stack([block_center_x, block_center_y, block_center_z])

        return positions, block_centers, grid_indices

    # ---- Generation ----
    def create_regular_central(self, pv_config: Dict[str, Any]) -> None:
        """
        Generate a regular grid (a "central") of PV panels, update geometry and metadata.

        Required Keys (angles in **degrees**)
        ---------------------------------
        PanelDimensionX, PanelDimensionY, PanelThickness,
        RepetitionDistanceOfPanelsX, RepetitionDistanceOfPanelsY,
        NumberOfPanelsX, NumberOfPanelsY,
        RepetitionDistanceOfPVBlocksX, RepetitionDistanceOfPVBlocksY,
        NumberOfPVBlocksX, NumberOfPVBlocksY,
        Height, CentralAzimut, TiltY

        Parameters
        ----------
        pv_config : dict
            Configuration dictionary. Missing optional keys are defaulted by
            ``_apply_defaults``.

        Raises
        ------
        ValueError
            If required parameters are missing, counts < 1, or dimensions <= 0.

        Notes
        -----
        - Angles are provided in **radians** but converted to **degrees** for PyVista.
        - Each created panel receives ``field_data``: ``ObjectID`` (int64) and ``Type=1`` (int32).
        - Appends the created panels to the multiblock, updates ``self.df``,
          and increments ``central_id`` and ``object_id`` accordingly.
        """
        config = self._apply_defaults(pv_config)

        required = [
            "PanelDimensionX", "PanelDimensionY", "PanelThickness",
            "RepetitionDistanceOfPanelsX", "RepetitionDistanceOfPanelsY",
            "NumberOfPanelsX", "NumberOfPanelsY",
            "RepetitionDistanceOfPVBlocksX", "RepetitionDistanceOfPVBlocksY",
            "NumberOfPVBlocksX", "NumberOfPVBlocksY",
            "Height", "CentralAzimut", "TiltY",
        ]
        missing = [k for k in required if k not in config]
        if missing:
            raise ValueError(f"Missing required parameters: {', '.join(missing)}")

        # Extract & validate
        panel_width = float(config["PanelDimensionX"])  # X
        panel_height = float(config["PanelDimensionY"])  # Y
        thickness = self._coerce_thickness(config["PanelThickness"])  # Z thickness (0 => 2D)
        #print(thickness)

        panel_spacing_x = float(config["RepetitionDistanceOfPanelsX"])  # pitch X
        panel_spacing_y = float(config["RepetitionDistanceOfPanelsY"])  # pitch Y
        panels_per_block_x = int(config["NumberOfPanelsX"])  # per block
        panels_per_block_y = int(config["NumberOfPanelsY"])  # per block

        block_spacing_x = float(config["RepetitionDistanceOfPVBlocksX"])  # block pitch X
        block_spacing_y = float(config["RepetitionDistanceOfPVBlocksY"])  # block pitch Y
        num_blocks_x = int(config["NumberOfPVBlocksX"])  # blocks
        num_blocks_y = int(config["NumberOfPVBlocksY"])  # blocks

        base_height = float(config["Height"])  # elevation
        azimuth_deg = float(config["CentralAzimut"])  # degrees
        tilt_deg = float(config["TiltY"])            # degrees

        if any(n < 1 for n in [panels_per_block_x, panels_per_block_y, num_blocks_x, num_blocks_y]):
            raise ValueError("All count parameters must be >= 1")
        if any(v <= 0 for v in
               [panel_width, panel_height, panel_spacing_x, panel_spacing_y, block_spacing_x, block_spacing_y]):
            raise ValueError("All dimension parameters must be > 0")

        # Angles already in degrees (PyVista expects degrees)

        # Base panel primitive
        if thickness > 0.0:
            base_panel = self._create_panel_3d(panel_width, panel_height, thickness)
        else:
            base_panel = self._create_panel_2d(panel_width, panel_height, 0.0)

        # Compute all positions & block centers
        positions, block_centers, grid_indices = self._compute_panel_grid_positions(
            num_blocks_x, num_blocks_y,
            panels_per_block_x, panels_per_block_y,
            block_spacing_x, block_spacing_y,
            panel_spacing_x, panel_spacing_y,
            base_height,
        )

        # Precompute area (constant per panel primitive)
        base_area = float(panel_width * panel_height)

        # ---- Creation loop (vectorized positions + single loop) ----
        pieces: List[Tuple[int, pyv.PolyData]] = []
        df_rows: Dict[int, Dict[str, Any]] = {}
        N = positions.shape[0]

        for idx in range(N):
            bx, by, mx, my = map(int, grid_indices[idx])
            offx, offy, offz = map(float, positions[idx])
            cx, cy, cz = map(float, block_centers[idx])

            panel = (
                base_panel.copy()
                .translate([offx, offy, offz])
                .rotate_y(tilt_deg, point=(cx, cy, cz))
                .rotate_z(-azimuth_deg, point=(0.0, 0.0, 0.0))
            )

            oid = self.object_id
            name = f"PV_{oid}"

            # field_data for robust mapping
            try:
                panel.field_data["ObjectID"] = np.array([oid], dtype=np.int64)
                panel.field_data["Type"] = np.array([1], dtype=np.int32)  # 1 = PV
            except Exception:
                pass

            pieces.append((oid, panel))
            df_rows[oid] = {
                "Central": self.central_id,
                "Block_X": bx,
                "Block_Y": by,
                "Module_X": mx,
                "Module_Y": my,
                "Type": "PV",
                "Center": tuple(map(float, panel.center)),
                "Bounds": tuple(map(float, panel.bounds)),
                "Area": base_area,  # area preserved under rigid transforms
                "Azimuth_deg": azimuth_deg,
                "Tilt_deg": tilt_deg,
                # Default tracking geometry: per-panel center pivot, X then Y axes
                "HingePoint": (float(panel.center[0]), float(panel.center[1]), float(panel.center[2])),
                "HingeAxis": (1.0, 0.0, 0.0),
                "SecondAxis": (0.0, 1.0, 0.0),
            }

            # Advance ObjectID and caches (temporary indices are overwritten after append)
            self.object_id += 1

        # Append to MultiBlock in a second pass
        start_pos = self.n_blocks
        for k, (oid, panel) in enumerate(pieces):
            name = f"PV_{oid}"
            self.append(panel, name=name)
            self._name_to_pos[name] = start_pos + k
            self._oid_to_pos[oid] = start_pos + k

        # Update DataFrame
        if df_rows:
            df_new = pd.DataFrame.from_dict(df_rows, orient="index")
            df_new.index.name = "ObjectID"
            self.df = pd.concat([self.df, df_new])

        # Bump central ID
        self.central_id += 1

    # ---- Query helpers ----
    def polydata_by_central(self, central_ids: Iterable[int] | int, *, extract_surface: bool = True) -> pyv.PolyData:
        """
        Merge and return the geometry for one or more central IDs.

        Parameters
        ----------
        central_ids : Iterable[int] or int
            Central identifier(s) to include.
        extract_surface : bool, default=True
            If ``True``, extract surfaces before merging (useful for ray tracing).

        Returns
        -------
        pyvista.PolyData
            Merged dataset of all panels matching the given central(s).

        Examples
        --------
        >>> pd0 = cfg.polydata_by_central(0)
        >>> pd01 = cfg.polydata_by_central([0, 1])
        """
        if isinstance(central_ids, int):
            centrals = {central_ids}
        else:
            centrals = set(int(c) for c in central_ids)
        idx = self.df.index[self.df["Central"].isin(list(centrals))]
        dsets: List[pyv.PolyData] = []
        for oid in idx:
            blk = self.get_block_by_oid(int(oid))
            if isinstance(blk, pyv.PolyData):
                dsets.append(blk)
        return merge_polydata(dsets, extract_surface=extract_surface)

    def polydata_by_property(self, property_dict: Dict[str, Iterable[Any]], *,
                             extract_surface: bool = True) -> pyv.PolyData:
        """
        Merge and return geometry filtered by multiple properties (AND semantics).

        Parameters
        ----------
        property_dict : dict[str, Iterable[Any]]
            Mapping of column name -> allowed values. All conditions must be met.
        extract_surface : bool, default=True
            If ``True``, extract surfaces before merging.

        Returns
        -------
        pyvista.PolyData
            Merged dataset of all panels matching the property filter.

        Raises
        ------
        KeyError
            If a property name is not a column in ``self.df``.

        Examples
        --------
        Select all PV panels in block X ∈ {0, 1}:

        >>> pd = cfg.polydata_by_property({"Block_X": [0, 1], "Type": ["PV"]})
        """
        if not property_dict:
            return pyv.PolyData()
        mask = pd.Series(True, index=self.df.index)
        for prop, values in property_dict.items():
            if prop not in self.df.columns:
                valid = ", ".join(self.df.columns)
                raise KeyError(f"Unknown property: {prop}. Valid: {valid}")
            mask &= self.df[prop].isin(list(values))
        idx = self.df.index[mask]
        dsets: List[pyv.PolyData] = []
        for oid in idx:
            blk = self.get_block_by_oid(int(oid))
            if isinstance(blk, pyv.PolyData):
                dsets.append(blk)
        return merge_polydata(dsets, extract_surface=extract_surface)



    # --- Convenience: all centrals merged ---
    def polydata_all_centrals(self, *, extract_surface: bool = True) -> pyv.PolyData:
        """Merge the geometry of all existing centrals into a single PolyData."""
        if self.df.empty:
            return pyv.PolyData()
        centrals = sorted(set(int(c) for c in self.df["Central"].unique()))
        return self.polydata_by_central(centrals, extract_surface=extract_surface)

# --------- Backward-compatible alias for PASE 1.x ----------
class PV_Configuration_3D(PVConfiguration3D):
    """Backward-compatible alias with legacy signature (params_dict, solar_vector=None, visualization=False)."""
    def __init__(self, params_dict: Optional[Dict[str, Any]] = None, *_ignore,
                 visualization: bool = False, **__ignore) -> None:
        super().__init__()
        if params_dict is not None:
            self.create_regular_central(params_dict)
        # 'visualization' kept for signature compatibility (no auto-render here).

    @property
    def PV_central_PD(self) -> pyv.PolyData:
        """Merged PolyData of all centrals (as expected by Ray_casting_scene)."""
        return self.polydata_all_centrals(extract_surface=True)

    @property
    def PV_central_MB(self) -> 'MultiBlockPASE':
        """MultiBlock subset of PV* blocks, for legacy compatibility."""
        return self.get_polydata_by_flag("PV")

