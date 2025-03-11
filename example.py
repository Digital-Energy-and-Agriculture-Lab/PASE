#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import numpy as np
import os
import pickle
from MODULES.user_support_tools import PASE_Logger
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider, Inputs_aggregator
from MODULES.DATA_MANAGEMENT.weather_data_provider import Weather_data
from MODULES.PHOTOVOLTAICS.configuration import PV_Configuration_3D
from MODULES.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from MODULES.ENVIRONMENT.light import show_light_map2, Ray_casting_scene
from MODULES.ENVIRONMENT.mesh import Mesh
from MODULES.PHOTOVOLTAICS.production import PV_Production
from MODULES.CROPS.run_crop_simulations import run_crop_simu

PASE_Logger()

###############
# Load inputs #
###############
Loc_1 = YAML_Inputs_provider(file='Example1_loc.yaml', subpath='SCENARIOS').inputs
# Import PV system and PV modules parameters
AV_1 = YAML_Inputs_provider(file='Example1_AV.yaml', subpath='AV_CENTRAL').inputs
PV_module_1 = YAML_Inputs_provider(file='Example1_PV_Module.yaml', subpath=os.path.join('HARDWARE','PV_MODULES')).inputs
crop_config = YAML_Inputs_provider(file='simple_example.yml', subpath=os.path.join('CROPS', 'config')).inputs
PV_params_dict = Inputs_aggregator([AV_1, PV_module_1]).aggregated_inputs

##################
# Pre-processing #
##################
# Import of weather data and computation of daily weather data
WD = Weather_data(Loc_1['Latitude'],
                  Loc_1['Longitude'],
                  Loc_1['SimulationStartingYear'],
                  Loc_1['SimulationEndingYear'],
                  Loc_1['WeatherDataOption'],
                  Loc_1['WeatherFileName'],
                  Loc_1['DailyWeatherFileName'])

# Import sun positions

# sampled for the direct light model
Sun_positions_samp = Sun_positions_sampled(Loc_1['Latitude'],
                                      Loc_1['Longitude'],
                                      Loc_1['PrecisionLevelOnSunPosition'],
                                      Loc_1['LocationName'],
                                      len(WD.nyears_data[str(Loc_1['SimulationStartingYear'])]),
                                      Loc_1['TimeZone'])
# complete for the HDKR model
Sun_positions_complete = Sun_positions(Loc_1['Latitude'],
                                       Loc_1['Longitude'],
                                       len(WD.nyears_data[str(Loc_1['SimulationStartingYear'])]),
                                       Loc_1['TimeZone'])

# Instantiation of the 3D PV central
PV_1_3Dconfig = PV_Configuration_3D(PV_params_dict,
                                    Sun_positions_samp.solar_vector,
                                    visualization=True)  # !!!! Problem with rotation angle that are negative

# Initiation of the object containing points of interest to compute light
M = Mesh()

# Add of the points of interests on the ground for crop models
M.add_plane_ground_regular_meshes(Loc_1['Xmin_InterestZone'],
                                  Loc_1['Xmax_InterestZone'],
                                  Loc_1['Ymin_InterestZone'],
                                  Loc_1['Ymax_InterestZone'],
                                  Loc_1['dX_InterestZone'],
                                  Loc_1['dY_InterestZone'],
                                  flag="crop")

# Computation of sun and light data
Light_instance = Light(WD.nyears_data, Sun_positions_complete)

# Iniation and run of light ray casting model (direct and diffuse) with points of interest and scene
L = Ray_casting_scene(mesh=M, geometry=PV_1_3Dconfig.PV_central_PD)
L.get_light_maps(180,Sun_positions_samp.solar_vector)

# Integration of irradiation along days
L.get_daily_irradiation_map(Sun_positions_samp.SP,
                            Light_instance.data)


# Examples of visualisation for the direct light map, diffuse light map (sky view factor)
# and daily irradiation map. Those lines are for PV system with no rotation axis. 
j = 5 #  julian day of the year

show_light_map2(L.sourcepoints[:,:-1], 
                L.dir_map[:,3], 
                PV_1_3Dconfig.PV_central_PD,
                "Direct map [-]")

show_light_map2(L.sourcepoints[:,:-1], 
                np.array(L.diff_map,dtype=np.float32), 
                PV_1_3Dconfig.PV_central_PD,
                "Sky visibility map [-]")

show_light_map2(L.sourcepoints[:,:-1], 
                L.daily_irr_spat['2005'][:,j],
                PV_1_3Dconfig.PV_central_PD,
                "Total irradiation reaching the ground on the julian day "+str(j)+" [MJ/m²]")


##############
# Processing #
##############

# PV production model
PV_central = PV_Production(PV_params_dict)
PV_central.get_several_years_of_electricity_production(Sun_positions_complete, Light_instance.data, WD.nyears_data)

for _ in ['2005', '2006', '2007']:
    PV_prod = PV_central.production[_]
    print(f'PV production for year 2005: {PV_prod["P_central"].sum():.2f} MW·h')

# Crop model
#Temporary line, this parameter (option_2D) should be in SCENARIOS input files (general parameters)
option_2D = 1 # 0: no 2D-spatialization ; 1 : 2D spatialization

Soil_plot, Crop_plot = run_crop_simu(crop_config, option_2D, WD.nyears_daily_data,
                                     L.daily_irr_spat,
                                     Loc_1)

# Display spatialized dry yield
show_light_map2(L.sourcepoints[:,:-1],
                Crop_plot.nyears_data['2005']['Dry_yield']['2005-10-10 00:00:00']/100,
                PV_1_3Dconfig.PV_central_PD,
                "Dry yield SIMPLE 2005 [t/ha]")
