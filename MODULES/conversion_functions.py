import numpy as np

def cart_to_sph(x, y, z):
    """

            Args:
                cart_coords:

            Returns:
                zenith_angle: zenith angle [rad]
            """
    r = np.sqrt(x**2 + y**2 + z**2)

    if z > 0:
        zenith = np.arctan((x**2+y**2)/z)
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
        az = np.nan

    return az, zenith

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
