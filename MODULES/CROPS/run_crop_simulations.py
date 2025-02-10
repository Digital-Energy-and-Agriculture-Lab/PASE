#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

from MODULES.CROPS.SIMPLE.run_simple import run_independant_years_of_crop
from MODULES.CROPS.STICS.JAVA.run_java_stics import run_independant_usms
from MODULES.CROPS.GRASSIM.run_grassim import run_grassim



def run_crop_simu(crop_model, option_2D, WD, daily_irr, scenario_P):
        
    if crop_model == 1:
        
        Soil_plot, Crop_plot = run_independant_years_of_crop(option_2D, WD, daily_irr, 
                                                             scenario_P['Latitude'],
                                                             scenario_P['Altitude'])
        
    if crop_model == 2:

        Soil_plot, Crop_plot = run_independant_usms(WD, daily_irr, scenario_P)        
        
    if crop_model == 3:
        
        Soil_plot, Crop_plot = run_grassim(WD, daily_irr, scenario_P['Latitude'], scenario_P['Altitude'])
        
    
    return Soil_plot, Crop_plot
