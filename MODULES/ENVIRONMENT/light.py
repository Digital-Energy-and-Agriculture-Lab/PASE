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
    
    def __init__(self, lat, long, precision_lvl):
        
        self.get_solar_positions(lat, long, precision_lvl)
        self.get_sun_vector(self.SP['elevation'], self.SP['azimuth'])
        
        
    def get_solar_positions(self, lat, long, precision_lvl):
        
        index = pd.date_range(start='2005-01-01 00:00', freq='1H', 
                              periods=365*24)
        
        solar_position = pvlib.solarposition.get_solarposition(index, lat, long)
        
        hour = index.hour
        month = index.month
        week_id = index.weekofyear
        solar_position.insert(0, "hour", hour)
        solar_position.insert(1, "month", month)
        solar_position.insert(2, "week", week_id)
        
        if precision_lvl == 1:
            SP_month = solar_position.groupby(by=['month','hour']).mean()
            self.SP = SP_month[SP_month['elevation']>=0]
        
        elif precision_lvl == 2:
            SP_week = solar_position.groupby(by=['week','hour']).mean()
            self.SP = SP_week[SP_week['elevation']>=0]
            
        else:
            self.SP = solar_position[solar_position['elevation']>=0]
               
         
    def get_sun_vector(self, beta, gamma):
        #Vectorial based system = {0,East=X, North=Y, Zenith=Z}
        #beta : sun elevation (from -90 to 90°), negative angle means it's night
        #gamma : azimuth from north to east
        gamma, beta = gamma*np.pi/180, beta*np.pi/180
        self.solar_vector = np.zeros((len(gamma),3))
        self.solar_vector[:,0]=np.sin(gamma)*np.cos(beta)
        self.solar_vector[:,1]=np.cos(gamma)*np.cos(beta)
        self.solar_vector[:,2]=np.sin(beta)
        #SOURCE : Kevin Anderson and Mark Mikofski, Slope-Aware Backtracking for Single-Axis Trackers, NREL

        
        
class Shade_direct_light:

    def __init__(self, meshgrid, PV_central, sun_P):
        
        self.SourcePoints = np.repeat(np.column_stack((meshgrid.X.flatten(),
                                                  meshgrid.Y.flatten(),
                                                  np.zeros(len(meshgrid.X.flatten())))),
                                      len(sun_P),
                                      axis=0)
        
        self.TargetPoints = np.tile(sun_P,[len(meshgrid.X.flatten()),1])
        
        self.n_rays = len(self.TargetPoints[:,0])
        self.ID_rays = np.arange(0, self.n_rays, 1)
        self.n_cells = len(meshgrid.X.flatten())
        self.n_sun_P = len(sun_P[:,0])
        
        _, id_rays_stopped, _ = PV_central.multi_ray_trace(self.SourcePoints,
                                                           self.TargetPoints,
                                                           first_point=False,
                                                           retry=False)
        
        self.shade_matrix_for_each_time(id_rays_stopped, meshgrid)
        
        
    def shade_matrix_for_each_time(self, id_rays_stp, meshgrid):
        
        bool_vector = np.ones(self.n_rays)       
        bool_vector[id_rays_stp] = 0
        
        self.direct_map_t = np.zeros((self.n_sun_P, len(meshgrid.Y[0,:]), len(meshgrid.X[:,0])))
        
        for s in range(self.n_sun_P):
            
            print(s)
            
            direct_map = np.where((self.ID_rays-np.ones(len(self.ID_rays))*s)%self.n_sun_P==0,
                                   bool_vector,
                                   3)
            direct_map = direct_map[direct_map!=3]            
            direct_map = direct_map.reshape(len(meshgrid.X[:,0]),len(meshgrid.Y[0,:])).transpose()
                       
            self.direct_map_t[s,:,:] = direct_map


            
class Sky_view_factor:
    
    def __init__(self, meshgrid, PV_central):
        
        n_small_suns = 108
        pTarget = self.fibonacci_half_sphere(n_small_suns)
            
        
        SourcePoints = np.repeat(np.column_stack((meshgrid.X.flatten(),
                                                  meshgrid.Y.flatten(),
                                                  np.zeros(len(meshgrid.X.flatten())))),
                                      n_small_suns,
                                      axis=0)
        
        TargetPoints = np.tile(pTarget,[len(meshgrid.X.flatten()),1])
        
        SourceID = np.repeat(np.linspace(0,
                                         len(meshgrid.X.flatten())-1,
                                         len(meshgrid.X.flatten())),
                             n_small_suns,
                             axis=0)
    
        _, id_rays_stopped, _ = PV_central.multi_ray_trace(SourcePoints,
                                                           TargetPoints,
                                                           first_point=True,
                                                           retry=False)
        
        self.sky_view_matrix(n_small_suns, SourceID, id_rays_stopped, meshgrid)
        
        
    def fibonacci_half_sphere(self, samples=18):
        
        phi = np.pi * (3. - np.sqrt(5.))
        i = np.linspace(0,samples-1,num=samples)
        yp = (1 - i/float(samples-1))
        radius = np.sqrt(1-yp**2) 
        theta = phi * i 
        xp = np.cos(theta) * radius
        zp = np.sin(theta) * radius
        return np.column_stack([xp,zp,yp])
    
    
    def sky_view_matrix(self, n_suns, sourcesID, ID_rays_Stp, meshgrid):
        
        Diffu = np.ones(len(meshgrid.X.flatten()))

        Touched = sourcesID[ID_rays_Stp]
        unique, counts = np.unique(Touched, return_counts=True)

        #Computation of a 1D vector giving the diffuse light
        Diffu[unique.astype("int")] = 1 - counts/n_suns
        self.diffuse_map_t = Diffu.reshape(len(meshgrid.X[:,0]),len(meshgrid.Y[0,:])).transpose()
            

        