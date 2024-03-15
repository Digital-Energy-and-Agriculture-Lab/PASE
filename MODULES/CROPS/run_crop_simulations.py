#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 23 12:26:28 2023

@author: roxane
"""

from MODULES.CROPS.SIMPLE.run_simple import run_independant_years_of_crop
from MODULES.CROPS.STICS.JAVA.run_java_stics import run_independant_usms
from MODULES.CROPS.GRASSIM.run_grassim import run_independant_years_of_grassland



def run_crop_simu(crop_model, option_2D, WD, daily_irr, scenario_P):
        
    if crop_model == 1:
        
        Soil_plot, Crop_plot = run_independant_years_of_crop(option_2D, WD, daily_irr, 
                                                             scenario_P['Latitude'],
                                                             scenario_P['Altitude'])
        
    if crop_model == 2:

        Soil_plot, Crop_plot = run_independant_usms(WD, daily_irr, scenario_P)        
        
    if crop_model == 3:
        
        Soil_plot, Crop_plot = run_independant_years_of_grassland(WD, daily_irr, scenario_P['Latitude'], scenario_P['Altitude'])
        
    
    return Soil_plot, Crop_plot