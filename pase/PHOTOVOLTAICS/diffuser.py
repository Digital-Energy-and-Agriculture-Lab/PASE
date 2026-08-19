#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
Author : Joran Dartevelle <Joran.Dartevelle@uliege.be>
This file is part of the PASE software, and is distributed under the MIT license.
"""

import numpy as np
from pase.conversion_functions import rotation_coordinate


class Diffuser:
    """
    General class for diffusers, allowing transfer functions not to be specified.
    Must be completed (by inheritance) by a specific diffuser class such as Lenticular_diffuser.

    Diffuser reference frame (e_x, e_y, e_z):
        e_z: Normal of the diffuser plane
        e_y: unit vector in the direction of the diffuser lenses in the case of a lenticular diffuser
        e_x: Cross product between e_y and e_z
    """

    def __init__(self, az_compass_deg, tilt_deg):
        """
        Input:
            az_compass_deg: Diffuser azimuth in degrees, using the compass convention (0 =
                North, positive clockwise towards East). Placing the diffuser at this azimuth
                uses the same rotate_z(-az_compass_deg) idiom as PVConfiguration3D (see
                DOCUMENTATION/angle_conventions.md), so this value must stay consistent with
                how the diffuser's own mesh is placed by
                PVConfiguration3D.add_diffusers_to_central.
            tilt_deg: Diffuser tilt in degrees (0 = flat/horizontal, 90 = vertical).

        Attributes:
            x_dr, y_dr, z_dr: Transmitted ray directions in the diffuser reference frame.
            az_rotation_rad: Rotation, in radians, placing the diffuser at az_compass_deg. This
                is a rotation angle, not an azimuth in either frame -- the same pattern as
                zone_azimut in DOCUMENTATION/angle_conventions.md -- obtained by negating the
                compass azimuth to match pyvista's counterclockwise rotate_z convention.
            tilt_rad: Diffuser tilt in radians.
        """
        self.x_dr = None
        self.z_dr = None
        self.y_dr = None
        # Rotating a scene by a compass azimuth is rotate_z(-A), not a frame relabelling;
        # see "Rotating by an azimuth is a different operation" in
        # DOCUMENTATION/angle_conventions.md.
        self.az_rotation_rad = -np.radians(az_compass_deg)
        self.tilt_rad = np.radians(tilt_deg)

    def generate_direction_diffuser_referential(self, vect_sun, angle_discr):
        """
        Call the transfer function to compute the direction of the transferred light
        with a given resolution.
        Input:
            vect_sun: the sun vectors (nSunPos x 3)
            angle_discr: the angle resolution for the transmitted light direction in degrees

        Output:
            x_dr, y_dr, z_dr: Transmitted ray directions in the diffuser reference frame (nSunPos x Nvec x 3).
            rho: energy contained in each vector (nSunPos x Nvec)
            ds: Size of the segment belonging to the vector (nSunPos x Nvec)
        """
        self.x_dr, self.y_dr, self.z_dr, self.rho, self.ds = self.transfer_function(vect_sun, angle_discr)

    def get_direction_sky_referential(self):
        """
        Call the function to switch to the sky reference frame
        Output:
            x_sr, y_sr, z_sr: Transmitted ray directions in the global reference frame (nSunPos x Nvec x 3).
        """
        y_vector = np.array([0, 1, 0])
        z_vector = np.array([0, 0, 1])
        vect_0 = np.array([self.x_dr, self.y_dr, self.z_dr])
        if hasattr(self, 'azimuth_lens'):
            vect_1 = rotation_coordinate(vect_0, z_vector, self.azimuth_lens)
        else:
            vect_1 = vect_0
        vect_2 = rotation_coordinate(vect_1, y_vector, self.tilt_rad)
        vect_3 = rotation_coordinate(vect_2, z_vector, self.az_rotation_rad)
        self.x_sr, self.y_sr, self.z_sr = vect_3

    def get_light_direction(self, vect_sun, discr, sigma, angle_discr):
        """
        General function to compute the directions and transform them in the right frame.
        Input:
            vect_sun: sun vectors (nSolPos x 3)
            discr: Direction of the sky patches (nPatch x 3)
            sigma: Size of the sky patch (nPatch)
            angle_discr: angular resolution of transmitted rays created.
        Output:
            W: Weight of the transmitted rays associate with each patch (nSolPos x nPatch)
        """
        self.generate_direction_diffuser_referential(vect_sun, angle_discr)
        self.get_direction_sky_referential()
        W = self.get_discretized_BSDF(discr, sigma)
        return W

    def get_discretized_BSDF(self, discr, sigma):
        """
        Compute the weight associate with each element of the discretization (discr).
        Input :
            discr (np.array of size (nPatch, 3):Direction of the sky patches, nPatch = number of patches
            sigma (np.array of size (nPatch): area proxy of each patch
            kernel (str): projection kernel.
        Output :
            W_trans (np.array of size (nSolPos, nPatch): Weight associate with each patch,
                                                        nSolPos = number of solar position
        """
        sigma2 = np.concatenate([np.sqrt(sigma),np.sqrt(sigma)])[np.newaxis, np.newaxis, :]
        discr2 = np.repeat(np.array([[1, 1, -1]]), discr.shape[0], axis=0) * discr
        sphere = np.concatenate([discr, discr2], axis=0)
        pts = np.stack([self.x_sr, self.y_sr, self.z_sr], axis=2)
        g = self.get_integration_kernel(pts, sphere, sigma2) #np.exp(-np.arccos(A) ** 2 / (2 * sigma2** 2))
        norm = g.sum(axis=2)[:, :, np.newaxis]
        g_norm = g/norm
        self.W = np.einsum('ij,ij,ijl->il',self.rho, self.ds, g_norm)    #sum_j self.rho_ij*self.ds_ij *g(A, sigma2)_ijl) --> il #i solar dimension and l sky dimension
        W_trans = self.W[:,:discr.shape[0]]
        return W_trans

    def get_transmission_reflection_weight(self):
        """
        Give the weight for the reflection and transmission hemisphere.
        Output:
            W_trans (np.array of size (nSolPos, nPatch): Weight associate with each patch for the transmission
            W_refl  (np.array of size (nSolPos, nPatch): Weight associate with each patch for the reflection
        """
        N = self.W.shape[1]
        W_trans = self.W[:N//2]
        W_refl = self.W[N//2:]
        return W_trans, W_refl

    def transfer_function(self, vect_sun, method, angle_discr):
        return NotImplementedError

    def get_integration_kernel(self, pts, sphere, sigma):
        """
        Compute the integration kernel for each patch
        Input
            pts (nPosSol, Nvec, 3): direction of the transmitted rays in the global reference frame
            sphere (2*nPatch, 3): direction of the sky patches
            sigma (newaxis, newaxis, 2*nPatch): size of each patch

        Output:
            g (nSolPos, Nvec, nPatch): radial gaussian integration kernel
        """
        dist = np.einsum('ijk, lk->ijl', pts, sphere)
        g = np.exp(-np.arccos(dist) ** 2 / (2 * sigma** 2))
        return g


class LenticularDiffuser(Diffuser):
    """
    Specific class that inherits from the Diffuser class. Adds the transfer function specific to lenticular diffusers
    """

    def __init__(self, lens_direction_angle, az_compass_deg, tilt_deg, omega=30, res=0.1, **kwargs):
        """
        Input:
            lens_direction_angle: Direction of the lens on the diffuser in degrees, in the
            diffuser's own local frame (not a compass bearing). 0 \
            is across the PV row (parallel to Y axis), 90 is along the PV row (parallel \
            to X axis). See the Wiki for reference on axes directions.
            az_compass_deg: Diffuser azimuth in degrees, using the compass convention. It's
            usually the central azimuth (same convention as CentralAzimut; see Diffuser.__init__)
            tilt_deg: Diffuser tilt in degrees. It's usually the PV panel tilt (TiltY)
            Omega (float): Lens aperture angle in degrees
            res (float): dimensionless multiplicative factor of the minimum root squared solid angle\
            of the sky discretization. It produces the resolution at which the rays are projected

        Attributes:
            x_dr, y_dr, z_dr: Transmitted ray directions in the diffuser reference frame.
            az_rotation_rad, tilt_rad: see Diffuser.__init__.
            """
        super().__init__(az_compass_deg, tilt_deg)
        # lens_direction_angle is a local diffuser-frame angle, not a compass bearing, so it is
        # not run through compass_to_trig. The minus sign rotates the pattern from the Y axis
        # towards +X as the angle increases from 0 to 90, matching the docstring above.
        self.azimuth_lens = -np.radians(lens_direction_angle)
        self.omega = np.deg2rad(omega)  # aperture angle
        l = np.array([[[0,1,0],[0,0,1]]]).T
        l = rotation_coordinate(l, np.array([0, 0, 1]), self.azimuth_lens)
        l = rotation_coordinate(l, np.array([0, 1, 0]), self.tilt_rad)
        l = rotation_coordinate(l, np.array([0, 0, 1]), self.az_rotation_rad)
        self.lens_vector = l[:, 0,0]  # the vector parallel to the axis of the lens (in the diffuser plane)
        self.normal =l[:,1,0]
        self.res=res

    def transfer_function(self, vect_sun, angle_discr):
        """
        Specific transfer function for lenticular diffusers.

        Gamma : Angle between the lens direction and the sun direction
        beta : Angle between the diffuser plane and the plane created by the
        sun vector and the lens vector.

        Input :
            vect_sun (nSunPos, 3): sun vectors
            angle_res (scalar): output angular resolution in radians

        Return :
            x, y, z: the direction of the transmitted light in the diffuser frame
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
        Compute the beta angle (i.e. angle between the diffuser plane and
        the plane defined by the sun vector and the lens vector.)

        Input:
            vect_sun (nSunPos, 3): sun vectors
            angle_res (scalar): output angular resolution in radians
        Output:
            beta (nSolPos, Nvec): beta angle in radians
        """
        plane_sun_lens = np.cross(vect_sun, self.lens_vector) # Plane (defined by its normal vector) build from the \
                                                             # sun vector and the lens vector
        beta = np.arctan2(
            np.dot(np.cross(plane_sun_lens, self.normal), self.lens_vector),
            np.dot(plane_sun_lens, self.normal)
        )
        beta_t = np.arange(-self.omega+angle_res/2, self.omega + angle_res/2, angle_res)
        beta = beta[:, np.newaxis] + beta_t
        return beta

    def get_gamma_angle(self, vect_sun, angle_res):
        """
        Compute the gamma angle (i.e. the Angle between the lens direction
        and the sun direction)

        Input :
            vect_sun (nSunPos, 3): sun vectors
            angle_res (scalar): output angular resolution in radians
        Output:
            gamma (nSolPos, Nvec): gamma angle in radians, Nvec is the number of segments
            discretizing the diffuser trace
        """
        cos_gamma = np.clip(np.dot(vect_sun, self.lens_vector), -1, 1)
        gamma = np.arccos(cos_gamma)
        gamma = gamma[:, np.newaxis]
        gamma = np.tile(gamma, (1, int((2 * self.omega + angle_res) // angle_res)))
        return gamma
