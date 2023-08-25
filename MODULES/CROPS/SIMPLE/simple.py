#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 25 13:41:47 2023

@author: roxane
"""

import pandas as pd
from MODULES.CROPS.SIMPLE import crop_growth
from MODULES.CROPS.SIMPLE import water_balance
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from MODULES.CROPS.SIMPLE.evapotranspiration_FAO56_PM import get_ET0


def simple_model(option_2D, WD, daily_irr, lat, alt):
    
    
    Crop_init = YAML_Inputs_provider(file = 'CROPS/SIMPLE/crop_init.yaml').i
    Crop_param = pd.read_csv('INPUTS/CROPS/SIMPLE/crops_parameters.csv', skiprows=int(Crop_init['CropID'])-1, nrows=1).to_dict('records')[0]
    Soil_param = YAML_Inputs_provider(file = 'CROPS/SIMPLE/soil_init.yaml').i
        
    
    for year in WD.keys():  

        Soil_plot = water_balance.Soil(Soil_param)
        Crop_plot = crop_growth.Crop(Crop_param, 
                                Crop_init)
        
        for day in WD[year].index:
            
            if option_2D==1:
                irradiation = daily_irr[year][:,:,day.day_of_year-1]
            
            ET0 = get_ET0(WD[year]['Avg_temp'][day],
                          WD[year]['Min_temp'][day],
                          WD[year]['Max_temp'][day],
                          WD[year]['Avg_WS_10m'][day],
                          WD[year]['Vap_press'][day],
                          irradiation,
                          Crop_plot.LAI,
                          day.day_of_year,
                          len(WD[year]['Avg_temp']),
                          lat,
                          alt,
                          Soil_param['Albedo'])
            
            Soil_plot.hydric_balance(WD[year]['Rain'][day],
                                     ET0,
                                     0,
                                     day)
            
            Crop_plot.growth(WD[year]['Avg_temp'][day],
                             WD[year]['Max_temp'][day],
                             WD[year]['CO2'][day],
                             irradiation, 
                             ET0,
                             Soil_plot.dict_transpi[str(day)],
                             day)
            
        Soil_plot.fill_nyears_data_dict(year)
        Crop_plot.fill_nyears_data_dict(year)
        
    return Soil_plot, Crop_plot