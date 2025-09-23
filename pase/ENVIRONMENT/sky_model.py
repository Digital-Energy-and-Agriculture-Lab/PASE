"""
Sky subdivision after:
Bourgeois, Denis & Reinhart, C. & Ward, G. (2008). Standard daylight coefficient model for dynamic daylighting simulations. Building Research and Information - BUILDING RES INFORM. 36. 10.1080/09613210701446325.
Paper openly available on Researchgate: https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://www.researchgate.net/publication/228683789_Standard_daylight_coefficient_model_for_dynamic_daylighting_simulations&ved=2ahUKEwjp96OWi_iLAxWj8LsIHea6LUMQFnoECAoQAQ&usg=AOvVaw060IkWjmPP1qEXHvIA08C6

"""

import logging
import math
import numpy as np
import os
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib

if os.environ.get("CI") == "true":
    matplotlib.use('Agg')
else:
    matplotlib.use('TkAgg')


from pase.conversion_functions import sph_to_cart

logger = logging.getLogger(__name__)

class ReinhartSky:

    def __init__(self, MF=1):
        self.MF = MF

        self.reinhart_sky, self.reinhart_num_total = self.get_reinhart(MF=MF)

        self.build_patches()

        # Add the top patch
        self.add_top_patch()

        # Compute solid angles of all patches
        self.check_sum_solid_angles()

        # Compute surface areas of all patches
        self.compute_surface_areas()

        # Compute x, y, z coordinates of unit vectors pointing towards the sky patches
        self.get_patches_xyz()

    def get_original_tregenza(self):
        original_tregenza_segments = pd.DataFrame()

        original_tregenza_segments['tregenza_row'] = np.arange(7)
        original_tregenza_segments['num_segments'] = np.array(
            [30, 30, 24, 24, 18, 12, 6])

        differential_altitude = 12  # [deg]
        original_tregenza_segments['altitude_deg'] = (np.arange(
            7) + 0.5) * differential_altitude

        original_tregenza_segments['diff_azimuth'] = np.array(
            [12, 12, 15, 15, 20, 30, 60])

        return original_tregenza_segments

    def get_corresp_tregenza145_row(self, F, MF):
        self.alpha = 90 / ((2 ** F * 7) + 1 / 2)  # [deg] Differential altitude

        self.num_rows = 2**F * 7

        reinhart_rows = np.arange(self.num_rows, dtype=int)
        tregenza_rows = np.floor(reinhart_rows/MF)

        return reinhart_rows, tregenza_rows

    def get_reinhart(self, MF, _verbose=False):
        F = np.log2(MF)

        original_tregenza_segments = self.get_original_tregenza()

        reinhart_sky = pd.DataFrame()
        reinhart_rows, tregenza_rows = self.get_corresp_tregenza145_row(
            F, MF)
        reinhart_sky['row'] = reinhart_rows
        reinhart_sky['altitude_deg'] = (reinhart_rows + 0.5) * self.alpha
        reinhart_sky['tregenza_row'] = tregenza_rows.astype(int)
        reinhart_sky = pd.merge(reinhart_sky, original_tregenza_segments[
            ['tregenza_row', 'num_segments']], on='tregenza_row', how='left')
        reinhart_sky = reinhart_sky.rename(
            columns={'num_segments': 'num_tregenza_segments'})

        reinhart_sky['num_segments'] = reinhart_sky[
                                           'num_tregenza_segments'] * round(
            2 ** F)

        reinhart_num_total = round(4 ** F * 144) + 1
        Ivanova_num_total = 144 * MF ** 2 + 1
        num_segments_checksum = reinhart_sky['num_segments'].sum() + 1

        # assert reinhart_num_total == num_segments_checksum
        diff1 = reinhart_num_total - Ivanova_num_total
        diff = num_segments_checksum - reinhart_num_total

        if _verbose or diff or diff1:
            print('\n', 5 * '#', f'{MF=} ; {F=}', 5 * '#')
            if not (diff) and not (diff1):
                print('Passed')

        if diff1:
            print('Mismatch in theoretical number of patches !!')
            print(f'Calc Reinhart = {reinhart_num_total}')
            print(f'Calc Ivanova et Gueymard = {Ivanova_num_total}')

        if diff != 0:
            print('Mismatch in implementation !!!')
        if diff > 0:
            print(f'{diff} extra patch(es)')
        elif diff < 0:
            print(f'{diff} missing patch(es)')

        return reinhart_sky, reinhart_num_total

    def build_patches(self):
        self.reinhart_patches = pd.DataFrame()
        self.patch_id = 0
        self.cols = ['row', 'patch_id', 'patch_id_in_row', 'd_el', 'd_az', 'el',
                     'az', 'solid_angle_sr']
        for row in self.reinhart_sky['row']:
            # print(f'{row=}')
            d_az = 360 / \
                   self.reinhart_sky[self.reinhart_sky['row'] == row][
                       'num_segments'].values[
                       0]
            el = self.alpha * (row + 1 / 2)  # [deg]

            for segment in range(self.reinhart_sky['num_segments'].iloc[row]):
                # print(f'{segment=}')
                az = d_az * (segment + 1 / 2)  # [deg]
                solid_angle = self.compute_solid_angle_from_elev_azim(el,
                                                                      d_az)

                df = pd.DataFrame(
                    [[row, self.patch_id, segment, self.alpha, d_az, el, az,
                      solid_angle]],
                    columns=self.cols)

                self.reinhart_patches = pd.concat([self.reinhart_patches, df],
                                             ignore_index=True)

                self.patch_id += 1

    def add_top_patch(self):
        top_row = max(self.reinhart_sky['row']) + 1
        top_patch_solid_angle = self.compute_solid_angle_cone(self.alpha / 2)
        top_patch = pd.DataFrame(
            [[top_row, self.patch_id, 0, self.alpha / 2, 360, 90, 0, top_patch_solid_angle]],
            columns=self.cols)
        self.reinhart_patches = pd.concat([self.reinhart_patches, top_patch],
                                     ignore_index=True)


    def compute_solid_angle_from_elev_azim(self, el, d_az):
        """

        Args:
            el: elevation at the center of the patch [deg]
            d_el: differential elevation of the patch [deg]
            d_az: differential azimuth of the patch [deg]

        Returns:
            solid_angle: solid angle of the patch [sr]
        """
        # inputs in deg, shape 2x1

        # convert to rad
        el = np.deg2rad(el)
        d_el = np.deg2rad(self.alpha)
        d_az = np.deg2rad(d_az)

        # compute the solid angle [sr]
        solid_angle = np.cos(el) * d_el * d_az

        # print(dw)

        return solid_angle

    def compute_solid_angle_cone(self, half_apex_angle):
        """

        Args:
            half_apex_angle: in degrees

        Returns:
            solid angle of a cone
        """
        half_apex_angle = np.deg2rad(half_apex_angle)
        solid_angle = 2 * np.pi * (1 - np.cos(half_apex_angle))

        return solid_angle

    def compute_surface_areas(self):
        # Compute surf area of each patch
        self.reinhart_patches['surf area'] = self.reinhart_patches['solid_angle_sr'] / (
                2 * np.pi)
        sum_surf_areas = self.reinhart_patches['surf area'].sum()

        logger.debug(f'Sum of surface areas = {sum_surf_areas:.4g}')

    def check_sum_solid_angles(self):
        # Check that the sum of solid angles is correct
        sum_solid_angles = self.reinhart_patches['solid_angle_sr'].sum()
        sum_solid_angles_div_pi = sum_solid_angles / np.pi
        logger.debug(f'Sum of solid angles = {sum_solid_angles_div_pi:.4g} * pi')
        if not math.isclose(sum_solid_angles, 2*np.pi):
            logger.warning('Sum of solid angles seems off, check the sky discretization scheme')
            logger.warning(f'Sum of solid angles = {sum_solid_angles_div_pi:.4g} * pi')

    def get_patches_xyz(self):
        # Compute xyz coords on a unit sphere (actually half sphere since it's the sky dome)
        self.reinhart_patches['x'], \
        self.reinhart_patches['y'], \
        self.reinhart_patches['z'] = sph_to_cart(units='deg',
                                                 azimut=self.reinhart_patches['az'],
                                                 elev=self.reinhart_patches['el'])

    def test_MFs(self):
        MFs = np.arange(1, 33)
        for MF in MFs:
            _, _ = self.get_reinhart(MF=MF, _verbose=False)

    def scatter_3D(self, text_id=False):
        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        ax.scatter(self.reinhart_patches['x'],
                   self.reinhart_patches['y'],
                   self.reinhart_patches['z'], marker='.', c='k')

        if text_id:
            for idx in range(len(self.reinhart_patches)):
                patch = self.reinhart_patches.iloc[idx]
                ax.text(patch['x'], patch['y'], patch['z'],
                        s=f"{patch['patch_id']:.0f}")

        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')

        title = f'{self.reinhart_num_total} patches (MF:{self.MF})'
        ax.set_title(title)
        ax.set_box_aspect([1.0, 1.0, 1/2])
        plt.show()

    def scatter_2D(self, text_id=False):
        fig = plt.figure()
        ax = fig.add_subplot()

        ax.scatter(self.reinhart_patches['x'], self.reinhart_patches['y'],
                   c=self.reinhart_patches['patch_id'])

        if text_id:
            for idx in range(len(self.reinhart_patches)):
                patch = self.reinhart_patches.iloc[idx]
                ax.text(patch['x'], patch['y'], f"{patch['patch_id']:.0f}")

        ax.set_xlabel('X')
        ax.set_ylabel('Y')

        ax.set_aspect('equal', adjustable='box')

        plt.show()


if __name__ == '__main__':
    sky = ReinhartSky(MF=1)
    sky.scatter_2D()
    sky.scatter_2D(text_id=True)
    sky.scatter_3D()
    sky.scatter_3D(text_id=True)
