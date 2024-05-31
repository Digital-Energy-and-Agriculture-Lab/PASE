# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Louis Lemaire (Louis.Lemaire@uliege.be)
#This file is part of the PASE software, and is distributed under the MIT license.

import pandas as pd
from MODULES.CROPS.GRASSIM import grassim
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from MODULES.CROPS.evapotranspiration_FAO56_PM import get_ET0


def run_independant_years_of_grassland(WD, daily_irr, lat, alt):
    
    Crop_init = YAML_Inputs_provider(file = 'CROPS/GRASSIM/crop_init_GEMBLOUX.yml').inputs
    Kc_values = YAML_Inputs_provider(file = 'CROPS/GRASSIM/Kc_values.yml').inputs
    PFT_composition = YAML_Inputs_provider(file = 'CROPS/GRASSIM/PFT_composition.yml').inputs
    PFT_values = pd.read_csv('INPUTS/CROPS/GRASSIM/Parameters_values_PFT.csv',header=0, sep=";", decimal='.')
    Management = YAML_Inputs_provider(file = 'CROPS/GRASSIM/Management.yml').inputs #need to add duration parameter
    albedo = 0.2 #needs to be in crop init parameters. Not available for GEMBLOUX crop.
    
    
    Soil_plot = 0 #for now, all of the output is stored in Crop_plot
    Crop_plot = grassim.Grassland(crop_init=Crop_init, Kc_values=Kc_values, PFT_composition=PFT_composition, PFT_values=PFT_values, Management=Management)
    
    for year in WD.keys():
        
        Crop_plot.initiate_one_year_variables(year)
        Crop_plot.init_crop(daily_irr[year])
    
        for day in WD[year].index:
            
            if day.day_of_year==366:
                break

            irradiation = daily_irr[year][:,day.day_of_year-1]
            
            if 'ET0' in WD[year].columns:
                ET0 = WD[year]['ET0'][day]
            else :
                #[FIX] column indexes are not right
                ET0 = get_ET0(WD[year]['Avg_temp'][day],
                              WD[year]['Min_temp'][day],
                              WD[year]['Max_temp'][day],
                              WD[year]['Avg_WS_2m'][day],
                              WD[year]['Vap_press'][day],
                              irradiation,
                              Crop_plot.LAI,
                              day.day_of_year,
                              len(WD[year]['Avg_temp']),
                              lat,
                              alt,
                              albedo)
            
            Crop_plot.growth(WD[year].loc[day], ET0, irradiation, day)

            Crop_plot.fill_nyears_data_dict(year)
    
    return Soil_plot, Crop_plot
