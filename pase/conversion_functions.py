import numpy as np
from scipy.spatial.transform import Rotation as R

# Azimuth frames. See DOCUMENTATION/angle_conventions.md.
#
# In the PASE world frame (East = X, North = Y, Zenith = Z):
#
#   COMPASS        0 deg = North, positive clockwise towards East.
#                  Unit vector (sin A, cos A). Used by get_sun_vector, the horizon
#                  mask, the CIE sky radiance model, CentralAzimut, PVGIS, pvlib.
#   TRIGONOMETRIC  0 deg = East, positive counterclockwise towards North.
#                  Unit vector (cos A, sin A). The mathematical convention, used by
#                  the primitives below and by pyvista's rotate_z.
#
# Reading one as the other swaps the East and North components, which is a
# reflection about the NE-SW diagonal: NE and SW are unchanged, N and E trade
# places, and SE and NW end up half a turn apart. That was issue #300.
COMPASS = 'compass'
TRIGONOMETRIC = 'trigonometric'

_FRAMES = (COMPASS, TRIGONOMETRIC)

_DEGREE_UNITS = ('deg', 'degree', 'degrees')
_RADIAN_UNITS = ('rad', 'radian', 'radians')


def _validate_frame(frame):
    """
    Check that an azimuth frame was declared, and that it is one we know.

    Args:
        frame: the frame of the azimuth being converted --> str

    Returns:
        the validated frame --> str
    """
    if frame not in _FRAMES:
        raise ValueError(
            f"frame must be one of {_FRAMES}, received {frame!r}. The frame is "
            f"mandatory: an azimuth is meaningless without it (see "
            f"DOCUMENTATION/angle_conventions.md)")
    return frame


def compass_to_trig(azimuth_deg):
    """
    Convert a compass azimuth (0 = North, clockwise) to a trigonometric one
    (0 = East, counterclockwise): az_trig = 90 - az_compass.

    The conversion is a reflection, so it is its own inverse — see
    trig_to_compass — and it leaves 45 deg (NE) and 225 deg (SW) unchanged. Those
    two fixed points are why a test with the sun on the NE-SW diagonal cannot
    detect a frame mix-up.

    Args:
        azimuth_deg: compass azimuth [deg] --> number, array or Series

    Returns:
        the same direction as a trigonometric azimuth [deg], not wrapped
    """
    return 90.0 - azimuth_deg


def trig_to_compass(azimuth_deg):
    """
    Convert a trigonometric azimuth to a compass one. Same formula as
    compass_to_trig, since the conversion is an involution; both names exist so
    that call sites can state which way they are reading.

    Args:
        azimuth_deg: trigonometric azimuth [deg] --> number, array or Series

    Returns:
        the same direction as a compass azimuth [deg], not wrapped
    """
    return compass_to_trig(azimuth_deg)


def compass_to_unit_vector(az_compass_deg, el_deg=None, zenith_deg=None):
    """
    Build unit vectors in the world frame from compass azimuths. This is the
    sanctioned way to turn a compass direction into a ray direction: prefer it to
    calling sph_to_cart with an explicit frame.

    Exactly one of el_deg and zenith_deg must be given.

    Args:
        az_compass_deg: compass azimuth [deg] --> number, array or Series
        el_deg: elevation above the horizon [deg] --> number, array or Series
        zenith_deg: zenith angle [deg], i.e. 90 - elevation --> number, array or Series

    Returns:
        x, y, z: components along East, North and Zenith, unit norm
    """
    if (el_deg is None) == (zenith_deg is None):
        raise ValueError("pass exactly one of el_deg or zenith_deg, not both and "
                         "not neither")

    return sph_to_cart('deg', az_compass_deg, elev=el_deg,
                       zenith_angle=zenith_deg, frame=COMPASS)


def unit_vector_to_compass_deg(x, y):
    """
    Compass heading of a direction, from its horizontal components. The inverse of
    compass_to_unit_vector, wrapped into [0, 360).

    A vector pointing straight up has no heading; this returns 0 for it rather
    than raising, so filter zenith directions out before calling if that matters.

    Args:
        x: East component --> number or array
        y: North component --> number or array

    Returns:
        compass heading [deg] in [0, 360)
    """
    return np.degrees(np.arctan2(x, y)) % 360.0


def cart_to_sph(x, y, z, *, frame):
    """
    Converts Cartesian coordinates to spherical coordinates.

    x, y, z : float : Cartesian coordinates
    frame : str : COMPASS or TRIGONOMETRIC, the frame the returned azimuth is
            expressed in. Keyword-only and mandatory.

    Returns:
    azimuth : float : azimuth angle in radians, in the requested frame, not
              wrapped (so it can fall outside [0, 2*pi)); use
              unit_vector_to_compass_deg for a wrapped compass heading in degrees
    zenith : float : zenith angle in radians
    """
    _validate_frame(frame)

    h = np.sqrt(x ** 2 + y ** 2)
    azimuth = np.arctan2(y, x)
    zenith = np.arctan2(h, z)

    if frame == COMPASS:
        azimuth = np.pi / 2 - azimuth

    return azimuth, zenith


def sph_to_cart(units, azimuth, elev=None, zenith_angle=None, dist=1, *, frame):
    """
    Convert spherical coordinates to cartesian (x,y,z) coordinates in the world
    frame: x towards East, y towards North, z towards the zenith.

    Args:
        units: 'deg' or 'rad'
        units type: str
        azimuth: azimuth angle in [deg] or [rad] (consistent with "units" arg)
        azimuth type: number or 1D array
        elev: elevation angle in [deg] or [rad] (consistent with "units" arg), only pass this or zenith_angle
        elev type: number or 1D array
        zenith_angle: zenith angle in [deg] or [rad] (consistent with "units" arg), only pass this or elev
        zenith_angle type: number or 1D array
        dist: the radius of the sphere, defaults to 1
        dist type: number or 1D array
        frame: COMPASS or TRIGONOMETRIC, the frame "azimuth" is expressed in.
               Keyword-only and mandatory: the same number means two different
               directions in the two frames, so there is no safe default.
        frame type: str

    Returns:
        x: x coordinates (East)
        y: y coordinates (North)
        z: z coordinates (Zenith)
    """

    _validate_frame(frame)

    if units not in _DEGREE_UNITS + _RADIAN_UNITS:
        raise ValueError('Incorrect units provided')

    if zenith_angle is not None and elev is not None:
        raise ValueError('You should only pass zenith_angle or elev arg, not both')

    if units in _DEGREE_UNITS:
        azimuth = np.deg2rad(azimuth)

        if elev is not None:
            elev = np.deg2rad(elev)

        if zenith_angle is not None:
            zenith_angle = np.deg2rad(zenith_angle)

    if zenith_angle is None:
        zenith_angle = (np.pi/2) - elev

    if frame == COMPASS:
        # Same reflection as compass_to_trig, in radians
        azimuth = (np.pi / 2) - azimuth

    x = dist * np.sin(zenith_angle) * np.cos(azimuth)
    y = dist * np.sin(zenith_angle) * np.sin(azimuth)
    z = dist * np.cos(zenith_angle)

    return x, y, z


def rotation_coordinate(vector_to_rotate, unit_vector, angle):
    """
    Function to rotate the directions of transmitted light
    from the diffuser frame of reference to the global frame of reference.

    Input :
        Vector_to_rotate : matrix of 3xNxP
        unit_vector : vector of rotation (rotation axis)
        angle : angle of rotation in radians
    Output :
        rotated vector with the same shape as the entry
    """
    x, y, z = unit_vector
    rot_mat = R.from_quat([np.sin(angle / 2) * x, np.sin(angle / 2) * y, np.sin(angle / 2) * z, np.cos(angle / 2)])
    vect_to_reshape_T = vector_to_rotate.T
    vtr = vect_to_reshape_T.reshape(vect_to_reshape_T.shape[0] * vect_to_reshape_T.shape[1], 3)
    vect_rot = rot_mat.apply(vtr)
    vect_rot = vect_rot.reshape(vect_to_reshape_T.shape)
    return vect_rot.T
