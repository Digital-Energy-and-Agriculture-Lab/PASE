#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 18 14:43:10 2023

@author: Roxane Bruhwyler
"""

import pyvista as pyV
import numpy as np


class PV_Configuration_3D:
    
    def __init__(self, PV_i, sun_vector, visualization=False):
        
        panel_dimX = PV_i['PanelDimensionX']
        panel_dimY = PV_i['PanelDimensionY']
        panel_thickness = PV_i['PanelThickness']
        repet_dist_panelsX = PV_i['RepetitionDistanceOfPanelsX']
        repet_dist_panelsY = PV_i['RepetitionDistanceOfPanelsY']
        n_panelsX = PV_i['NumberOfPanelsX']
        n_panelsY = PV_i['NumberOfPanelsY']
        repet_dist_blockX = PV_i['RepetitionDistanceOfPVBlocksX']
        repet_dist_blockY = PV_i['RepetitionDistanceOfPVBlocksY']
        n_blocksX = PV_i['NumberOfPVBlocksX']
        n_blocksY = PV_i['NumberOfPVBlocksY']
        height = PV_i['Height']
        azimut = PV_i['CentralAzimut']
        tilt = PV_i['TiltY']
        GCR_x = (PV_i['PanelDimensionX']*PV_i['NumberOfPanelsX']/
                      PV_i['RepetitionDistanceOfPVBlocksX'])
        
        two_facets_rel_position = PV_i['TwoFacetsRelativePosition']
        
        self.visualization = visualization
        
        if panel_thickness is True:
            first_panel = self.create_first_panel_3D(panel_dimX, panel_dimY, 0.1)
        else:
            first_panel = self.create_first_panel(panel_dimX, panel_dimY)
            
        PV_block = self.create_block_of_panels(repet_dist_panelsX, 
                                               repet_dist_panelsY,
                                               n_panelsX,
                                               n_panelsY,
                                               first_panel)  
        
        if PV_i['RotationAxisNumber'] == 0:        
            PV_block_tilted = self.rotation_1st_axis(PV_block, tilt)
            self.PV_central = self.create_central(PV_block_tilted, 
                                                  repet_dist_blockX,
                                                  repet_dist_blockY, 
                                                  n_blocksX, 
                                                  n_blocksY, 
                                                  height,
                                                  azimut,
                                                  two_facets_rel_position)
        else:
            self.PV_central = []
            self.get_tiltY_along_time(sun_vector, azimut, GCR_x)
            for tilt in self.tiltY_along_time:
                PV_block_tilted = self.rotation_1st_axis(PV_block, tilt)
                PV_central = self.create_central(PV_block_tilted, 
                                                 repet_dist_blockX,
                                                 repet_dist_blockY, 
                                                 n_blocksX, 
                                                 n_blocksY, 
                                                 height,
                                                 azimut,
                                                 two_facets_rel_position=0)
                self.PV_central.append(PV_central)
            
                
    def create_first_panel(self, panel_dimX, panel_dimY):
                
        first_panel_vertices = np.array([[-panel_dimX/2, panel_dimY/2, 0],
                                         [panel_dimX/2, panel_dimY/2, 0],
                                         [-panel_dimX/2, -panel_dimY/2, 0],
                                         [panel_dimX/2, -panel_dimY/2, 0]])
        
        first_panel_meshes = np.hstack([[3, 0, 1, 2],    # first triangular mesh
                                        [3, 1, 2, 3],])  # second triangular mesh
        
        first_panel = pyV.PolyData(first_panel_vertices, first_panel_meshes)
        
        return first_panel
    
    
    def create_first_panel_3D(self, panel_dimX, panel_dimY,panel_dimZ):
                 
         first_panel_vertices = np.array([
                                          [-panel_dimX/2, panel_dimY/2, panel_dimZ/2],
                                          [panel_dimX/2, panel_dimY/2, panel_dimZ/2],
                                          [-panel_dimX/2, -panel_dimY/2, panel_dimZ/2],
                                          [panel_dimX/2, -panel_dimY/2, panel_dimZ/2],
                                          
                                          [-panel_dimX/2, panel_dimY/2, -panel_dimZ/2],
                                          [panel_dimX/2, panel_dimY/2, -panel_dimZ/2],
                                          [-panel_dimX/2, -panel_dimY/2, -panel_dimZ/2],
                                          [panel_dimX/2, -panel_dimY/2, -panel_dimZ/2],

                                          ])
         
         first_panel_meshes = np.hstack([
                                         [3, 0, 1, 2],    # first triangular mesh
                                         [3, 1, 2, 3],
                                         [3, 4, 5, 6],    
                                         [3, 5, 6, 7],
                                         [3, 1, 3, 7],    
                                         [3, 1, 5, 7],
                                         [3, 0, 2, 6],
                                         [3, 0, 4, 6],
                                         [3, 2, 3, 7],
                                         [3, 2, 6, 7],
                                         [3, 0, 1, 5],
                                         [3, 0, 4, 5]
                                         ])  # second triangular mesh
         
         first_panel = pyV.PolyData(first_panel_vertices, first_panel_meshes)
         
         return first_panel
        
    
    def create_block_of_panels(self, repet_dist_panelsX, repet_dist_panelsY,
                               n_panelsX, n_panelsY, fst_panel):
        
        xrng = np.arange(repet_dist_panelsX*0.5*(1-n_panelsX), 
                         repet_dist_panelsX*0.5*(n_panelsX+1),
                         repet_dist_panelsX, dtype=np.float32)
        yrng = np.arange(repet_dist_panelsY*0.5*(1-n_panelsY), 
                         repet_dist_panelsY*0.5*(n_panelsY+1),
                         repet_dist_panelsY, dtype=np.float32)
        zrng = np.arange(0, 1, 2, dtype=np.float32)
        
        x, y, z = np.meshgrid(xrng, yrng, zrng)    
        
        GlobalMesh = pyV.StructuredGrid(x, y, z)
        PV_block  = GlobalMesh.glyph(geom=fst_panel, factor=1)
        
        return PV_block
        
    def rotation_1st_axis(self, PV_block, tilt):
        
        tilted_PV_block = PV_block.rotate_y(tilt)
        
        return tilted_PV_block
        
        
    def create_central(self, PV_block_tilted, repet_dist_blockX, 
                       repet_dist_blockY, n_blocksX, n_blocksY, height, azimut,
                       two_facets_rel_position):
        
        xrng = np.arange(repet_dist_blockX*0.5*(1-n_blocksX)+two_facets_rel_position, 
                         repet_dist_blockX*0.5*(n_blocksX+1)+two_facets_rel_position,
                         repet_dist_blockX, dtype=np.float32)
        yrng = np.arange(repet_dist_blockY*0.5*(1-n_blocksY), 
                         repet_dist_blockY*0.5*(n_blocksY+1),
                         repet_dist_blockY, dtype=np.float32)
        zrng = np.arange(height, height*2, height, dtype=np.float32)
        x, y, z = np.meshgrid(xrng, yrng, zrng)
        self.x = x
        
        GlobalMesh = pyV.StructuredGrid(x, y, z)
        
        PV_central = GlobalMesh.glyph(geom=PV_block_tilted, factor=1)
        
        PV_central = PV_central.rotate_z(azimut)
        
        #test afficher le sol
        
        if self.visualization:
            plotter = pyV.Plotter(lighting=None)
            plotter.add_mesh(PV_central, color='black')
            
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
            
        return PV_central
            
    def get_tiltY_along_time(self, sun_vect, azimut, GCR_x):
                    
        sun_vect_central_coord = self.get_sun_vect_in_central_coord(sun_vect, azimut)
        true_tracking_angle = self.get_true_tracking_angle(sun_vect_central_coord)
        backT_corr_angle = self.get_backT_corr_angle(true_tracking_angle, GCR_x)
        tiltY_corrected = self.get_corrected_tracking_angle(true_tracking_angle,
                                                             backT_corr_angle)
        tiltY_limited = self.get_limitated_angle(tiltY_corrected)
        self.tiltY_along_time = tiltY_limited*180/np.pi
        
    def get_sun_vect_in_central_coord(self, sun_vect, azimut):
        # Do not take into account the slope of the area and the slope of the 
        # rotation axis (see the previous framework to complete)
        sun_vect_CC = np.zeros((len(sun_vect[:,0]),3))
            
        sun_vect_CC[:,0] = sun_vect[:,0]*np.cos(azimut)\
            - sun_vect[:,1]*np.sin(azimut)                                               
                                                     
        sun_vect_CC[:,1] = sun_vect[:,0]*np.sin(azimut)\
            + sun_vect[:,1]*np.cos(azimut)
                                                       
        sun_vect_CC[:,2] = sun_vect[:,2]
        
        return sun_vect_CC
    
    
    def get_true_tracking_angle(self, sun_v_central_coord):
                    
        true_tracking_angle = np.arctan2(sun_v_central_coord[:,0],
                                         sun_v_central_coord[:,2])
            
        return true_tracking_angle
        
    def get_backT_corr_angle(self, true_angle, GCR_x):
        
        value = np.abs(np.cos(true_angle)/GCR_x)  
           
        backT_corr_angle = np.zeros((len(true_angle)))
        backT_corr_angle[value>=1] = 0
        backT_corr_angle[value<1] = (-np.sign(true_angle[value<1])
                                     *np.arccos((np.abs(np.cos(true_angle[value<1])))/
                                                         GCR_x))
            
        return backT_corr_angle
    
    def get_corrected_tracking_angle(self, true_T_angle, backT_corr_angle):
            
        corrected_tiltY = true_T_angle + backT_corr_angle
                    
        return corrected_tiltY
    
    def get_limitated_angle(self, tiltY):
       
        ind = np.where(tiltY>np.pi/2)
        tiltY[ind] = 0
        ind = np.where(tiltY<-np.pi/2)
        tiltY[ind] = 0
               
        return tiltY
        
        