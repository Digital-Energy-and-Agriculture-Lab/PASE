"""
Equivalence tests for the matrix-vector rewrite of
Ray_casting_scene.compute_daily_diff_irradiation.

The optimized method accumulates matrix-vector products instead of
materializing the full (nSourcePoints x nSkyPatches) array at every instant.
This is a pure re-association of the original sum, so the daily diffuse
irradiance must be identical (to machine precision) to the previous
per-instant implementation, both without and with sun tracking.

The reference implementation below replicates the original (pre-optimization)
computation by stacking the per-instant outputs of get_shaded_radiance_contrib,
so the test stays valid even though the production method no longer takes
that path for the panel / tracking cases.
"""
import numpy as np
import pandas as pd
import pytest

from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.sky_model import ReinhartSky

VALID_SKY_TYPES = [1, 4, 7, 11, 13]
N_FREQ = 4


@pytest.fixture(scope="module")
def discrete_sky():
    return ReinhartSky(MF=1).reinhart_patches


def _make_weather(rng, n_instants):
    return pd.DataFrame({
        "DHI": rng.uniform(20.0, 400.0, n_instants),
        "azimuth": rng.uniform(90.0, 270.0, n_instants),
        "elevation": rng.uniform(5.0, 70.0, n_instants),
        "CIE Sky Type": rng.choice(VALID_SKY_TYPES, n_instants),
    })


def _make_scene(discrete_sky, geometry, diffuse_mask):
    """Minimal scene exposing only what the diffuse computation needs."""
    scene = object.__new__(Ray_casting_scene)
    scene.discrete_sky = discrete_sky
    scene.geometry = geometry
    scene.diffuse_mask = diffuse_mask
    scene.get_diffuse_weights_map()  # sets normalized_diffuse_weights_map
    return scene


def _reference_diff_irradiation(scene, df, n_freq, indices=None):
    """Original per-instant implementation, used as ground truth."""
    dhi = df["DHI"].to_numpy()
    az = df["azimuth"].to_numpy()
    el = df["elevation"].to_numpy()
    sky_type = df["CIE Sky Type"].to_numpy()
    T = dhi.shape[0]

    outs = [scene.get_shaded_radiance_contrib(az[i], el[i], sky_type[i])
            for i in range(T)]
    if outs[0].ndim == 2:  # no tracking
        stacked = np.stack(outs, axis=0)
        diff = (stacked * dhi[:, None, None]).sum(axis=(0, 2))
    elif outs[0].ndim == 3:  # tracking
        stacked = np.stack(outs, axis=0)
        selected = stacked[np.arange(T), :, indices, :]
        diff = (selected * dhi[:, None, None]).sum(axis=(0, 2))
    else:  # ndim == 1
        stacked = np.stack(outs, axis=0)
        diff = (stacked * dhi[:, None, None]).sum(axis=-1)
    return diff * 3600.0 * 1e-6 / n_freq


@pytest.mark.parametrize("n_sourcepoints", [200, 5000])
def test_diff_irradiation_matvec_equivalence_no_tracking(discrete_sky, n_sourcepoints):
    rng = np.random.default_rng(0)
    n_patches = len(discrete_sky)
    df = _make_weather(rng, n_instants=15)
    diffuse_mask = rng.uniform(0.0, 1.0, (n_sourcepoints, n_patches))

    scene = _make_scene(discrete_sky, geometry=object(), diffuse_mask=diffuse_mask)
    fast = scene.compute_daily_diff_irradiation(df.copy(), N_FREQ)

    ref_scene = _make_scene(discrete_sky, geometry=object(), diffuse_mask=diffuse_mask)
    ref = _reference_diff_irradiation(ref_scene, df.copy(), N_FREQ)

    assert np.allclose(fast, ref)


@pytest.mark.parametrize("n_sourcepoints", [200, 5000])
def test_diff_irradiation_matvec_equivalence_tracking(discrete_sky, n_sourcepoints):
    rng = np.random.default_rng(1)
    n_patches = len(discrete_sky)
    n_orientations = 24
    df = _make_weather(rng, n_instants=15)
    diffuse_mask = rng.uniform(0.0, 1.0, (n_sourcepoints, n_orientations, n_patches))
    indices = rng.integers(0, n_orientations, len(df))

    geometry = [object()] * n_orientations  # list -> tracking branch
    scene = _make_scene(discrete_sky, geometry=geometry, diffuse_mask=diffuse_mask)
    fast = scene.compute_daily_diff_irradiation(df.copy(), N_FREQ, indices=indices)

    ref_scene = _make_scene(discrete_sky, geometry=geometry, diffuse_mask=diffuse_mask)
    ref = _reference_diff_irradiation(ref_scene, df.copy(), N_FREQ, indices=indices)

    assert np.allclose(fast, ref)


def test_diff_irradiation_tracking_requires_indices(discrete_sky):
    rng = np.random.default_rng(2)
    n_patches = len(discrete_sky)
    n_orientations = 8
    df = _make_weather(rng, n_instants=5)
    diffuse_mask = rng.uniform(0.0, 1.0, (10, n_orientations, n_patches))

    geometry = [object()] * n_orientations
    scene = _make_scene(discrete_sky, geometry=geometry, diffuse_mask=diffuse_mask)
    with pytest.raises(ValueError):
        scene.compute_daily_diff_irradiation(df.copy(), N_FREQ, indices=None)
