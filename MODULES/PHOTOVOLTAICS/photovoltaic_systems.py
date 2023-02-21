#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 16 08:09:49 2023

@author: roxane
"""

import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as R

class PV_system:
    
    def __init__(self, inputs):
        
        self.bifaciality = inputs['Bifaciality']
        self.bifaciality_factor = inputs['Bifaciality_factor']
        self.tilt_nonleapY = np.ones(8760)*inputs['TiltY']
        self.tilt_leapY = np.ones(8784)*inputs['TiltY']
        self.azimut = inputs['CentralAzimut']
        panel_peak_power = inputs['Panel_Peak_Power']
        self.panel_area = inputs['PanelDimensionX']*inputs['PanelDimensionY']
        self.panel_efficiency = panel_peak_power/(self.panel_area*1000)
        self.n_panels = (inputs['NumberOfPanelsX']*inputs['NumberOfPanelsY']*
                         inputs['NumberOfPVBlocksX']*inputs['NumberOfPVBlocksY'])
        
        self.n_rot_axis = inputs['RotationAxisNumber']
        self.tiltY = inputs['TiltY']
        
        #Temporary line
        self.slope_in_rot_axis_direction = 0
        self.soil_angle = 0
        self.block_dim_x = (inputs['RepetitionDistanceOfPanelsX']*inputs['NumberOfPanelsX']
                            -inputs['RepetitionDistanceOfPanelsX']
                            +inputs['PanelDimensionX'])
        
        self.block_space_x = inputs['RepetitionDistanceOfPVBlocksX']
        
        self.GCR_x = (inputs['PanelDimensionX']*inputs['NumberOfPanelsX']/
                      self.block_space_x)
            
    
    def get_electricity_production(self, SP, light, WD):
        
        self.production = {}
        
        for year in light.keys():
            
            if int(year)%4 == 0:
                sun_vect = SP.sun_vect_leapY
                app_zenith = SP.sp_leapY['apparent_zenith'].to_numpy()
                
            else:
                sun_vect = SP.sun_vect_nonleapY
                app_zenith = SP.sp_nonleapY['apparent_zenith'].to_numpy()
            
            self.get_tiltY_and_shade_factor_along_time(sun_vect)
            
            #Temporary lines
            GHI_reaching_ground = light[year]['GHI'].to_numpy()*0.5
            albedo = 0.25  #should be a vector with the albedo of the crop evolving on the year
            
            GTI_front, GTI_rear = self.get_GTI(sun_vect, app_zenith, 
                                               light[year], GHI_reaching_ground,
                                               albedo)
            
            ws = WD[year]['WS10m'].to_numpy()
            amb_temp = WD[year]['T2m'].to_numpy()
            
            panels_temp = self.get_panels_temperature(ws, amb_temp,
                                                      GTI_front+GTI_rear)
            
            self.get_power_production(panels_temp, GTI_front, GTI_rear)
            
            df = pd.DataFrame({'GTI_f': GTI_front.tolist(),
                               'GTI_r': GTI_rear.tolist(),
                               'panels_T': panels_temp.tolist(),
                               'SF_f': self.SF_front.tolist(),
                               'SF_r': self.SF_rear.tolist(),   
                               'front_P_panel': self.front_power_panel.tolist(),
                               'rear_P_panel': self.rear_power_panel.tolist(),
                               'P_central': self.power_central.tolist()}, 
                               index=WD[year].index)
            
            self.production[year] = df 

            
    def get_power_production(self, panels_T, GTI_front, GTI_rear, alpha=-0.4, T_std=25):
        
        one = np.ones((len(panels_T)))
        
        self.front_power_panel = (self.panel_efficiency*GTI_front
                                  *(1+((alpha/100)*(panels_T-T_std*one)))
                                  *self.panel_area) # W
        
        self.rear_power_panel = (self.panel_efficiency*self.bifaciality_factor
                                 *GTI_rear
                                 *(1+((alpha/100)*(panels_T-T_std*one)))
                                 *self.panel_area) # W
                                   
        self.power_central = ((self.front_power_panel + self.rear_power_panel)
                              *self.n_panels*(10**-6))  # MW        
            
                
    def get_GTI(self, sun_vect, app_zenith, light, GHI_reaching_ground,
                albedo):
        
        self.cos_teta = self.get_cos_angle_btw_light_and_panels_normal(sun_vect,
                                                                  [0,0,1])
        cos_teta_z = self.get_cos_angle_btw_light_and_zenith(app_zenith)
        
        self.Rb = self.get_ratio_beam_radiation(self.cos_teta, cos_teta_z)
        
        GTI_front = self.compute_global_tilted_irradiance(self.Rb,
                                                          GHI_reaching_ground,
                                                          albedo,
                                                          light['BHI'].to_numpy(),
                                                          light['DHI'].to_numpy(),
                                                          light['Ai'].to_numpy(),
                                                          light['f'].to_numpy())
        
        if self.bifaciality == 1:
            
            self.cos_teta_rear = self.get_cos_angle_btw_light_and_panels_normal(
                sun_vect, [0,0,-1])
            
            self.Rb_rear = self.get_ratio_beam_radiation(self.cos_teta_rear, cos_teta_z)
            
            GTI_rear = self.compute_global_tilted_irradiance(self.Rb_rear,
                                                             GHI_reaching_ground,
                                                             albedo,
                                                             light['BHI'].to_numpy(),
                                                             light['DHI'].to_numpy(),
                                                             light['Ai'].to_numpy(),
                                                             light['f'].to_numpy())
            
        else:
            self.GTI_rear = np.zeros(len(sun_vect))
            
        return GTI_front, GTI_rear
            
            
    def compute_global_tilted_irradiance(self, Rb, GHI_ground, albedo, BHI,
                                         DHI, Ai, f):
        
        one = np.ones((len(Ai)))
        zero_vector = np.zeros((len(Ai)))
        
        tilt = self.tiltY*np.pi/180
        
        #temporaire
        shade_factor_front = zero_vector
        
        direct_component = (BHI + DHI*Ai)*Rb*(one - shade_factor_front)
        
        diffuse_component = (DHI*(one - Ai)*((one + np.cos(tilt))/2)
                                  *(one + f*(np.sin(tilt/2))**3))    
        
        reflected_component = (GHI_ground*albedo*(one-np.cos(tilt))/2)   
        
        GTI = direct_component + diffuse_component + reflected_component
        
        return GTI
    
             
    def get_cos_angle_btw_light_and_panels_normal(self, sun_vect, 
                                                  init_panel_normal):    
        
        rot_axis_init = np.array([[0,1,0]])*np.ones((len(sun_vect),1))
        panels_normal_init = np.array((init_panel_normal))
        zenith = np.array([[0,0,1]])
        panels_tilt_rad = np.zeros((len(sun_vect[:,0]),1))
        panels_tilt_rad[:,0] = self.tiltY*np.pi/180
        rotation_vector1 = panels_tilt_rad*rot_axis_init
        rotation_vector2 = -self.azimut*zenith
        rotation1 = R.from_rotvec(rotation_vector1)
        rotation2 = R.from_rotvec(rotation_vector2)
        panels_normal = rotation2.apply(rotation1.apply(panels_normal_init))
        cos_teta = np.sum(panels_normal*sun_vect, axis=1) #panels_normal and sun_vect are normed vectors
        
        return cos_teta
    
    def get_cos_angle_btw_light_and_zenith(self, app_zenith):
        
        cos_teta_z = np.cos(app_zenith*np.pi/180)
        
        return cos_teta_z
    
    def get_ratio_beam_radiation(self, cos_teta, cos_teta_z):
        #source : John A. Duffie, William A. Beckman(auth.)- Solar Engineering of Thermal Processes, 
        #Fourth Edition (2013), page 23, equation 1.8.1
        Rb = cos_teta/cos_teta_z
        ind1 = np.where(cos_teta<=0)
        Rb[ind1] = 0
        ind2 = np.where(cos_teta_z<=0)
        Rb[ind2] = 0
        Rb[Rb>25] = 25
        
        return Rb

        
    def get_panels_temperature(self, WS, T, tot_GTI):
        
        #Source : Thermal lost in PVsyst (https://www.pvsyst.com/help/thermal_loss.htm)
        
        Uc = 25 # [W/m².K] 
        Uv = 1.2  # [(W/(m².K))/(m/s)]
        alpha = 0.9  # absorption coefficient
        U = Uc*np.ones((len(WS))) + Uv*WS
        
        panels_temp = T + 1/U*(alpha*tot_GTI*(1-self.panel_efficiency))
        
        return panels_temp
    
    
    def get_tiltY_and_shade_factor_along_time(self, sun_vect):
        
        if self.n_rot_axis == 0:
            
            self.tiltY = self.tiltY*np.ones((len(sun_vect[:,0])))             
            sun_vect_central_coord = self.get_sun_vect_in_central_coord(sun_vect)
            self.get_shading_factor(sun_vect_central_coord)
                        
        elif self.n_rot_axis == 1:
            
            sun_vect_central_coord = self.get_sun_vect_in_central_coord(sun_vect)
            true_tracking_angle = self.get_true_tracking_angle(sun_vect_central_coord)
            backT_corr_angle = self.get_backT_corr_angle(true_tracking_angle)
            tiltY_corrected = self.get_corrected_tracking_angle(true_tracking_angle,
                                                                 backT_corr_angle)
            tiltY_limited = self.get_limitated_angle(tiltY_corrected)
            self.tiltY = tiltY_limited*180/np.pi
            self.get_shading_factor(sun_vect_central_coord)
            
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
        
        one = np.ones((len(true_angle)))
        soil_angle = self.soil_angle*one
        value = np.abs((np.cos(true_angle-self.soil_angle))/
                                   (self.GCR_x*np.cos(self.soil_angle)))  
           
        backT_corr_angle = np.zeros((len(true_angle)))
        backT_corr_angle[value>=1] = 0
        backT_corr_angle[value<1] = -np.sign(true_angle[value<1])*np.arccos(
                                                         (np.abs(np.cos(true_angle[value<1]-soil_angle[value<1])))/
                                                         (self.GCR_x*np.cos(soil_angle[value<1])))
            
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

    def get_shading_factor(self, sun_vect_cc):
        
        # Teta_r is the sun elevation in the plane perpendicular to the 
        # rotation axis of the blocks of panels
        
        # Don't take into account the possibility to have an area with a slope 
        # perpendicular to the rotation axis or a slope of the rotation axis
        
        teta_r_front = np.arctan(sun_vect_cc[:,2]/sun_vect_cc[:,0])
        teta_r_front[sun_vect_cc[:,2]<0] = 'NaN'
        teta_r_front[sun_vect_cc[:,0]<0] = 'NaN'
        
        teta_r_rear = - np.arctan(sun_vect_cc[:,2]/sun_vect_cc[:,0])
        teta_r_rear[sun_vect_cc[:,2]<0] = 'NaN'
        teta_r_rear[sun_vect_cc[:,0]>0] = 'NaN'
                       
        one = np.ones((len(self.tiltY)))
            
        delta_H_h_l = (np.sin(self.tiltY)*self.block_dim_x)                    # Height difference between highest point of one panel and the lowest point of the panel just next to it
        delta_L_h_l_front = (self.block_space_x*one)-(np.cos(self.tiltY)*
                                                      self.block_dim_x)        # Distance between the highest point of one panel and the lowest point of the panel just next to it
        delta_L_h_l_rear = (self.block_space_x*one)+(np.cos(self.tiltY)*
                                                      self.block_dim_x)
        
        sun_elev_treshold_front = np.arctan(delta_H_h_l/delta_L_h_l_front)     # Sun elevation at which shade factor reaches 0, which is the min value of shade factor
        sun_elev_treshold_rear = np.arctan(delta_H_h_l/delta_L_h_l_rear)
            
        shade_factor_max = one                                                 # Max value of the shade factor
            
        m_front = -shade_factor_max/sun_elev_treshold_front                    # Angular coefficient of the linear equation
        m_rear = -shade_factor_max/sun_elev_treshold_rear
            
        p = shade_factor_max                                                   # y-intercept
            
        self.SF_front = m_front*teta_r_front + p                               # Linear equation
        self.SF_rear = m_rear*teta_r_rear + p
                
        self.SF_front[np.isnan(teta_r_front)] = 1                              # When sun elevation is < 0 or the sun on the other side of the panel face ==> SF = 1
        self.SF_rear[np.isnan(teta_r_rear)] = 1
        
        self.SF_front[np.where(teta_r_front>sun_elev_treshold_front)] = 0      # When sun elevation is > treshold, then the SF is nul
        self.SF_rear[np.where(teta_r_rear>sun_elev_treshold_rear)] = 0  
         
        