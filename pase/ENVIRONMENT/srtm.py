#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (c) 2020-2026 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
Authors : Arnaud Bouvry (abouvry@uliege.be).
This file is part of the PASE software, and is distributed under the MIT license.

Pure-Python SRTM tile fetcher: bounding box → cropped WGS84 elevation raster.

This module replaces the ``elevation`` package, which implemented its clip by
writing a Makefile and shelling out to ``make`` + the GDAL command line tools.
Those binaries are absent from an unactivated conda interpreter (an IDE run
configuration), from ``pip`` wheels (which bundle the GDAL *libraries* but no
CLI), and from Windows (no ``make``), so the DEM path could not run there (#286).

Everything here is standard library + numpy, except the final GeoTIFF write,
which uses rasterio — already required by the rest of the terrain pipeline.

Data source
    1 arc-second tiles from the public AWS *Terrain Tiles* mirror
    (``elevation-tiles-prod``, no authentication). This is the same source the
    ``elevation`` package reads for its ``SRTM1`` product, so elevations match
    tile-for-tile. The tileset is global: outside SRTM's own 60°N–56°S footprint
    it is filled from other datasets, and ocean tiles carry **bathymetry**
    (negative values), not nodata.

Georeferencing
    An ``.hgt`` tile is a header-less raster of big-endian ``int16`` metres
    covering exactly one degree square, named after its south-west corner. Its
    samples sit on a global lattice at whole multiples of 1/3600°, and a tile
    holds the samples of *both* its edges — hence 3601 rows, and hence adjacent
    tiles sharing a duplicated edge. Mosaicking is therefore exact array
    copying, with no resampling and no overlap ambiguity.

    Rasters are written pixel-as-area with the sample at the pixel centre, the
    convention GDAL's own ``SRTMHGT`` driver uses, so the output is
    interchangeable with what ``elevation`` produced.
"""

import gzip
import logging
import math
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

SKADI_BASE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/skadi"

#: Void sentinel used by the SRTM format.
SRTM_NODATA = -32768

#: Samples per degree for each supported product. A tile is ``spd + 1`` square,
#: since it carries the samples of both its edges.
PRODUCT_SAMPLES_PER_DEGREE = {
    "SRTM1": 3600,
}

DEFAULT_PRODUCT = "SRTM1"
DEFAULT_CACHE_DIR = "~/.cache/pase/dem/"
DEFAULT_TIMEOUT = 120.0


# ── tile identity ─────────────────────────────────────────────────────────────

def tile_name(lat: int, lon: int) -> str:
    """Return the SRTM tile name for the degree square with this SW corner.

    Parameters
    ----------
    lat, lon : int
        South-west corner of the 1°×1° tile, in whole degrees.

    Returns
    -------
    str
        e.g. ``'N45E006'``, ``'S01W001'``. Latitude is zero-padded to two
        digits, longitude to three.
    """
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"{ns}{abs(lat):02d}{ew}{abs(lon):03d}"


def tile_url(lat: int, lon: int) -> str:
    """Return the mirror URL of the gzipped ``.hgt`` tile with this SW corner."""
    name = tile_name(lat, lon)
    return f"{SKADI_BASE_URL}/{name[:3]}/{name}.hgt.gz"


def tiles_for_bounds(bounds: tuple) -> list:
    """Return the SW corners of every tile the bounding box touches.

    Parameters
    ----------
    bounds : tuple of float
        ``(west, south, east, north)`` in decimal degrees (WGS84).

    Returns
    -------
    list of tuple
        ``(lat, lon)`` whole-degree corners, latitude-major. An edge falling
        exactly on a degree includes the further tile as well: that tile carries
        the shared samples, so including it keeps the crop window covered.
    """
    west, south, east, north = bounds
    return [
        (lat, lon)
        for lat in range(math.floor(south), math.floor(north) + 1)
        for lon in range(math.floor(west), math.floor(east) + 1)
    ]


# ── decoding ──────────────────────────────────────────────────────────────────

def decode_hgt(raw: bytes, samples_per_degree: int = PRODUCT_SAMPLES_PER_DEGREE[DEFAULT_PRODUCT]) -> np.ndarray:
    """Decode the (decompressed) payload of an ``.hgt`` tile.

    Parameters
    ----------
    raw : bytes
        Decompressed tile payload: ``(spd + 1)²`` big-endian ``int16`` metres,
        row-major from the **north** edge southwards and from the west edge
        eastwards.
    samples_per_degree : int
        1 arc-second data has 3600, i.e. a 3601² tile.

    Returns
    -------
    np.ndarray
        Read-only ``(spd + 1, spd + 1)`` array of elevations in metres, with
        voids left at :data:`SRTM_NODATA`. Row 0 is the northernmost.

    Raises
    ------
    ValueError
        When the payload size does not match a square tile — the signature of a
        truncated download, which must fail loudly rather than reshape into
        plausible-looking nonsense.
    """
    n = samples_per_degree + 1
    expected = n * n * 2
    if len(raw) != expected:
        raise ValueError(
            f"Unexpected SRTM tile size: got {len(raw)} bytes, expected "
            f"{expected} ({n}×{n} big-endian int16). The download is likely "
            "truncated or the product resolution is wrong."
        )
    return np.frombuffer(raw, dtype=">i2").reshape(n, n)


# ── download + cache ──────────────────────────────────────────────────────────

def _read_url(url: str, timeout: float = DEFAULT_TIMEOUT) -> bytes:
    """Return the bytes served at *url* (the single network seam of this module)."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def _download_tile(lat: int, lon: int, timeout: float) -> Optional[bytes]:
    """Fetch one gzipped tile, or return ``None`` when the mirror has no such tile."""
    name = tile_name(lat, lon)
    url = tile_url(lat, lon)
    logger.info(f"  Downloading SRTM tile {name}...")
    try:
        return _read_url(url, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404):
            logger.warning(
                f"  No SRTM tile {name} on the mirror (HTTP {exc.code}); that "
                "area of the terrain will be nodata."
            )
            return None
        raise RuntimeError(
            f"Could not download SRTM tile {name} from {url} (HTTP {exc.code})."
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not download SRTM tile {name} from {url}: {exc.reason}. "
            "Check the network connection or any proxy settings; tiles are "
            "cached after a first successful run."
        ) from exc


def read_tile(
    lat: int,
    lon: int,
    cache_dir,
    samples_per_degree: int = PRODUCT_SAMPLES_PER_DEGREE[DEFAULT_PRODUCT],
    force_download: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> Optional[np.ndarray]:
    """Return one decoded tile, downloading it once and caching it on disk.

    Parameters
    ----------
    lat, lon : int
        South-west corner of the tile, in whole degrees.
    cache_dir : str or Path
        Directory holding the ``<tile>.hgt.gz`` files. Created if absent.
    samples_per_degree : int
        Expected resolution, used to validate and reshape the payload.
    force_download : bool
        Re-download even when the tile is already cached.
    timeout : float
        Per-request timeout [s].

    Returns
    -------
    np.ndarray or None
        The decoded tile, or ``None`` when the mirror has no tile there (the
        caller leaves that area at :data:`SRTM_NODATA`).

    Raises
    ------
    ValueError
        When a cached file is corrupt; the message names the file to delete.
    RuntimeError
        When the download fails for any reason other than an absent tile.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{tile_name(lat, lon)}.hgt.gz"

    if force_download or not path.exists():
        payload = _download_tile(lat, lon, timeout)
        if payload is None:
            return None
        # Write via a temporary name so an interrupted download cannot leave a
        # truncated file behind that later runs would trust.
        partial = path.with_name(path.name + ".part")
        partial.write_bytes(payload)
        os.replace(partial, path)
    else:
        logger.debug(f"  Using cached SRTM tile {path}")

    try:
        raw = gzip.decompress(path.read_bytes())
    except (OSError, EOFError) as exc:
        raise ValueError(
            f"The cached SRTM tile {path} is corrupt and cannot be "
            f"decompressed ({exc}). Delete it and retry, or call the pipeline "
            "with force_download=True."
        ) from exc

    try:
        return decode_hgt(raw, samples_per_degree=samples_per_degree)
    except ValueError as exc:
        raise ValueError(f"The cached SRTM tile {path} is unusable: {exc}") from exc


# ── mosaic + crop ─────────────────────────────────────────────────────────────

def mosaic_tiles(tiles: dict, bounds: tuple, samples_per_degree: int):
    """Assemble tiles into one north-up array cropped to *bounds*.

    Samples are placed by their position on the global lattice — column
    ``lon × spd``, row ``lat × spd`` — so no resampling takes place and the edge
    that neighbouring tiles duplicate carries the same value either way.

    Parameters
    ----------
    tiles : dict
        ``{(lat, lon): tile_array}``, as returned by :func:`read_tile`. Tiles the
        box needs but that are missing may simply be absent.
    bounds : tuple of float
        ``(west, south, east, north)`` in decimal degrees (WGS84).
    samples_per_degree : int
        Resolution of the tiles.

    Returns
    -------
    elev : np.ndarray
        ``int16`` elevations, row 0 northernmost, uncovered cells left at
        :data:`SRTM_NODATA`. The window is rounded **outwards**, so it always
        covers at least *bounds*.
    transform : affine.Affine
        Pixel-as-area geotransform in WGS84 degrees.
    """
    from rasterio.transform import from_origin

    west, south, east, north = bounds
    spd = samples_per_degree

    col_min, col_max = math.floor(west * spd), math.ceil(east * spd)
    row_min, row_max = math.floor(south * spd), math.ceil(north * spd)

    elev = np.full((row_max - row_min + 1, col_max - col_min + 1),
                   SRTM_NODATA, dtype=np.int16)

    for (lat0, lon0), tile in tiles.items():
        # Lattice extent of this tile, both edges included.
        gc0, gc1 = lon0 * spd, (lon0 + 1) * spd
        gr0, gr1 = lat0 * spd, (lat0 + 1) * spd

        c_lo, c_hi = max(col_min, gc0), min(col_max, gc1)
        r_lo, r_hi = max(row_min, gr0), min(row_max, gr1)
        if c_lo > c_hi or r_lo > r_hi:
            continue

        # Rows count southwards in both the tile (from its north edge, gr1) and
        # the output (from the window's north edge, row_max).
        elev[row_max - r_hi:row_max - r_lo + 1,
             c_lo - col_min:c_hi - col_min + 1] = \
            tile[gr1 - r_hi:gr1 - r_lo + 1, c_lo - gc0:c_hi - gc0 + 1]

    res = 1.0 / spd
    # Samples are pixel centres, so the pixel-as-area origin sits half a pixel
    # north-west of the first sample.
    transform = from_origin(col_min * res - res / 2, row_max * res + res / 2,
                            res, res)
    return elev, transform


# ── public entry point ────────────────────────────────────────────────────────

def fetch_srtm_clip(
    bounds: tuple,
    output: str,
    cache_dir: Optional[str] = None,
    force_download: bool = False,
    product: str = DEFAULT_PRODUCT,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Write the SRTM elevations covering *bounds* to a WGS84 GeoTIFF.

    Drop-in replacement for ``elevation.clip(bounds=..., output=..., product=...)``.

    Parameters
    ----------
    bounds : tuple of float
        ``(west, south, east, north)`` in decimal degrees (WGS84).
    output : str
        Path of the GeoTIFF to write; overwritten if it exists.
    cache_dir : str, optional
        Root of the tile cache (tiles land in its ``tiles/`` subdirectory).
        Defaults to ``~/.cache/pase/dem/``.
    force_download : bool
        Re-download the tiles even when they are cached.
    product : str
        Only ``'SRTM1'`` (1 arc-second, ~30 m) is served by this mirror.
    timeout : float
        Per-request timeout [s].

    Returns
    -------
    str
        The *output* path.

    Raises
    ------
    ValueError
        On inverted/degenerate bounds, or an unsupported product.

    Notes
    -----
    Tiles the mirror does not serve become :data:`SRTM_NODATA`; the caller is
    expected to fill or reject voids (``terrain_pipeline._fill_nodata`` does).
    """
    import rasterio

    west, south, east, north = bounds
    if east <= west or north <= south:
        raise ValueError(
            f"Invalid bounds {bounds}: expected (west, south, east, north) "
            "with west < east and south < north, in decimal degrees."
        )

    if product not in PRODUCT_SAMPLES_PER_DEGREE:
        raise ValueError(
            f"Unsupported DEM product '{product}'. This mirror serves "
            f"{sorted(PRODUCT_SAMPLES_PER_DEGREE)} only (1 arc-second, ~30 m). "
            "For other resolutions or sources, download the raster yourself and "
            "load it with terrain_pipeline.load_terrain_from_file()."
        )
    spd = PRODUCT_SAMPLES_PER_DEGREE[product]

    tile_cache = Path(os.path.expanduser(cache_dir or DEFAULT_CACHE_DIR)) / "tiles"

    corners = tiles_for_bounds(bounds)
    logger.info(f"  {product}: {len(corners)} tile(s) cover the requested extent")

    tiles = {}
    for lat, lon in corners:
        tile = read_tile(lat, lon, cache_dir=tile_cache, samples_per_degree=spd,
                         force_download=force_download, timeout=timeout)
        if tile is not None:
            tiles[(lat, lon)] = tile

    elev, transform = mosaic_tiles(tiles, bounds, spd)

    with rasterio.open(
        output, "w",
        driver="GTiff",
        height=elev.shape[0],
        width=elev.shape[1],
        count=1,
        dtype="int16",
        crs="EPSG:4326",
        transform=transform,
        nodata=SRTM_NODATA,
    ) as dst:
        dst.write(elev, 1)

    logger.info(f"  Wrote {elev.shape[1]} × {elev.shape[0]} px DEM to {output}")
    return str(output)
