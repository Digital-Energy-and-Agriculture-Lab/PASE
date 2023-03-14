#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 17 16:06:55 2023

@author: Roxane Bruhwyler
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from windrose import WindroseAxes 
from MODULES.user_support_tools import PASE_Logger
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from MODULES.DATA_MANAGEMENT.weather_data_provider import Weather_data
from MODULES.PHOTOVOLTAICS.configurations import PV_Configuration_3D
from MODULES.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from MODULES.ENVIRONMENT.environment_config import Plane_Ground_regular_meshes
from MODULES.ENVIRONMENT.light import show_light_map, Light_shade_scene
from MODULES.PHOTOVOLTAICS.photovoltaic_systems import PV_system
from MODULES.CROP.evapotranspiration import ET0_FAO56_PM
from MODULES.ENVIRONMENT import Windbreak2D


PASE_Logger()

Loc_1 = YAML_Inputs_provider(file='Chanco.yaml').i

PV_1 = YAML_Inputs_provider(file='PV_central.yaml').i

WD = Weather_data(Loc_1['Latitude'],
                  Loc_1['Longitude'],
                  Loc_1['SimulationStartingYear'],
                  Loc_1['SimulationEndingYear'],
                  Loc_1['WeatherDataOption'],
                  Loc_1['WeatherFileName'],
                  Loc_1['DailyWeatherFileName'])

Sun_positions_samp = Sun_positions_sampled(Loc_1['Latitude'],
                                      Loc_1['Longitude'],
                                      Loc_1['PrecisionLevelOnSunPosition'],
                                      Loc_1['LocationName'],
                                      len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                                      Loc_1['TimeZone'])



PV_1_3Dconfig = PV_Configuration_3D(PV_1, Sun_positions_samp.solar_vector,
                                    visualization=False)                        # !!!! Problem with rotation angle that are negative

msh_grid = Plane_Ground_regular_meshes(Loc_1['Xmin_InterestZone'], Loc_1['Xmax_InterestZone'],
                                       Loc_1['Ymin_InterestZone'], Loc_1['Ymax_InterestZone'],
                                       Loc_1['dX_InterestZone'], Loc_1['dY_InterestZone'])



Sun_positions = Sun_positions(Loc_1['Latitude'],
                              Loc_1['Longitude'],
                              len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                              Loc_1['TimeZone'])

Light = Light(WD.nyears, Sun_positions)

PV_central = PV_system(PV_1)


shade_scene = Light_shade_scene(msh_grid,PV_1_3Dconfig.PV_central)
shade_scene.get_light_map(360, Sun_positions_samp.solar_vector)

shade_scene.get_daily_irradiation_map(Sun_positions_samp.SP,
                                      len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                                      Light.data)



PV_central.get_electricity_production(Sun_positions, Light.data, WD.nyears)


### VISUALISATION (temporary)

show_light_map(shade_scene.dir_map[:,:,40], msh_grid, PV_1_3Dconfig.PV_central, 0, 1)
# IF there is one rotation axis
#show_light_map(shade_scene.dir_map[:,:,5], msh_grid, PV_1_3Dconfig.PV_central[5])

show_light_map(shade_scene.diff_map.astype(np.float32), msh_grid, PV_1_3Dconfig.PV_central, 0, 1)


#temporary lines
j=2
show_light_map(shade_scene.daily_irr_spat['2021'][:,:,j],
               msh_grid,
               PV_1_3Dconfig.PV_central,
               shade_scene.daily_irr_spat['2021'][:,:,j].min(),
               shade_scene.daily_irr_spat['2021'][:,:,j].max())


porosity = 0.284
#X & Y MESHES
DH = np.arange(-14,14,0.2)
nY = len(np.arange(-16.4,16.4,0.4))

#Reading of the meteo DB
DB = pd.read_csv(r"DATABASE/METEO/Chanco_Chile_WD.csv").drop(columns=['date','G(h)', 'T2m', 'RH2m',  'PRECIP', 'Gb(n)','Gd(h)'])
WindAngle = np.tile(DB['WD10m'].to_numpy(),(len(DH),1)).reshape((len(DH),365,96))
WindSpeed = np.tile(DB['WS10m'].to_numpy(),(len(DH),1)).reshape((len(DH),365,96))
#WindAngle(DH,day,quarter/hour)

#Projection of the windspeed at 2m
WindSpeed = Windbreak2D.get_wind_speed(WindSpeed)

#Creation of the 2D vector of DH
DH_2D = np.tile(DH,(96,365,1)).transpose()

#Computation of the 2D map of windspeed
WindMap_2D = Windbreak2D.get_ru_Chanco(WindAngle,porosity,DH_2D,WindSpeed,yrep=nY)


#Visualization of the results : mean on the year
import matplotlib.pyplot as plt
plt.imshow(np.mean(WindMap_2D,2).transpose())
ax = plt.gca();
plt.colorbar()
ax.plot()
print('average windspeed at 2m: ' + str(np.mean(WindSpeed)))
print('average windspeed at 2m with the windbreaks :'  + str(np.mean(WindMap_2D)))



# Computation of ET0 for the whole year
ET0_2D = ET0_FAO56_PM(Loc_1['Altitude'], Loc_1['Latitude'], 
                      WD.nyears_daily_WD['2021'], 
                      shade_scene.daily_irr_spat['2021'],
                      WindMap_2D)


# SHOW the ET0 map for a specified julian day
show_light_map(ET0_2D[:,:,j],
               msh_grid,
               PV_1_3Dconfig.PV_central,
               ET0_2D[:,:,j].min(),
               ET0_2D[:,:,j].max())



#### WINDROSE wind direction with wind speed  ####
wind_QH = DB['WD10m'].to_numpy()
ind = np.where(wind_QH>180)
wind_QH = wind_QH+180
wind_QH[ind] = wind_QH[ind]-360

fig = plt.figure()
ax = WindroseAxes.from_ax()
ax.bar(wind_QH, DB['WS10m'], normed=True, opening=1, edgecolor="black", bins=[0, 2, 4, 5, 6, 8, 10])
ax.set_legend(loc='lower left', title='Wind speed (m/s)', fontsize=22)
ax.set_xticklabels(['E', 'NE','N', 'NW', 'W', 'SW', 'S', 'SE'])
ax.set_yticklabels(['4.6 %', '9.2 %','13.8 %', '18.4 %', '23.0 %'])
plt.savefig('OUTPUTS/GRAPHS/windrose.png')



# Windrose with wind direction in function of the month
"""
new_index = pd.date_range(f"01-01-2021 00:00:00",
                          f"31-12-2021 23:45:00",
                          freq='15Min')
M = new_index.month

ax = WindroseAxes.from_ax()
ax.bar(wind_QH, M, normed=True, opening=0.9, edgecolor="white", bins=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
ax.set_legend(loc='lower left', title='Month ID')
ax.set_xticklabels(['E', 'NE','N', 'NW', 'W', 'SW', 'S', 'SE'])
plt.savefig('windrose_month.png')
"""


"""
from datetime import datetime
test = pd.read_csv('DATABASE/METEO/Chili_WD.csv', ';')
test['date'] = pd.to_datetime(test['date'])
test['date'] = pd.to_datetime(test['date'], format='%d-%m-%Y %H:%M:%S')
test = test.set_index(test['date'])
mask = ((test['date']>='01-01-2021 00:00:00') & 
       (test['date']<'01-01-2022 00:00:00'))

test = test.set_index(test['date'])
test = test.drop(['date'], axis=1)
test.index = pd.to_datetime(test.index)
test.index = test.index.strftime('%d-%m-%Y %H:%M:%S')
test2 = test.loc[test.index.year == 2021]
mask = ((test.index>='01-01-2021 00:00:00') & 
       (test.index<'01-01-2022 00:00:00'))
"""

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
