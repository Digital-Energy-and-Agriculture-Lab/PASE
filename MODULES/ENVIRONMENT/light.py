#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 31 09:30:10 2023

@author: roxane
"""

import numpy as np
import pandas as pd
import pyvista as pyV
import pvlib.solarposition as pvlibSP
import matplotlib.pyplot as plt

def fibonacci_half_sphere( samples=18):
    
    phi = np.pi * (3. - np.sqrt(5.))
    i = np.linspace(0,samples-1,num=samples)
    yp = (1 - i/float(samples-1))
    radius = np.sqrt(1-yp**2) 
    theta = phi * i 
    xp = np.cos(theta) * radius
    zp = np.sin(theta) * radius
    return np.column_stack([xp,zp,yp])


class Sun_positions:
    
    def __init__(self, lat, long, freq_deter):
        
        self.lat = lat
        self.long = long
        self.get_solar_positions(freq_deter)
        
    def get_solar_positions(self, freq_deter):
        
        if (freq_deter == 8760 or freq_deter == 8784):
            frq = '1H'
            n = 1
        elif (freq_deter == 35040 or freq_deter == 35136):
            frq = '15min'
            n = 4
        elif (freq_deter == 52560 or freq_deter == 52704):
            frq = '10min'
            n = 6
            
        self.SD_leap_year(frq, n)
        self.SD_nonleap_year(frq, n)
            
    def SD_leap_year(self, frq, n):
            
        index_leap_year = pd.date_range(start='2008-01-01 00:00', freq=frq, 
                                       periods=366*24*n)        
        self.sp_leapY = pvlibSP.get_solarposition(index_leap_year, 
                                                  self.lat, 
                                                  self.long)
        
        self.sun_vect_leapY = self.get_sun_vector(self.sp_leapY['elevation'], 
                                                  self.sp_leapY['azimuth'])
        
        self.top_atm_rad_leapY = self.get_top_of_atm_radiation(index_leap_year,
                                                               n)
        
    def SD_nonleap_year(self, frq, n):
        
        index_com_year = pd.date_range(start='2005-01-01 00:00', freq=frq, 
                                       periods=365*24*n)       
        self.sp_nonleapY = pvlibSP.get_solarposition(index_com_year, 
                                                     self.lat, 
                                                     self.long)
        
        self.sun_vect_nonleapY = self.get_sun_vector(self.sp_nonleapY['elevation'], 
                                                     self.sp_nonleapY['azimuth'])
        
        self.top_atm_rad_nonleapY = self.get_top_of_atm_radiation(index_com_year,
                                                                  n)
        
        
    def get_sun_vector(self, beta, gamma):
        #Vectorial based system = {0,East=X, North=Y, Zenith=Z}
        #beta : sun elevation (from -90 to 90°), negative angle means it's night
        #gamma : azimuth from north to east
        gamma, beta = gamma*np.pi/180, beta*np.pi/180
        solar_vector = np.zeros((len(gamma),3))
        solar_vector[:,0]=np.sin(gamma)*np.cos(beta)
        solar_vector[:,1]=np.cos(gamma)*np.cos(beta)
        solar_vector[:,2]=np.sin(beta)
        #SOURCE : Kevin Anderson and Mark Mikofski, Slope-Aware Backtracking for Single-Axis Trackers, NREL
        return solar_vector
        
    def get_top_of_atm_radiation(self, index, n):
        
        day_of_year = np.array(index.dayofyear)
        n_days_in_year = day_of_year[len(index)-1]
        solar_declination = self.get_solar_declination(day_of_year)
        solar_hour_angle = self.get_solar_hour_angle(day_of_year, index)
        
        lat_rad = self.lat*np.pi/180
        solar_cst = 1367
        top_of_atm_radiation = solar_cst*(np.ones(len(index)) +
                                0.033*np.cos((360*day_of_year/n_days_in_year)*np.pi/180))* \
                                (np.cos(lat_rad)*np.cos(solar_declination)*
                                np.cos(solar_hour_angle*np.pi/180) +
                                np.sin(lat_rad)*np.sin(solar_declination))
        top_of_atm_radiation[top_of_atm_radiation<0] = 0
        return top_of_atm_radiation
        
    def get_solar_declination(self, day_of_year):
        
        declination = pvlibSP.declination_spencer71(day_of_year)
        
        return declination
    
    def get_solar_hour_angle(self, day_of_year, index):
        
        equation_of_time = pvlibSP.equation_of_time_spencer71(day_of_year)
        solar_hour_angle = pvlibSP.hour_angle(index, self.long, equation_of_time)
        
        return solar_hour_angle
    
    
class Light:

    def __init__(self, WD, SP):
        
        self.data = {}
       
        for year in WD.keys():
            
            GHI = WD[year]['G(h)'].to_numpy()
            
            if int(year)%4 == 0:                
                rad_top_atm = SP.top_atm_rad_leapY
            else:
                rad_top_atm = SP.top_atm_rad_nonleapY
                
            kt = self.get_clearness_sky_index(rad_top_atm, GHI)    
            DHI = self.get_diffuse_horizontal_radiation(kt, GHI)
            BHI = self.get_beam_horizontal_radiation(GHI, DHI)
            Ai = self.get_anisotropy_index(rad_top_atm, BHI)
            f = self.get_modulating_factor(GHI, BHI)
            
            df = pd.DataFrame({'GHI': GHI.tolist(),
                               'BHI': BHI.tolist(),
                               'DHI': DHI.tolist(),
                               'rad_top_atm': rad_top_atm.tolist(),
                               'kt': kt.tolist(),
                               'Ai': Ai.tolist(),
                               'f': f.tolist()}, index=WD[year].index)
            
            self.data[year] = df            
                    
    def get_clearness_sky_index(self, rad_top_atm, GHI):
            
        kt = np.zeros(len(rad_top_atm))    
        kt[rad_top_atm>0] = np.maximum(0.1, np.minimum(GHI[rad_top_atm>0]/rad_top_atm[rad_top_atm>0], 0.9))
        kt[np.where(rad_top_atm<=0)] = 0.1
        
        return kt
    
    def get_diffuse_horizontal_radiation(self, kt, GHI):
        # Erbs et al. correlation (1982), 
        #source : John A. Duffie, William A. Beckman(auth.)- Solar Engineering of Thermal Processes, 
        #Fourth Edition (2013), page 76, equation 2.10.1
        DHI = np.zeros(len(GHI))
        
        ind = np.where(kt<=0.8)
        DHI[ind] = (0.9511*np.ones_like(ind)
                    - 0.1604*kt[ind]
                    + 4.388*kt[ind]**2
                    - 16.638*kt[ind]**3
                    + 12.336*kt[ind]**4)*GHI[ind]
        
        ind = np.where(kt<=0.22)
        DHI[ind] = (np.ones_like(ind) - 0.09*kt[ind])*GHI[ind]

        ind = np.where(kt>0.8)
        DHI[ind] = 0.165*GHI[ind]
        
        return DHI
    
    def get_beam_horizontal_radiation(self, GHI, DHI):
        
        BHI = GHI - DHI
        
        return BHI
    
    def get_anisotropy_index(self, rad_top_atm, BHI):
        #source : John A. Duffie, William A. Beckman(auth.)- Solar Engineering of Thermal Processes, 
        #Fourth Edition (2013), page 92, equation 2.16.3

        Ai = np.zeros(len(rad_top_atm))
        ind = np.where(rad_top_atm!=0)
        Ai[ind] = BHI[ind]/rad_top_atm[ind]
        
        return Ai  
    
    def get_modulating_factor(self, GHI, BHI):
        
        f = np.zeros(len(GHI))
        f[GHI>0] = np.sqrt(BHI[GHI>0]/GHI[GHI>0])
        
        return f
    
        
class Sun_positions_sampled:
    
    def __init__(self, lat, long, precision_lvl, loc_name):
        
        self.lat = lat
        self.long = long
        self.loc_name = loc_name
        self.get_solar_positions_sampled(lat, long, precision_lvl)
        self.get_sun_vector(self.SP['elevation'], self.SP['azimuth'])
        self.get_sun_path_diagram()
        self.get_PVSyst_Plot()
        
    
    def get_solar_positions_sampled(self, lat, long, precision_lvl):
        
        index = pd.date_range(start='2005-01-01 00:00', freq='1H', 
                              periods=365*24)
        
        solar_position = pvlibSP.get_solarposition(index, lat, long)
        
        solar_position['hour'] = index.hour
        solar_position['month'] = index.month//(365/12)
        solar_position['week'] = index.dayofyear//7
        solar_position['doy'] = index.dayofyear
        
        
        if precision_lvl == 1:       
            # Creation of a sampling month variable which is offset by half of 365/12
            # The first created period is removed by removing negative value
            solar_position['monthS'] = (index.dayofyear-365/12/2)//30.4
            solar_position = solar_position.loc[solar_position['monthS']>0,:]
            SP_month = solar_position.drop_duplicates(subset = ['monthS','hour'],keep = 'first').drop(columns = ["monthS"])
            self.SP = SP_month[SP_month['elevation']>=0]
            self.SP = self.SP.set_index('week', append=True)
            self.SP = self.SP.set_index('hour', append=True)

        elif precision_lvl == 2:  
            # Creation of a sampling week variable which is offset by half of 365/12
            # The first created period is removed by removing negative value
            solar_position['weekS'] = (index.dayofyear-3.5)//7
            solar_position.weekS[solar_position.weekS==-1] = 52
            #solar_position = solar_position.loc[solar_position['weekS']>0,:]
            SP_week = solar_position.drop_duplicates(subset = ['weekS','hour'],keep = 'first') #.drop(columns = ["weekS"])
            self.SP = SP_week[SP_week['elevation']>=0]
            self.SP = self.SP.set_index('month', append=True)
            self.SP = self.SP.set_index('hour', append=True)

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
                            s=2, label=None, c=self.SP.doy.round(0))
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
            solpos = pvlibSP.get_solarposition(times, 
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
        
    def get_PVSyst_Plot(self):
        
        fig, ax = plt.subplots()
        points = ax.scatter(self.SP.azimuth, self.SP.apparent_elevation, s=2,
                    c=self.SP.doy.round(0), label=None)
        fig.colorbar(points)
        
        SP_june = self.SP.query("month == 6")
        
        for h in np.unique(SP_june.hour):
            # choose label position by the largest elevation for each hour
            subset = SP_june.loc[SP_june['hour'] == h]
            height = subset.apparent_elevation
            pos = subset.loc[height.idxmax(),:]
            ax.text(pos['azimuth'], pos['apparent_elevation'], str(h))

        for date in pd.to_datetime(['2019-03-21', '2019-06-21', '2019-09-21','2019-12-21']):
            times = pd.date_range(date, date+pd.Timedelta('24h'), freq='5min')
            solpos = pvlibSP.get_solarposition(times, 
                                               self.lat,
                                               self.long)
            solpos = solpos.loc[solpos['apparent_elevation'] > 0, :]
            label = date.strftime('%Y-%m-%d')
            ax.plot(solpos.azimuth, solpos.apparent_elevation, label=label)

        ax.figure.legend(loc='upper left')
        ax.set_xlabel('Solar Azimuth (degrees)')
        ax.set_ylabel('Solar Elevation (degrees)')

        plt.show()
        fig.savefig('OUTPUTS/GRAPHS/PVSystDiagram_'+self.loc_name+'.svg')
        



class Light_shade_scene:
    
    #The class light shade scene init with a geometry (pyvista.polydata) and a meshgrid instance
    def __init__(self,meshgrid,geometry):
        self.meshgrid = meshgrid
        self.geometry = geometry
        
    def get_light_map(self, n_small_suns, sun_P):
        
        if type(self.geometry) == list:
            sv = np.zeros((1,3))
            self.dir_map = np.zeros((len(self.meshgrid.X[0,:]),
                                     len(self.meshgrid.X[:,0]),
                                     len(sun_P[:,0])))
            self.diff_map = np.zeros((len(self.meshgrid.X[0,:]),
                                     len(self.meshgrid.X[:,0]),
                                     len(sun_P[:,0])))
            
            for time in range(len(sun_P[:,0])):
                print(time)
                geometry = self.geometry[time]
                diff_map = self.diffuse_map(n_small_suns, geometry)
                sv[0,:] = sun_P[time,:]
                dir_map = self.direct_map(geometry, sv)
                self.dir_map[:,:,time] = dir_map[:,:,0]   
                self.diff_map[:,:,time] = diff_map
        else:
            self.diff_map = self.diffuse_map(n_small_suns, self.geometry)
            self.dir_map = self.direct_map(self.geometry, sun_P)
            
    
    def diffuse_map(self, n_small_suns, geometry):
        
        #Get direction of ray to reach the small suns and compute the sky view of each point
        pTarget = fibonacci_half_sphere(n_small_suns)
            
        #Creation of the source points array (Nx3) with N = len(Source) * len(n_small_suns)
        SourcePoints = np.repeat(np.column_stack((self.meshgrid.X.flatten(),
                                                  self.meshgrid.Y.flatten(),
                                                  np.zeros(len(self.meshgrid.X.flatten())))),
                                      n_small_suns,
                                      axis=0)
        
        #Creation of the target points array (Nx3) with N = len(Source) * len(n_small_suns)
        TargetPoints = np.tile(pTarget,[len(self.meshgrid.X.flatten()),1])
        
        #Computation of the ray interception of the N rays
        #id_rays_stopped provided the index of the ray which has been intercepted
        _, id_rays_stopped, _ = geometry.multi_ray_trace(SourcePoints,
                                                         TargetPoints,
                                                         first_point=True,
                                                         retry=False)
        
        #Creation of a vector providing the sourceID from which each ray has been shooted
        
        SourceID = np.repeat(np.linspace(0,
                                         len(self.meshgrid.X.flatten())-1,
                                         len(self.meshgrid.X.flatten())),
                             n_small_suns,
                             axis=0)

        #Touched provide a list with the sourceID of the intercept ray
        #Then the number of time a ray from a position has been intercepted is count
        # and given in the counts variable
        Touched = SourceID[id_rays_stopped]
        unique, counts = np.unique(Touched, return_counts=True)
        
        #Creation of the empty matrix of sky view
        Diffu = np.ones(self.meshgrid.X.shape, dtype=np.float16)

        #Transformation of the 1D index to 2D indexes
        matrix_index = np.unravel_index(unique.astype("int"),Diffu.shape)

        #Computation of the sky view by removing the fraction of intercepted ray at each location
        Diffu[matrix_index] = 1 - counts/n_small_suns
    
        return Diffu.transpose()

    
    def direct_map(self, geometry, sun_P):
    
        #Creation of the source points array (Nx3) with N = len(Source) * len(n_small_suns)
        SourcePoints = np.repeat(np.column_stack((self.meshgrid.X.flatten(),
                                                  self.meshgrid.Y.flatten(),
                                                  np.zeros(len(self.meshgrid.X.flatten())))),
                                      len(sun_P[:,0]),
                                      axis=0)
        #Creation of the target points array (Nx3) with N = len(Source) * len(n_small_suns)
        TargetPoints = np.tile(sun_P,[len(self.meshgrid.X.flatten()),1])
        
        #Computation of the ray interception of the N rays
        #id_rays_stopped provided the index of the ray which has been intercepted
        _, id_rays_stopped, _ = geometry.multi_ray_trace(SourcePoints,
                                                         TargetPoints,
                                                         first_point=True,
                                                         retry=False)
        
        #Creation of the initial direct map based on the shape of sun_Positions
        direct_1D_map = np.ones(len(TargetPoints[:,0]), dtype=np.uint16)
        #Transformation of the 1D index to 3D indexes
    
        #Computation of the shade by setting at 0 the locations where rays were intercepted
        direct_1D_map[id_rays_stopped] = 0
    
        #Reshape of direct map to get a X,Y,t map
        direct_map =  direct_1D_map.reshape(len(self.meshgrid.Y[:,0]),
                                            len(self.meshgrid.X[0,:]),
                                            len(sun_P[:,0]))  
        direct_map = np.transpose(direct_map, (1,0,2))
    
        return direct_map


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
        show_edges=False,
        scalar_bar_args={"title": "Rate of residual light [%]"},
        clim=[0, 1])

    plotter.show()