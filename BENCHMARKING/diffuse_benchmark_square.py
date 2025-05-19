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
import numpy as np
import pandas as pd
import pyvista as pyV

from MODULES.user_support_tools import PASE_Logger
from MODULES.DATA_MANAGEMENT.benchmarking import export_benchmark
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider, Inputs_aggregator
from MODULES.DATA_MANAGEMENT.weather_data_provider import Weather_data
from MODULES.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization
from MODULES.PHOTOVOLTAICS.configuration import PV_Configuration_3D
from MODULES.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from MODULES.ENVIRONMENT.light import Ray_casting_scene
from MODULES.ENVIRONMENT.mesh import Mesh
from MODULES.PHOTOVOLTAICS.production import PV_Production
from MODULES.CROPS.run_crop_simulations import run_crop_simu, visualize_map_of_a_variable

PASE_Logger()

DEBUG = False
PLOT = False
SAVE = True

# Instantiation of the 3D PV central
PV_params_dict = {'PanelDimensionX': 1,
                  'PanelDimensionY': 1,
                  'PanelThickness': False,
                  'RepetitionDistanceOfPanelsX': 1,
                  'RepetitionDistanceOfPanelsY': 1,
                  'NumberOfPanelsX': 1,
                  'NumberOfPanelsY': 1,
                  'RepetitionDistanceOfPVBlocksX': 1,
                  'RepetitionDistanceOfPVBlocksY': 1,
                  'NumberOfPVBlocksX': 1,
                  'NumberOfPVBlocksY': 1,
                  'Height': 1,
                  'CentralAzimut': 0,
                  'TiltY': 0,
                  'TwoFacetsRelativePosition': 0,
                  'RotationAxisNumber': 0}

# Configure the scene
PV_1_3Dconfig = PV_Configuration_3D(PV_params_dict,
                                    None,
                                    visualization=False)

# Initiation of the mesh object containing points of interest to compute light
M = Mesh()

# Add sensors to the scene
step = 0.5
start = -0.5
stop = 0.5

x_sensors = np.arange(start, stop+step, step=step)
y_sensors = np.arange(start, stop+step, step=step)

for y, x in product(y_sensors, x_sensors):
    M.add_sensor(x, y,0)

# Iniation and run of light ray casting model (direct and diffuse) with points of interest and scene
L = Ray_casting_scene(mesh=M, geometry=PV_1_3Dconfig.PV_central_PD)

MFs = [1, 2, 4, 8]
results_indices = ['point ID', 0, 1, 2, 3, 4, 5, 6, 7, 8, 'COV corners', 'COV midpoints', 'Test result']
results = []
results_cols = ['point ID']

for MF in MFs:
    results_cols.append(f'MF: {MF}')

    diffuse_map = L.diffuse_map(L.geometry,
                                scheme='Reinhart',
                                MF=MF,
                                n_small_suns=0)

    L.diff_map = diffuse_map

    if PLOT:
        L.visualize_diffuse_light_map()

    print(f'{MF=}')
    print(L.diff_map[0:3])
    print(L.diff_map[3:6])
    print(L.diff_map[6:9])

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
        # results.append({f'{MF=}': 'pass', 'cov corners': cov_corners, 'cov midpoints': cov_midpoints})
    elif (math.isclose(cov_midpoints, 0, abs_tol=0.01)) or (math.isclose(cov_midpoints, 0, abs_tol=0.01)):
        result = 'borderline'
        print('Test borderline.')
        # results.append({f'{MF=}': 'Borderline', 'cov corners': cov_corners, 'cov midpoints': cov_midpoints})
    else:
        result = 'FAILED'
        print('Test failed.')
        # results.append({f'{MF=}': 'FAIL', 'cov corners': cov_corners, 'cov midpoints': cov_midpoints})
    results.append([L.diff_map[0], L.diff_map[1], L.diff_map[2], L.diff_map[3], L.diff_map[4], L.diff_map[5], L.diff_map[6], L.diff_map[7], L.diff_map[8], cov_corners, cov_midpoints, result])
    print('')

print('Computation is over')
df = pd.DataFrame(results).T
df.columns = results_cols[1:]
df.set_index(pd.Series(results_indices[1:]), inplace=True)

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

if SAVE:
    export_benchmark(df, fname_prefix='diffuse_benchmark_square_')

