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

Parameter conventions (SlopedGround constructor — geometric primitive)
----------------------------------------------------------------------
terrain_normal_azimuth   — horizontal azimuth of the surface normal [°],
                           meteorological convention: 0°=North, 90°=East,
                           180°=South, 270°=West.
                           Equal to the downhill direction (the normal's
                           horizontal projection points the same way as the
                           slope falls).
terrain_normal_elevation — elevation angle of the surface normal above the
                           horizontal plane [°].
                           90° → flat terrain (normal points straight up).
                           60° → 30° slope.   0° → vertical wall.

YAML-facing parameters (intuitive layer — see ``ground_from_config``)
---------------------------------------------------------------------
TerrainSlopeAngle  — terrain inclination from horizontal [°] (0° = flat).
TerrainSlopeAspect — downhill direction [°] (same meteorological convention).
Mapping: terrain_normal_elevation = 90 − TerrainSlopeAngle,
         terrain_normal_azimuth   = TerrainSlopeAspect.

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
    samples: int = 2,
) -> float:
    """
    Return the maximum terrain elevation over a block footprint.

    The block is an axis-aligned rectangle ``[cx ± half_x] × [cy ± half_y]`` in
    the pre-rotation (central) frame.  Sample points are mapped to world
    coordinates by rotating by ``-azimuth_deg`` about the origin before sampling
    the ground.

    Anchoring PV blocks (panels + structure) at this elevation — rather than at
    the ground elevation at their center — guarantees that no component of the
    block sits below the terrain, since the block top is lifted to the highest
    terrain point under its footprint.

    Parameters
    ----------
    samples : int
        Number of sample points per axis (``>= 2``).  ``samples=2`` evaluates
        the 4 corners only — exact for a tilted plane, where the maximum over a
        rectangle is always attained at a corner.  Real (bumpy) terrain may peak
        in the interior, so ``DEMGround`` requests a denser ``samples`` grid via
        its ``footprint_samples`` attribute.
    """
    samples = max(2, int(samples))
    az = math.radians(azimuth_deg)
    cos_az, sin_az = math.cos(az), math.sin(az)
    z_max = -math.inf
    for x_pre in np.linspace(cx - half_x, cx + half_x, samples):
        for y_pre in np.linspace(cy - half_y, cy + half_y, samples):
            x_w = x_pre * cos_az + y_pre * sin_az
            y_w = -x_pre * sin_az + y_pre * cos_az
            z = float(ground.elevation(x_w, y_w))
            if z > z_max:
                z_max = z
    return z_max


# ── Base class — flat ground ──────────────────────────────────────────────────

class Ground:
    """Flat ground at z = 0.  All queries always return True for contains()."""

    #: Sample points per axis used by ``block_reference_elevation`` to anchor
    #: blocks.  2 (the 4 corners) is exact for planar grounds; ``DEMGround``
    #: raises this to capture interior peaks on bumpy real terrain.
    footprint_samples: int = 2

    def assert_covers(self, x_min, x_max, y_min, y_max) -> None:
        """Raise if the footprint is not fully within the ground extent.

        No-op for unbounded grounds (flat / sloped infinite planes).  Overridden
        by ``DEMGround`` to fail early with an actionable message.
        """
        return None

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

    #: Real terrain can peak inside a footprint, not only at its corners, so we
    #: sample a denser grid than the 2-corner default of planar grounds.
    footprint_samples: int = 5

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

    def assert_covers(self, x_min, x_max, y_min, y_max) -> None:
        """Fail early if the PV layout extends beyond the DEM extent.

        Raises a clear, actionable error (increase ``TerrainExtentRadius``)
        instead of letting an opaque per-pole ``ValueError`` surface mid-build.
        """
        if (x_min < self._xmin or x_max > self._xmax
                or y_min < self._ymin or y_max > self._ymax):
            raise ValueError(
                "The PV layout extends beyond the downloaded terrain extent "
                f"(layout X [{x_min:.1f} – {x_max:.1f}] Y [{y_min:.1f} – {y_max:.1f}] "
                f"vs DEM X [{self._xmin:.1f} – {self._xmax:.1f}] "
                f"Y [{self._ymin:.1f} – {self._ymax:.1f}]). "
                "Increase 'TerrainExtentRadius' in the scenario YAML so the "
                "terrain covers the whole installation."
            )

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


# ── Config-driven factory ─────────────────────────────────────────────────────

_METERS_PER_DEGREE_LAT = 111_320.0


def bounds_around(lat: float, lon: float, radius_m: float) -> tuple:
    """Return a ``(west, south, east, north)`` WGS84 box of half-size *radius_m*
    metres centred on (*lat*, *lon*).

    Used to build the SRTM download extent around the scenario location.
    """
    dlat = radius_m / _METERS_PER_DEGREE_LAT
    cos_lat = max(math.cos(math.radians(lat)), 1e-6)
    dlon = radius_m / (_METERS_PER_DEGREE_LAT * cos_lat)
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def _dem_ground_from_config(cfg: dict) -> "DEMGround":
    """Download SRTM terrain around the location and wrap it in a ``DEMGround``.

    Requires ``Latitude`` / ``Longitude`` (from the scenario YAML) and uses
    ``TerrainExtentRadius`` [m] for the download box.  Imports the SRTM pipeline
    lazily so the optional ``elevation`` / ``rasterio`` deps are only needed for
    this mode.
    """
    if 'Latitude' not in cfg or 'Longitude' not in cfg:
        raise ValueError(
            "TerrainSource='srtm' requires 'Latitude' and 'Longitude' to build "
            "the terrain extent. Pass the scenario/location config via "
            "ground_from_config(config, location=<loc>)."
        )
    lat = float(cfg['Latitude'])
    lon = float(cfg['Longitude'])
    radius = float(cfg.get('TerrainExtentRadius', 500.0))
    bounds = bounds_around(lat, lon, radius)

    from pase.ENVIRONMENT.terrain_pipeline import build_terrain_surface
    surface = build_terrain_surface(bounds=bounds)
    return DEMGround(surface)


def ground_from_config(config: dict, location: dict | None = None) -> "Ground":
    """Build a Ground from terrain parameters in the config / location dicts.

    Reads from a merged view (the central ``config`` overrides the scenario
    ``location``), so terrain keys may live in either file.

    Parameters
    ----------
    TerrainSource      — ``flat`` | ``sloped`` | ``srtm`` (default ``flat``).
    TerrainSlopeAngle  — terrain inclination from horizontal [°], 0 = flat (``sloped``).
    TerrainSlopeAspect — downhill direction [°], meteorological convention
                         (0°=N, 90°=E, 180°=S, 270°=W) (``sloped``).
    Latitude/Longitude — location, required for ``srtm``.
    TerrainExtentRadius — half-size [m] of the SRTM download box (``srtm``).

    ``sloped`` maps onto the geometric ``SlopedGround`` convention via
    ``terrain_normal_elevation = 90 - TerrainSlopeAngle`` and
    ``terrain_normal_azimuth = TerrainSlopeAspect``.  ``srtm`` downloads a real
    DEM around the location and returns a ``DEMGround``.
    """
    cfg = {**(location or {}), **(config or {})}
    source = str(cfg.get('TerrainSource', 'flat')).lower()

    if source in ('srtm', 'dem'):
        return _dem_ground_from_config(cfg)

    slope_angle = float(cfg.get('TerrainSlopeAngle', 0.0))
    if source == 'sloped' or slope_angle > 1e-6:
        aspect = float(cfg.get('TerrainSlopeAspect', 0.0))
        return SlopedGround(terrain_normal_azimuth=aspect,
                            terrain_normal_elevation=90.0 - slope_angle)
    return Ground()