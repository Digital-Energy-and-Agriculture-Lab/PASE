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
import os
from windrose import WindroseAxes
from MODULES.user_support_tools import PASE_Logger
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider, inputs_aggregator
from MODULES.DATA_MANAGEMENT.weather_data_provider import Weather_data
from MODULES.PHOTOVOLTAICS.configurations import PV_Configuration_3D
from MODULES.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from MODULES.ENVIRONMENT.environment_config import Plane_Ground_regular_meshes
from MODULES.ENVIRONMENT.light import show_light_map, Light_shade_scene
from MODULES.ENVIRONMENT.mesh import Mesh
from MODULES.PHOTOVOLTAICS.photovoltaic_systems import PV_system
from MODULES.CROPS.run_crop_simulations import run_crop_simu

PASE_Logger()

Loc_1 = YAML_Inputs_provider(file='Siguesol_loc.yaml', subpath='SCENARIOS').i

AV_1 = YAML_Inputs_provider(file='AV_siguesol.yaml', subpath='AV_CENTRAL').i
PV_module_1 = YAML_Inputs_provider(file='PV_module_SigueSOL.yaml', subpath=os.path.join('HARDWARE','PV_MODULES')).i

PV_params_dict = inputs_aggregator([AV_1, PV_module_1]).aggregated_inputs

"""
PV_1 = YAML_Inputs_provider(file='PV_central_east.yaml', subpath='AV_CENTRAL').i
PV_2 = YAML_Inputs_provider(file='PV_central_west.yaml', subpath='AV_CENTRAL').i
"""

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

Sun_positionsInstance = Sun_positions(Loc_1['Latitude'],
                              Loc_1['Longitude'],
                              len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                              Loc_1['TimeZone'])

PV_1_3Dconfig = PV_Configuration_3D(PV_params_dict, Sun_positions_samp.solar_vector,
                                    visualization=False)                        # !!!! Problem with rotation angle that are negative

PV_params_dictBis = PV_params_dict.copy()
PV_params_dictBis['PanelThickness'] = False
PV_1_3DconfigMeshTop = PV_Configuration_3D(PV_params_dictBis, Sun_positions_samp.solar_vector,
                                    visualization=False)

PV_params_dictBis["PanelDimensionZ"] = -0.1
PV_1_3DconfigMeshBot = PV_Configuration_3D(PV_params_dictBis, Sun_positions_samp.solar_vector,
                                    visualization=False)
M = Mesh()
M.Add_PV_Mesh(PV_1_3DconfigMeshTop.PV_central,flag = "TopPV", radius = 0.5)
M.Add_PV_Mesh(PV_1_3DconfigMeshBot.PV_central, flag = "BotPV", radius = 0.5)
M.Add_Plane_Ground_regular_meshes(0,1,0,3,0.1,1,flag="corn")
M.Add_Plane_Ground_regular_meshes(1,2,0,3,0.1,1,flag="wheat")

TopPoints = M.Get_SourcePoints_ByFlag('TopPV')
BotPoints = M.Get_SourcePoints_ByFlag('BotPV')
TopPointsBis = M.Get_SourcePoints(FlagId=[0])
BotPointsBis = M.Get_SourcePoints(FlagId=[1])
FlagIdTop = M.Get_FlagId_ByFlag("BotPV")
print("The Bottom of the PV have the FlagID = " + str(FlagIdTop))

import pyvista
P = pyvista.Plotter()
P.add_mesh(PV_1_3Dconfig.PV_central)
P.add_mesh(pyvista.PolyData(TopPoints[:,:-1]),color="blue")
P.add_mesh(pyvista.PolyData(BotPoints[:,:-1]),color="red")
P.show()

Light_instance = Light(WD.nyears, Sun_positionsInstance)

L = Light_shade_scene(mesh=M, geometry=PV_1_3Dconfig.PV_central)
L.get_light_map(180,Sun_positions_samp.solar_vector)
L.get_daily_irradiation_map(Sun_positions_samp.SP,
                                      len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                                      Light_instance.data)
DiffuseGround = L.Get_diffuse_map_byFlag(Flags=["wheat","corn"])
DirectGround = L.Get_direct_map_byFlag(Flags=["wheat","corn"])

import pyvista
P = pyvista.Plotter()
P.add_mesh(PV_1_3Dconfig.PV_central)
P.add_mesh(pyvista.PolyData(TopPoints[:,:-1]),color="blue")
P.add_mesh(pyvista.PolyData(BotPoints[:,:-1]),color="red")
P.show()

# L = Light_shade_scene(mesh=M, geometry=PV_1_3Dconfig.PV_central)

# import time
# start = time.time()
# L.diffuse_map(180)
# time1 = time.time() - start
# print(time1)

# start = time.time()
# L.direct_map(Sun_positions_samp.solar_vector)
# time2 = time.time() - start
# print(time2)

#Example of a way to combine multiple configurations of PV rows and integration of a barrier 
#(Nicolas started to integrate the combination of mutpliple PV_central files in functions in the MaiBis.py)
"""
PV_2_3Dconfig = PV_Configuration_3D(PV_2, Sun_positions_samp.solar_vector,
                                    visualization=True) 

#### TEMPORARY: EXAMPLE OF a .OBJ importation and merging with the PV panels and merge of the 2 PV polydata
import pyvista
reader = pyvista.get_reader('INPUTS/HARDWARE/STRUCTURES/atc030006.obj')
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
"""

# msh_grid = Plane_Ground_regular_meshes(Loc_1['Xmin_InterestZone'], Loc_1['Xmax_InterestZone'],
                                       # Loc_1['Ymin_InterestZone'], Loc_1['Ymax_InterestZone'],
                                       # Loc_1['dX_InterestZone'], Loc_1['dY_InterestZone'])

# Sun_positions = Sun_positions(Loc_1['Latitude'],
#                               Loc_1['Longitude'],
#                               len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
#                               Loc_1['TimeZone'])

# Light = Light(WD.nyears, Sun_positions)

# PV_central = PV_system(PV_params_dict)

# shade_scene = Light_shade_scene(msh_grid, PV_1_3Dconfig.PV_central)
# shade_scene.get_light_map(360, Sun_positions_samp.solar_vector)

# shade_scene.get_daily_irradiation_map(Sun_positions_samp.SP,
#                                       len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
#                                       Light.data)

# PV_central.get_electricity_production(Sun_positions, Light.data, WD.nyears)

# ### VISUALISATION (temporary)

# j=150
# show_light_map(shade_scene.dir_map[:,:,j], msh_grid, PV_1_3Dconfig.PV_central, 0, 1, "Relative direct light reaching the ground [-]")
# # IF there is one rotation axis
# #show_light_map(shade_scene.dir_map[:,:,5], msh_grid, PV_1_3Dconfig.PV_central[5])

# show_light_map(shade_scene.diff_map.astype(np.float32), msh_grid, PV_1_3Dconfig.PV_central, 0, 1, "Sky visibility factor [-]")

# #temporary lines

# show_light_map(shade_scene.daily_irr_spat['2005'][:,:,j],
#                msh_grid,
#                PV_1_3Dconfig.PV_central,
#                shade_scene.daily_irr_spat['2005'][:,:,j].min(),
#                shade_scene.daily_irr_spat['2005'][:,:,j].max(),
#                "Total irradiation reaching the ground on the julian day "+str(j)+" [MJ/m²]")




#Temporary lines, those 2 parameters (crop_model and option_2D) should be in SCENARIOS input files
crop_model = 2 # 0 pour pas de crop model, 1 pour SIMPLE, 2 pour STICS JAVA et 3 pour STICS python
option_2D = 1 # 0 pour pas de spatialisation et 1 pour une spatialisation du modèle de culture
# (à discuter avec Nicolas et Arnaud, parfois on voudra la map au sol et parfois avoir juste des points d'intérêt suffira)

test = np.ones((3, 365))*5
test_dict = {}             # Je mets ceci tant que les résultats du modèle de lumière sont mappés en 2D, à termes ce sera juste une liste 1D des points d'intérêt
test_dict['2005'] = test
test_dict['2006'] = test  

Soil_plot, Crop_plot = run_crop_simu(crop_model, option_2D, WD.nyears_daily_WD, 
                                     test_dict, #shade_scene.daily_irr_spat  (à remettre pour crop_model = 1)
                                     Loc_1)
