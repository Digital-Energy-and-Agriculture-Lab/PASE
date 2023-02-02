#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 17 16:06:55 2023

@author: Roxane Bruhwyler
"""


from MODULES.user_support_tools import PASE_Logger
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from MODULES.PHOTOVOLTAICS.configurations import PV_Configuration_3D
from MODULES.ENVIRONMENT.light import Sun_positions
from MODULES.ENVIRONMENT.environment_config import Plane_Ground_regular_meshes
from MODULES.ENVIRONMENT.light import Shade_direct_light, Sky_view_factor

PASE_Logger()

Loc_1 = YAML_Inputs_provider(file='Wallhausen.yaml').i

PV_1 = YAML_Inputs_provider(file='PV_central.yaml').i

PV_1_3Dconfig = PV_Configuration_3D(PV_1)

Sun_positions = Sun_positions(Loc_1['Latitude'], Loc_1['Longitude'], Loc_1['PrecisionLevelOnSunPosition'])

msh_grid = Plane_Ground_regular_meshes(Loc_1['Xmin_InterestZone'], Loc_1['Xmax_InterestZone'],
                                       Loc_1['Ymin_InterestZone'], Loc_1['Ymax_InterestZone'],
                                       Loc_1['dX_InterestZone'], Loc_1['dY_InterestZone'])

Direct_light_map = Shade_direct_light(msh_grid, PV_1_3Dconfig.PV_central, Sun_positions.solar_vector)

Diffuse_light_map = Sky_view_factor(msh_grid, PV_1_3Dconfig.PV_central)



"""
import pyvista as pv
import numpy as np

grid = pv.StructuredGrid(msh_grid.X, msh_grid.Y, np.ones((len(msh_grid.X[:,0]),len(msh_grid.X[0,:])))*0.05)

test1 = Diffuse_light_map.diffuse_map_t[:,:].ravel()

plotter = pv.Plotter()

plotter.add_mesh(PV_1_3Dconfig.PV_central, color='black')
ground = np.array([[-100, 100, 0],
                   [100, 100, 0],
                   [-100, -100, 0],
                   [100, -100, 0]])

ground_m = np.hstack([[3, 0, 1, 2],    
                      [3, 1, 2, 3],])

grnd = pv.PolyData(ground, ground_m)

plotter.add_mesh(grnd, color='green')
plotter.show_axes()

plotter.add_mesh(
    grid,
    scalars=test1,
    lighting=False,
    show_edges=True,
    scalar_bar_args={"title": "Height"},
    clim=[0, 1])

plotter.show()

"""













"""

import pyvista as pv
import numpy as np

grid = pv.StructuredGrid(msh_grid.X, msh_grid.Y, np.ones((len(msh_grid.X[:,0]),len(msh_grid.X[0,:])))*0.05)

test1 = Direct_light_map.direct_map_hours[0,:,:].ravel()

plotter = pv.Plotter()

plotter.add_mesh(PV_1_3Dconfig.PV_central, color='black')
ground = np.array([[-100, 100, 0],
                   [100, 100, 0],
                   [-100, -100, 0],
                   [100, -100, 0]])

ground_m = np.hstack([[3, 0, 1, 2],    
                      [3, 1, 2, 3],])

grnd = pv.PolyData(ground, ground_m)

plotter.add_mesh(grnd, color='green')
plotter.show_axes()

plotter.add_mesh(
    grid,
    scalars=test1,
    lighting=False,
    show_edges=True,
    scalar_bar_args={"title": "Height"},
    clim=[0, 1])

#plotter.show()

# Open a gif
plotter.open_gif(filename="shade.gif", loop=0, fps=1)

pts = grid.points.copy()

# Update Z and write a frame for each updated position
nframe = 146
for s in range(nframe)[:nframe]:
    plotter.update_coordinates(pts, render=False)
    test = Direct_light_map.direct_map_hours[s,:,:].ravel()
    plotter.update_scalars(test, render=False)

    # Write a frame. This triggers a render.
    plotter.write_frame()

# Closes and finalizes movie
plotter.close()

"""