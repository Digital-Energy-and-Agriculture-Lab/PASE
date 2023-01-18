#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 18 14:43:10 2023

@author: Roxane Bruhwyler
"""

import pyvista as pyV
import numpy as np


class PV_Configuration_3D:
    
    def __init__(self, PV_i):
        
        self.PV_i = PV_i
        
        self.create_first_panel()
        
        
    def create_first_panel(self):
                
        first_panel_vertices = np.array([[-self.PV_i['PanelDimensionX']/2, self.PV_i['PanelDimensionY']/2, 0],
                                         [self.PV_i['PanelDimensionX']/2, self.PV_i['PanelDimensionY']/2, 0],
                                         [-self.PV_i['PanelDimensionX']/2, -self.PV_i['PanelDimensionY']/2, 0],
                                         [self.PV_i['PanelDimensionX']/2, -self.PV_i['PanelDimensionY']/2, 0]])
        
        first_panel_meshes = np.hstack([[3, 0, 1, 2],    # first triangular mesh
                                        [3, 1, 2, 3],])  # second triangular mesh
        
        first_panel = pyV.PolyData(first_panel_vertices, first_panel_meshes)
        
            
            