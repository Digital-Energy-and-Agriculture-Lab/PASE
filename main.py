#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 17 16:06:55 2023

@author: Roxane Bruhwyler
"""
import numpy as np
from MODULES.user_support_tools import PASE_Logger
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from MODULES.DATA_MANAGEMENT.weather_data_provider import Weather_data
from MODULES.PHOTOVOLTAICS.configurations import PV_Configuration_3D
from MODULES.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from MODULES.ENVIRONMENT.environment_config import Plane_Ground_regular_meshes
from MODULES.ENVIRONMENT.light import show_light_map, Light_shade_scene
from MODULES.PHOTOVOLTAICS.photovoltaic_systems import PV_system

PASE_Logger()

Loc_1 = YAML_Inputs_provider(file='Wallhausen.yaml').i

PV_1 = YAML_Inputs_provider(file='PV_central.yaml').i

Sun_positions_samp = Sun_positions_sampled(Loc_1['Latitude'],
                                      Loc_1['Longitude'],
                                      Loc_1['PrecisionLevelOnSunPosition'],
                                      Loc_1['LocationName'])

PV_1_3Dconfig = PV_Configuration_3D(PV_1, Sun_positions_samp.solar_vector,
                                    visualization=False)

msh_grid = Plane_Ground_regular_meshes(Loc_1['Xmin_InterestZone'], Loc_1['Xmax_InterestZone'],
                                       Loc_1['Ymin_InterestZone'], Loc_1['Ymax_InterestZone'],
                                       Loc_1['dX_InterestZone'], Loc_1['dY_InterestZone'])

WD = Weather_data(Loc_1['Latitude'],
                  Loc_1['Longitude'],
                  Loc_1['SimulationStartingYear'],
                  Loc_1['SimulationEndingYear'],
                  Loc_1['WeatherDataOption'])

Sun_positions = Sun_positions(Loc_1['Latitude'],
                              Loc_1['Longitude'],
                              len(WD.nyears[str(Loc_1['SimulationStartingYear'])]))

Light = Light(WD.nyears, Sun_positions)

PV_central = PV_system(PV_1)

PV_central.get_electricity_production(Sun_positions, Light.data, WD.nyears)


shade_scene = Light_shade_scene(msh_grid,PV_1_3Dconfig.PV_central)
shade_scene.get_light_map(144, Sun_positions_samp.solar_vector)




show_light_map(shade_scene.dir_map[:,:,5], msh_grid, PV_1_3Dconfig.PV_central)
# IF there is one rotation axis
#show_light_map(shade_scene.dir_map[:,:,5], msh_grid, PV_1_3Dconfig.PV_central[5])

show_light_map(shade_scene.diff_map.astype(np.float32), msh_grid, PV_1_3Dconfig.PV_central)




















"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pvlib

fig = plt.figure()        
ax = plt.subplot(1, 1, 1, projection='polar')
points = ax.scatter(np.radians(Sun_positions.SP.azimuth), Sun_positions.SP.apparent_zenith,
                    s=2, label=None, c=Sun_positions.SP.J_day.round(0))
ax.figure.colorbar(points)

Sun_positions.SP = Sun_positions.SP.reset_index(level='hour')

# draw hour labels
SP_june = Sun_positions.SP.query("month == 6")
for h in np.unique(SP_june.hour):
    # choose label position by the smallest radius for each hour
    subset = SP_june.loc[SP_june['hour'] == h]
    r = subset.apparent_zenith
    print(r)
    pos = subset.loc[r.idxmin(),:]
    ax.text(np.radians(pos['azimuth']), pos['apparent_zenith'], str(h))
 
# draw individual days
for date in pd.to_datetime(['2019-03-21', '2019-06-21', '2019-12-21']):
    times = pd.date_range(date, date+pd.Timedelta('24h'), freq='5min')
    solpos = pvlib.solarposition.get_solarposition(times, 
                                                   Sun_positions.lat,
                                                   Sun_positions.long)
    solpos = solpos.loc[solpos['apparent_elevation'] > 0, :]
    label = date.strftime('%Y-%m-%d')
    ax.plot(np.radians(solpos.azimuth), solpos.apparent_zenith, label=label)

ax.figure.legend(loc='upper left')

# change coordinates to be like a compass
ax.set_theta_zero_location('N')
ax.set_theta_direction(-1)
ax.set_rmax(90)

fig.savefig('OUTPUTS/GRAPHS/SunPathDiagram_'+Sun_positions.loc_name+'.svg')

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
