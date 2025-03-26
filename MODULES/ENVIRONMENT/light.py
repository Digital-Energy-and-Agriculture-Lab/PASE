#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Authors : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com) and Nicolas De Cock (nicolas.decock1@gmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import logging
import numpy as np
import pandas as pd
import pyvista as pyV
import pvlib.solarposition as pvlibSP
import matplotlib.pyplot as plt
import os

import MODULES.conversion_functions as cf
from MODULES.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization
from MODULES.ENVIRONMENT.sky_model import ReinhartSky

logger = logging.getLogger(__name__)

def fibonacci_half_sphere(samples=18):
    """
    Function computing a number of direction sampling a virtual upper half sphere with a center at 0,0,0
    
    Parameters:
        samples (int): Number of directions

    Returns:
       Directions (np.array): Matrix (samples x 3) providing the direction
    """
    phi = np.pi * (3. - np.sqrt(5.))
    i = np.linspace(0,samples-1,num=samples)
    yp = (1 - i/float(samples-1))
    radius = np.sqrt(1-yp**2) 
    theta = phi * i 
    xp = np.cos(theta) * radius
    zp = np.sin(theta) * radius
    return np.column_stack([xp,zp,yp])


class Sun_positions:
    
    def __init__(self, lat, long, freq_deter, TZ):
        
        self.lat = lat
        self.long = long
        self.get_solar_positions(freq_deter, TZ)
        
    def get_solar_positions(self, freq_deter, TZ):
        
        if (freq_deter == 8760 or freq_deter == 8784):
            frq = '1H'
            n = 1
        elif (freq_deter == 35040 or freq_deter == 35136):
            frq = '15min'
            n = 4
        elif (freq_deter == 52560 or freq_deter == 52704):
            frq = '10min'
            n = 6
            
        self.SD_leap_year(frq, n, TZ)
        self.SD_nonleap_year(frq, n, TZ)
            
    def SD_leap_year(self, frq, n, TZ):
            
        index_leap_year = pd.date_range(start='2008-01-01 00:00', freq=frq, 
                                       periods=366*24*n, tz=TZ)        
        self.sp_leapY = pvlibSP.get_solarposition(index_leap_year, 
                                                  self.lat, 
                                                  self.long)
        
        self.sun_vect_leapY = self.get_sun_vector(self.sp_leapY['elevation'], 
                                                  self.sp_leapY['azimuth'])
        
        self.sp_leapY['Top_atm_radiation'] = self.get_top_of_atm_radiation(index_leap_year,
                                                               n)
        
    def SD_nonleap_year(self, frq, n, TZ):
        
        index_com_year = pd.date_range(start='2005-01-01 00:00', freq=frq, 
                                       periods=365*24*n, tz=TZ)       
        self.sp_nonleapY = pvlibSP.get_solarposition(index_com_year, 
                                                     self.lat, 
                                                     self.long)
        
        self.sun_vect_nonleapY = self.get_sun_vector(self.sp_nonleapY['elevation'], 
                                                     self.sp_nonleapY['azimuth'])
        
        self.sp_nonleapY['Top_atm_radiation'] = self.get_top_of_atm_radiation(index_com_year,
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
    def __init__(self, WD, SP, ghi_multiplier=1):
        
        self.data = {}
       
        for year in WD.keys():
            
            GHI = WD[year]['G(h)'].to_numpy() * ghi_multiplier
            
            if int(year)%4 == 0:                
                rad_top_atm = SP.sp_leapY['Top_atm_radiation'].to_numpy()
            else:
                rad_top_atm = SP.sp_nonleapY['Top_atm_radiation'].to_numpy()
                
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
    
    def __init__(self, lat, long, precision_lvl, loc_name, freq_deter, TZ):
        
        self.lat = lat
        self.long = long
        self.loc_name = loc_name
        self.get_solar_positions_sampled(lat, long, precision_lvl, freq_deter, TZ)
        self.get_sun_vector(self.SP['elevation'], self.SP['azimuth'])
        #self.get_sun_path_diagram()
        #self.get_PVSyst_Plot()
   
    def get_solar_positions_sampled(self, lat, long, precision_lvl, freq_deter, TZ):
        """
        Private method, used to compute the sun positions at an hourly or 1/4 hourly frequence
        for each day (precision = 3), one day per week (precision = 2) or one day per month (precision = 1)

        Returns:
           None
       Attribute SP is a dataframe containing the sun positions at the requested sampling
        """
        if (freq_deter == 8760 or freq_deter == 8784):
            frq = '1H'
            n = 1
        elif (freq_deter == 35040 or freq_deter == 35136):
            frq = '15min'
            n = 4
        elif (freq_deter == 52560 or freq_deter == 52704):
            n = 6
            frq = '10min'
        #Query of the sun positions parameters from pvlib
        index = pd.date_range(start='2005-01-01 00:00', freq=frq, 
                              periods=365*24*n, tz=TZ)
        solar_position = pvlibSP.get_solarposition(index, lat, long)
        
        #Sampling based on required precision level
        if precision_lvl == 1:
            
            SP = solar_position.loc[solar_position.index.day==15]
            
        elif precision_lvl == 2:
            
            SP = solar_position.loc[solar_position.index.day_of_week==3]
            
        else:
            
            SP = solar_position
        #Positions when the sun elevation is below the horizon are discarded to save computation ressources    
        self.SP = SP.loc[SP['elevation']>=0]
        
                
   
            
               
         
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

        fig.savefig(os.path.join('OUTPUTS', 'GRAPHS', 'SunPathDiagram_'+self.loc_name+'.svg'))

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
        fig.savefig(os.path.join('OUTPUTS', 'GRAPHS', 'PVSystDiagram_'+self.loc_name+'.svg'))




class Ray_casting_scene:
    '''
    Class Light_shade_scene
    
    This class compute the diffuse and direct light using ray casting.
    The ray casting requires point sources from which the ray are casted and direction  
    towards the ray are casted. The point sources are provided by the "Mesh" class.
    For diffuse light, the directions are compute within the class, whilst for direct light
    the directions require the position of the sun which is an input of the class.
    
    
    The class is initiate with a mesh containing the source points and a geometry
    '''
    #The class light shade scene init with a geometry (pyvista.polydata) and a mesh instance
    def __init__(self,mesh,geometry):
        self.mesh = mesh
        self.sourcepoints = self.mesh.get_sourcepoints()
        self.geometry = geometry
        self.n_sourcepoints = self.sourcepoints.shape[0]
        self.sources_flag_dict = mesh.get_sources_flag_dict()
        
        
    def get_light_maps(self, sun_P, scheme='Reinhart', MF=1, n_small_suns=180, visualization=False, Sun_P_map_to_visualize=None):
    
        if type(self.geometry) == list:
            sv = np.zeros((1,3))
            self.dir_map = np.zeros((len(self.sourcepoints),len(sun_P[:,0])))
            self.diff_map = np.zeros((len(self.sourcepoints),len(sun_P[:,0])))
            
            for time in range(len(sun_P[:,0])):
                print(time)
                geometry = self.geometry[time]
                difff_map = self.diffuse_map(geometry,
                                             scheme=scheme,
                                             MF=MF,
                                             n_small_suns=n_small_suns)
                sv[0,:] = sun_P[time,:]
                dirrr_map = self.direct_map(sv, geometry)
                self.dir_map[:,time] = dirrr_map 
                self.diff_map[:,time] = difff_map
        else:
            self.diff_map = self.diffuse_map(self.geometry,
                                             scheme=scheme,
                                             MF=MF,
                                             n_small_suns=n_small_suns)
            self.dir_map = self.direct_map(sun_P, self.geometry)
            
            
        if visualization == True:
            self.visualize_direct_light_map(Sun_P_map_to_visualize)
            self.visualize_diffuse_light_map(Sun_P_map_to_visualize)
        else:
            pass
        

    def self_intercept(self,SourcePoints,intercept_points,id_rays_stopped,tol = 0.01):
        """
        Private method, used to discard auto-intercept of rays. This can happend when a mesh has been
        done on a geometry (e.g. on a top of a PV). The ray can be intercept nearly at his starting position
        
        Parameters:
            SourcePoints (np.ndarray n x 3): Coordinates of the source points
            intercept_points (np.ndarray n x 3): Coordinates of the interception points
            id_rays_stopped  (list of int): List containing the mapping 
                                            between the source points and the interception points
            tol (float): maximal distance below which an interception is discarded

        Returns:
           cleaned id_rays_stopped list where the auto-interception have been removed
        """
        
        delta = np.linalg.norm(intercept_points - SourcePoints[id_rays_stopped,:], axis=1)
        return np.unique(id_rays_stopped[delta>tol])
        
 
    def diffuse_map(self, geometry, scheme='Reinhart', MF=1, n_small_suns=180):
        """
        Public method, compute the diffuse light at the point sources defined in the input mesh using
         the approximation of a isotropic half sphere sky. 
         The method uses the mesh and the geometry set at the initialization of the instance
        
        Parameters:
            n_small_suns (int): number of sources consider in the sky for the diffuse light computation
            higher number will provide a better accuracy but heavier computation

        Returns:
           Diffu (np.array 1 x n):  Providing a vector with the fraction ([0-1]) of diffuse light 
                                   for each of the "n" source points defined in the mesh
        """
      
    
        #Get direction of ray to reach the small suns and compute the sky view of each point
        if scheme.lower() == 'reinhart':
            sky = ReinhartSky(MF=MF)
            pTarget = np.column_stack([sky.reinhart_patches.x,
                                       sky.reinhart_patches.y,
                                       sky.reinhart_patches.z])
            n_small_suns = len(sky.reinhart_patches)
        elif scheme.lower() == 'fibonacci':
            pTarget = fibonacci_half_sphere(n_small_suns)
        else:
            raise NotImplementedError('Unrecognized sky discretization scheme')
        
        
        #Creation of the source points array (Nx3) with N = len(Source) * len(n_small_suns)
        SourcePoints = np.repeat(np.column_stack((
                                                  self.sourcepoints[:,0],
                                                  self.sourcepoints[:,1],
                                                  self.sourcepoints[:,2]
                                                 )),
                                      n_small_suns,
                                      axis=0)
        
        #Creation of the target points array (Nx3) with N = len(Source) * len(n_small_suns)
        TargetPoints = np.tile(pTarget,[self.n_sourcepoints,1])
        
        #Computation of the ray interception of the N rays
        #id_rays_stopped provided the index of the ray which has been intercepted
        intercept_points, id_rays_stopped, _ = geometry.multi_ray_trace(SourcePoints,
                                                         TargetPoints,
                                                         first_point=False,
                                                         retry=False)
        
        id_rays_stopped_filtred = self.self_intercept(SourcePoints,intercept_points,id_rays_stopped,tol = 0.01)
        
        
        #Creation of a vector providing the sourceID from which each ray has been shooted
        
        SourceID = np.repeat(np.linspace(0,
                                         self.n_sourcepoints-1,
                                         self.n_sourcepoints),
                             n_small_suns,
                             axis=0)
        
        #Touched provide a list with the sourceID of the intercept ray
        #Then the number of time a ray from a position has been intercepted is counted
        # and given in the counts variable
        Touched = SourceID[id_rays_stopped_filtred]
        unique, counts = np.unique(Touched, return_counts=True)

        # Compute the cos(zenith angle) of all the small suns for the normalization
        _, _zenith_angle_all = cf.get_zenith_angle_from_cart(TargetPoints)
        _cos_zenith_angle_all = np.cos(_zenith_angle_all).reshape(self.n_sourcepoints, n_small_suns)

        # Compute the cos(zenith angle) of the small suns that do NOT contribute to the diffuse map
        # (i.e. rays that were intercepted)

        _mask = np.ones(_cos_zenith_angle_all.size, bool)
        _mask[id_rays_stopped_filtred] = 0
        _cos_zenith_angle_blocked = _cos_zenith_angle_all.copy()
        _mask = _mask.reshape(self.n_sourcepoints, n_small_suns)
        _cos_zenith_angle_blocked[_mask] = 0

        #Creation of the empty matrix of sky view
        Diffu = np.ones(self.n_sourcepoints, dtype=np.float16)

        #Computation of the sky view by removing the fraction of intercepted ray at each location
        Diffu[unique.astype("int")] = 1 - np.sum(_cos_zenith_angle_blocked[unique.astype("int"), :], axis=1)/np.sum(_cos_zenith_angle_all[unique.astype("int"), :], axis=1)

        return Diffu

    def get_direct_map_by_flag(self,Flags):
        """
        Public method, filter the computed Direct_Map based on flags
        
        Parameters:
            Flags (list of str): flag used to filter the direct_map
    
        Returns:
           direct_t_map (np.array t x n):  Providing a matrix of boolean (0/1) for each source points (n) and each
                                           sun positions (t). If the point does not directly see the sun a value of 0 is given.
        """

        Index = self.mesh.get_source_points_index(Flags)
        return self.dir_map[Index,:]
    
    def get_diffuse_map_by_flag(self,Flags):
        """
        Public method, filter the computed Diffuse_Map based on flags
        
        
        Parameters:
            Flags (list of str): flag used to filter the diffuse_map

        Returns:
           Diffu (np.array 1 x n):  Providing a vector with the fraction ([0-1]) of diffuse light 
                                   for each of the "n" source points defined in the mesh
        """
        
        Index = self.mesh.get_source_points_index(Flags)
        return self.diff_map[Index]
    
    
    def get_irradiation_map_by_flag(self,Flags):
        """
        Public method, filter the computed Diffuse_Map based on flags
        
        
        Parameters:
            Flags (list of str): flag used to filter the diffuse_map

        Returns:
            Diffu (np.array 1 x n):  Providing a vector with the fraction ([0-1]) of diffuse light 
                                    for each of the "n" source points defined in the mesh
        """
        
        Index = self.mesh.get_source_points_index(Flags)
        return {y:self.daily_irr_spat[y][:,Index] for y in self.daily_irr_spat}
    
    def direct_map(self, sun_P, geometry):
        """
        Public method, compute the direct light at the point sources defined in the input mesh for
         the positions provide in the sun_P input.
         The method uses the mesh and the geometry set at the initialization of the instance
        
        
        Parameters:
            sun_P (int): sun positions

        Returns:
           direct_ID_t_map (np.array n x t):  Providing a matrix of boolean (0/1) for each source points (n) and each
                                           sun positions (t). If the point does not directly see the sun a value of 0 is given.
        """
        #Creation of the source points array (Nx3) with N = len(Source) * len(sun_positions)
        SourcePoints = np.repeat(np.column_stack((
                                                  self.sourcepoints[:,0],
                                                  self.sourcepoints[:,1],
                                                  self.sourcepoints[:,2]
                                                 )),
                                      len(sun_P[:,0]),
                                      axis=0)
        
        #Creation of the target points array (Nx3) with N = len(Source) * len(sun_positions)
        TargetPoints = np.tile(sun_P,[self.n_sourcepoints,1])
        
        #Computation of the ray interception of the N rays
        #id_rays_stopped provided the index of the ray which has been intercepted
        intercept_points, id_rays_stopped, _ = geometry.multi_ray_trace(SourcePoints,
                                                         TargetPoints,
                                                         first_point=False,
                                                         retry=False)
        
        #Creation of the initial direct map based on the shape of sun_Positions
        direct_1D_map = np.ones(len(TargetPoints[:,0]), dtype=np.uint16)
        
        if len(intercept_points)==0:
            pass
        else:
            id_rays_stopped_filtred = self.self_intercept(SourcePoints,intercept_points,id_rays_stopped,tol = 0.01)
            #Computation of the shade by setting at 0 the locations where rays were intercepted
            direct_1D_map[id_rays_stopped_filtred] = 0
        
        
    
        
        if type(self.geometry) != list:
        #Reshape of direct map to get a ID,t map
            direct_ID_t_map =  direct_1D_map.reshape(self.n_sourcepoints,
                                                     len(sun_P[:,0]))
        else:
            direct_ID_t_map = direct_1D_map
    
        return direct_ID_t_map
    
       
    
    def get_daily_irradiation_map(self, SP_sampled, light_data, visualization=False, year=None, julian_day=None):
        """
        Public method, compute the daily diffuse direct and total irradiation for each location of the input mesh.
        The results are written as an attribute of the class instance
        
        Parameters:
            SP_sampled (df): dataframe with sun positions
            light_data (df): dataframe with meterological data
            visualization (bool): boolean True/False to activate/desactivate the automatic visualization of results
            year (int): year on which visualizing the results of daily irradiation
            julian_day (int): julian day on which visualizing the daily irradiation map

        Returns:
           None
        """
        
        self.daily_irr_spat = {}
        self.daily_dir_irr_spat = {}
        self.daily_diff_irr_spat = {}
        
        
        #initialisation des différents dataframes utilisés
        #df1 contient les données lié aux positions du soleil utilisé pour les cartes d'ombrage
        #df2 et df3 contiennent les données météos

        #df_1 = SP_sampled.tz_convert('Etc/GMT+0').reset_index()
        dfShade = SP_sampled.tz_localize(None).reset_index()
        dfShade['doy'] = dfShade['index'].dt.dayofyear
        dfShade['RefDate'] = pd.to_datetime(dfShade['index'].dt.date)
 #       dfShade['hour'] = dfShade['index'].dt.hour
        dfShade['second'] = pd.to_timedelta(dfShade['index'].dt.time.astype(str)).dt.total_seconds()
 #       dfShade['RefHour'] = dfShade['hour'] 
        dfShade['RefSecond'] = dfShade['second'] 

        for year in light_data: 
            
            freq_deter = len(light_data[year]['GHI'])
            if (freq_deter == 8760 or freq_deter == 8784):
                n = 1
            elif (freq_deter == 35040 or freq_deter == 35136):
                n = 4
            elif (freq_deter == 52560 or freq_deter == 52704):
                n = 6
                
  
            #dfWeather = light_data[year].tz_localize('Etc/GMT+0').reset_index()
            dfWeather = light_data[year].tz_localize(None).reset_index()
            dfWeather['doy'] = dfWeather['index'].dt.dayofyear
     #       dfWeather['hour'] = dfWeather['index'].dt.hour
            dfWeather['second'] = pd.to_timedelta(dfWeather['index'].dt.time.astype(str)).dt.total_seconds()

            # Jointure entre les données météos et les données d'ombrage en vue de déterminée la date/index liée aux données d'ombrage
            #la plus proche pour chaque donnée météo
            dfWeatherMerged = pd.merge_asof(dfWeather,dfShade[['RefDate','doy']],on=['doy'],direction='nearest',suffixes=('_x','_y')).sort_values('second')
            irradianceMap_direct = {}
            irradianceMap_diffus = {}
            
            # Boucle sur les n jours de l'annee afin de calculer l'irradiation journaliere
            doy = dfWeatherMerged['index'].dt.dayofyear.unique()
            doy.sort()
            for day in doy:
                
                #Creation de sous dataframe comprenant les donnees du jour numero "doy"
                sublight_df = dfWeatherMerged.loc[dfWeatherMerged['index'].dt.dayofyear==day,:]
                df_subShade = dfShade.loc[sublight_df['RefDate'].unique()[0]==dfShade['RefDate']]
                df_subShade_merged = df_subShade.join(sublight_df[['second','BHI','GHI','DHI']].set_index('second'),on='second',how='left',rsuffix='_',lsuffix="__")
                
                #df_subShade_merged = df_subShade.join(sublight_df[['hour','BHI','GHI','DHI']].set_index('hour'),on='hour',how='left',rsuffix='_',lsuffix="__")
                #Jointure sur l'instant de la journee la plus proche sur base des secondes écoulées depuis le debut de la journee
                df_subShade_merged = pd.merge_asof(df_subShade,sublight_df[['second','BHI','GHI','DHI','doy']].set_index('second'),on=['second'],direction='nearest',suffixes=('_x','_y')).sort_values('second')

                #Calcul de l'irradiation directe et diffuse dans ce jour et injection de la donnee dans le dictionnaire lie
                irradianceMap_direct[day] = np.sum(self.dir_map[:,list(df_subShade.index)] * df_subShade_merged['BHI'].to_numpy(),axis=1)*10**-6*60*60/n
                if type(self.geometry) != list:
                    irradianceMap_diffus[day] = np.sum(df_subShade_merged['DHI'].to_numpy())*self.diff_map*10**-6*60*60/n
                else:
                    print('day')
                    irradianceMap_diffus[day] = np.sum(df_subShade_merged['DHI'].to_numpy()*self.diff_map[:,list(df_subShade.index)], axis=1)*10**-6*60*60/n
            
            #Conversion des dictionnaires en matrice numpy et ajout dans l attribut ad-hoc
            self.daily_irr_spat[year] = pd.DataFrame.from_dict(irradianceMap_diffus).to_numpy()    + pd.DataFrame.from_dict(irradianceMap_direct).to_numpy() 
            self.daily_dir_irr_spat[year] = pd.DataFrame.from_dict(irradianceMap_direct).to_numpy()    
            self.daily_diff_irr_spat[year] = pd.DataFrame.from_dict(irradianceMap_diffus).to_numpy()
            
            
        if visualization == True:
            self.visualize_daily_irrad_map(year, julian_day)
        else:
            pass
            

    def visualize_direct_light_map(self, Sun_P_map_to_visualize):
        """
        Open the visualization of the direct light map for a specific 
        sun position corresponding to the sun positions sampled vector

        Parameters
        ----------
        Sun_P_map_to_visualize : integer
            id of the sun position in the sun positions sampled vector

        Returns
        -------
        None.

        """
        
        if type(self.geometry) == list:
            geo = self.geometry[Sun_P_map_to_visualize]
        else:
            geo = self.geometry
        
        open_pyvista_3D_visualization(self.sourcepoints[:,:-1], 
                                      self.dir_map[:,Sun_P_map_to_visualize], 
                                      geo,
                                      "Direct map [-]")
        

    def visualize_diffuse_light_map(self, Sun_P_map_to_visualize=None):
        """
        Open the visualization of the diffuse light map for a specific 
        tilt of the PV modules if there is a rotation axis
        (corresponding to a sun position from the sun positions sampled vector)

        Parameters
        ----------
        Sun_P_map_to_visualize : integer
            id of the sun position in the sun positions sampled vector

        Returns
        -------
        None.

        """
        
        if type(self.geometry) == list:
            geo = self.geometry[Sun_P_map_to_visualize]
            diff_map = self.diff_map[:,Sun_P_map_to_visualize]
        else:
            geo = self.geometry
            diff_map = self.diff_map
        
        open_pyvista_3D_visualization(self.sourcepoints[:,:-1], 
                                      np.array(diff_map, dtype=np.float32), 
                                      geo,
                                      "Sky visibility map [-]")

            
    def visualize_daily_irrad_map(self, year, julian_day):
        """
        Open the visualization of the daily irradiation map 
        for a specific year and julian day

        Parameters
        ----------
        year : integer
            year on which to visualize daily irradiation
        julian_day : integer
            julian day on which to visualize daily irradiation

        Returns
        -------
        None.

        """
      
        if type(self.geometry) == list:
            geo = self.geometry[0]
        else:
            geo = self.geometry
        
        open_pyvista_3D_visualization(self.sourcepoints[:,:-1], 
                                      self.daily_irr_spat[str(year)][:,julian_day], 
                                      geo,
                                      "Total irradiation reaching the ground on the julian day "+str(julian_day)+" of "+ str(year) +" [MJ/m²]")

