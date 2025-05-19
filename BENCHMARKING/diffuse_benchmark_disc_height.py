#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.
""""
Benchmark the diffuse irradiance map
"""
from itertools import product
import math
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('TkAgg')
import numpy as np
import pandas as pd
import pyvista as pyV

from MODULES.user_support_tools import PASE_Logger
from MODULES.DATA_MANAGEMENT.benchmarking import export_benchmark
from MODULES.ENVIRONMENT.light import Ray_casting_scene
from MODULES.ENVIRONMENT.mesh import Mesh

PASE_Logger()

DEBUG = False
PLOT = False
SAVE = True

def compute_analytical_f(disc_radius, heights):
    theta_0 = np.arctan(disc_radius / heights)
    analytical_f = 1 - (np.sin(theta_0)) ** 2

    return analytical_f

def compute_RMSE(actual, predicted):
    diff = np.subtract(actual, predicted)
    square = np.square(diff)
    mse = square.mean()
    rmse = np.sqrt(mse)

    return rmse

# Various heights
if DEBUG:
    # shorter heights vector for faster debug
    heights = np.linspace(0.1, 1, 4)
else:
    step1 = 0.1
    heights = np.arange(0.1, 1, step=step1)

    step2 = 0.25
    heights = np.concatenate([heights, np.arange(1, 2, step=step2)])

    step3 = 1
    heights = np.concatenate([heights, np.arange(2, 6, step=step3)])

# Disc constants
disc_direction = (0, 0, 1)
disc_thickness = 0.001
disc_radius = np.sqrt(1/np.pi)

# Analytical view factors
theta_0 = np.arctan(disc_radius/heights)
analytical_f_vec = 1 - (np.sin(theta_0))**2

# Build results DataFrame
df = pd.DataFrame([heights, analytical_f_vec]).T
df.columns = ['Height [m]', 'Analytical view factor']

# Configure sensors' positions in the scene
step = disc_radius
start = -disc_radius
stop = disc_radius

x_sensors = np.arange(start, stop+step, step=step)
y_sensors = np.arange(start, stop+step, step=step)

# Various MF values
if DEBUG:
    # fewer MF values for faster debug
    MFs = [1, 2]
else:
    MFs = [1, 2, 6]

rmse_list = []
for MF in MFs:
    computed_view_factor = []
    rel_error_center_value_list = []

    for disc_height in heights:
        # Configure the scene
        disc_center = (0, 0, disc_height)

        # Compute analytical view factor
        theta_0 = np.arctan(disc_radius / disc_height)
        analytical_f = 1 - (np.sin(theta_0)) ** 2

        disc = pyV.Cylinder(center=disc_center, radius=disc_radius,
                            height=disc_thickness,
                            direction=disc_direction).triangulate()

        # Initiation of the mesh object containing points of interest to compute light
        M = Mesh()

        for y, x in product(y_sensors, x_sensors):
            M.add_sensor(x, y,0)

        # Iniation and run of light ray casting model (direct and diffuse) with points of interest and scene
        L = Ray_casting_scene(mesh=M, geometry=disc)

        diffuse_map = L.diffuse_map(L.geometry,
                                    scheme='Reinhart',
                                    MF=MF,
                                    n_small_suns=0)

        L.diff_map = diffuse_map

        if PLOT:
            L.visualize_diffuse_light_map()

        print(f'{MF=}, height = {disc_height} m')
        print(L.diff_map[0:3])
        print(L.diff_map[3:6])
        print(L.diff_map[6:9])

        # Check value at center
        center_id = 4
        center_computed_value = L.diff_map[center_id]
        print(f'Center point computed value = {center_computed_value}')
        print(f'Center point expected value = {analytical_f}')
        rel_error_center_value = (1 - center_computed_value/analytical_f) * 100  # [%]
        print(f'Relative error on center value = {rel_error_center_value:.3g} %')
        # results.append([center_computed_value, rel_error_center_value])
        computed_view_factor.append(center_computed_value)
        rel_error_center_value_list.append(rel_error_center_value)

        # Analyze corners
        corners_ids = [0, 2, 6, 8]
        print(10 * '-')
        print("Corners' values:")
        print(L.diff_map[corners_ids])
        print('coef of var =', L.diff_map[corners_ids].std()/L.diff_map[corners_ids].mean())
        cov_corners = L.diff_map[corners_ids].std()/L.diff_map[corners_ids].mean()

        # Analyze midpoints
        midpoints_ids = [1, 3, 5, 7]
        print(10 * '-')
        print("Midpoints' values:")
        print(L.diff_map[midpoints_ids])
        print('coef of var =', L.diff_map[midpoints_ids].std()/L.diff_map[midpoints_ids].mean())
        cov_midpoints = L.diff_map[midpoints_ids].std()/L.diff_map[midpoints_ids].mean()

        print(20*'=')
        if (cov_midpoints == 0) and (cov_corners == 0):
            result = 'passed'
            print('Test passed !')
        elif (math.isclose(cov_midpoints, 0, abs_tol=0.01)) or (math.isclose(cov_midpoints, 0, abs_tol=0.01)):
            result = 'borderline'
            print('Test borderline.')
        else:
            result = 'FAILED'
            print('Test failed.')

        print('')

        print('Loop end')

    df[f'MF:{MF} computed value'] = computed_view_factor
    df[f'MF:{MF} rel error'] = rel_error_center_value_list

    rmse_list.append(compute_RMSE(computed_view_factor, analytical_f_vec))

print('Computations over')

df_rmse = pd.DataFrame([MFs, rmse_list]).T
df_rmse.columns = ['MF', 'RMSE']
df_rmse.set_index('MF', inplace=True)

print(df_rmse)

# debug 3D view
if DEBUG:
    labels = dict(zlabel='Z (ZENITH)', xlabel='X (EAST)', ylabel='Y (NORTH)')

    plotter = pyV.Plotter()

    plotter.add_mesh(L.geometry, color='black', opacity=0.5)

    ground = np.array([[-200, 200, 0],
                       [200, 200, 0],
                       [-200, -200, 0],
                       [200, -200, 0]])

    ground_m = np.hstack([[3, 0, 1, 2],
                          [3, 1, 2, 3], ])

    grnd = pyV.PolyData(ground, ground_m)

    plotter.add_mesh(grnd, color='green', opacity=0.5)

    plotter.add_axes(**labels)

    spatialized_variable = np.array(L.diff_map, dtype=np.float32)
    lgd_title = 'Diffuse map'
    plotter.add_mesh(L.sourcepoints[:,:-1],
                     scalars=spatialized_variable,
                     point_size=10,
                     lighting=False,
                     show_edges=False,
                     scalar_bar_args={"title": lgd_title},
                     clim=[spatialized_variable.min(),
                           spatialized_variable.max()])

    # Add vertical lines
    for y, x in product(y_sensors, x_sensors):
        points = np.array([[x, y, 0], [x, y, 1]])

        actor = plotter.add_lines(points, color='purple', width=3)

    plotter.show()

# Plot results graph
plt.figure()
# TODO : homogenize colormap with the graph below
plt.plot(heights, analytical_f_vec, 'k-', label='analytical value')
for MF in MFs:
    plt.plot(heights, df[f'MF:{MF} computed value'], 'x-', label=f'MF:{MF}')

plt.xlabel('Height [m]')
plt.ylabel('View factor [-]')

plt.legend()

plt.show()

# Plot error graph
plt.figure()

colors = plt.cm.rainbow(np.linspace(0, 1, len(MFs)))

for i, MF in enumerate(MFs):
    markerline, stemlines, baseline = plt.stem(heights,
                                               df[f'MF:{MF} rel error'],
                                               label=f'MF:{MF}',
                                               basefmt='k-')
    # baseline.set_edgecolor('none')
    stemlines.set_edgecolor(colors[i])
    markerline.set_markerfacecolor('none')
    markerline.set_markeredgecolor(colors[i])

plt.xlabel('Height [m]')
plt.ylabel('View factor rel error [%]')

plt.legend()

plt.show()

# Save results
if SAVE:
    fname = export_benchmark(df, fname_prefix='diffuse_benchmark_disc_height_', mode='x')
    export_benchmark(df_rmse, fname=fname, mode='a')
