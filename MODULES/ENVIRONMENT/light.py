#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 31 09:30:10 2023

@author: roxane
"""

import numpy as np
import pandas as pd
import pyvista as pyV
import pvlib

class Sun_positions:
    
    def __init__(self, lat, long):
        
        
        index = pd.date_range(start='2005-01-01 00:00', freq='1H', 
                              periods=365*24*4)
        hour = index.hour
        month = index.month
        
        self.solar_position = pvlib.solarposition.get_solarposition(index, lat, long)
        
        self.solar_position.insert(0, "hour", hour)
        self.solar_position.insert(1, "month", month)
        
        
        
        self.test = self.solar_position.groupby(by=['month','hour']).mean()
        
        
        
        
        # https://pvlib-python.readthedocs.io/en/stable/gallery/solar-position/plot_sunpath_diagrams.html#sphx-glr-gallery-solar-position-plot-sunpath-diagrams-py
    