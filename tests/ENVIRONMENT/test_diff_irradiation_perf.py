"""
Regression guard for the matrix-vector rewrite of
Ray_casting_scene.compute_daily_diff_irradiation.

The optimized method accumulates matrix-vector products instead of materializing
the full (nSourcePoints x nSkyPatches) array per instant. Pure re-association ->
daily diffuse irradiance must be identical to the old per-instant path, with and
without sun tracking. No-track *physics* is already locked by
test_class_raytracingscene.test_diffuse_irr_unity_all_sky_types; what is new here
is multi-instant accumulation and the tracking branch (no golden exists for it).

Equivalence is exact and the code path is identical for any nSourcePoints (a
single matmul / broadcast over axis 0), so a small size and a few mixed-sky-type
instants are enough -- a larger grid would only add runtime, not coverage.
"""
import numpy as np
import pandas as pd
import pytest

from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.sky_model import ReinhartSky

VALID_SKY_TYPES = [1, 7, 13]
N_FREQ = 4
N_SOURCES = 64    # equivalence is exact for any size (matmul/broadcast over axis 0)
N_INSTANTS = 4    # >1 instant, mixed sky types -> locks per-instant accumulation


@pytest.fixture(scope="module")
def discrete_sky():
    return ReinhartSky(MF=1).reinhart_patches


def _make_weather(rng, n):
    return pd.DataFrame({
        "DHI": rng.uniform(20.0, 400.0, n),
        "azimuth": rng.uniform(90.0, 270.0, n),
        "elevation": rng.uniform(5.0, 70.0, n),
        "CIE Sky Type": rng.choice(VALID_SKY_TYPES, n),
    })


def _make_scene(discrete_sky, geometry, diffuse_mask):
    """Minimal scene exposing only what the diffuse computation reads."""
    scene = object.__new__(Ray_casting_scene)
    scene.discrete_sky = discrete_sky
    scene.geometry = geometry
    scene.diffuse_mask = diffuse_mask
    scene.get_diffuse_weights_map()  # sets normalized_diffuse_weights_map
    return scene


def _reference(scene, df, indices=None):
    """Original per-instant path (via get_shaded_radiance_contrib) = oracle."""
    dhi = df["DHI"].to_numpy()
    az, el, st = (df[c].to_numpy() for c in ("azimuth", "elevation", "CIE Sky Type"))
    outs = np.stack([scene.get_shaded_radiance_contrib(az[i], el[i], st[i])
                     for i in range(len(df))], axis=0)
    if indices is None:                                  # no tracking: (T, M, P)
        diff = (outs * dhi[:, None, None]).sum(axis=(0, 2))
    else:                                                # tracking: (T, M, O, P)
        sel = outs[np.arange(len(df)), :, indices, :]
        diff = (sel * dhi[:, None, None]).sum(axis=(0, 2))
    return diff * 3600.0 * 1e-6 / N_FREQ


def test_equivalence_no_tracking(discrete_sky):
    rng = np.random.default_rng(0)
    p = len(discrete_sky)
    df = _make_weather(rng, N_INSTANTS)
    mask = rng.uniform(0.0, 1.0, (N_SOURCES, p))
    fast = _make_scene(discrete_sky, object(), mask).compute_daily_diff_irradiation(df.copy(), N_FREQ)
    ref = _reference(_make_scene(discrete_sky, object(), mask), df.copy())
    assert np.allclose(fast, ref)


def test_equivalence_tracking(discrete_sky):
    rng = np.random.default_rng(1)
    p, o = len(discrete_sky), 6
    df = _make_weather(rng, N_INSTANTS)
    mask = rng.uniform(0.0, 1.0, (N_SOURCES, o, p))
    idx = rng.integers(0, o, N_INSTANTS)
    geom = [object()] * o  # list -> tracking branch
    fast = _make_scene(discrete_sky, geom, mask).compute_daily_diff_irradiation(df.copy(), N_FREQ, indices=idx)
    ref = _reference(_make_scene(discrete_sky, geom, mask), df.copy(), indices=idx)
    assert np.allclose(fast, ref)


def test_tracking_requires_indices(discrete_sky):
    rng = np.random.default_rng(2)
    p, o = len(discrete_sky), 6
    df = _make_weather(rng, N_INSTANTS)
    mask = rng.uniform(0.0, 1.0, (8, o, p))
    scene = _make_scene(discrete_sky, [object()] * o, mask)
    with pytest.raises(ValueError):
        scene.compute_daily_diff_irradiation(df.copy(), N_FREQ, indices=None)
