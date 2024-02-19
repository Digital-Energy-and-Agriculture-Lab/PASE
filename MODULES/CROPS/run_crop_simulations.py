#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 23 12:26:28 2023

@author: roxane
"""

from MODULES.CROPS.SIMPLE.simple import simple_model
from MODULES.CROPS.STICS.JAVA.run_java_stics import run_independants_usms
from MODULES.CROPS.GRASSIM.call_grassim import call_grassim



def run_crop_simu(crop_model, option_2D, WD, daily_irr, scenario_P):
        
    if crop_model == 1:
        
        Soil_plot, Crop_plot = simple_model(option_2D, WD, daily_irr, 
                                            scenario_P['Latitude'],
                                            scenario_P['Altitude'])
        
    if crop_model == 2:

        Soil_plot, Crop_plot = run_independants_usms(WD, daily_irr, scenario_P)        
        
    if crop_model == 3:
        
        Soil_plot, Crop_plot = call_grassim(WD, daily_irr, scenario_P['Latitude'], scenario_P['Altitude'])
        
    
    return Soil_plot, Crop_plot