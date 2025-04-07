#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

from MODULES.CROPS.SIMPLE.run_simple import run_independant_years_of_crop
from MODULES.CROPS.STICS.JAVA.run_java_stics import run_independant_usms
from MODULES.CROPS.GRASSIM.run_grassim import run_grassim



def run_crop_simu(config, option_2D, WD, daily_irr, scenario_P):

    results = {}
        
    if config['CropModel'] == 'simple':
        Soil_plot, Crop_plot = run_independant_years_of_crop(config, option_2D, WD, daily_irr, 
                                                             scenario_P['Latitude'],
                                                             scenario_P['Altitude'])
        results = merge_results([Soil_plot, Crop_plot])
        
    if config['CropModel'] == 'stics':
        Crop_plot = run_independant_usms(config, WD, daily_irr, scenario_P)  
        results = Crop_plot.nyears_data      
        
    if config['CropModel'] == 'grassim':
        Soil_plot, Crop_plot, Management_plot = run_grassim(config, WD, daily_irr, scenario_P['Latitude'], scenario_P['Altitude'])
        results = merge_results([Soil_plot, Crop_plot, Management_plot])
    
    return results


def merge_results(objects):
    results = {}
    years = objects[0].nyears_data.keys()
    for year in years:
        merged_dict = {}
        for object in objects:
            merged_dict.update(object.nyears_data[year])
        results[year] = merged_dict
    return results
