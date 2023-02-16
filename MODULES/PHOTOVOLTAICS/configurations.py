#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 18 14:43:10 2023

@author: Roxane Bruhwyler
"""

import pyvista as pyV
import numpy as np


class PV_Configuration_3D:
    
    def __init__(self, PV_i,visualization=False):
        
        self.PV_i = PV_i
        self.visualization = visualization
        fst_panel = self.create_first_panel()
        self.create_block_of_panels(fst_panel)
        self.rotation_1st_axis()
        self.create_central()
        
        
    def create_first_panel(self):
                
        first_panel_vertices = np.array([[-self.PV_i['PanelDimensionX']/2, self.PV_i['PanelDimensionY']/2, 0],
                                         [self.PV_i['PanelDimensionX']/2, self.PV_i['PanelDimensionY']/2, 0],
                                         [-self.PV_i['PanelDimensionX']/2, -self.PV_i['PanelDimensionY']/2, 0],
                                         [self.PV_i['PanelDimensionX']/2, -self.PV_i['PanelDimensionY']/2, 0]])
        
        first_panel_meshes = np.hstack([[3, 0, 1, 2],    # first triangular mesh
                                        [3, 1, 2, 3],])  # second triangular mesh
        
        first_panel = pyV.PolyData(first_panel_vertices, first_panel_meshes)
        
        return first_panel
        
    
    def create_block_of_panels(self, fst_panel):
        
        xrng = np.arange(self.PV_i['RepetitionDistanceOfPanelsX']*0.5*(1-self.PV_i['NumberOfPanelsX']), 
                         self.PV_i['RepetitionDistanceOfPanelsX']*0.5*(self.PV_i['NumberOfPanelsX']+1),
                         self.PV_i['RepetitionDistanceOfPanelsX'], dtype=np.float32)
        yrng = np.arange(self.PV_i['RepetitionDistanceOfPanelsY']*0.5*(1-self.PV_i['NumberOfPanelsY']), 
                         self.PV_i['RepetitionDistanceOfPanelsY']*0.5*(self.PV_i['NumberOfPanelsY']+1),
                         self.PV_i['RepetitionDistanceOfPanelsY'], dtype=np.float32)
        zrng = np.arange(0, 1, 2, dtype=np.float32)
        
        x, y, z = np.meshgrid(xrng, yrng, zrng)    
        
        GlobalMesh = pyV.StructuredGrid(x, y, z)
        self.PV_block  = GlobalMesh.glyph(geom=fst_panel, factor=1)
        
        
    def rotation_1st_axis(self):
        
        self.tilted_PV_block = self.PV_block.rotate_y(self.PV_i['TiltY'])
        
        
    def create_central(self):
        
        xrng = np.arange(self.PV_i['RepetitionDistanceOfPVBlocksX']*0.5*(1-self.PV_i['NumberOfPVBlocksX']), 
                         self.PV_i['RepetitionDistanceOfPVBlocksX']*0.5*(self.PV_i['NumberOfPVBlocksX']+1),
                         self.PV_i['RepetitionDistanceOfPVBlocksX'], dtype=np.float32)
        yrng = np.arange(self.PV_i['RepetitionDistanceOfPVBlocksY']*0.5*(1-self.PV_i['NumberOfPVBlocksY']), 
                         self.PV_i['RepetitionDistanceOfPVBlocksY']*0.5*(self.PV_i['NumberOfPVBlocksY']+1),
                         self.PV_i['RepetitionDistanceOfPVBlocksY'], dtype=np.float32)
        zrng = np.arange(self.PV_i['Height'], self.PV_i['Height']*2, self.PV_i['Height'], dtype=np.float32)
        x, y, z = np.meshgrid(xrng, yrng, zrng)
        
        GlobalMesh = pyV.StructuredGrid(x, y, z)
        
        PV_central = GlobalMesh.glyph(geom=self.tilted_PV_block, factor=1)
        
        self.PV_central = PV_central.rotate_z(self.PV_i['CentralAzimut'])
        
        #test afficher le sol
        
        if self.visualization:
            plotter = pyV.Plotter(lighting=None)
            plotter.add_mesh(self.PV_central, color='black')
            
            ground = np.array([[-100, 100, 0],
                               [100, 100, 0],
                               [-100, -100, 0],
                               [100, -100, 0]])
            
            ground_m = np.hstack([[3, 0, 1, 2],    
                                  [3, 1, 2, 3],])
            
            grnd = pyV.PolyData(ground, ground_m)
            
            plotter.add_mesh(grnd, color='green')
            
            light = pyV.Light()
            light.set_direction_angle(30, 45)    
            plotter.add_light(light)
            
            #plotter.set_background(color='#A6D0DE')
            
            plotter.show()
        
        