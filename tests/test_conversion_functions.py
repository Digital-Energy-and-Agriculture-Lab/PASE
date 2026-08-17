import numpy as np

from pase.conversion_functions import (COMPASS,
                                       TRIGONOMETRIC,
                                       cart_to_sph,
                                       sph_to_cart,
                                       rotation_coordinate)

# The azimuths below are trigonometric (0 deg = East, positive counterclockwise):
# they come from arctan2(y, x). The tests in this module check that sph_to_cart and
# cart_to_sph are mutual inverses, which is a frame-blind property — it holds
# equally in either convention. The absolute witnesses that do pin the frame live
# in tests/test_angle_conventions.py; see DOCUMENTATION/angle_conventions.md.
x = np.array([1,1,1,1, 1, 1,0,0,0, 0, 0,-1,-1,-1,-1,-1,-1]) # some vectors to create some cartesian coordinates (1)
y = np.array([0,0,1,1,-1,-1,0,1,1,-1,-1, 0, 0, 1, 1,-1,-1])
z = np.array([1,0,1,0, 1, 0,1,1,0, 1, 0, 1, 0, 1, 0, 1, 0])
N = np.sqrt(x**2 + y**2 + z**2) # norm of each point

true_zen = np.array([np.pi/4,np.pi/2,np.arctan(np.sqrt(2)),np.pi/2,
                     np.arctan(np.sqrt(2)),np.pi/2,0,np.pi/4, np.pi/2,
                     np.pi/4,np.pi/2,np.pi/4, np.pi/2, np.arctan(np.sqrt(2)),
                     np.pi/2, np.arctan(np.sqrt(2)),np.pi/2 ]) #equivalent spherical coordinates (2)
true_az = np.radians([0,0,45,45,-45,-45,0,90,90,-90,-90,180,180,135,135,-135,-135])
def test_cart_to_sph():
    for i,(xi,yi,zi) in enumerate(zip(x,y,z)):
        az, zenith = cart_to_sph(xi,yi,zi, frame=TRIGONOMETRIC) # transform cartesian coordinates (1) to spherical coordinates (2*)
        assert az == true_az[i] #compare (2*) to (2) for each point individually
        assert zenith == true_zen[i]

cart_coord = np.array([x,y,z]).T

def test_cart_to_sph_vector():
    az, zenith = cart_to_sph(x,y,z, frame=TRIGONOMETRIC) # equivalent to the previous test but with vector entries
    assert np.allclose(az, true_az)
    assert np.allclose(zenith, true_zen)

def test_sph_to_cart():
    x_new, y_new, z_new = sph_to_cart('rad', true_az, zenith_angle= true_zen, dist=N,
                                      frame=TRIGONOMETRIC)                       # transform spherical
    assert np.allclose(x_new, x)                                                           #coordinates (2) to cartesian
    assert np.allclose(y_new, y)                                                           #coordinates (1*) and compare
    assert np.allclose(z_new, z)                                                           #(1*) to (1)
    x_new, y_new, z_new = sph_to_cart('deg', np.degrees(true_az), zenith_angle=np.degrees(true_zen), dist=N,
                                      frame=TRIGONOMETRIC)
    assert np.allclose(x_new, x) # same but with degrees unit
    assert np.allclose(y_new, y)
    assert np.allclose(z_new, z)
    elev = np.pi/2 - true_zen
    x_new, y_new, z_new = sph_to_cart('rad', true_az, elev=elev, dist=N,
                                      frame=TRIGONOMETRIC)
    assert np.allclose(x_new, x) # same but with elevation instead of zenithal angles
    assert np.allclose(y_new, y)
    assert np.allclose(z_new, z)


def test_sph_to_cart_trigonometric_frame_is_absolute():
    """
    Anchor the frame this module works in, which the round-trip tests above cannot
    do: in the trigonometric convention azimuth 0 is due East (+X) and azimuth 90
    is due North (+Y). The compass counterpart of this assertion, and the rest of
    the frame witnesses, live in tests/test_angle_conventions.py.
    """
    east = sph_to_cart('deg', 0.0, elev=0.0, frame=TRIGONOMETRIC)
    north = sph_to_cart('deg', 90.0, elev=0.0, frame=TRIGONOMETRIC)
    assert np.allclose(np.asarray(east, dtype=float).ravel(), [1.0, 0.0, 0.0])
    assert np.allclose(np.asarray(north, dtype=float).ravel(), [0.0, 1.0, 0.0])
    # the same number read as a compass azimuth points somewhere else entirely
    assert np.allclose(
        np.asarray(sph_to_cart('deg', 0.0, elev=0.0, frame=COMPASS), dtype=float).ravel(),
        [0.0, 1.0, 0.0])

def test_rotation_coordinate(): # test the rotation using quaternion paradigm
    u1, u2, u3, v =  np.array([31, 0, 0]),  np.array([0, 31, 0]), np.array([-9,24,-6]), np.array([1, 0, 0]) # some test vectors
    u1 = u1.reshape((3,1,1))                                                            # v is the unit rotation vector.
    u2 = u2.reshape((3, 1, 1))
    u32 = u3.reshape((3, 1, 1))
    angles = np.deg2rad([0, 13, 49, 87, 103, 176, 182, 209, 222, 273, 360]) #rotation angles
    for a in angles:
        up1 = rotation_coordinate(u1, v, a) # after rotation u1 should remain the same
        up2 = rotation_coordinate(u2, v, a)
        dot_2 = np.sum(up2*u2) # Euclidian inner product
        angle2 = np.arccos(dot_2/(np.linalg.norm(up2)*np.linalg.norm(u2))) # angle given by the geometry behind the inner product
        angle2 =2*np.pi - angle2  if up2[2] < 0 else angle2
        up3 = rotation_coordinate(u32, v, a)
        up3p = (u3 - v*(np.dot(u3,v)))*np.cos(a) + np.cross(v, u3)*np.sin(a) + v*(np.dot(u3,v)) # Application of the
        assert np.isclose(u1, up1, rtol=1e-5).all()                      # Olinde Rodrigues equation to rotate a vector.
        assert np.isclose(angle2, a, rtol=1e-5).all()
        assert np.isclose(up3p, up3.reshape((3,)), rtol=1e-5).all()

