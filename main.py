#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 17 16:06:55 2023

@author: Roxane Bruhwyler
"""
import numpy as np
import os
import pickle
from MODULES.user_support_tools import PASE_Logger
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider, inputs_aggregator
from MODULES.DATA_MANAGEMENT.weather_data_provider import Weather_data
from MODULES.PHOTOVOLTAICS.PV_configurations import PV_Configuration_3D
from MODULES.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from MODULES.ENVIRONMENT.light import show_light_map2, Light_shade_scene
from MODULES.ENVIRONMENT.mesh import Mesh
from MODULES.PHOTOVOLTAICS.PV_productions import PV_production
from MODULES.CROPS.run_crop_simulations import run_crop_simu

PASE_Logger()
# Import of general parameters
Loc_1 = YAML_Inputs_provider(file='Siguesol_loc.yaml', subpath='SCENARIOS').i
# Import PV central and panels parameters
AV_1 = YAML_Inputs_provider(file='AV_siguesol.yaml', subpath='AV_CENTRAL').i
PV_module_1 = YAML_Inputs_provider(file='PV_module_SigueSOL.yaml', subpath=os.path.join('HARDWARE','PV_MODULES')).i
PV_params_dict = inputs_aggregator([AV_1, PV_module_1]).aggregated_inputs

# Import of weather data and computation of daily weather data
WD = Weather_data(Loc_1['Latitude'],
                  Loc_1['Longitude'],
                  Loc_1['SimulationStartingYear'],
                  Loc_1['SimulationEndingYear'],
                  Loc_1['WeatherDataOption'],
                  Loc_1['WeatherFileName'],
                  Loc_1['DailyWeatherFileName'])

# Import sun positions, complete for the HDKR model and sampled for the direct light model
Sun_positions_samp = Sun_positions_sampled(Loc_1['Latitude'],
                                      Loc_1['Longitude'],
                                      Loc_1['PrecisionLevelOnSunPosition'],
                                      Loc_1['LocationName'],
                                      len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                                      Loc_1['TimeZone'])
Sun_positions_complete = Sun_positions(Loc_1['Latitude'],
                                       Loc_1['Longitude'],
                                       len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                                       Loc_1['TimeZone'])
# Creation of the 3D PV central
PV_1_3Dconfig = PV_Configuration_3D(PV_params_dict, Sun_positions_samp.solar_vector,
                                    visualization=False)                        # !!!! Problem with rotation angle that are negative

# Initiation of the object containing points of interest to compute light
M = Mesh()

# Parts to integer in a function that aims to use ray casting light model for PV panels production
# Still have to integer this in a user friendly way and to couple with eletricity production part
"""
PV_params_dictBis = PV_params_dict.copy()
PV_params_dictBis['PanelThickness'] = False
PV_1_3DconfigMeshTop = PV_Configuration_3D(PV_params_dictBis, Sun_positions_samp.solar_vector,
                                    visualization=False)
PV_params_dictBis["PanelDimensionZ"] = -0.1
PV_1_3DconfigMeshBot = PV_Configuration_3D(PV_params_dictBis, Sun_positions_samp.solar_vector,
                                    visualization=False)
M.Add_PV_Mesh(PV_1_3DconfigMeshTop.PV_central,flag = "TopPV", radius = 0.5)
M.Add_PV_Mesh(PV_1_3DconfigMeshBot.PV_central, flag = "BotPV", radius = 0.5)
#TopPoints = M.Get_SourcePoints_ByFlag('TopPV')
#BotPoints = M.Get_SourcePoints_ByFlag('BotPV')
#TopPointsBis = M.Get_SourcePoints(FlagId=[0])
#BotPointsBis = M.Get_SourcePoints(FlagId=[1])
#FlagIdTop = M.Get_FlagId_ByFlag("BotPV")
#print("The Bottom of the PV have the FlagID = " + str(FlagIdTop))
"""

# Add of the points of interests on the ground for crop models
M.Add_Plane_Ground_regular_meshes(Loc_1['Xmin_InterestZone'],
                                  Loc_1['Xmax_InterestZone'],
                                  Loc_1['Ymin_InterestZone'],
                                  Loc_1['Ymax_InterestZone'],
                                  Loc_1['dX_InterestZone'],
                                  Loc_1['dY_InterestZone'],
                                  flag="crop")


# Computation of sun and light data
Light_instance = Light(WD.nyears, Sun_positions_complete)
# Iniation and run of light ray casting model (direct and diffuse) with points of interest and scene
L = Light_shade_scene(mesh=M, geometry=PV_1_3Dconfig.PV_central)
L.get_light_map(180,Sun_positions_samp.solar_vector)
# Integration of irradiation along days
L.get_daily_irradiation_map(Sun_positions_samp.SP,
                            Light_instance.data)
#DiffuseGround = L.Get_diffuse_map_byFlag(Flags=["wheat","corn"])
#DirectGround = L.Get_direct_map_byFlag(Flags=["crop"])


# Examples of visualisation
j = 5 #day definition

show_light_map2(L.sourcePoints[:,:-1], 
                L.dir_map[:,3], 
                PV_1_3Dconfig.PV_central,
                "Direct map [-]")

show_light_map2(L.sourcePoints[:,:-1], 
                np.array(L.diff_map,dtype=np.float32), 
                PV_1_3Dconfig.PV_central,
                "Sky visibility map [-]")

show_light_map2(L.sourcePoints[:,:-1], 
                L.daily_irr_spat['2005'][:,j], 
                PV_1_3Dconfig.PV_central,
                "Total irradiation reaching the ground on the julian day "+str(j)+" [MJ/m²]")

# Example of visualisation of the meshes generate on both sides of the PV panels to compute light
"""
import pyvista
P = pyvista.Plotter()
P.add_mesh(PV_1_3Dconfig.PV_central)
P.add_mesh(pyvista.PolyData(TopPoints[:,:-1]),color="blue")
P.add_mesh(pyvista.PolyData(BotPoints[:,:-1]),color="red")
P.show()
"""

# Method to compute the computational time of different parts of the model
"""
import time
start = time.time()
L.diffuse_map(180)
time1 = time.time() - start
print(time1)
start = time.time()
L.direct_map(Sun_positions_samp.solar_vector)
time2 = time.time() - start
print(time2)
"""

#Example of a way to combine multiple configurations of PV rows and integration of a barrier 
#(Nicolas started to integrate the combination of mutpliple PV_central files in functions in the MaiBis.py)
#### TEMPORARY: EXAMPLE OF a .OBJ importation and merging with the PV panels and merge of the 2 PV polydata
import pyvista
reader = pyvista.get_reader('INPUTS/HARDWARE/STRUCTURES/gen_siguesol.obj')
structure = reader.read()

xrng = np.arange(1.08, 2.08, 2, dtype=np.float32)
yrng = np.arange(-1.54, -0.54, 2, dtype=np.float32)
zrng = np.arange(-3.3, -2.3, 2, dtype=np.float32)

x, y, z = np.meshgrid(xrng, yrng, zrng)    
GlobalMesh = pyvista.StructuredGrid(x, y, z)
structures = GlobalMesh.glyph(geom=structure, factor=0.001)
structures = structures.rotate_z(-AV_1['CentralAzimut'])

merged = PV_1_3Dconfig.PV_central.merge(structures)
PV_1_3Dconfig.PV_central.plot()
structures.plot()
merged.plot()


# PV production model based on a geometric approach
PV_central = PV_production(PV_params_dict)
PV_central.get_electricity_production(Sun_positions_complete, Light_instance.data, WD.nyears)



### CROP MODEL
#Temporary lines, those 2 parameters (crop_model and option_2D) should be in SCENARIOS input files (general parameters)
crop_model = 2 # 0 pour pas de crop model, 1 pour SIMPLE, 2 pour STICS JAVA et 3 pour GRASSIM
option_2D = 1 # 0 pour pas de spatialisation et 1 pour une spatialisation du modèle de culture
Soil_plot, Crop_plot = run_crop_simu(crop_model, option_2D, WD.nyears_daily_WD, 
                                     L.daily_irr_spat,
                                     Loc_1)

show_light_map2(L.sourcePoints[:,:-1], 
                Crop_plot.nyears_data['2006']['Dry_yield'], 
                PV_1_3Dconfig.PV_central,
                "Dry yield STICS 2006 [t/ha]")