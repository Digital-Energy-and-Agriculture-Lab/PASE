"""
diffusers class
"""
import numpy as np
from scipy.special import i0
import matplotlib.pyplot as plt
from pase.conversion_functions import rotation_coordinate


class Diffuser:
    """
    General class for diffusers, allowing transfer functions not to be specified.
    Must be completed (by inheritance) by a specific diffuser class such as Lenticular_diffuser.

    azimut_diff : Diffuser azimuth
    elevation_diff : Diffuser elevation
    geometry : Diffuser geometry (pyVista)
    """

    def __init__(self, azimuth, elevation, kernel = 'gaussian'):
        self.x_dr = None
        self.z_dr = None
        self.y_dr = None
        self.azimuth_diff = -np.radians(azimuth-90)
        self.elevation_diff = np.radians(elevation)
        self.kernel = kernel

    def generate_direction_diffuser_referential(self, vect_sun, angle_discr):
        """
        Call the transfer function to compute the direction of the transferred light with a giver resolution.
        Input :
            vect_sun : the sun vectors
            res : the angle resolution for the transmitted light direction in degrees
        """
        self.x_dr, self.y_dr, self.z_dr, self.rho, self.ds = self.transfer_function(vect_sun, angle_discr)

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

    def get_light_direction(self, vect_sun, discr, sigma, angle_discr):
        """
        General function to compute the directions and transform them in the right frame.
        Input :
            vect_sun : sun vectors
        """
        self.generate_direction_diffuser_referential(vect_sun, angle_discr)
        self.get_direction_sky_referential()
        W = self.get_discretized_BSDF(discr, sigma, self.kernel)
        return W

    def get_BTDF_plot(self, azimuth, zenith):
        """
        Create the BTDF plot for the given azimuth and zenith data.
        """
        azimuth = np.radians(270-azimuth)
        fig, ax = plt.subplots(subplot_kw=dict(projection='polar'))
        ax.plot(azimuth, zenith)
        ax.set_ylim(0, 90)
        ax.set_xticks(np.radians[0, 45, 90, 135, 180, 225, 270, 315])
        ax.set_xticklabels(['90°','45°','0°','315°', '270°', '225°', '180°', '135°'])

    def get_discretized_BSDF(self, discr, sigma, kernel="gaussian"):
        """
        Compute the weight associate with each element of the discretization (discr).
        Input :
            discr (np.array of size (Nx3): Discretization of the sky, N = number of patches
            sigma (np.array of size (N): area proxy of each patch
            kernel (str): projection kernel.
        Output :
            W_trans (np.array of size (SxN): Weight associate with each patch, S = number of solar position
        """
        sigma2 = np.concatenate([np.sqrt(sigma),np.sqrt(sigma)])[np.newaxis, np.newaxis, :]
        discr2 = np.repeat(np.array([[1, 1, -1]]), discr.shape[0], axis=0) * discr
        sphere = np.concatenate([discr, discr2], axis=0)
        pts = np.stack([self.x_sr, self.y_sr, self.z_sr], axis=2)
        g = self.get_integration_kernel(pts, sphere, sigma2, kernel=kernel) #np.exp(-np.arccos(A) ** 2 / (2 * sigma2** 2))
        norm = g.sum(axis=2)[:, :, np.newaxis]
        g_norm = g/norm
        self.W = np.einsum('ij,ij,ijl->il',self.rho, self.ds, g_norm)    #sum_j self.rho_ij*self.ds_ij *g(A, sigma2)_ijl) --> il #i solar dimension and l sky dimension
        W_trans = self.W[:,:discr.shape[0]]
        return W_trans

    def get_transmission_reflexion_weight(self):
        N = self.W.shape[1]
        return self.W[:N//2], self.W[N//2:]

    def transfer_function(self, vect_sun, method, angle_discr):
        return NotImplementedError

    def get_integration_kernel(self, pts, sphere, sigma, kernel='gaussian'):
        """
        Compute the integration kernel for each patch
        """
        dist = np.einsum('ijk, lk->ijl', pts, sphere)
        if kernel == 'gaussian':
            g = np.exp(-np.arccos(dist) ** 2 / (2 * sigma** 2))
        elif kernel == 'von_mises':
            g = np.exp(dist*10/sigma)/i0(10/sigma)
        else:
            raise("Kernel not implemented. Valid values are 'gaussian' or 'von_mises'")
        return g


class LenticularDiffuser(Diffuser):
    """
    Specific class that inherits from the Diffuser class. Adds the transfer function specific to lenticular diffusers

    Omega = Lens aperture angle in degrees
    """

    def __init__(self, azimuth_diff, elevation_diff, omega=30, res=0.1, **kwargs):
        super().__init__(azimuth_diff, elevation_diff)
        self.omega = np.deg2rad(omega)  # aperture angle
        l = np.array([[[0,1,0],[0,0,1]]]).T
        l = rotation_coordinate(l,np.array([0,0,1]), self.azimuth_diff)
        l = rotation_coordinate(l, np.array([0, 1, 0]), self.elevation_diff)
        self.len_vector = l[:, 0,0]
        self.normal =l[:,1,0]
        self.res=res

    def transfer_function(self, vect_sun, angle_discr):
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
        res = self.res*angle_discr if self.res is not None else 0.1
        gamma = self.get_gamma_angle(vect_sun, res)
        beta= self.get_beta_angle(vect_sun, res)
        x = -np.sin(gamma) * (np.sin(beta-res/2) - np.sin(beta+res/2))/res
        y = np.cos(gamma)
        z = -np.sin(gamma) * (np.cos(beta+res/2) - np.cos(beta-res/2))/res
        ds = np.sin(gamma) * res
        L = ds.sum(axis=1)[:, np.newaxis]
        L = np.tile(L, (1, int((2 * self.omega + res) // res )))
        rho = 1/L
        return x, y, z, rho, ds

    def get_beta_angle(self, vect_sun, angle_res):
        """
        Compute the beta angle (i.e. angle between the diffuser plan and
        the plan created by the sun vector and the lens vector.)

        Input :
            vect_sun : sun vectors
            Anle_res : output angular resolution
        """
        plan_sunl = np.cross(vect_sun, self.len_vector)
        norm_psl = np.linalg.norm(plan_sunl, axis=1)
        ind = np.where(np.linalg.norm(plan_sunl, axis=1) == 0)
        norm_psl[ind] = 1
        cos_beta = np.clip(np.dot(plan_sunl, self.normal) / (norm_psl * np.linalg.norm(self.normal)), -1, 1)
        beta = np.arccos(cos_beta)
        beta_t = np.arange(-self.omega+angle_res/2, self.omega + angle_res/2, angle_res)
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
        cos_gamma = np.clip(np.dot(vect_sun, self.len_vector), -1, 1)
        gamma = np.arccos(cos_gamma)
        gamma = gamma[:, np.newaxis]
        gamma = np.tile(gamma, (1, int((2 * self.omega + Angle_res) // Angle_res)))
        return gamma
