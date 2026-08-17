import math
import numpy as np
import pytest

from pase.ENVIRONMENT.light import get_sun_vector
from pase.ENVIRONMENT.sky_model import ReinhartSky, CIEStandardSky

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
    assert len(sky.reinhart_patches) == Ivanova_num_total

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


# ---------------------------------------------------------------------------
# compute_rel_radiance normalization
# ---------------------------------------------------------------------------

def test_uniform_sky_rel_radiance_sums_to_N():
    """
    For sky type 5 (uniform), rel_radiance_distribution must equal 1 for every
    patch (f_P = 1, not f_P/N).
    """
    sky_MF1 = ReinhartSky(MF=1)
    N = len(sky_MF1.reinhart_patches)
    cie = CIEStandardSky(sky_MF1.reinhart_patches, sun_az=180, sun_el=45, sky_type=5)
    assert np.isclose(cie.rel_radiance_distribution.sum(), N, rtol=1e-6), (
        f"Expected sum={N} (f_P=1 for all patches); "
        f"got {cie.rel_radiance_distribution.sum():.4f}. "
        f"Possible /N normalization bug."
    )


# ---------------------------------------------------------------------------
# TestCIEStandardSky
# ---------------------------------------------------------------------------

class TestCIEStandardSky:

    SUN_AZ = 180.0
    SUN_EL = 45.0
    ALL_SKY_TYPES = list(range(1, 16))

    @pytest.fixture(scope='class')
    def patches(self):
        return ReinhartSky(MF=1).reinhart_patches

    @pytest.mark.parametrize('sky_type', ALL_SKY_TYPES)
    def test_rel_radiance_non_negative(self, patches, sky_type):
        """Relative radiance must be non-negative for all sky types and all patches."""
        cie = CIEStandardSky(patches, sun_az=self.SUN_AZ, sun_el=self.SUN_EL,
                             sky_type=sky_type)
        assert (cie.rel_radiance_distribution >= 0).all(), (
            f"sky_type={sky_type}: negative values found in rel_radiance_distribution"
        )

    @pytest.mark.parametrize('sky_type', ALL_SKY_TYPES)
    def test_rel_radiance_not_divided_by_N(self, patches, sky_type):
        """
        rel_radiance_distribution must not be divided by N (number of sky patches).
        By construction of the CIE model, the zenith patch always has f_P = 1, so
        max(rel_radiance_distribution) >= 1. If the /N bug were present, the max
        would be <= 1/N << 1.
        """
        N = len(patches)
        cie = CIEStandardSky(patches, sun_az=self.SUN_AZ, sun_el=self.SUN_EL,
                             sky_type=sky_type)
        assert cie.rel_radiance_distribution.max() >= 1.0 - 1e-6, (
            f"sky_type={sky_type}: max={cie.rel_radiance_distribution.max():.6f}. "
            f"Suspicion of /N normalization bug (1/N = {1/N:.5f})"
        )

    def test_uniform_sky_constant_radiance(self, patches):
        """For sky type 5 (uniform), all patches must have identical radiance f_P = 1."""
        cie = CIEStandardSky(patches, sun_az=self.SUN_AZ, sun_el=self.SUN_EL,
                             sky_type=5)
        assert np.allclose(cie.rel_radiance_distribution, 1.0), (
            "Uniform sky (type 5): expected f_P=1 for all patches, "
            f"got min={cie.rel_radiance_distribution.min():.6f}, "
            f"max={cie.rel_radiance_distribution.max():.6f}"
        )

    @pytest.mark.parametrize('sky_type', ALL_SKY_TYPES)
    def test_sky_integral_finite_positive(self, patches, sky_type):
        """
        sky_integral = Σ_P(f_P * norm_P) must be finite and positive for all sky
        types. This is the per-timestep normalization factor used in
        get_shaded_radiance_contrib() to ensure energy conservation.
        """
        norm = patches['cos(z)'].values * patches['Normalized surf area'].values
        norm = norm / norm.sum()
        cie = CIEStandardSky(patches, sun_az=self.SUN_AZ, sun_el=self.SUN_EL,
                             sky_type=sky_type)
        sky_integral = float((cie.rel_radiance_distribution * norm).sum())
        assert np.isfinite(sky_integral), (
            f"sky_type={sky_type}: sky_integral is not finite"
        )
        assert sky_integral > 0, (
            f"sky_type={sky_type}: sky_integral={sky_integral:.4f} is not positive"
        )


# ---------------------------------------------------------------------------
# Sky patch azimuth pairing (issue #300)
# ---------------------------------------------------------------------------

def _compass_heading(x, y):
    """
    Compass heading of a horizontal direction: 0 deg = North, positive clockwise
    towards East, in the PASE world frame (East = X, North = Y, Zenith = Z).

    :param x: East component(s)
    :param y: North component(s)
    :return: heading(s) in [0, 360) [deg]
    """
    return np.degrees(np.arctan2(x, y)) % 360.0


def _wrapped_gap(a, b):
    """Absolute angular difference between two headings [deg], wrap-aware."""
    return np.abs((np.asarray(a) - np.asarray(b) + 180.0) % 360.0 - 180.0)


class TestSkyPatchAzimuthPairing:
    """
    The discrete sky carries each patch direction twice: as the 'az'/'el' columns,
    read as compass angles by the CIE radiance model and by the horizon mask, and
    as the 'x'/'y'/'z' columns, used as ray directions by the diffuse ray casting
    and by the diffuser map. The two must describe the same direction.

    The sun azimuths below are all at least 45 deg away from both 45 deg and
    225 deg. Those two headings are the fixed points of the reflection that
    issue #300 introduces, so a sun placed there cannot see the defect.
    """

    SUN_AZ = (90.0, 135.0, 180.0, 270.0, 315.0)
    SUN_EL = (10.0, 30.0, 60.0)
    ANISOTROPIC_SKY_TYPES = (7, 8, 11, 12, 13, 15)

    # Measured post-fix bounds over the grid below, at MF 1 and 2:
    #   angle(brightest patch, solar vector)  <= 27.0 deg  (>= 40.1 deg mirrored)
    #   radiance(patch nearest the sun)/peak  >= 0.755     (<= 0.376 mirrored)
    # The thresholds sit in those gaps. They are not tight bounds on the physics:
    # under a strongly graded sky the brightest patch is genuinely not always the
    # one nearest the sun, so the assertions below deliberately do not require it.
    MAX_ANGLE_TO_SUN_DEG = 35.0
    MIN_NEAREST_RADIANCE_RATIO = 0.5

    @pytest.fixture(scope='class')
    def patches(self):
        return ReinhartSky(MF=1).reinhart_patches

    @pytest.mark.parametrize('mf', [1, 2, 4])
    def test_patch_heading_matches_declared_azimuth(self, mf):
        """
        The heading a patch is drawn at must be the compass azimuth it declares.

        This is the single invariant behind issue #300: every downstream consumer
        pairs the 'az' column with the cartesian columns by index, so if these two
        disagree the radiance, the horizon visibility and the ray direction of a
        given patch describe three different points of the sky.

        The zenith cap is excluded: it has no horizontal heading.
        """
        patches = ReinhartSky(MF=mf).reinhart_patches
        off_zenith = patches['el'].to_numpy() < 90.0
        drawn = _compass_heading(patches['x'].to_numpy()[off_zenith],
                                 patches['y'].to_numpy()[off_zenith])
        declared = patches['az'].to_numpy()[off_zenith]
        gap = _wrapped_gap(drawn, declared)
        assert gap.max() < 1e-6, (
            f"MF={mf}: {int((gap > 1e-6).sum())} of {off_zenith.sum()} off-zenith "
            f"patches are drawn away from their declared azimuth, by up to "
            f"{gap.max():.3f} deg. Worst patch: az column "
            f"{declared[int(np.argmax(gap))]:.1f} deg drawn at "
            f"{drawn[int(np.argmax(gap))]:.1f} deg."
        )

    @pytest.mark.parametrize('mf', [1, 2, 4])
    def test_zenith_patch_points_to_zenith(self, mf):
        """
        The zenith cap must point straight up, which is what makes it legitimate
        to exclude it from the heading invariant above.
        """
        patches = ReinhartSky(MF=mf).reinhart_patches
        cap = patches.loc[patches['el'] >= 90.0]
        assert len(cap) == 1, f"MF={mf}: expected exactly one zenith cap, got {len(cap)}"
        np.testing.assert_allclose(
            cap[['x', 'y', 'z']].to_numpy()[0], [0.0, 0.0, 1.0], atol=1e-9
        )

    @pytest.mark.parametrize('mf', [1, 2])
    def test_patch_directions_are_unit_vectors(self, mf):
        """Patch directions must be unit vectors, whatever the convention."""
        patches = ReinhartSky(MF=mf).reinhart_patches
        norms = np.linalg.norm(patches[['x', 'y', 'z']].to_numpy(), axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-9)

    @pytest.mark.parametrize('sky_type', ANISOTROPIC_SKY_TYPES)
    @pytest.mark.parametrize('sun_az', SUN_AZ)
    def test_brightest_patch_lies_towards_the_sun(self, patches, sky_type, sun_az):
        """
        The most radiant patch of an anisotropic sky must lie in the direction of
        the sun, where the direction is taken from the cartesian columns and the
        sun from get_sun_vector -- so this crosses the radiance model's azimuth
        convention with the ray directions' one.

        Not asserted: that the brightest patch *is* the patch nearest the sun.
        Under a steep gradation the horizon rows can outshine the circumsolar
        region by a patch or two, which is physical.
        """
        directions = patches[['x', 'y', 'z']].to_numpy()
        for sun_el in self.SUN_EL:
            sun = get_sun_vector(np.array([sun_el]), np.array([sun_az]))[0]
            radiance = np.asarray(CIEStandardSky(patches, sun_az, sun_el,
                                                 sky_type=sky_type)
                                  .rel_radiance_distribution)
            brightest = int(np.argmax(radiance))
            angle = np.degrees(np.arccos(
                np.clip(float(directions[brightest] @ sun), -1.0, 1.0)))
            assert angle <= self.MAX_ANGLE_TO_SUN_DEG, (
                f"sky_type={sky_type}, sun az={sun_az} el={sun_el}: the brightest "
                f"patch (index {brightest}, az column "
                f"{patches['az'].iloc[brightest]:.1f} deg, drawn at heading "
                f"{_compass_heading(*directions[brightest][:2]):.1f} deg) sits "
                f"{angle:.1f} deg from the solar vector."
            )

    @pytest.mark.parametrize('sky_type', ANISOTROPIC_SKY_TYPES)
    @pytest.mark.parametrize('sun_az', SUN_AZ)
    def test_patch_nearest_the_sun_carries_near_peak_radiance(self, patches,
                                                              sky_type, sun_az):
        """
        Converse of the previous witness: the patch geometrically nearest the
        solar vector must be one of the bright ones. It catches the same defect
        from the other end -- under the mirror it carries a few percent of the
        peak.
        """
        directions = patches[['x', 'y', 'z']].to_numpy()
        for sun_el in self.SUN_EL:
            sun = get_sun_vector(np.array([sun_el]), np.array([sun_az]))[0]
            nearest = int(np.argmax(directions @ sun))
            radiance = np.asarray(CIEStandardSky(patches, sun_az, sun_el,
                                                 sky_type=sky_type)
                                  .rel_radiance_distribution)
            ratio = float(radiance[nearest] / radiance.max())
            assert ratio >= self.MIN_NEAREST_RADIANCE_RATIO, (
                f"sky_type={sky_type}, sun az={sun_az} el={sun_el}: the patch "
                f"nearest the solar vector (index {nearest}) carries {ratio:.3f} "
                f"of the peak radiance."
            )