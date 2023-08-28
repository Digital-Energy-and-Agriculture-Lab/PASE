#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 25 18:06:29 2023

@author: roxane
"""

import numpy as np

def get_wind_speed(windSpeed10m=10, height=2, roughness=0.25):    
    wind_speed = windSpeed10m*(np.log(height/roughness)/np.log(10/roughness))  
    return wind_speed