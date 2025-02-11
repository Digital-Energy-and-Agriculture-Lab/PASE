# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Louis Lemaire (Louis.Lemaire@uliege.be)
#This file is part of the PASE software, and is distributed under the MIT license.

import os
import pandas as pd
import yaml
from MODULES.CROPS.GRASSIM.plants.plants import Plants
from MODULES.CROPS.GRASSIM.soil.soil import Soil
from MODULES.CROPS.GRASSIM.management.management import Management
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from MODULES.CROPS.evapotranspiration_FAO56_PM import get_ET0

def run_grassim(config, WD, daily_irr, lat, alt):

    soil_init = YAML_Inputs_provider(file=f"CROPS/GRASSIM/soil/{config['soil_init']}").inputs
    crop_init = YAML_Inputs_provider(file=f"CROPS/GRASSIM/crop/{config['crop_init']}").inputs
    kc_values = YAML_Inputs_provider(file=f"CROPS/GRASSIM/crop/{config['Kc_values']}").inputs
    pft_composition = YAML_Inputs_provider(file=f"CROPS/GRASSIM/{config['PFT_composition']}").inputs
    pft_values = pd.read_csv(f"INPUTS/CROPS/GRASSIM/{config['PFT_values']}",header=0, sep=";", decimal='.')
    management = YAML_Inputs_provider(file=f"CROPS/GRASSIM/management/{config['management']}").inputs
    
    with open(f"INPUTS/CROPS/GRASSIM/{config['variables_to_save']}", "r") as file:
        variables_to_save = yaml.safe_load(file)

    simulation_dates = get_sim_dates(WD)

    grid = get_grid_shape(daily_irr)
    soil = Soil(grid=grid, inits=soil_init, variables_to_save=variables_to_save['soil_variables'])
    crop = Plants(grid=grid, pft_composition=pft_composition, inits=crop_init, kc_values=kc_values, pft_values=pft_values, variables_to_save=variables_to_save['crop_variables'])
    management = Management(grid=grid, config=management, variables_to_save=variables_to_save['management_variables'])

    for year in simulation_dates.keys():
        for day in simulation_dates[year]:
            day_irr = daily_irr[year][:,day.dayofyear-1]
            ET0 = get_ET0(WD[year]['Avg_temp'][day],
                                WD[year]['Min_temp'][day],
                                WD[year]['Max_temp'][day],
                                WD[year]['Avg_WS_2m'][day],
                                WD[year]['Vap_press'][day],
                                day_irr,
                                crop.LAI,
                                day.day_of_year,
                                len(WD[year]['Avg_temp']),
                                lat,
                                alt,
                                soil.albedo)

            run_daily_loop(day, ET0, WD[year].loc[day], day_irr, soil, crop, management)

    return soil, (crop, management)


def run_daily_loop(day, ET0, WD, day_irr, soil, crop, management):

    crop.init_daily_loop(day=day, WD=WD, ET0=ET0, day_irr=day_irr)
    soil.init_daily_loop(day=day)
    management.init_daily_loop(day=day, crop=crop, soil=soil)
    # computation sequence : equivalent of grassim.py
    crop.compute_aet() # Uses Kc (BMGV in the future), needed for soil water balance
    crop.compute_potential_growth()

    crop.compute_st()
    crop.compute_fAge() # need st, used for SEN & ABS
    crop.compute_senescence_abscission()
    crop.compute_N_plant_litter

    crop.compute_fT()
    crop.compute_fPARi()
    crop.compute_fW(soil.W)
    crop.compute_N_supply(Nmin=soil.Nmin, FNAmax=0.07, NSc=270)
    crop.compute_fN()
    crop.compute_N_demand()
    crop.compute_N_uptake()
    crop.compute_N_plant_litter()
    crop.compute_environmental_stress() # fPAR*fT*fWfN, used for GRO
    crop.compute_seasonal_effect() # need st, used for GRO

    crop.compute_actual_growth()
    crop.update() # update BM compartments, OMD, sward height, age, based on actual growth

    soil.compute_water_balance(PP=crop.PP, AET=crop.AET)
    soil.compute_N_mineralization(K=crop.K, Tref=crop.Tref, Temp=crop.Temp) # parameters for soil activity (Ruelle et al., 2018)
    soil.compute_N_immobilization()
    soil.compute_N_leached()
    soil.compute_N2O_emissions()
    soil.compute_N_from_rain(crop.PP)
    soil.compute_Norg(percentageofNmin=crop.percentageofNmin, N_plant_litter=crop.N_plant_litter, fert_org=management.fert_org)
    soil.compute_Nmin(percentageofNmin=crop.percentageofNmin, NH3volatfactor=crop.NH3volatfactor, N_uptake=crop.N_uptake, fert_org=management.fert_org, fert_min=management.fert_min)

    crop.save_variables()
    soil.save_variables()
    management.save_variables()


def get_sim_dates(weather_data):
    """
    weather_data : Weather_data object from weather_data_provider
    
    returns : 
        simulation_dates : list of simulation days
    """
    simulation_dates = {}

    for year in weather_data.keys():
        simulation_dates[year] = []
        for day in weather_data[year].index:
            simulation_dates[year].append(day)

    return simulation_dates


def get_yaml_params(filename):
    return YAML_Inputs_provider(file=filename).inputs


def get_grid_shape(daily_irradiance):
    """
    daily irradiance : daily_irr_spat dictionnary attribut from Ray_casting_scene object
    """
    return daily_irradiance[next(iter(daily_irradiance))].shape[0]