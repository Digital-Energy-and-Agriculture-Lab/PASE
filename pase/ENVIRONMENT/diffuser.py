"""
diffusers class
"""
import numpy as np
from scipy.spatial.transform import Rotation as R
import matplotlib.pyplot as plt


def cartesian_to_spherical(x, y, z):
    """
    Converts Cartesian coordinates to spherical coordinates.

    x, y, z : float : Cartesian coordinates

    Returns:
    azimuth : float : azimuth angle in degrees
    zenith : float : zenith angle in degrees
    """
    h = np.sqrt(x ** 2 + y ** 2)
    azimuth = np.degrees(np.arctan2(y, x))
    zenith = np.degrees(np.arctan2(h, z))
    return azimuth, zenith


def spherical_to_cartesian(azimuth, zenith):
    """
    Converts spherical coordinates to Cartesian coordinates.

    azimuth : float : azimuth angle in degrees
    zenith : float : zenith angle in degrees

    Returns:
    x, y, z : float : Cartesian coordinates
    """
    azimuth = np.radians(azimuth)
    zenith = np.radians(zenith)
    x = np.sin(zenith) * np.cos(azimuth)
    y = np.sin(zenith) * np.sin(azimuth)
    z = np.cos(zenith)
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


class Diffuser:
    """
    General class for diffusers, allowing transfer functions not to be specified.
    Must be completed (by inheritance) by a specific diffuser class such as Lenticular_diffuser.

    azimut_diff : Diffuser azimuth
    elevation_diff : Diffuser elevation
    geometry : Diffuser geometry (pyVista)
    """

    def __init__(self, azimuth_diff, elevation_diff):
        self.x_dr = None
        self.z_dr = None
        self.y_dr = None
        self.azimuth_diff = -np.radians(azimuth_diff-90)
        self.elevation_diff = np.radians(elevation_diff)

    def generate_direction_diffuser_referential(self, vect_sun):
        """
        Call the transfer function to compute the direction of the transferred light with a giver resolution.
        Input :
            vect_sun : the sun vectors
            res : the angle resolution for the transmitted light direction in degrees
        """
        self.x_dr, self.y_dr, self.z_dr = self.transfer_function(vect_sun)

    def get_direction_sky_referential(self):
        """
        Call the function to switch to the sky reference frame
        """
        y_vector = np.array([0, 1, 0])
        z_vector = np.array([0, 0, 1])
        vect_0 = np.array([self.x_dr, self.y_dr, self.z_dr])
        vect_1 = rotation_coordinate(vect_0, z_vector, self.azimuth_diff)
        vect_2 = rotation_coordinate(vect_1, y_vector, self.elevation_diff)
        self.x_sr, self.y_sr, self.z_sr = vect_2

    def get_light_direction(self, vect_sun, discr):
        """
        General function to compute the directions and transform them in the right frame.
        Input :
            vect_sun : sun vectors
        """
        self.generate_direction_diffuser_referential(vect_sun)
        self.get_direction_sky_referential()
        W = self.get_discretized_BSDF(discr)
        return W
    def get_BTDF_plot(self, azimuth, zenith):
        """
        Create the BTDF plot for the given azimuth and zenith data.
        """
        zenith_d = np.degrees(zenith)
        fig, ax = plt.subplots(subplot_kw=dict(projection='polar'))
        ax.scatter(azimuth, zenith)
        ax.set_ylim(0, 90)

    def get_discretized_BSDF(self, discr):
        pts = np.stack([self.x_sr, self.y_sr, self.z_sr], axis=2)
        A = np.einsum('ijk, lk->ijl', pts, discr)
        M = np.argmax(A, axis=2)
        ulist = [np.unique(M[i], return_counts=True) for i in range(M.shape[0])]
        W = np.zeros((pts.shape[0], discr.shape[0]))
        for i in range(M.shape[0]):
            W[i, ulist[i][0]] = ulist[i][1] / A.shape[1]
        return W

    def transfer_function(self, vect_sun, res):
        return NotImplementedError


class LenticularDiffuser(Diffuser):
    """
    Specific class that inherits from the Diffuser class. Adds the transfer function specific to lenticular diffusers

    Omega = Lens aperture angle in degrees
    """

    def __init__(self, omega=30, **kwargs):
        super().__init__(**kwargs)
        self.omega = np.deg2rad(omega)  # aperture angle
        self.len_vector = np.array([np.cos(self.elevation_diff) * np.cos(self.azimuth_diff),
                                    np.cos(self.elevation_diff) * np.sin(self.azimuth_diff),
                                    np.sin(self.elevation_diff)])

    def transfer_function(self, vect_sun, res=0.1):
        """
        Specific transfer function for lenticular diffusers.

        Gamma : Angle between the lens direction and the sun direction
        beta : Angle between the diffuser plan and the plan created by the
        sun vector and the lens vector.

        Input :
            vect_sun : sun vectors
            res : output angular resolution

        Return :
            x, y, z : the direction of the transmitted light in the diffuser frame
        """
        gamma = self.get_gamma_angle(vect_sun, res)
        beta= self.get_beta_angle(vect_sun, res)
        x = np.cos(gamma)
        y = np.cos(beta) * np.sin(gamma)
        z = np.sin(beta) * np.sin(gamma)
        return x, y, z

    def get_beta_angle(self, vect_sun, angle_res):
        """
        Compute the beta angle (i.e. angle between the diffuser plan and
        the plan created by the sun vector and the lens vector.)

        Input :
            vect_sun : sun vectors
            Anle_res : output angular resolution
        """
        normal = np.array([np.cos(self.elevation_diff)*np.sin(self.azimuth_diff),
                           np.cos(self.elevation_diff)*np.cos(self.azimuth_diff),
                           np.sin(self.elevation_diff)])  # diffusers normal
        plan_sunl = np.cross(vect_sun, self.len_vector)
        beta = np.arccos(np.dot(plan_sunl, normal) / (np.linalg.norm(plan_sunl, axis=1) * np.linalg.norm(normal)))
        beta_t = np.arange(-self.omega, self.omega + angle_res, angle_res)
        beta = beta[:, np.newaxis] + beta_t
        return beta

    def get_gamma_angle(self, vect_sun, Angle_res):
        """
        Compute the gamma angle (i.e. the Angle between the lens direction
        and the sun direction)

        Input :
            vect_sun : sun vectors
            Anle_res : output angular resolution
        """
        gamma = np.arccos(np.abs(np.dot(vect_sun, self.len_vector)) / (
                    np.linalg.norm(vect_sun, axis=1) * np.linalg.norm(self.len_vector)))
        ind = np.where((vect_sun[:, 0] < 0))
        gamma[ind] = -gamma[ind] + np.pi
        gamma = gamma[:, np.newaxis]
        gamma = np.tile(gamma, (1, int((2 * self.omega + Angle_res) // Angle_res + 1)))  # shape (T, NPoints)
        return gamma
