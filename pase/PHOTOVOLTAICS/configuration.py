#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Authors : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com) and Nicolas De Cock (nicolas.decock1@gmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import pyvista as pyV
import numpy as np
from pase.user_support_tools import prompt

pyV.global_theme.allow_empty_mesh = True

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
        
        self.panel_dim_x = PV_i['PanelDimensionX']
        self.panel_dim_y = PV_i['PanelDimensionY']
        panel_thickness = PV_i['PanelThickness']
        self.repet_dist_panels_x = PV_i['RepetitionDistanceOfPanelsX']
        self.repet_dist_panels_y = PV_i['RepetitionDistanceOfPanelsY']
        self.n_panels_x = PV_i['NumberOfPanelsX']
        self.n_panels_y = PV_i['NumberOfPanelsY']
        self.repet_dist_block_x = PV_i['RepetitionDistanceOfPVBlocksX']
        self.repet_dist_block_y = PV_i['RepetitionDistanceOfPVBlocksY']
        self.n_blocks_x = PV_i['NumberOfPVBlocksX']
        self.n_blocks_y = PV_i['NumberOfPVBlocksY']
        self.height = PV_i['Height']
        self.azimut = PV_i['CentralAzimut']
        self.GCR_x = (PV_i['PanelDimensionX']*PV_i['NumberOfPanelsX']/
                      PV_i['RepetitionDistanceOfPVBlocksX'])
        
        self.two_facets_rel_position = PV_i['TwoFacetsRelativePosition']
        self.rot_axis_nbr = PV_i['RotationAxisNumber']
        
        self.visualization = visualization
        
        if panel_thickness is True:
            first_panel = self.create_first_panel_3D(PV_i["PanelDimensionZ"])
        else:
            first_panel = self.create_first_panel(PV_i["PanelDimensionZ"]/2)
            
        PV_block_PD, xyz_block = self.create_block_of_panels(first_panel)
        
        if self.rot_axis_nbr == 0:
            self.tilt = PV_i['TiltY']
            PV_block_PD = self.rotation_1st_axis(PV_block_PD)
            self.PV_central_PD, self.PV_central_MB = self.create_central(PV_block_PD,
                                                                         first_panel,
                                                                         xyz_block)
        else:
            self.PV_central_PD = []
            self.get_tiltY_along_time(sun_vector)
            counter_viz = 0
            for tilt in self.tiltY_along_time:
                PV_block_tilted = self.rotation_1st_axis(PV_block_PD, tilt)
                PV_central, PV_central_mb = self.create_central(PV_block_tilted)
                self.PV_central_PD.append(PV_central)

                if self.visualization:
                    counter_viz += 1
                # Prompt : keep showing PV structure ?
                if counter_viz % 3 == 0 and self.visualization:
                    counter_viz += 1
                    resp = prompt('Keep showing PV structures ? y/[n]', valid=('y', 'n'), default='n')
                    if resp == 'n':
                        self.visualization = False
            
    #Set default parameters in the dict, this avoid error of missing key
    def get_dict_default_parameters(self, PV_i):
        
        keys = list(PV_i.keys())
        if not("PanelDimensionZ" in keys):
            PV_i["PanelDimensionZ"] = 0.1
        if not("MeshConfig" in keys):
            PV_i["MeshConfig"] = False
        return PV_i
            
    def create_first_panel(self, z_level = 0):
                
        first_panel_vertices = np.array([[-self.panel_dim_x/2, self.panel_dim_y/2, z_level],
                                         [self.panel_dim_x/2, self.panel_dim_y/2, z_level],
                                         [-self.panel_dim_x/2, -self.panel_dim_y/2, z_level],
                                         [self.panel_dim_x/2, -self.panel_dim_y/2, z_level]])
        
        first_panel_meshes = np.hstack([[3, 0, 1, 2],    # first triangular mesh
                                        [3, 1, 2, 3],])  # second triangular mesh
        
        first_panel = pyV.PolyData(first_panel_vertices, first_panel_meshes)
        
        return first_panel
    
    
    def create_first_panel_3D(self,panel_dimZ):
                 
         first_panel_vertices = np.array([
                                          [-self.panel_dim_x/2, self.panel_dim_y/2, panel_dimZ/2],
                                          [self.panel_dim_x/2, self.panel_dim_y/2, panel_dimZ/2],
                                          [-self.panel_dim_x/2, -self.panel_dim_y/2, panel_dimZ/2],
                                          [self.panel_dim_x/2, -self.panel_dim_y/2, panel_dimZ/2],
                                          
                                          [-self.panel_dim_x/2, self.panel_dim_y/2, -panel_dimZ/2],
                                          [self.panel_dim_x/2, self.panel_dim_y/2, -panel_dimZ/2],
                                          [-self.panel_dim_x/2, -self.panel_dim_y/2, -panel_dimZ/2],
                                          [self.panel_dim_x/2, -self.panel_dim_y/2, -panel_dimZ/2],

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
        
    
    def create_block_of_panels(self,
                               fst_panel):

        xrng = self.repet_dist_panels_x * np.arange(-(self.n_panels_x - 1) / 2, (self.n_panels_x + 1) / 2)
        yrng = self.repet_dist_panels_y * np.arange(-(self.n_panels_y - 1) / 2, (self.n_panels_y + 1) / 2)
        zrng = np.arange(0, 1, 2, dtype=np.float32)
        
        x, y, z = np.meshgrid(xrng, yrng, zrng)            
        GlobalMesh = pyV.StructuredGrid(x, y, z)
        PV_block_polydata  = GlobalMesh.glyph(geom=fst_panel, factor=1)
        
        #From Stackoverflow 3D coordinates from meshgrid
        xyz = np.stack(np.meshgrid(xrng, yrng, zrng),axis = -1).reshape(-1,3)  
        
        return PV_block_polydata, xyz
        
    def rotation_1st_axis(self, PV_polydata_or_multiblock, center=None):
        if type(PV_polydata_or_multiblock) == pyV.core.pointset.PolyData:
            PV_polydata_or_multiblock = PV_polydata_or_multiblock.rotate_y(self.tilt)
        
        else:
            for i, panel in enumerate(PV_polydata_or_multiblock):
                panel.rotate_y(self.tilt,center[i], inplace=True)
        
        return PV_polydata_or_multiblock 
        
    def create_central(self, PV_block_polydata, fst_panel=None, xyz_block=None):
        
        xrng = np.arange(self.repet_dist_block_x*0.5*(1-self.n_blocks_x)+self.two_facets_rel_position,
                         self.repet_dist_block_x*0.5*(self.n_blocks_x+1)+self.two_facets_rel_position,
                         self.repet_dist_block_x, dtype=np.float32)
        yrng = np.arange(self.repet_dist_block_y*0.5*(1-self.n_blocks_y),
                         self.repet_dist_block_y*0.5*(self.n_blocks_y+1),
                         self.repet_dist_block_y, dtype=np.float32)
        zrng = np.arange(self.height, self.height*2, self.height, dtype=np.float32)
        x, y, z = np.meshgrid(xrng, yrng, zrng)
        
        GlobalMesh = pyV.StructuredGrid(x, y, z)        
        PV_central_polydata = GlobalMesh.glyph(geom=PV_block_polydata, factor=1)        
        PV_central_polydata = PV_central_polydata.rotate_z(-self.azimut)
        
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
                                                 .rotate_z(-self.azimut),'PV')
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
            
            plotter.add_mesh(grnd, color='green', opacity=0.5)

            labels = dict(zlabel='Z (ZENITH)', xlabel='X (EAST)',
                          ylabel='Y (NORTH)')
            plotter.add_axes(**labels)
            
            light = pyV.Light()
            light.set_direction_angle(30, 45)    
            plotter.add_light(light)
            
            #plotter.set_background(color='#A6D0DE')
            
            plotter.show()
            
        return PV_central_polydata, PV_central_multiblock
            
    def get_tiltY_along_time(self, sun_vect):
                    
        sun_vect_central_coord = self.get_sun_vect_in_central_coord(sun_vect)
        true_tracking_angle = self.get_true_tracking_angle(sun_vect_central_coord)
        backT_corr_angle = self.get_backT_corr_angle(true_tracking_angle)
        tiltY_corrected = self.get_corrected_tracking_angle(true_tracking_angle,
                                                             backT_corr_angle)
        tiltY_limited = self.get_limitated_angle(tiltY_corrected)
        self.tiltY_along_time = tiltY_limited*180/np.pi
        
    def get_sun_vect_in_central_coord(self, sun_vect):
        # Do not take into account the slope of the area and the slope of the 
        # rotation axis (see the previous framework to complete)
        sun_vect_CC = np.zeros((len(sun_vect[:,0]),3))
            
        sun_vect_CC[:,0] = sun_vect[:,0]*np.cos(self.azimut)\
            - sun_vect[:,1]*np.sin(self.azimut)
                                                     
        sun_vect_CC[:,1] = sun_vect[:,0]*np.sin(self.azimut)\
            + sun_vect[:,1]*np.cos(self.azimut)
                                                       
        sun_vect_CC[:,2] = sun_vect[:,2]
        
        return sun_vect_CC
    
    
    def get_true_tracking_angle(self, sun_v_central_coord):
                    
        true_tracking_angle = np.arctan2(sun_v_central_coord[:,0],
                                         sun_v_central_coord[:,2])
            
        return true_tracking_angle
        
    def get_backT_corr_angle(self, true_angle):
        
        value = np.abs(np.cos(true_angle)/self.GCR_x)
           
        backT_corr_angle = np.zeros((len(true_angle)))
        backT_corr_angle[value>=1] = 0
        backT_corr_angle[value<1] = (-np.sign(true_angle[value<1])
                                     *np.arccos((np.abs(np.cos(true_angle[value<1])))/
                                                         self.GCR_x))
            
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
        
        
