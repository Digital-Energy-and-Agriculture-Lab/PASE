#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Authors : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com) and Nicolas De Cock (nicolas.decock1@gmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import pyvista as pyV
import numpy as np

class MultiBlock_PASE(pyV.MultiBlock):
    '''
    New class which add new functionnalities
    '''
    
    def Get_Lowest_Corners(self,polydata):
        corners = polydata.points
        lowestCorner = corners[corners[:,2]==np.min(corners[:,2]),:]
        if len(lowestCorner) == 2:
            lowestCorner = np.hstack([lowestCorner[0,:],lowestCorner[1,:]])
            return lowestCorner
        elif len(lowestCorner) == 1:
            otherCorners = corners[~corners[:,2]==np.min(corners[:,2]),:]
            SecondLowestCorner = otherCorners[otherCorners[:,2]==np.min(otherCorners[:,2]),:]
            lowestCorner = np.hstack([lowestCorner,SecondLowestCorner])
            return lowestCorner
        else:
            raise("More than 2 lowest corners found")
 
    def Get_Lowest_Corners_Multiblock(self,flag='PV'):
        geometry = self.Get_Polydata_By_Flag('PV')
        for i,g in enumerate(geometry):
            if i ==0:
                corners = self.Get_Lowest_Corners(g)  
            else:
                corners = np.vstack([corners,self.Get_Lowest_Corners(g)])
        return corners

    def Get_Area_Multiblock(self,flag='PV'):
        geometry = self.Get_Polydata_By_Flag('PV')

        for i,g in enumerate(self):
            if i ==0:
                areas = g.area 
            else:
                areas = np.vstack([areas,g.area ])
        return areas
    
    def Get_Height_Multiblock(self,flag='PV'):
        geometry = self.Get_Polydata_By_Flag('PV')

        for i,g in enumerate(self):
            if i ==0:
                height = np.array([np.min(g.points[:,2])])
            else:
                height = np.vstack([height,np.min(g.points[:,2]) ])
        return height.reshape(len(height),1)
    
    def Get_Normal_Multiblock(self,flag='PV'):
        geometry = self.Get_Polydata_By_Flag('PV')

        for i,g in enumerate(self):
            if i ==0:
                areas = g.cell_normals[0]
            else:
                areas = np.vstack([areas,g.cell_normals[0] ])
        return areas
    
    def Get_Polydata_By_Flag(self,flag):
        multi = MultiBlock_PASE()
        for i in range(self.n_blocks):
            if self.get_block_name(i) in flag:
                multi.append(self[i], self.get_block_name(i))
        return multi

class PV_Configuration_3D:
    
    def __init__(self, PV_i, sun_vector, visualization=False):
        
        PV_i = self.get_dict_default_parameters(PV_i)
        
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
        self.rot_axis_nbr = PV_i['RotationAxisNumber']
        
        self.visualization = visualization
        
        if panel_thickness is True:
            first_panel = self.create_first_panel_3D(panel_dimX, panel_dimY, PV_i["PanelDimensionZ"])
        else:
            first_panel = self.create_first_panel(panel_dimX, panel_dimY,PV_i["PanelDimensionZ"]/2)
            
        PV_block_PD, xyz_block = self.create_block_of_panels(repet_dist_panelsX, 
                                                             repet_dist_panelsY,
                                                             n_panelsX,
                                                             n_panelsY,
                                                             first_panel)  
        
        if PV_i['RotationAxisNumber'] == 0:        
            PV_block_PD = self.rotation_1st_axis(PV_block_PD, tilt)
            self.tilt = tilt
            self.PV_central_PD, self.PV_central_MB = self.create_central(PV_block_PD,                                                                         
                                                                         repet_dist_blockX,
                                                                         repet_dist_blockY, 
                                                                         n_blocksX, 
                                                                         n_blocksY, 
                                                                         height,
                                                                         two_facets_rel_position,
                                                                         azimut,
                                                                         first_panel,
                                                                         xyz_block)
        else:
            self.PV_central_PD = []
            self.get_tiltY_along_time(sun_vector, azimut, GCR_x)
            for tilt in self.tiltY_along_time:
                PV_block_tilted = self.rotation_1st_axis(PV_block_PD, tilt)
                PV_central, PV_central_mb = self.create_central(PV_block_tilted, 
                                                 repet_dist_blockX,
                                                 repet_dist_blockY, 
                                                 n_blocksX, 
                                                 n_blocksY, 
                                                 height,
                                                 two_facets_rel_position,
                                                 azimut)
                self.PV_central_PD.append(PV_central)
            
            
    #Set default parameters in the dict, this avoid error of missing key
    def get_dict_default_parameters(self, PV_i):
        
        keys = list(PV_i.keys())
        if not("PanelDimensionZ" in keys):
            PV_i["PanelDimensionZ"] = 0.1
        if not("MeshConfig" in keys):
            PV_i["MeshConfig"] = False
        return PV_i
            
    def create_first_panel(self, panel_dimX, panel_dimY,z_level = 0):
                
        first_panel_vertices = np.array([[-panel_dimX/2, panel_dimY/2, z_level],
                                         [panel_dimX/2, panel_dimY/2, z_level],
                                         [-panel_dimX/2, -panel_dimY/2, z_level],
                                         [panel_dimX/2, -panel_dimY/2, z_level]])
        
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
        PV_block_polydata  = GlobalMesh.glyph(geom=fst_panel, factor=1)
        
        #From Stackoverflow 3D coordinates from meshgrid
        xyz = np.stack(np.meshgrid(xrng, yrng, zrng),axis = -1).reshape(-1,3)  
        
        return PV_block_polydata, xyz
        
    def rotation_1st_axis(self, PV_polydata_or_multiblock, tilt, center=None):
        if type(PV_polydata_or_multiblock) == pyV.core.pointset.PolyData:
            PV_polydata_or_multiblock = PV_polydata_or_multiblock.rotate_y(tilt)
        
        else:
            for i, panel in enumerate(PV_polydata_or_multiblock):
                panel.rotate_y(tilt,center[i],inplace=True)
        
        return PV_polydata_or_multiblock 
        
    def create_central(self, PV_block_polydata, repet_dist_blockX, 
                       repet_dist_blockY, n_blocksX, n_blocksY, height,
                       two_facets_rel_position, azimut, fst_panel=None, xyz_block=None):
        
        xrng = np.arange(repet_dist_blockX*0.5*(1-n_blocksX)+two_facets_rel_position, 
                         repet_dist_blockX*0.5*(n_blocksX+1)+two_facets_rel_position,
                         repet_dist_blockX, dtype=np.float32)
        yrng = np.arange(repet_dist_blockY*0.5*(1-n_blocksY), 
                         repet_dist_blockY*0.5*(n_blocksY+1),
                         repet_dist_blockY, dtype=np.float32)
        zrng = np.arange(height, height*2, height, dtype=np.float32)
        x, y, z = np.meshgrid(xrng, yrng, zrng)
        
        GlobalMesh = pyV.StructuredGrid(x, y, z)        
        PV_central_polydata = GlobalMesh.glyph(geom=PV_block_polydata, factor=1)        
        PV_central_polydata = PV_central_polydata.rotate_z(-azimut)
        
        if self.rot_axis_nbr == 0:   
            #From Stackoverflow 3D coordinates from meshgrid
            xyz_central = np.stack(np.meshgrid(xrng, yrng, zrng),axis = -1).reshape(-1,3)
                    
            PV_central_multiblock = MultiBlock_PASE()  
            #rot_centre_list = []
            for coord_block in xyz_central:
                for coord_panel in xyz_block:
                    PV_central_multiblock.append(fst_panel.copy().translate(coord_panel)
                                                 .translate(coord_block)
                                                 .rotate_y(self.tilt,coord_block,inplace=True)
                                                 .rotate_z(-azimut),'PV')
                    #rot_centre_list.append(coord_block)
            
            #PV_central_multiblock = self.rotation_1st_axis(PV_central_multiblock, self.tilt, rot_centre_list)
        else:
            PV_central_multiblock = None
        
        if self.visualization:
            plotter = pyV.Plotter(lighting=None)
            plotter.add_mesh(PV_central_polydata, color='black')
            
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
            
        return PV_central_polydata, PV_central_multiblock
            
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
       
        ind = np.where(tiltY>np.pi/3)
        tiltY[ind] = np.pi/3
        ind = np.where(tiltY<-np.pi/3)
        tiltY[ind] = -np.pi/3
               
        return tiltY
        
        
