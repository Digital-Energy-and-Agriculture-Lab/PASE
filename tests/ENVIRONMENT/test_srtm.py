"""Tests for pase.ENVIRONMENT.srtm — the pure-Python SRTM tile fetcher (#286).

The fetcher replaces the ``elevation`` package, which implemented its clip by
shelling out to ``make`` + ``gdalbuildvrt`` and therefore could not run from an
unactivated interpreter, from a pip install, or on Windows.

The tests below fall in four groups:

- tile naming / selection — the N/S/E/W sign conventions and the tiles a
  bounding box needs (the easy things to get wrong);
- ``.hgt`` decoding — big-endian int16, square grid, voids preserved;
- mosaic + crop geometry — north-up output, row/column order, shared tile edges,
  missing tiles becoming nodata rather than an exception;
- wiring — ``build_terrain_surface`` goes through the fetcher and imports no
  ``elevation`` / spawns no subprocess.

Only the tests marked ``network`` touch the mirror; they stay off the release
path (``pytest -m "not network"``).
"""

import ast
import gzip
import urllib.error
from pathlib import Path

import numpy as np
import pytest
import rasterio

from pase.ENVIRONMENT import srtm


# ── helpers ───────────────────────────────────────────────────────────────────

TEST_SPD = 4          # samples per degree: a 5x5 "tile", so the maths stays hand-checkable
TEST_RES = 1.0 / TEST_SPD


def _synthetic_tile(spd=TEST_SPD, base=0):
    """Return a ``(spd+1, spd+1)`` int16 tile whose values encode (row, col).

    ``tile[i, j] = base + 100 * i + j`` — row 0 is the *north* edge, column 0 the
    *west* edge, so any row-flip or transposition in the mosaic shows up as a
    wrong value rather than a plausible one.
    """
    n = spd + 1
    i, j = np.meshgrid(np.arange(n), np.arange(n), indexing='ij')
    return (base + 100 * i + j).astype(np.int16)


def _hgt_bytes(tile):
    """Serialize a tile the way an ``.hgt`` file stores it (big-endian int16)."""
    return tile.astype('>i2').tobytes()


# ── tile naming ───────────────────────────────────────────────────────────────

class TestTileName:
    @pytest.mark.parametrize("lat, lon, expected", [
        (45, 6, "N45E006"),        # Alps — the reference tile of example_dem_terrain
        (0, 0, "N00E000"),         # origin: no sign flip
        (-1, -1, "S01W001"),       # both hemispheres, single-digit padding
        (45, -1, "N45W001"),       # just west of the prime meridian
        (-1, 6, "S01E006"),        # just south of the equator
        (-34, 18, "S34E018"),      # Cape Town
        (60, -180, "N60W180"),     # three-digit longitude, antimeridian
    ])
    def test_sign_and_padding_conventions(self, lat, lon, expected):
        assert srtm.tile_name(lat, lon) == expected

    def test_url_points_at_the_skadi_mirror(self):
        url = srtm.tile_url(45, 6)
        assert url == f"{srtm.SKADI_BASE_URL}/N45/N45E006.hgt.gz"


# ── tile selection ────────────────────────────────────────────────────────────

class TestTilesForBounds:
    def test_single_tile(self):
        # Chamonix box, well inside N45E006.
        tiles = srtm.tiles_for_bounds((6.8493, 45.9038, 6.8893, 45.9438))
        assert tiles == [(45, 6)]

    def test_spans_a_tile_corner(self):
        # Straddles both the 7 deg meridian and the 46 deg parallel: 4 tiles.
        tiles = set(srtm.tiles_for_bounds((6.9, 45.9, 7.1, 46.1)))
        assert tiles == {(45, 6), (45, 7), (46, 6), (46, 7)}

    def test_crosses_the_prime_meridian(self):
        tiles = set(srtm.tiles_for_bounds((-0.1, 45.5, 0.1, 45.6)))
        assert tiles == {(45, -1), (45, 0)}

    def test_crosses_the_equator(self):
        tiles = set(srtm.tiles_for_bounds((6.1, -0.1, 6.2, 0.1)))
        assert tiles == {(-1, 6), (0, 6)}

    def test_edge_exactly_on_a_degree_includes_both_tiles(self):
        # east == 7.0 sits on the shared edge; the eastern tile carries that
        # column too, and including it keeps the crop window fully covered.
        tiles = set(srtm.tiles_for_bounds((6.5, 45.5, 7.0, 45.6)))
        assert tiles == {(45, 6), (45, 7)}


# ── .hgt decoding ─────────────────────────────────────────────────────────────

class TestDecodeHgt:
    def test_roundtrip_preserves_values_and_orientation(self):
        tile = _synthetic_tile()
        decoded = srtm.decode_hgt(_hgt_bytes(tile), samples_per_degree=TEST_SPD)
        assert decoded.shape == (TEST_SPD + 1, TEST_SPD + 1)
        np.testing.assert_array_equal(decoded, tile)

    def test_srtm1_shape(self):
        raw = np.zeros((3601, 3601), dtype='>i2').tobytes()
        assert srtm.decode_hgt(raw).shape == (3601, 3601)

    def test_voids_are_preserved(self):
        tile = _synthetic_tile()
        tile[2, 3] = srtm.SRTM_NODATA
        decoded = srtm.decode_hgt(_hgt_bytes(tile), samples_per_degree=TEST_SPD)
        assert decoded[2, 3] == srtm.SRTM_NODATA

    def test_truncated_payload_raises(self):
        # A partially downloaded tile must fail loudly, not reshape silently.
        with pytest.raises(ValueError, match="size"):
            srtm.decode_hgt(b"\x00" * 100, samples_per_degree=TEST_SPD)


# ── mosaic + crop ─────────────────────────────────────────────────────────────

class TestMosaic:
    """Geometry of the mosaic, hand-checked with a 5x5 tile (0.25 deg pixels).

    For ``bounds = (6.3, 45.3, 6.7, 45.7)`` and ``spd = 4`` the global sample
    lattice indices are ``lon * 4`` and ``lat * 4``, so the crop window is
    columns 25..27 and rows 181..183. Tile (45, 6) spans columns 24..28 and rows
    180..184, and its row 0 is the *north* edge (row 184).
    """

    BOUNDS = (6.3, 45.3, 6.7, 45.7)

    def test_single_tile_values_and_transform(self):
        tile = _synthetic_tile()
        elev, transform = srtm.mosaic_tiles({(45, 6): tile}, self.BOUNDS,
                                            samples_per_degree=TEST_SPD)

        assert elev.shape == (3, 3)
        # North-west output pixel = global (row 183, col 25) = tile (row 1, col 1).
        assert elev[0, 0] == tile[1, 1]
        # South-east output pixel = global (row 181, col 27) = tile (row 3, col 3).
        assert elev[2, 2] == tile[3, 3]

        assert transform.a == pytest.approx(TEST_RES)     # +x eastwards
        assert transform.e == pytest.approx(-TEST_RES)    # north-up raster
        assert transform.c == pytest.approx(25 * TEST_RES - TEST_RES / 2)   # 6.125
        assert transform.f == pytest.approx(183 * TEST_RES + TEST_RES / 2)  # 45.875

    def test_output_covers_the_requested_bounds(self):
        elev, transform = srtm.mosaic_tiles({(45, 6): _synthetic_tile()},
                                            self.BOUNDS,
                                            samples_per_degree=TEST_SPD)
        west, south, east, north = self.BOUNDS
        rows, cols = elev.shape
        assert transform.c <= west
        assert transform.f >= north
        assert transform.c + cols * transform.a >= east
        assert transform.f + rows * transform.e <= south

    def test_shared_edge_between_two_tiles_leaves_no_gap(self):
        # Straddle the 7 deg meridian: the two tiles share that column.
        tiles = {(45, 6): _synthetic_tile(base=0),
                 (45, 7): _synthetic_tile(base=10_000)}
        elev, transform = srtm.mosaic_tiles(tiles, (6.8, 45.3, 7.2, 45.7),
                                            samples_per_degree=TEST_SPD)
        assert not (elev == srtm.SRTM_NODATA).any()
        # Western columns come from tile 6, eastern ones from tile 7.
        assert elev[0, 0] < 10_000
        assert elev[0, -1] >= 10_000

    def test_missing_tile_becomes_nodata_not_an_exception(self):
        # Only the western tile is available; the eastern half stays nodata,
        # which the existing _fill_nodata in terrain_pipeline handles.
        elev, _ = srtm.mosaic_tiles({(45, 6): _synthetic_tile()},
                                    (6.8, 45.3, 7.2, 45.7),
                                    samples_per_degree=TEST_SPD)
        assert (elev == srtm.SRTM_NODATA).any()
        assert (elev != srtm.SRTM_NODATA).any()

    def test_no_tiles_at_all_is_all_nodata(self):
        elev, _ = srtm.mosaic_tiles({}, self.BOUNDS, samples_per_degree=TEST_SPD)
        assert (elev == srtm.SRTM_NODATA).all()


# ── download + cache ──────────────────────────────────────────────────────────

class TestReadTile:
    def test_downloads_then_caches(self, tmp_path, monkeypatch):
        tile = _synthetic_tile()
        payload = gzip.compress(_hgt_bytes(tile))
        calls = []

        def fake_urlopen(url, timeout=None):
            calls.append(url)
            return payload

        monkeypatch.setattr(srtm, "_read_url", fake_urlopen)

        first = srtm.read_tile(45, 6, cache_dir=tmp_path, samples_per_degree=TEST_SPD)
        np.testing.assert_array_equal(first, tile)
        assert len(calls) == 1
        assert (tmp_path / "N45E006.hgt.gz").exists()

        # Second read is served from disk — no second request.
        second = srtm.read_tile(45, 6, cache_dir=tmp_path, samples_per_degree=TEST_SPD)
        np.testing.assert_array_equal(second, tile)
        assert len(calls) == 1

    def test_force_download_refetches(self, tmp_path, monkeypatch):
        tile = _synthetic_tile()
        calls = []

        def fake_urlopen(url, timeout=None):
            calls.append(url)
            return gzip.compress(_hgt_bytes(tile))

        monkeypatch.setattr(srtm, "_read_url", fake_urlopen)
        srtm.read_tile(45, 6, cache_dir=tmp_path, samples_per_degree=TEST_SPD)
        srtm.read_tile(45, 6, cache_dir=tmp_path, samples_per_degree=TEST_SPD,
                       force_download=True)
        assert len(calls) == 2

    def test_absent_tile_returns_none(self, tmp_path, monkeypatch):
        # Ocean tiles are simply not on the mirror: nodata, not a crash.
        def fake_urlopen(url, timeout=None):
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

        monkeypatch.setattr(srtm, "_read_url", fake_urlopen)
        assert srtm.read_tile(0, -30, cache_dir=tmp_path,
                              samples_per_degree=TEST_SPD) is None

    def test_network_failure_propagates_with_an_actionable_message(self, tmp_path,
                                                                  monkeypatch):
        def fake_urlopen(url, timeout=None):
            raise urllib.error.URLError("no route to host")

        monkeypatch.setattr(srtm, "_read_url", fake_urlopen)
        with pytest.raises(RuntimeError, match="N45E006"):
            srtm.read_tile(45, 6, cache_dir=tmp_path, samples_per_degree=TEST_SPD)

    def test_corrupt_cached_tile_is_reported_with_its_path(self, tmp_path, monkeypatch):
        # The failure mode that produced the "corrupt SRTM tile" advice in
        # build_terrain_surface: the message must name the file to delete.
        cached = tmp_path / "N45E006.hgt.gz"
        cached.write_bytes(b"not gzip at all")
        monkeypatch.setattr(srtm, "_read_url",
                            lambda url, timeout=None: pytest.fail("must not download"))
        with pytest.raises(ValueError, match="N45E006.hgt.gz"):
            srtm.read_tile(45, 6, cache_dir=tmp_path, samples_per_degree=TEST_SPD)


# ── fetch_srtm_clip (the elevation.clip replacement) ──────────────────────────

class TestFetchSrtmClip:
    def _patch_small_tiles(self, monkeypatch):
        """Shrink SRTM1 to a 5x5 tile and serve synthetic data — no network."""
        monkeypatch.setitem(srtm.PRODUCT_SAMPLES_PER_DEGREE, "SRTM1", TEST_SPD)
        monkeypatch.setattr(
            srtm, "read_tile",
            lambda lat, lon, cache_dir, samples_per_degree,
            force_download=False, timeout=None: _synthetic_tile(),
        )

    def test_writes_a_georeferenced_wgs84_geotiff(self, tmp_path, monkeypatch):
        self._patch_small_tiles(monkeypatch)
        out = tmp_path / "clip.tif"

        srtm.fetch_srtm_clip(bounds=(6.3, 45.3, 6.7, 45.7), output=str(out),
                             cache_dir=str(tmp_path))

        assert out.exists()
        with rasterio.open(out) as src:
            assert src.crs.to_epsg() == 4326
            assert src.count == 1
            assert src.nodata == srtm.SRTM_NODATA
            assert src.dtypes[0] == 'int16'
            # Covers the request and is north-up, as steps 2-3 of the pipeline expect.
            assert src.bounds.left <= 6.3 and src.bounds.right >= 6.7
            assert src.bounds.bottom <= 45.3 and src.bounds.top >= 45.7
            assert src.transform.e < 0
            # A sampled value matches the synthetic tile at the same lattice node.
            data = src.read(1)
            assert data[0, 0] == _synthetic_tile()[1, 1]

    def test_existing_output_is_overwritten_not_appended(self, tmp_path, monkeypatch):
        self._patch_small_tiles(monkeypatch)
        out = tmp_path / "clip.tif"
        out.write_bytes(b"stale")
        srtm.fetch_srtm_clip(bounds=(6.3, 45.3, 6.7, 45.7), output=str(out),
                             cache_dir=str(tmp_path))
        with rasterio.open(out) as src:
            assert src.count == 1

    def test_unknown_product_raises(self, tmp_path):
        with pytest.raises(ValueError, match="SRTM1"):
            srtm.fetch_srtm_clip(bounds=(6.3, 45.3, 6.7, 45.7),
                                 output=str(tmp_path / "x.tif"),
                                 cache_dir=str(tmp_path),
                                 product="SRTM30")

    def test_inverted_bounds_raise(self, tmp_path):
        with pytest.raises(ValueError, match="bounds"):
            srtm.fetch_srtm_clip(bounds=(6.7, 45.7, 6.3, 45.3),
                                 output=str(tmp_path / "x.tif"),
                                 cache_dir=str(tmp_path))


# ── wiring into the terrain pipeline ─────────────────────────────────────────

class TestTerrainPipelineWiring:
    def test_pipeline_no_longer_imports_elevation_or_shells_out(self):
        """The acceptance condition of #286: no GDAL CLI, no make, no subprocess.

        ``elevation.clip`` ran ``make`` + ``gdalbuildvrt``, which are absent from
        an unactivated conda interpreter, from pip wheels, and from Windows.
        """
        source = Path("pase/ENVIRONMENT/terrain_pipeline.py").read_text()
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split('.')[0])
        assert "elevation" not in imported
        assert "subprocess" not in imported

    def test_build_terrain_surface_goes_through_the_fetcher(self, tmp_path,
                                                            monkeypatch):
        """End-to-end steps 1-4 with the download seam stubbed."""
        import pyvista as pv
        from pase.ENVIRONMENT import terrain_pipeline

        bounds = (6.3, 45.3, 6.7, 45.7)
        calls = []

        def fake_fetch(bounds, output, cache_dir=None, force_download=False,
                       product="SRTM1", timeout=None):
            calls.append(bounds)
            # A tiny WGS84 DEM covering the requested box, sloping east.
            res = 0.1
            rows = cols = 6
            data = (np.arange(rows * cols).reshape(rows, cols) * 10).astype(np.int16)
            transform = rasterio.transform.from_origin(6.2, 45.8, res, res)
            with rasterio.open(output, "w", driver="GTiff", height=rows,
                               width=cols, count=1, dtype="int16",
                               crs="EPSG:4326", transform=transform,
                               nodata=srtm.SRTM_NODATA) as dst:
                dst.write(data, 1)
            return output

        monkeypatch.setattr("pase.ENVIRONMENT.srtm.fetch_srtm_clip", fake_fetch)

        surface = terrain_pipeline.build_terrain_surface(
            bounds=bounds,
            cache_dir=str(tmp_path),
            center_lonlat=(6.5, 45.5),
        )

        assert calls == [bounds]
        assert isinstance(surface, pv.PolyData)
        assert surface.n_points > 0
        assert "Elevation" in surface.point_data
        assert surface.field_data["z_exaggeration"][0] == pytest.approx(1.0)
        # Centred on the given location, in metres (UTM), so the PV layout at the
        # origin stays aligned with the terrain.
        assert abs(surface.points[:, 0]).min() < 5_000


# ── live mirror ───────────────────────────────────────────────────────────────

@pytest.mark.network
class TestLiveMirror:
    """Real fetches from the public skadi mirror (no authentication).

    Asserted against independently known ground truth rather than against our own
    output, so a sign or row-order regression cannot pass.
    """

    def test_real_tile_decodes_and_matches_known_elevations(self, tmp_path):
        tile = srtm.read_tile(45, 6, cache_dir=tmp_path, samples_per_degree=3600)
        assert tile is not None
        assert tile.shape == (3601, 3601)

        def sample(lat, lon):
            row = int(round((46 - lat) * 3600))
            col = int(round((lon - 6) * 3600))
            return int(tile[row, col])

        # Chamonix town centre, ~1035 m.
        assert 950 < sample(45.9237, 6.8694) < 1150
        # Mont Blanc summit (4808 m); SRTM smooths sharp peaks, hence the band.
        assert 4600 < sample(45.8326, 6.8652) < 4850
        # Sanity on the whole tile: alpine relief, no wild sentinel leakage.
        valid = tile[tile != srtm.SRTM_NODATA]
        assert 0 < valid.min() < 1000
        assert 4000 < valid.max() < 5000

    def test_clip_is_georeferenced_against_the_source_tile(self, tmp_path):
        out = tmp_path / "chamonix.tif"
        srtm.fetch_srtm_clip(bounds=(6.8493, 45.9038, 6.8893, 45.9438),
                             output=str(out), cache_dir=str(tmp_path))
        with rasterio.open(out) as src:
            assert src.crs.to_epsg() == 4326
            assert abs(src.transform.a) == pytest.approx(1 / 3600, rel=1e-6)
            value = next(src.sample([(6.8694, 45.9237)]))[0]
        assert 950 < value < 1150
