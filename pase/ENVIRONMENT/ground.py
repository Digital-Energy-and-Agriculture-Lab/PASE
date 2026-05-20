"""
Ground abstraction for terrain-aware PV structure placement.

Three concrete implementations:

    Ground()                                              — flat ground at z = 0 (default)
    SlopedGround(terrain_normal_azimuth,
                 terrain_normal_elevation)                — tilted plane
    DEMGround(terrain)                                    — real DEM from a pv.PolyData surface

All share the same interface:

    .elevation(x, y)  → float          z at position (x, y)
    .normal(x, y)     → ndarray        unit normal vector at (x, y)
    .gradient(x, y)   → (float, float) (dz/dx, dz/dy) at (x, y)
    .contains(x, y)   → bool           is (x, y) within the ground extent?
    .to_polydata(x_range, y_range, resolution) → pv.PolyData

Parameter conventions (SlopedGround)
--------------------------------------
TerrainNormalAzimuth   — horizontal azimuth of the surface normal [°],
                         meteorological convention: 0°=North, 90°=East,
                         180°=South, 270°=West.
                         Equal to the downhill direction (the normal's
                         horizontal projection points the same way as the
                         slope falls).
TerrainNormalElevation — elevation angle of the surface normal above the
                         horizontal plane [°].
                         90° → flat terrain (normal points straight up).
                         60° → 30° slope.   0° → vertical wall.

Open-design-question answers (from issue #14)
---------------------------------------------
- TerrainNormalElevation = 90  →  panel horizontal (normal points vertically upward).
- Tracking axis option: horizontal or slope-aligned (to be added).
- Slope pivots around (0, 0, 0).
- Out-of-bounds (x, y) on a DEMGround raises ValueError.
"""

from __future__ import annotations

import math
import numpy as np
import pyvista as pv


# ── Utility functions ─────────────────────────────────────────────────────────

def rotation_from_z_to_normal(n: np.ndarray) -> np.ndarray:
    """
    3 × 3 rotation matrix that maps (0, 0, 1) onto unit normal *n*.

    Uses Rodrigues' formula.  Returns the identity when n ≈ (0, 0, 1).
    """
    n = np.asarray(n, dtype=float)
    n = n / np.linalg.norm(n)
    z = np.array([0.0, 0.0, 1.0])
    axis = np.cross(z, n)
    sin_a = float(np.linalg.norm(axis))
    cos_a = float(np.dot(z, n))

    if sin_a < 1e-10:
        return np.eye(3) if cos_a > 0 else -np.eye(3)

    axis /= sin_a
    K = np.array([
        [ 0,       -axis[2],  axis[1]],
        [ axis[2],  0,       -axis[0]],
        [-axis[1],  axis[0],  0      ],
    ])
    return np.eye(3) + sin_a * K + (1 - cos_a) * (K @ K)


def apply_rotation_matrix(
    polydata: pv.PolyData,
    R: np.ndarray,
    pivot: tuple = (0.0, 0.0, 0.0),
) -> pv.PolyData:
    """
    Apply 3 × 3 rotation matrix *R* to *polydata* around *pivot* (in-place).
    """
    pts = polydata.points - np.array(pivot)
    polydata.points = (R @ pts.T).T + np.array(pivot)
    return polydata


def block_reference_elevation(
    ground: "Ground",
    cx: float,
    cy: float,
    half_x: float,
    half_y: float,
    azimuth_deg: float = 0.0,
) -> float:
    """
    Return the maximum terrain elevation over the 4 corners of a block footprint.

    The block is an axis-aligned rectangle ``[cx ± half_x] × [cy ± half_y]`` in
    the pre-rotation (central) frame.  Corners are mapped to world coordinates
    by rotating by ``-azimuth_deg`` about the origin before sampling the ground.

    Anchoring PV blocks (panels + structure) at this elevation — rather than at
    the ground elevation at their center — guarantees that no component of the
    block sits below the terrain on a slope, since on a tilted plane the
    maximum elevation over a rectangle is always attained at one of its corners.
    """
    az = math.radians(azimuth_deg)
    cos_az, sin_az = math.cos(az), math.sin(az)
    z_max = -math.inf
    for dx in (-half_x, half_x):
        for dy in (-half_y, half_y):
            x_pre = cx + dx
            y_pre = cy + dy
            x_w = x_pre * cos_az + y_pre * sin_az
            y_w = -x_pre * sin_az + y_pre * cos_az
            z = float(ground.elevation(x_w, y_w))
            if z > z_max:
                z_max = z
    return z_max


# ── Base class — flat ground ──────────────────────────────────────────────────

class Ground:
    """Flat ground at z = 0.  All queries always return True for contains()."""

    def elevation(self, x, y) -> float | np.ndarray:
        """Return z at (x, y).  Accepts scalars or NumPy arrays."""
        return np.zeros_like(np.asarray(x, dtype=float))

    def normal(self, x, y) -> np.ndarray:
        """Return unit normal at (x, y)."""
        return np.array([0.0, 0.0, 1.0])

    def gradient(self, x, y) -> tuple[float, float]:
        """Return (dz/dx, dz/dy) at (x, y)."""
        return (0.0, 0.0)

    def contains(self, x, y) -> bool:
        """Return True — flat ground is an infinite plane."""
        return True

    def to_polydata(
        self,
        x_range: tuple[float, float],
        y_range: tuple[float, float],
        resolution: float = 1.0,
    ) -> pv.PolyData:
        """Build a flat triangulated mesh over the given extent."""
        xs = np.arange(x_range[0], x_range[1] + resolution, resolution)
        ys = np.arange(y_range[0], y_range[1] + resolution, resolution)
        xx, yy = np.meshgrid(xs, ys)
        zz = np.zeros_like(xx)
        return pv.StructuredGrid(xx, yy, zz).extract_surface().triangulate()


# ── Tilted plane ──────────────────────────────────────────────────────────────

class SlopedGround(Ground):
    """
    Tilted-plane ground defined by the surface normal's azimuth and elevation.

    Parameters
    ----------
    terrain_normal_azimuth : float
        Horizontal azimuth of the surface normal [°] — meteorological
        convention (0°=North, 90°=East).  Equal to the downhill direction.
    terrain_normal_elevation : float
        Elevation angle of the surface normal above horizontal [°].
        90° → flat terrain.  60° → 30° slope.  0° → vertical wall.
    origin : tuple
        Point on the plane around which the slope pivots (default: (0, 0, 0)).
    """

    def __init__(
        self,
        terrain_normal_azimuth: float,
        terrain_normal_elevation: float,
        origin: tuple = (0.0, 0.0, 0.0),
    ):
        az = math.radians(terrain_normal_azimuth)
        # Internal tilt from horizontal = 90° − TerrainNormalElevation
        t  = math.radians(90.0 - terrain_normal_elevation)
        # The downhill direction is d = (sin(az), cos(az)).
        # Elevation decreases in that direction at rate sin(t), so:
        #   dz/dx = -sin(t)*sin(az),  dz/dy = -sin(t)*cos(az)
        # The upward surface normal is proportional to (-dz/dx, -dz/dy, 1),
        # normalized to unit length → (sin(az)*sin(t), cos(az)*sin(t), cos(t)).
        self._normal = np.array([
            math.sin(az) * math.sin(t),
            math.cos(az) * math.sin(t),
            math.cos(t),
        ])
        self._origin = np.array(origin, dtype=float)

    def elevation(self, x, y) -> float | np.ndarray:
        nx, ny, nz = self._normal
        ox, oy, oz = self._origin
        return oz - (nx * (np.asarray(x) - ox)
                   + ny * (np.asarray(y) - oy)) / nz

    def normal(self, x, y) -> np.ndarray:
        return self._normal.copy()

    def gradient(self, x, y) -> tuple[float, float]:
        nx, ny, nz = self._normal
        return (-nx / nz, -ny / nz)

    def contains(self, x, y) -> bool:
        return True   # infinite plane

    def to_polydata(
        self,
        x_range: tuple[float, float],
        y_range: tuple[float, float],
        resolution: float = 1.0,
    ) -> pv.PolyData:
        xs = np.arange(x_range[0], x_range[1] + resolution, resolution)
        ys = np.arange(y_range[0], y_range[1] + resolution, resolution)
        xx, yy = np.meshgrid(xs, ys)
        zz = self.elevation(xx, yy)
        return pv.StructuredGrid(xx, yy, zz).extract_surface().triangulate()


# ── Real DEM terrain ──────────────────────────────────────────────────────────

class DEMGround(Ground):
    """
    Real terrain from a triangulated PyVista PolyData (e.g. from SRTM).

    Typically produced by ``terrain_pipeline.build_terrain_surface()``.

    Elevation is queried by vertical ray-casting; normal and gradient are
    derived from the per-point normals stored on the mesh.

    Raises
    ------
    ValueError
        When (x, y) is **outside** the terrain bounding box.
    """

    def __init__(self, terrain: pv.PolyData):
        if "Normals" not in terrain.point_data:
            terrain = terrain.compute_normals(consistent_normals=True)
        self._terrain = terrain
        b = terrain.bounds   # (xmin, xmax, ymin, ymax, zmin, zmax)
        self._xmin, self._xmax = b[0], b[1]
        self._ymin, self._ymax = b[2], b[3]
        self._z_top = b[5] + 200.0
        self._z_bot = b[4] - 10.0

    # ── bounds ────────────────────────────────────────────────────────────────

    def contains(self, x: float, y: float) -> bool:
        return (self._xmin <= x <= self._xmax
                and self._ymin <= y <= self._ymax)

    def _check(self, x: float, y: float) -> None:
        if not self.contains(x, y):
            raise ValueError(
                f"Position ({x:.2f}, {y:.2f}) is outside the DEM extent "
                f"X [{self._xmin:.1f} – {self._xmax:.1f}] "
                f"Y [{self._ymin:.1f} – {self._ymax:.1f}]."
            )

    # ── elevation ─────────────────────────────────────────────────────────────

    def elevation(self, x: float, y: float) -> float:
        """
        Return terrain z at (x, y) via vertical ray-cast.

        Raises ValueError when (x, y) is outside the DEM extent.
        """
        self._check(x, y)
        hits, _ = self._terrain.ray_trace(
            origin=[x, y, self._z_top],
            end_point=[x, y, self._z_bot],
        )
        if len(hits) > 0:
            return float(hits[0, 2])
        # Fallback (point inside bbox but ray misses — very rare near edges)
        idx = self._terrain.find_closest_point(
            [x, y, (self._z_top + self._z_bot) / 2]
        )
        return float(self._terrain.points[idx, 2])

    # ── normal ────────────────────────────────────────────────────────────────

    def normal(self, x: float, y: float) -> np.ndarray:
        """Return the interpolated unit normal at (x, y)."""
        self._check(x, y)
        z   = self.elevation(x, y)
        idx = self._terrain.find_closest_point([x, y, z])
        n   = self._terrain.point_data["Normals"][idx].copy()
        mag = np.linalg.norm(n)
        return n / mag if mag > 1e-12 else np.array([0.0, 0.0, 1.0])

    # ── gradient ──────────────────────────────────────────────────────────────

    def gradient(self, x: float, y: float) -> tuple[float, float]:
        """Return (dz/dx, dz/dy) derived from the local surface normal."""
        n = self.normal(x, y)
        nx, ny, nz = n
        if abs(nz) < 1e-12:
            return (0.0, 0.0)
        return (-nx / nz, -ny / nz)

    # ── to_polydata ───────────────────────────────────────────────────────────

    def to_polydata(
        self,
        x_range: tuple[float, float] | None = None,
        y_range: tuple[float, float] | None = None,
        resolution: float = 1.0,          # unused for DEM (resolution fixed)
    ) -> pv.PolyData:
        """
        Return the terrain mesh, optionally clipped to *x_range* / *y_range*.
        """
        if x_range is None and y_range is None:
            return self._terrain
        x_range = x_range or (self._xmin, self._xmax)
        y_range = y_range or (self._ymin, self._ymax)
        return self._terrain.clip_box(
            bounds=(x_range[0], x_range[1],
                    y_range[0], y_range[1],
                    self._z_bot, self._z_top),
            invert=False,
        )