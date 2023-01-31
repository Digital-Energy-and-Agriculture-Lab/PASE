#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 31 09:07:04 2023

@author: roxane
"""

import numpy as np

class Plane_Ground_regular_meshes:
    
    def __init__(self, X_min, X_max, Y_min, Y_max, X_increment, Y_increment):
        
        xrng = np.arange(X_min, X_max, X_increment)
        yrng = np.arange(Y_min, Y_max, Y_increment)
        
        self.X, self.Y = np.meshgrid(xrng, yrng)
        
        