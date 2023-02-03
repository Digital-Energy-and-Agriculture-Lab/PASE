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
import matplotlib.pyplot as plt


class Sun_positions:
    
    def __init__(self, lat, long, precision_lvl, loc_name):
        
        self.lat = lat
        self.long = long
        self.loc_name = loc_name
        self.get_solar_positions(lat, long, precision_lvl)
        self.get_sun_vector(self.SP['elevation'], self.SP['azimuth'])
        self.get_sun_path_diagram()
        
        
    def get_solar_positions(self, lat, long, precision_lvl):
        
        index = pd.date_range(start='2005-01-01 00:00', freq='1H', 
                              periods=365*24)
        
        solar_position = pvlib.solarposition.get_solarposition(index, lat, long)
        
        hour = index.hour
        month = index.month
        week_id = index.weekofyear
        julian_day = index.dayofyear
        
        solar_position.insert(0, "hour", hour)
        solar_position.insert(1, "J_day", julian_day)
        solar_position.insert(2, "month", month)
        solar_position.insert(3, "week", week_id)
        
        if precision_lvl == 1:           
            SP_month = solar_position.groupby(by=['month','hour']).mean()
            self.SP = SP_month[SP_month['elevation']>=0]
            self.SP = self.SP.set_index('week', append=True)
        
        elif precision_lvl == 2:  
            SP_week = solar_position.groupby(by=['week','hour']).mean()
            self.SP = SP_week[SP_week['elevation']>=0]
            self.SP = self.SP.set_index('month', append=True)
                        
        else:
            self.SP = solar_position[solar_position['elevation']>=0]
            self.SP = self.SP.set_index('month', append=True)
            self.SP = self.SP.set_index('hour', append=True)
            self.SP = self.SP.set_index('week', append=True)
            
               
         
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
        
    def get_sun_path_diagram(self):
        
        #SOURCE : https://pvlib-python.readthedocs.io/en/stable/gallery/solar-position/plot_sunpath_diagrams.html#sphx-glr-gallery-solar-position-plot-sunpath-diagrams-py
        
        fig = plt.figure()        
        ax = plt.subplot(1, 1, 1, projection='polar')
        points = ax.scatter(np.radians(self.SP.azimuth), self.SP.apparent_zenith,
                            s=2, label=None, c=self.SP.J_day.round(0))
        ax.figure.colorbar(points)

        self.SP = self.SP.reset_index(level='hour')

        # draw hour labels
        SP_june = self.SP.query("month == 6")
        for h in np.unique(SP_june.hour):
            # choose label position by the smallest radius for each hour
            subset = SP_june.loc[SP_june['hour'] == h]
            r = subset.apparent_zenith
            pos = subset.loc[r.idxmin(),:]
            ax.text(np.radians(pos['azimuth']), pos['apparent_zenith'], str(h))
         
        # draw individual days
        for date in pd.to_datetime(['2019-03-21', '2019-06-21', '2019-12-21']):
            times = pd.date_range(date, date+pd.Timedelta('24h'), freq='5min')
            solpos = pvlib.solarposition.get_solarposition(times, 
                                                           self.lat,
                                                           self.long)
            solpos = solpos.loc[solpos['apparent_elevation'] > 0, :]
            label = date.strftime('%Y-%m-%d')
            ax.plot(np.radians(solpos.azimuth), solpos.apparent_zenith, label=label)

        ax.figure.legend(loc='upper left')

        # change coordinates to be like a compass
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_rmax(90)

        fig.savefig('OUTPUTS/GRAPHS/SunPathDiagram_'+self.loc_name+'.svg')
        
    
       
        
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
        
        direct_1D_map = np.ones(len(self.TargetPoints[:,0].flatten()))
    
    
        direct_1D_map[id_rays_stp] = 0
    
        direct_map =  direct_1D_map.reshape(len(meshgrid.Y[:,0]),
                                            len(meshgrid.X[0,:]),
                                            self.n_sun_P)  
        direct_map = np.transpose(direct_map, (1,0,2))
        self.direct_map_t = direct_map


            
class Sky_view_factor:
    
    def __init__(self, meshgrid, PV_central, n_small_suns):
        
        
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
            

def show_light_map(light_matrix, msh_grid, PV_central):
    
    grid = pyV.StructuredGrid(msh_grid.X, msh_grid.Y, np.ones((len(msh_grid.X[:,0]),len(msh_grid.X[0,:])))*0.05)

    test1 = light_matrix.ravel()

    plotter = pyV.Plotter()

    plotter.add_mesh(PV_central, color='black')
    ground = np.array([[-100, 100, 0],
                       [100, 100, 0],
                       [-100, -100, 0],
                       [100, -100, 0]])

    ground_m = np.hstack([[3, 0, 1, 2],    
                          [3, 1, 2, 3],])

    grnd = pyV.PolyData(ground, ground_m)

    plotter.add_mesh(grnd, color='green')
    plotter.show_axes()

    plotter.add_mesh(
        grid,
        scalars=test1,
        lighting=False,
        show_edges=True,
        scalar_bar_args={"title": "Height"},
        clim=[0, 1])

    plotter.show()