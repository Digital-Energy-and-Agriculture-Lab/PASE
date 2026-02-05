#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
# Author : Nicolas De Cock (nicolas.decock1@gmail.com)
# This file is part of the PASE software, and is distributed under the MIT license.

"""
Mesh utilities for scene sampling.

The goal of this module is to provide readable and robust helpers to create
scene meshes that will later be used by light computations.  The new
implementation focuses on clarity while keeping the operations explicit and
safe.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import pyvista as pv


VectorLike = Union[Tuple[float, float, float], List[float], np.ndarray]


class Mesh:
    """Create and track meshes used in the light scene.

    The class exposes utilities to generate rectangular or triangular surfaces,
    import meshes from configuration objects, or wrap existing polydata.  Each
    mesh is stored in a :class:`pyvista.MultiBlock` container with metadata that
    records how it was produced.  This makes it straightforward to retrieve
    centers, normals, and areas for any registered mesh.
    """

    def __init__(self, default_azimut: float = 0.0) -> None:
        self.meshes = pv.MultiBlock()
        self.metadata = pd.DataFrame(
            columns=["id", "name", "type", "parameters"], dtype=object
        )
        # Orientation par défaut de la zone d'intérêt ("zone_azimut")
        self.default_azimut = default_azimut

    # ======================================================================
    # Public API
    # ======================================================================

    def add_rectangular_surface(
        self,
        width: float,
        height: float,
        density: float,
        name: str = "rectangular_surface",
        center: VectorLike = (0.0, 0.0, 0.0),
        normal: VectorLike = (0.0, 0.0, 1.0),
        reference_direction: Optional[VectorLike] = None,
        face_type: str = "triangle",
    ) -> int:
        """Create a rectangular surface subdivided into triangles or rectangles.

        The rectangle can be inclined by providing a custom normal.  A
        reference direction sets the axis used for the width; when omitted, an
        orthogonal direction is computed automatically.  The ``face_type``
        parameter controls whether each cell is triangulated (default) or kept
        as a rectangle, enabling a mix of face types across meshes.
        """

        normal_vector = _normalize_vector(normal)
        center_vector = _to_array(center)

        width_direction = self._compute_width_direction(normal_vector, reference_direction)
        height_direction = np.cross(normal_vector, width_direction)
        height_direction = _normalize_vector(height_direction)

        num_width_divisions = _division_count(width, density)
        num_height_divisions = _division_count(height, density)

        grid_points = self._build_rectangular_grid(
            center=center_vector,
            width=width,
            height=height,
            width_direction=width_direction,
            height_direction=height_direction,
            num_width_divisions=num_width_divisions,
            num_height_divisions=num_height_divisions,
        )

        normalized_face_type = face_type.lower()
        if normalized_face_type == "triangle":
            faces = _triangulate_grid(num_width_divisions, num_height_divisions)
        elif normalized_face_type == "rectangle":
            faces = _rectangularize_grid(num_width_divisions, num_height_divisions)
        else:
            raise ValueError("face_type must be either 'triangle' or 'rectangle'.")
        polydata = pv.PolyData(grid_points, faces=faces)

        return self._register_mesh(
            polydata=polydata,
            name=name,
            mesh_type="rectangular_surface",
            parameters={
                "width": width,
                "height": height,
                "density": density,
                "center": center_vector.tolist(),
                "normal": normal_vector.tolist(),
                "reference_direction": None
                if reference_direction is None
                else _to_array(reference_direction).tolist(),
                "face_type": normalized_face_type,
            },
        )

    def add_oriented_plane_ground_mesh(
        self,
        X_min: float,
        X_max: float,
        Y_min: float,
        Y_max: float,
        X_increment: float,
        Y_increment: float,
        azimuth_deg: Optional[float] = None,
        flag: str = "ground",
        zcoord: float = 0.0,
    ) -> int:
        """Créer une surface rectangulaire au sol orientée par un azimut.

        Cette méthode maintient le concept de ``zone_azimut`` : si aucun azimut
        n'est fourni, on utilise l'orientation par défaut définie pour la zone
        d'intérêt. Les paramètres ``X_increment`` et ``Y_increment`` sont
        convertis en une densité minimale pour générer le maillage.
        """

        azimuth_to_use = self.default_azimut if azimuth_deg is None else azimuth_deg

        width = X_max - X_min
        height = Y_max - Y_min
        center = ((X_min + X_max) / 2.0, (Y_min + Y_max) / 2.0, zcoord)

        density = min(X_increment, Y_increment)
        reference_direction = _direction_from_azimuth(azimuth_to_use)

        return self.add_rectangular_surface(
            width=width,
            height=height,
            density=density,
            name=flag,
            center=center,
            normal=(0.0, 0.0, 1.0),
            reference_direction=reference_direction,
            face_type="triangle",
        )

    def import_from_pvconfiguration(
        self,
        pv_objects: Iterable[pv.PolyData],
        name: str = "pv_configuration",
        include_top: bool = True,
        include_bottom: bool = False,
        density: float = 0.5,
        property_filter: Optional[Callable[[pv.PolyData], bool]] = None,
        property_dict: Optional[Dict[str, Iterable[Any]]] = None,

    ) -> List[int]:
        """Create meshes for all polydata that match optional property filters.

        The method distinguishes between the top and bottom faces based on the
        Z component of the face normals, enabling targeted sampling of
        photovoltaic surfaces. When ``property_dict`` is provided and the
        input object exposes a ``df`` DataFrame (as with ``MultiBlockPASE``),
        the properties are used to pre-filter the blocks by column values
        (e.g. ``Block_X`` or ``Block_Y``). Use ``property_filter`` to apply an
        additional boolean filter on each PolyData, for example:

        >>> def keep_large_panels(poly):
        ...     return poly.area > 1.0
        >>> mesh.import_from_pvconfiguration(pv_objects, property_filter=keep_large_panels)
        """

        added_indices: List[int] = []
        if property_dict is not None and hasattr(pv_objects, "df") and hasattr(pv_objects, "get_block_by_oid"):
            df = pv_objects.df
            mask = pd.Series(True, index=df.index)
            for prop, values in property_dict.items():
                if prop not in df.columns:
                    valid = ", ".join(df.columns)
                    raise KeyError(f"Unknown property: {prop}. Valid: {valid}")
                mask &= df[prop].isin(list(values))
            idx = df.index[mask]
            iterable = []
            for oid in idx:
                block = pv_objects.get_block_by_oid(int(oid))
                if isinstance(block, pv.PolyData):
                    iterable.append(block)
        else:
            iterable = pv_objects

        for index, polydata in enumerate(iterable):
            if property_filter is not None and not property_filter(polydata):
                continue

            triangulated = polydata.triangulate()
            normalised = triangulated.compute_normals(cell_normals=True, point_normals=False)

            face_mask = _select_faces_by_orientation(
                polydata=normalised,
                include_top=include_top,
                include_bottom=include_bottom,
            )

            filtered_polydata = normalised.extract_cells(face_mask)
            refined_polydata = _subdivide_for_density(filtered_polydata, density)

            registration_id = self._register_mesh(
                polydata=refined_polydata,
                name=f"{name}_{index}",
                mesh_type="pvconfiguration_import",
                parameters={
                    "include_top": include_top,
                    "include_bottom": include_bottom,
                    "density": density,
                },
            )
            added_indices.append(registration_id)

        return added_indices

    def add_triangular_probe(
        self,
        position: VectorLike,
        normal: VectorLike,
        area: float,
        name: str = "triangular_probe",
    ) -> int:
        """Add a small triangular surface centered on a position."""

        normal_vector = _normalize_vector(normal)
        position_vector = _to_array(position)

        side_length = _equilateral_side_length(area)
        base_direction = self._compute_width_direction(normal_vector, reference_direction=None)
        height_direction = np.cross(normal_vector, base_direction)
        height_direction = _normalize_vector(height_direction)

        base_offset = base_direction * (side_length / 2.0)
        height_offset = height_direction * (math.sqrt(3.0) * side_length / 6.0)

        first_vertex = position_vector + base_offset + height_offset
        second_vertex = position_vector - base_offset + height_offset
        third_vertex = position_vector - height_direction * (math.sqrt(3.0) * side_length / 3.0)

        points = np.vstack([first_vertex, second_vertex, third_vertex])
        faces = np.hstack([[3, 0, 1, 2]])
        polydata = pv.PolyData(points, faces=faces)

        return self._register_mesh(
            polydata=polydata,
            name=name,
            mesh_type="triangular_probe",
            parameters={"position": position_vector.tolist(), "normal": normal_vector.tolist(), "area": area},
        )

    def set_interest_zone_orientation(
        self, Loc_1: Dict[str, object], AV_1: Dict[str, object]
    ) -> float:
        """Définir l'orientation par défaut (zone_azimut) de la zone d'intérêt.

        Modes disponibles dans ``Loc_1['InterestZoneOrientationMode']`` :

        - ``default`` : azimut = 0°
        - ``auto`` : azimut = ``AV_1['CentralAzimut']``
        - ``custom`` : azimut = ``Loc_1['InterestZoneCustomAngle']``
        """

        try:
            mode = str(Loc_1.get("InterestZoneOrientationMode", "default"))
            custom_angle = Loc_1.get("InterestZoneCustomAngle", 0)
        except Exception as exc:  # pragma: no cover - defensive fallback
            raise ValueError("Invalid orientation configuration") from exc

        mode_lower = mode.lower()
        if mode_lower == "default":
            zone_azimut = 0.0
        elif mode_lower == "auto":
            zone_azimut = float(AV_1["CentralAzimut"])
        elif mode_lower == "custom":
            zone_azimut = float(custom_angle)
        else:
            raise ValueError(f"Unknown InterestZoneOrientationMode: {mode}")

        self.default_azimut = zone_azimut
        return zone_azimut

    def add_polydata(
        self,
        polydata: pv.PolyData,
        name: str = "polydata",
        control_point_amount: bool = False,
    ) -> int:
        """Register an existing polydata mesh and optionally clean point counts."""

        if control_point_amount:
            cleaned = polydata.clean(point_merging=True)
            polydata_to_use = cleaned
        else:
            polydata_to_use = polydata.copy(deep=True)

        return self._register_mesh(
            polydata=polydata_to_use,
            name=name,
            mesh_type="polydata_import",
            parameters={"control_point_amount": control_point_amount},
        )

    def get_mesh_data(
        self,
        identifier: Union[int, str],
    ) -> Dict[str, np.ndarray]:
        """Return centers, normals, and areas for a mesh referenced by ID or name."""

        mesh_index = self._resolve_mesh_index(identifier)
        if isinstance(mesh_index,int):
            polydata = self.meshes[mesh_index]
        else:
            polydata = pv.MultiBlock([self.meshes[i] for i in mesh_index]).combine().extract_surface()

        cell_centers = polydata.cell_centers().points
        normals = polydata.compute_normals(cell_normals=True, point_normals=False).cell_data["Normals"]
        areas = polydata.compute_cell_sizes(length=False, area=True, volume=False).cell_data["Area"]

        return {"centers": cell_centers, "normals": normals, "areas": areas}

    def get_sourcepoints(self) -> np.ndarray:
        """Return the cell centers of every mesh as a single (n, 3) array."""

        centers: List[np.ndarray] = []
        for block in self.meshes:
            polydata = pv.PolyData(block)
            block_centers = polydata.cell_centers().points
            if block_centers.size:
                centers.append(block_centers)

        if not centers:
            return np.empty((0, 3))

        return np.vstack(centers)

    @property
    def sourcepoints(self) -> np.ndarray:
        """Return the cell centers of every mesh as a single (n, 3) array."""

        return self.get_sourcepoints()

    # ======================================================================
    # Private helpers
    # ======================================================================

    def _register_mesh(
        self,
        polydata: pv.PolyData,
        name: str,
        mesh_type: str,
        parameters: Dict[str, object],
    ) -> int:
        """Store a mesh and its metadata, returning its registration index."""
        mesh_id = len(self.meshes)
        self.meshes.append(polydata)

        metadata_entry = {
            "id": mesh_id,
            "name": name,
            "type": mesh_type,
            "parameters": parameters,
        }
        self.metadata = pd.concat(
            [self.metadata, pd.DataFrame([metadata_entry])],
            ignore_index=True,
        )

        return mesh_id

    def _compute_width_direction(
        self,
        normal: np.ndarray,
        reference_direction: Optional[VectorLike],
    ) -> np.ndarray:
        """Return a unit vector perpendicular to ``normal`` to span the width."""
        if reference_direction is not None:
            candidate = _normalize_vector(reference_direction)
        else:
            fallback_axis = np.array([1.0, 0.0, 0.0])
            if np.allclose(np.cross(normal, fallback_axis), 0.0):
                fallback_axis = np.array([0.0, 1.0, 0.0])
            candidate = fallback_axis

        width_direction = np.cross(normal, np.cross(candidate, normal))
        width_direction = _normalize_vector(width_direction)
        return width_direction

    def _build_rectangular_grid(
        self,
        center: np.ndarray,
        width: float,
        height: float,
        width_direction: np.ndarray,
        height_direction: np.ndarray,
        num_width_divisions: int,
        num_height_divisions: int,
    ) -> np.ndarray:
        """Generate grid points covering a rectangle defined by center and axes."""
        half_width = width / 2.0
        half_height = height / 2.0

        width_positions = np.linspace(-half_width, half_width, num_width_divisions + 1)
        height_positions = np.linspace(-half_height, half_height, num_height_divisions + 1)

        grid_points: List[np.ndarray] = []
        for height_offset in height_positions:
            for width_offset in width_positions:
                offset_vector = width_direction * width_offset + height_direction * height_offset
                point = center + offset_vector
                grid_points.append(point)

        return np.vstack(grid_points)

    def _resolve_mesh_index(
        self, identifier: Union[int, str, Iterable[int]]
    ) -> Union[int, List[int]]:
        """Translate a mesh id or name into its numerical index."""
        if isinstance(identifier, int):
            return identifier
        if isinstance(identifier, (list, tuple, np.ndarray)):
            if not identifier:
                return []

            if all(isinstance(item, int) for item in identifier):
                return [int(item) for item in identifier]

            if all(isinstance(item, str) for item in identifier):
                return [self._resolve_mesh_index(item) for item in identifier]

            raise TypeError("Mesh identifier list must contain only int or only str values.")

        matches = self.metadata[self.metadata["name"] == identifier]
        if matches.empty:
            raise KeyError(f"Unknown mesh name: {identifier}")

        return int(matches.iloc[0]["id"])

    def compute_homogeneity(self, identifier: Union[int, str]) -> float:
        """Quantify point distribution homogeneity using coefficient of variation."""

        mesh_data = self.get_mesh_data(identifier)
        centers = mesh_data["centers"]

        if centers.shape[0] < 2:
            return 0.0

        distances = _nearest_neighbor_distances(centers)
        mean_distance = float(np.mean(distances))
        std_distance = float(np.std(distances))

        if math.isclose(mean_distance, 0.0):
            return 0.0

        coefficient_of_variation = std_distance / mean_distance
        return coefficient_of_variation


# ======================================================================
# Standalone helper functions
# ======================================================================


def _to_array(vector: VectorLike) -> np.ndarray:
    """Convert a vector-like object into a NumPy array of floats."""
    array = np.asarray(vector, dtype=float)
    return array


def _normalize_vector(vector: VectorLike) -> np.ndarray:
    """Return a unit-length array from the provided vector-like object."""
    array = _to_array(vector)
    norm = np.linalg.norm(array)
    if math.isclose(norm, 0.0):
        raise ValueError("Cannot normalize a zero-length vector.")
    return array / norm


def _direction_from_azimuth(azimuth_deg: float) -> np.ndarray:
    """Compute a unit vector in the XY plane from an azimuth angle (degrees)."""

    theta = math.radians(azimuth_deg)
    return np.array([math.cos(theta), math.sin(theta), 0.0])


def _division_count(length: float, density: float) -> int:
    """Determine how many subdivisions are required to meet a target density."""
    minimum_divisions = 1
    estimated_divisions = int(math.ceil(length / max(density, 1e-6)))
    return max(minimum_divisions, estimated_divisions)


def _triangulate_grid(width_divisions: int, height_divisions: int) -> np.ndarray:
    """Return faces for a grid tessellated into triangles."""
    faces: List[int] = []

    row_length = width_divisions + 1
    for height_index in range(height_divisions):
        for width_index in range(width_divisions):
            bottom_left = height_index * row_length + width_index
            bottom_right = bottom_left + 1
            top_left = bottom_left + row_length
            top_right = top_left + 1

            faces.extend([3, bottom_left, bottom_right, top_right])
            faces.extend([3, bottom_left, top_right, top_left])

    return np.array(faces, dtype=int)


def _rectangularize_grid(width_divisions: int, height_divisions: int) -> np.ndarray:
    """Return faces for a grid represented as rectangles."""
    faces: List[int] = []

    row_length = width_divisions + 1
    for height_index in range(height_divisions):
        for width_index in range(width_divisions):
            bottom_left = height_index * row_length + width_index
            bottom_right = bottom_left + 1
            top_left = bottom_left + row_length
            top_right = top_left + 1

            faces.extend([4, bottom_left, bottom_right, top_right, top_left])

    return np.array(faces, dtype=int)


def _select_faces_by_orientation(
    polydata: pv.PolyData,
    include_top: bool,
    include_bottom: bool,
) -> np.ndarray:
    """Select faces with normals oriented toward the top and/or bottom."""
    normals = polydata.cell_data["Normals"]
    z_components = normals[:, 2]

    top_mask = z_components > 0.0
    bottom_mask = z_components < 0.0

    if include_top and include_bottom:
        return np.ones_like(z_components, dtype=bool)
    if include_top:
        return top_mask
    if include_bottom:
        return bottom_mask

    return np.zeros_like(z_components, dtype=bool)


def _subdivide_for_density(polydata: pv.PolyData, density: float) -> pv.PolyData:
    """Refine a surface mesh until subdivision spacing approximates density."""
    if density <= 0:
        return polydata.copy(deep=True)

    surface = polydata.extract_surface().triangulate()

    bounds = surface.bounds
    width = abs(bounds[1] - bounds[0])
    height = abs(bounds[3] - bounds[2])
    average_dimension = (width + height) / 2.0

    target_divisions = _division_count(average_dimension, density)
    subdivisions = max(0, target_divisions - 1)

    subdivided = surface.subdivide(subdivisions)
    if "Normals" not in subdivided.cell_data:
        subdivided = subdivided.compute_normals(cell_normals=True, point_normals=False)

    return subdivided


def _equilateral_side_length(area: float) -> float:
    """Compute the side length of an equilateral triangle with the given area."""
    if area <= 0.0:
        raise ValueError("Area must be positive to create a triangular probe.")

    side_length = math.sqrt((4.0 * area) / math.sqrt(3.0))
    return side_length


def _nearest_neighbor_distances(points: np.ndarray) -> np.ndarray:
    """Calculate distances to the nearest neighbor for each point in a set."""
    distances: List[float] = []
    for index, origin in enumerate(points):
        other_points = np.delete(points, index, axis=0)
        deltas = other_points - origin
        norms = np.linalg.norm(deltas, axis=1)
        nearest = float(np.min(norms))
        distances.append(nearest)

    return np.asarray(distances)


