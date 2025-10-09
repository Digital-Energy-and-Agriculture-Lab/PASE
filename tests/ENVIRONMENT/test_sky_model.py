import math
import numpy as np
import pytest

from pase.ENVIRONMENT.sky_model import ReinhartSky

sky = ReinhartSky()

@pytest.mark.parametrize(
    "mf, expected_mf, expected_f",
    [
        (1, 1, 0),
        (2, 2, 1),
        (4, 4, 2),
        (8, 8, 3),
        (16, 16, 4),
        (4.0, 4, 2),               # float entier accepté
        (np.int64(8), 8, 3),       # numpy int accepté
        (np.float64(32.0), 32, 5), # numpy float accepté
        ("4", 4, 2),               # chaîne numérique acceptée
    ],
)
def test_validate_mf_f_valid_values(mf, expected_mf, expected_f):
    got_mf, got_f = sky.validate_MF_F(mf)
    assert got_mf == expected_mf
    assert got_f == expected_f
    assert (2 ** got_f) == got_mf

@pytest.mark.parametrize("mf", [0, -1, -2, 3.5, "four", None])
def test_validate_mf_f_invalid_values(mf):
    with pytest.raises((TypeError, ValueError)):
        sky.validate_MF_F(mf)

def test_validate_mf_f_boolean_behavior():
    got_mf, got_f = sky.validate_MF_F(True)
    assert got_mf == 1 and got_f == 0

def test_validate_mf_f_large_values():
    mf = 2 ** 30
    got_mf, got_f = sky.validate_MF_F(mf)
    assert got_mf == mf
    assert got_f == 30
    assert (2 ** got_f) == got_mf

def test_validate_mf_f_string_equivalence():
    got_mf, got_f = sky.validate_MF_F("16")
    assert got_mf == 16 and got_f == 4

@pytest.mark.parametrize(
    'mf',
    np.arange(1, 32+1)
)
def test_num_sky_patches_matches_reference(mf):
    # Reference is Ivanova et al. formula:
    # Ivanova_num_total = 144 * (MF**2) + 1
    # Check for MF values 1 to 16

    # Compute reference:
    Ivanova_num_total = 144 * (mf**2) + 1

    sky = ReinhartSky(MF=mf)
    _, reinhart_num_total = sky.get_reinhart()
    assert reinhart_num_total == Ivanova_num_total

@pytest.mark.parametrize(
    'mf',
    np.arange(1, 32+1)
)
def test_patches_sum_surf_areas(mf):
    """
    Sum of normalized surface areas of all patches should amount to 1
    :param mf:
    """
    sky = ReinhartSky(MF=mf)
    sum_surf_areas = sky.reinhart_patches['Normalized surf area'].sum()
    assert math.isclose(sum_surf_areas, 1, rel_tol=5e-3)

@pytest.mark.parametrize(
    'mf',
    np.arange(1, 32+1)
)
def test_patches_sum_solid_angles(mf):
    sky = ReinhartSky(MF=mf)
    sum_solid_angles = sky.reinhart_patches['solid_angle_sr'].sum()
    assert math.isclose(sum_solid_angles, 2*np.pi, rel_tol=5e-3)

def test_compute_solid_angle_elev_azim():
    assert sky.compute_solid_angle_from_elev_azim(45, 2)

def test_compute_solid_angle_cone():
    assert math.isclose(sky.compute_solid_angle_cone(5),
                        0.024,
                        rel_tol=1e-2)