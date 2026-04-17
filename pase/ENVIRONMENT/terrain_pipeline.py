"""
Pipeline: GPS bounding box → SRTM DEM → 3D terrain surface in PyVista.

Dependencies:
    pip install elevation rasterio pyproj pyvista numpy

Usage (as module):
    from pase.ENVIRONMENT.terrain_pipeline import build_terrain_surface
    terrain = build_terrain_surface(bounds=(6.8493, 45.9038, 6.8893, 45.9438))

Usage (standalone):
    python pase/ENVIRONMENT/terrain_pipeline.py

Notes:
    - First run downloads SRTM tiles (~25 MB per tile); subsequent runs use the
      disk cache in ``cache_dir`` (default: ~/.cache/pase/dem/).
    - Requires an internet connection on first run only.
    - SRTM coverage: 60°N to 56°S.
"""

import os
import numpy as np
import pyvista as pv

Z_EXAGGERATION = 1.0


# ── Pipeline function ─────────────────────────────────────────────────────────

def build_terrain_surface(
    bounds: tuple,
    cache_dir: str = None,
    force_download: bool = False,
    z_exaggeration: float = Z_EXAGGERATION,
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
        Vertical scale factor for visualization (1.0 = real scale).

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

    slug = f"w{west:.4f}_s{south:.4f}_e{east:.4f}_n{north:.4f}"
    output_raw = os.path.join(cache_dir, f"{slug}_raw.tif")
    output_utm = os.path.join(cache_dir, f"{slug}_utm.tif")

    # ── 1. Download SRTM ──────────────────────────────────────────────────────
    if force_download or not os.path.exists(output_raw):
        import elevation
        print("Downloading SRTM data (cached after first run)...")
        elevation.clip(
            bounds=(west, south, east, north),
            output=output_raw,
            product='SRTM1',
        )
        print(f"  DEM saved to {output_raw}")
    else:
        print(f"  Using cached DEM: {output_raw}")

    # ── 2. Reproject WGS84 → UTM ──────────────────────────────────────────────
    if force_download or not os.path.exists(output_utm):
        import rasterio
        from rasterio.warp import calculate_default_transform, reproject, Resampling

        print("Reprojecting to UTM...")
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
        print(f"  UTM DEM saved to {output_utm} (CRS: {dst_crs})")
    else:
        print(f"  Using cached UTM DEM: {output_utm}")

    # ── 3. Read UTM DEM ───────────────────────────────────────────────────────
    import rasterio

    print("Building 3D mesh...")
    with rasterio.open(output_utm) as src:
        elev = src.read(1).astype(np.float64)
        if src.nodata is not None:
            elev[elev == src.nodata] = np.nan

        x_coords = src.transform[2] + np.arange(src.width)  * src.transform[0]
        y_coords = src.transform[5] + np.arange(src.height) * src.transform[4]

        print(f"  Grid: {src.width} × {src.height} px  |  "
              f"pixel size: {src.transform[0]:.1f} m  |  "
              f"elevation: {np.nanmin(elev):.0f}–{np.nanmax(elev):.0f} m")

    # ── 4. Build PyVista surface ──────────────────────────────────────────────
    x_centered = x_coords - x_coords.mean()
    y_centered = y_coords - y_coords.mean()

    xx, yy = np.meshgrid(x_centered, y_centered)
    zz = elev * z_exaggeration

    terrain = pv.StructuredGrid(xx, yy, zz)
    surface = terrain.extract_surface().triangulate()
    surface = surface.compute_normals(consistent_normals=True)
    surface["Elevation"] = surface.points[:, 2] / z_exaggeration

    print(f"  Mesh: {surface.n_points} points, {surface.n_cells} triangles")
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
        Vertical scale factor for visualisation (1.0 = real scale).

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

    print(f"Loading terrain from file: {filepath}")

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
                print(f"  Reprojected to {dst_crs}")

        with rasterio.open(work_file) as src:
            elev = src.read(1).astype(np.float64)
            if src.nodata is not None:
                elev[elev == src.nodata] = np.nan
            if np.any(np.isnan(elev)):
                elev = np.where(np.isnan(elev), np.nanmin(elev), elev)

            x_coords = src.transform[2] + np.arange(src.width)  * src.transform[0]
            y_coords = src.transform[5] + np.arange(src.height) * src.transform[4]

            print(f"  Grid: {src.width} × {src.height} px  |  "
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

        print(f"  Mesh: {surface.n_points} points, {surface.n_cells} triangles")
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
