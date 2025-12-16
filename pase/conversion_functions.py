import numpy as np
from scipy.spatial.transform import Rotation as R

def cart_to_sph(x, y, z):
    """

            Args:
                cart_coords:

            Returns:
                zenith_angle: zenith angle [rad]
            """
    r = np.sqrt(x**2 + y**2 + z**2)

    if z > 0:
        zenith = np.arctan(np.sqrt(x**2+y**2)/z)
    elif z < 0:
        raise NotImplementedError('Not done yet')
    elif (z == 0) and (np.sqrt(x**2+y**2) != 0):
        zenith = np.pi/2

    elev = np.pi/2 - zenith

    if x > 0:
        az = np.arctan(y/x)
    elif (x < 0) and (y >= 0):
        az = np.arctan(y/x) + np.pi
    elif (x < 0) and (y < 0):
        az = np.arctan(y/x) - np.pi
    elif (x==0) and (y > 0):
        az = np.pi/2
    elif (x==0) and (y < 0):
        az = -np.pi/2
    elif (x==0) and (y==0):
        az = 0  # should be nan but to be able to inverse this operation 0 is better

    return az, zenith

def cartesian_to_spherical(x, y, z):
    """
    Converts Cartesian coordinates to spherical coordinates.

    x, y, z : float : Cartesian coordinates

    Returns:
    azimuth : float : azimuth angle in degrees
    zenith : float : zenith angle in degrees
    """
    h = np.sqrt(x ** 2 + y ** 2)
    azimuth = np.arctan2(y, x)
    zenith = np.arctan2(h, z)
    return azimuth, zenith

def get_zenith_angle_from_cart(cart_coords):
    """

    Args:
        cart_coords: cartesian coordinates (x, y and z) to convert to azimuth, zenith
        cart_coords type: Numpy array of shape (N, 3)

    Returns:
        azimuth_angle: zenith angle [rad]
        zenith_angle: zenith angle [rad]
    """
    cart_to_sph_vect = np.vectorize(cart_to_sph)

    x_vect = np.atleast_2d(cart_coords)[:, 0]
    y_vect = np.atleast_2d(cart_coords)[:, 1]
    z_vect = np.atleast_2d(cart_coords)[:, 2]

    azimuth, zenith_angle = cart_to_sph_vect(x_vect, y_vect, z_vect)

    return azimuth, zenith_angle

def sph_to_cart(units, azimut, elev=None, zenith_angle=None, dist=1):
    """
    Convert spherical coordinates to cartesian (x,y,z) coordinates.

    Args:
        units: 'deg' or 'rad'
        units type: str
        azimut: azimuth angle in [deg] or [rad] (consistent with "units" arg)
        azimut type: number or 1D array
        elev: elevation angle in [deg] or [rad] (consistent with "units" arg), only pass this or zenith_angle
        elev type: number or 1D array
        zenith_angle: zenith angle in [deg] or [rad] (consistent with "units" arg), only pass this or elev
        zenith_angle type: number or 1D array
        dist: the radius of the sphere, defaults to 1
        dist type: number or 1D array

    Returns:
        x: x coordinates
        y: y coordinates
        z: z coordinates
    """

    if units not in ['deg', 'degree', 'degrees', 'rad', 'radian', 'radians']:
        raise ValueError('Incorrect units provided')

    if zenith_angle is not None and elev is not None:
        raise ValueError('You should only pass zenith_angle or elev arg, not both')

    if units in ['deg', 'degree', 'degrees']:
        azimut = np.deg2rad(azimut)

        if elev is not None:
            elev = np.deg2rad(elev)

        if zenith_angle is not None:
            zenith_angle = np.deg2rad(zenith_angle)

    if zenith_angle is None:
        zenith_angle = (np.pi/2) - elev

    x = dist * np.sin(zenith_angle) * np.cos(azimut)
    y = dist * np.sin(zenith_angle) * np.sin(azimut)
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
