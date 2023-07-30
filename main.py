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
from MODULES.CROP.evapotranspiration import ET0_FAO56_PM, get_ETo_0D
from MODULES.ENVIRONMENT import Windbreak2D
from MODULES.DATA_MANAGEMENT import graphs


PASE_Logger()

Loc_1 = YAML_Inputs_provider(file='Siguesol_loc.yaml').i

PV_1 = YAML_Inputs_provider(file='PV_central_east.yaml').i
PV_2 = YAML_Inputs_provider(file='PV_central_west.yaml').i

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
                                    visualization=True)                        # !!!! Problem with rotation angle that are negative

PV_2_3Dconfig = PV_Configuration_3D(PV_2, Sun_positions_samp.solar_vector,
                                    visualization=True) 

#### TEMPORARY: EXAMPLE OF a .OBJ importation and merging with the PV panels and merge of the 2 PV polydata
import pyvista
reader = pyvista.get_reader('DATABASE/OBJ/atc030006.obj')
barriere = reader.read()
xrng = np.arange(0, 
                 24,
                 4, dtype=np.float32)
yrng = np.arange(0, 
                 1,
                 2, dtype=np.float32)
zrng = np.arange(0, 1, 2, dtype=np.float32)
x, y, z = np.meshgrid(xrng, yrng, zrng)    
GlobalMesh = pyvista.StructuredGrid(x, y, z)
barrieres = GlobalMesh.glyph(geom=barriere, factor=0.001)

merged = PV_1_3Dconfig.PV_central.merge(PV_2_3Dconfig.PV_central)
merged2 = merged.merge(barrieres)
merged2.plot(style='wireframe', color='tan')
####

msh_grid = Plane_Ground_regular_meshes(Loc_1['Xmin_InterestZone'], Loc_1['Xmax_InterestZone'],
                                       Loc_1['Ymin_InterestZone'], Loc_1['Ymax_InterestZone'],
                                       Loc_1['dX_InterestZone'], Loc_1['dY_InterestZone'])



Sun_positions = Sun_positions(Loc_1['Latitude'],
                              Loc_1['Longitude'],
                              len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                              Loc_1['TimeZone'])

Light = Light(WD.nyears, Sun_positions)

PV_central = PV_system(PV_1)


shade_scene = Light_shade_scene(msh_grid, merged2)
shade_scene.get_light_map(360, Sun_positions_samp.solar_vector)

shade_scene.get_daily_irradiation_map(Sun_positions_samp.SP,
                                      len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                                      Light.data)



PV_central.get_electricity_production(Sun_positions, Light.data, WD.nyears)


### VISUALISATION (temporary)

show_light_map(shade_scene.dir_map[:,:,7], msh_grid, merged2, 0, 1, "Relative direct light reaching the ground [-]")
# IF there is one rotation axis
#show_light_map(shade_scene.dir_map[:,:,5], msh_grid, PV_1_3Dconfig.PV_central[5])

show_light_map(shade_scene.diff_map.astype(np.float32), msh_grid, merged2, 0, 1, "Sky visibility factor [-]")


#temporary lines
j=2
show_light_map(shade_scene.daily_irr_spat['2005'][:,:,j],
               msh_grid,
               merged2,
               shade_scene.daily_irr_spat['2005'][:,:,j].min(),
               shade_scene.daily_irr_spat['2005'][:,:,j].max(),
               "Total irradiation reaching the ground on the julian day "+str(j)+" [MJ/m²]")



