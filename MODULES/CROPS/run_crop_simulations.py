#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 23 12:26:28 2023

@author: roxane
"""

from MODULES.CROPS.SIMPLE.simple import simple_model


def run_crop_simu(crop_model, option_2D, WD, daily_irr, lat, alt):
        
    if crop_model == 1:
        
        Soil_plot, Crop_plot = simple_model(option_2D, WD, daily_irr, lat, alt)
        
    return Soil_plot, Crop_plot
    