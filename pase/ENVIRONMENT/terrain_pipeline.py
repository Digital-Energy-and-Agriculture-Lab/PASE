"""
Pipeline: GPS bounding box → SRTM DEM → 3D terrain surface in PyVista.

Dependencies:
    pip install rasterio pyproj pyvista numpy

Usage (as module):
    from pase.ENVIRONMENT.terrain_pipeline import build_terrain_surface
    terrain = build_terrain_surface(bounds=(6.8493, 45.9038, 6.8893, 45.9438))

Usage (standalone):
    python pase/ENVIRONMENT/terrain_pipeline.py

Notes:
    - First run downloads SRTM tiles (~25 MB per tile); subsequent runs use the
      disk cache in ``cache_dir`` (default: ~/.cache/pase/dem/).
    - Requires an internet connection on first run only.
    - Tiles come from the public AWS mirror via :mod:`pase.ENVIRONMENT.srtm`,
      which covers the whole globe: outside SRTM's own 60°N–56°S footprint the
      data comes from other datasets, and sea tiles carry bathymetry (negative
      elevations) rather than nodata.
"""

import logging
import os
from typing import Optional
import numpy as np
import pyvista as pv
from scipy import ndimage

from pase.ENVIRONMENT import srtm

logger = logging.getLogger(__name__)

Z_EXAGGERATION = 1.0


def _fill_nodata(elev: np.ndarray) -> np.ndarray:
    """Replace NaN gaps with the nearest finite elevation.

    SRTM (and user-provided) rasters contain nodata voids, common over water
    and steep terrain. Filling each void with its nearest valid pixel avoids the
    artificial pits, cliffs, and bogus surface normals that a constant
    global-minimum fill produces. Returns ``elev`` unchanged when it holds no
    NaNs; callers are expected to reject entirely-nodata rasters beforehand.
    """
    nan_mask = np.isnan(elev)
    if not nan_mask.any():
        return elev
    # Index of the nearest non-NaN pixel for every position, then gather.
    nearest = ndimage.distance_transform_edt(
        nan_mask, return_distances=False, return_indices=True
    )
    return elev[tuple(nearest)]


# ── Pipeline function ─────────────────────────────────────────────────────────

def build_terrain_surface(
    bounds: tuple,
    cache_dir: Optional[str] = None,
    force_download: bool = False,
    z_exaggeration: float = Z_EXAGGERATION,
    center_lonlat: Optional[tuple] = None,
    product: str = 'SRTM1',
) -> pv.PolyData:
    """
    Download (once) and convert SRTM data to a triangulated PyVista surface.

    Parameters
    ----------
    bounds : tuple of float
        Geographic bounding box ``(west, south, east, north)`` in decimal
        degrees (WGS84).
    cache_dir : str, optional
        Directory for downloaded and reprojected raster files.
        Defaults to ``~/.cache/pase/dem/``.
    force_download : bool
        Re-download and reproject even when cached files exist.
    z_exaggeration : float
        Vertical scale factor for **visualization only** (1.0 = real scale).
        Must be left at 1.0 for any surface fed to ``DEMGround`` / simulation,
        which rejects exaggerated terrain (the applied value is stamped on the
        returned surface's field data).
    center_lonlat : tuple of float, optional
        ``(lon, lat)`` of the scenario location in WGS84. When given, the mesh
        is centred so this point maps to X=Y=0, keeping the terrain aligned with
        the PV layout (which sits at the origin). Because the download box is
        symmetric in *degrees* while UTM is metric, the raster centroid does not
        coincide with the location, so relying on the grid mean introduces a
        horizontal offset (a z error on slopes). Falls back to the grid centroid
        when omitted.
    product : str
        DEM product passed to :func:`pase.ENVIRONMENT.srtm.fetch_srtm_clip`.
        Only ``'SRTM1'`` (1 arc-second, ~30 m) is served by the mirror; it is
        part of the cache key, so switching products cannot reuse stale tiles.

    Returns
    -------
    pv.PolyData
        Triangulated terrain surface with an ``"Elevation"`` scalar [m].
        Coordinates are in UTM metres, centred around (0, 0).
    """
    west, south, east, north = bounds

    if cache_dir is None:
        cache_dir = os.path.expanduser("~/.cache/pase/dem/")
    os.makedirs(cache_dir, exist_ok=True)

    slug = f"{product}_w{west:.4f}_s{south:.4f}_e{east:.4f}_n{north:.4f}"
    output_raw = os.path.join(cache_dir, f"{slug}_raw.tif")
    output_utm = os.path.join(cache_dir, f"{slug}_utm.tif")

    # ── 1. Download SRTM ──────────────────────────────────────────────────────
    if force_download or not os.path.exists(output_raw):
        logger.info("Downloading SRTM data (cached after first run)...")
        srtm.fetch_srtm_clip(
            bounds=(west, south, east, north),
            output=output_raw,
            cache_dir=cache_dir,
            force_download=force_download,
            product=product,
        )
        logger.info(f"  DEM saved to {output_raw}")
    else:
        logger.info(f"  Using cached DEM: {output_raw}")

    # ── 2. Reproject WGS84 → UTM ──────────────────────────────────────────────
    if force_download or not os.path.exists(output_utm):
        import rasterio
        from rasterio.warp import calculate_default_transform, reproject, Resampling

        logger.info("Reprojecting to UTM...")
        with rasterio.open(output_raw) as src:
            center_lon = (src.bounds.left + src.bounds.right) / 2
            center_lat = (src.bounds.bottom + src.bounds.top) / 2
            utm_zone   = int((center_lon + 180) / 6) + 1
            hemisphere = 326 if center_lat >= 0 else 327
            dst_crs    = f"EPSG:{hemisphere}{utm_zone:02d}"

            transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds
            )
            kwargs = src.meta.copy()
            kwargs.update(crs=dst_crs, transform=transform,
                          width=width, height=height)

            with rasterio.open(output_utm, "w", **kwargs) as dst:
                reproject(
                    source=rasterio.band(src, 1),
                    destination=rasterio.band(dst, 1),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.bilinear,
                )
        logger.info(f"  UTM DEM saved to {output_utm} (CRS: {dst_crs})")
    else:
        logger.info(f"  Using cached UTM DEM: {output_utm}")

    # ── 3. Read UTM DEM ───────────────────────────────────────────────────────
    import rasterio

    logger.info("Building 3D mesh...")
    with rasterio.open(output_utm) as src:
        elev = src.read(1).astype(np.float64)
        if src.nodata is not None:
            elev[elev == src.nodata] = np.nan

        x_coords = src.transform[2] + np.arange(src.width)  * src.transform[0]
        y_coords = src.transform[5] + np.arange(src.height) * src.transform[4]
        utm_crs = src.crs

        if not np.any(np.isfinite(elev)):
            raise ValueError(
                f"No valid elevation data in {output_utm} (the DEM is entirely "
                "nodata). This usually means the mirror serves no tile for this "
                f"extent, or a corrupt tile in {cache_dir}. Clear that cache and "
                "retry, or call build_terrain_surface(..., force_download=True)."
            )
        # Fill any remaining nodata gaps so the mesh stays finite everywhere.
        elev = _fill_nodata(elev)

        logger.info(f"  Grid: {src.width} × {src.height} px  |  "
                    f"pixel size: {abs(src.transform[0]):.1f} m  |  "
                    f"elevation: {np.nanmin(elev):.0f}–{np.nanmax(elev):.0f} m")

    # ── 4. Build PyVista surface ──────────────────────────────────────────────
    # Centre on the scenario location (so the terrain aligns with the PV layout
    # at the origin) when known, else on the raster centroid.
    if center_lonlat is not None:
        from pyproj import Transformer
        lon0, lat0 = center_lonlat
        transformer = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
        x_origin, y_origin = transformer.transform(lon0, lat0)
    else:
        x_origin, y_origin = x_coords.mean(), y_coords.mean()

    x_centered = x_coords - x_origin
    y_centered = y_coords - y_origin

    xx, yy = np.meshgrid(x_centered, y_centered)
    zz = elev * z_exaggeration

    terrain = pv.StructuredGrid(xx, yy, zz)
    surface = terrain.extract_surface().triangulate()
    surface = surface.compute_normals(consistent_normals=True)
    surface["Elevation"] = surface.points[:, 2] / z_exaggeration
    # Record the applied exaggeration so DEMGround can reject non-real-scale
    # terrain (elevation is ray-cast off this geometry to place pole feet).
    surface.field_data["z_exaggeration"] = np.array([float(z_exaggeration)])

    logger.info(f"  Mesh: {surface.n_points} points, {surface.n_cells} triangles")
    return surface


# ── User-provided DEM loader ─────────────────────────────────────────────────

def load_terrain_from_file(
    filepath: str,
    z_exaggeration: float = 1.0,
) -> pv.PolyData:
    """
    Load a user-provided raster file (GeoTIFF or any rasterio-supported format)
    as a triangulated PyVista terrain surface.

    If the file's CRS is geographic (lat/lon), it is automatically reprojected
    to the local UTM zone so that X/Y coordinates are in metres.
    Files already in a projected metric CRS are used as-is.

    Parameters
    ----------
    filepath : str
        Path to the raster DEM file.
    z_exaggeration : float
        Vertical scale factor for **visualisation only** (1.0 = real scale).
        Must be left at 1.0 for any surface fed to ``DEMGround`` / simulation,
        which rejects exaggerated terrain (the applied value is stamped on the
        returned surface's field data).

    Returns
    -------
    pv.PolyData
        Triangulated terrain surface with an ``"Elevation"`` scalar [m].
        Coordinates are centred around (0, 0).
    """
    import tempfile
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"DEM file not found: {filepath}")

    logger.info(f"Loading terrain from file: {filepath}")

    _tmp_file = None
    try:
        work_file = filepath

        with rasterio.open(filepath) as src:
            needs_reproject = (src.crs is None) or (not src.crs.is_projected)

        if needs_reproject:
            with rasterio.open(filepath) as src:
                center_lon = (src.bounds.left  + src.bounds.right) / 2
                center_lat = (src.bounds.bottom + src.bounds.top)  / 2
                utm_zone   = int((center_lon + 180) / 6) + 1
                hemisphere = 326 if center_lat >= 0 else 327
                dst_crs    = f"EPSG:{hemisphere}{utm_zone:02d}"

                transform, width, height = calculate_default_transform(
                    src.crs, dst_crs, src.width, src.height, *src.bounds
                )
                kwargs = src.meta.copy()
                kwargs.update(crs=dst_crs, transform=transform,
                              width=width, height=height)

                tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
                tmp.close()
                _tmp_file = tmp.name

                with rasterio.open(_tmp_file, "w", **kwargs) as dst:
                    reproject(
                        source=rasterio.band(src, 1),
                        destination=rasterio.band(dst, 1),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=dst_crs,
                        resampling=Resampling.bilinear,
                    )
                work_file = _tmp_file
                logger.info(f"  Reprojected to {dst_crs}")

        with rasterio.open(work_file) as src:
            elev = src.read(1).astype(np.float64)
            if src.nodata is not None:
                elev[elev == src.nodata] = np.nan
            if not np.any(np.isfinite(elev)):
                raise ValueError(
                    f"No valid elevation data in {filepath} (the raster is "
                    "entirely nodata)."
                )
            elev = _fill_nodata(elev)

            x_coords = src.transform[2] + np.arange(src.width)  * src.transform[0]
            y_coords = src.transform[5] + np.arange(src.height) * src.transform[4]

            logger.info(f"  Grid: {src.width} × {src.height} px  |  "
                        f"pixel size: {abs(src.transform[0]):.1f} m  |  "
                        f"elevation: {np.nanmin(elev):.0f}–{np.nanmax(elev):.0f} m")

        x_centered = x_coords - x_coords.mean()
        y_centered = y_coords - y_coords.mean()

        xx, yy = np.meshgrid(x_centered, y_centered)
        zz = elev * z_exaggeration

        terrain = pv.StructuredGrid(xx, yy, zz)
        surface = terrain.extract_surface().triangulate()
        surface = surface.compute_normals(consistent_normals=True)
        surface["Elevation"] = surface.points[:, 2] / z_exaggeration
        # Record the applied exaggeration so DEMGround can reject non-real-scale
        # terrain (elevation is ray-cast off this geometry to place pole feet).
        surface.field_data["z_exaggeration"] = np.array([float(z_exaggeration)])

        logger.info(f"  Mesh: {surface.n_points} points, {surface.n_cells} triangles")
        return surface

    finally:
        if _tmp_file is not None and os.path.exists(_tmp_file):
            os.unlink(_tmp_file)


# ── Standalone visualisation ──────────────────────────────────────────────────

if __name__ == "__main__":
    # Example: Chamonix area (French Alps)
    _BOUNDS = (6.8493, 45.9038, 6.8893, 45.9438)

    surface = build_terrain_surface(bounds=_BOUNDS)

    pl = pv.Plotter()
    pl.add_mesh(
        surface,
        scalars="Elevation",
        cmap="terrain",
        line_width=0.5,
        lighting=True,
    )
    light = pv.Light(position=(1, 1, 1), intensity=0.3)
    pl.add_light(light)
    pl.camera_position = "iso"
    pl.show()
