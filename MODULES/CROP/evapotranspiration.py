#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 24 16:27:39 2023

@author: roxane
"""

import numpy as np


def ET0_FAO56_PM(altitude, latitude, daily_WD, daily_rad_in, ws_crop):
    """
    Function to compute the daily reference evapotranspiration [mm]. All the equations
    are from the chapter 3 of the book (Allen. R, Pereira. L et al.,1998), link above.

    Ref : Crop evapotranspiration - Guidelines for computing crop water requirements - FAO Irrigation and drainage paper 56" (Allen. R, Pereira. L et al.,1998)

    Parameters
    ----------
    altitude : float, default None
        Altitude of the location [m]
    latitude : float, default None
        Latitude of the location [°]
    min_temp : float, default None
        Daily minimal temperature [°C]
    max_temp : float, default None
        Daily maximal temperature [°C]
    avg_T : float, default None
        Daily average temperature [°C]
    min_RH : float, default None
        Daily minimal relative humidity [-]
    max_RH : float, default None
        Daily maximal relative humidity [-]
    ws_crop : float, default None
        Daily average wind speed at crop height [m/s]
    daily_rad_in : float, default None
        Daily radiation [MJ/m²]
    day_of_the_year : int, default None
        Number of days from 1st January to the current day
    CropLAI : float, default None
        Ratio between total leaf surface and total surface
    crop_albedo : float, default None
        Reflexion coefficient of the crop
    soil_albedo : float, default None
        Reflexion coefficient of the soil

    Returns
    -------
    ET0 : float
        Daily reference evapotranspiration [mm]
        
    """

    specific_heat = 1.013*10**-3 # [MJ.kg-1.°C-1]
    latent_heat_vaporization = 2.45  # [MJ.kg-1]
    ratio_molecul_weight_watervap_dryair = 0.622  # [-]
    solar_constant = 0.0820 # [MJ.m-2min-1]
    stefan_boltzmann_constant = 4.903*10**-9
    soil_heat_flux_density = 0                # negligable for daily calculations (see Woli et al, 2012, chap 3)

    #if self.cropLAI < 3:
    #    albedo = ((self.cropLAI/3)*self.crop_albedo + (1-(self.cropLAI/3))*self.soil_albedo)
    #else:
    #    albedo = self.crop_albedo
    
    albedo = 0.23
    
    avg_T = daily_WD['Avg_temp'].to_numpy().reshape(356,1)
    min_temp = daily_WD['Min_temp'].to_numpy().reshape(356,1)
    max_temp = daily_WD['Max_temp'].to_numpy().reshape(356,1)
    min_RH = daily_WD['Min_RH'].to_numpy().reshape(356,1)
    max_RH = daily_WD['Max_RH'].to_numpy().reshape(356,1)
    vap_press = daily_WD['Vap_press'].to_numpy().reshape(356,1)
       
    one = np.ones((365,1))
    
    day_of_the_year = np.arange(0,365,1).reshape(356,1)+one
    n_days_in_year = len(day_of_the_year)
    
    if min_RH[0,0] is not 'nan':
        actual_vap_pressure = ((0.6108*np.exp((17.27*min_temp)/(min_temp+237.3*one))
                                *(max_RH/100))
                               +(0.6108*np.exp((17.27*max_temp)/(max_temp+237.3*one))
                                 *(min_RH/100)))/2
    else:
        actual_vap_pressure = vap_press/10
    

    avg_T_K = avg_T+273.16*one
    max_temp_K = max_temp+273.16*one
    min_temp_K = min_temp+273.16*one

    # Computation of all the data needed to compute reference evapotranspiration (ETo) (link in first doc string)

    slope_vap_pressure_curve = ((4098*0.6108*np.exp((17.27*avg_T)/(avg_T+237.3*one)))
                                /(avg_T+237.3*one)**2)

    atmospheric_pressure = 101.3*((293-0.0065*altitude)/293)**5.26
    psychometric_constant = ((specific_heat*atmospheric_pressure)
                             /(latent_heat_vaporization*ratio_molecul_weight_watervap_dryair))

    mean_sat_vap_pressure = (0.6108*(np.exp((17.27*max_temp)/(max_temp+237.3*one))
                                     +np.exp((17.27*min_temp)/(min_temp+237.3*one))))/2
    
    diff_vap_press = mean_sat_vap_pressure-actual_vap_pressure    
    ind = np.where(diff_vap_press<0)
    diff_vap_press[ind] = 0           #https://hal.inrae.fr/hal-02593413/document,
                                      #chap 3.3.6, Seuillage des différents termes de l'ET0

    inverse_rel_dist_earth_sun = one+(0.033*np.cos((2*np.pi*day_of_the_year)/n_days_in_year))
    solar_decination = 0.409*np.sin(((2*np.pi*day_of_the_year)/n_days_in_year)-1.39*one)
    sunset_hour_angle = np.arccos(-np.tan(latitude*(np.pi/180))*np.tan(solar_decination))  # !!!! correcte de laisser la latitude comme ça ?

    extraterre_radiation = (((24*60)/np.pi)*solar_constant*inverse_rel_dist_earth_sun
                            *(sunset_hour_angle*np.sin(latitude*(np.pi/180))*np.sin(solar_decination)
                              +np.cos(latitude*(np.pi/180))*np.cos(solar_decination)*np.sin(sunset_hour_angle)))

    clear_sky_solar_radiation = (0.75 + 2*10**-5*altitude)*extraterre_radiation
    
    ## RESTART HERE !!!!
    
    relative_shortwave_radiation = self.resid_GHI_2D/clear_sky_solar_radiation

    net_longwave_radiation_out = stefan_boltzmann_constant*(((max_temp_K**4)+(min_temp_K**4))/2)*(0.34-0.14*math.sqrt(actual_vap_pressure))*(1.35*relative_shortwave_radiation)
    net_shortwave_radiation_in = (1-albedo)*self.resid_GHI_2D
    net_radiation_in = net_shortwave_radiation_in-net_longwave_radiation_out
    
    self.one_matrix = np.ones((len(self.resid_GHI_2D[:,0]),len(self.resid_GHI_2D[0,:])))
    self.zero_matrix = np.zeros((len(self.resid_GHI_2D[:,0]),len(self.resid_GHI_2D[0,:])))

    # Computation of reference evapotranspiration (ETo)
    ET0 = ((0.408*slope_vap_pressure_curve*(net_radiation_in-self.zero_matrix))/
             (slope_vap_pressure_curve+(psychometric_constant*(1+0.34*self.ws_crop))))\
          +(((psychometric_constant*(900/avg_T_K)*self.ws_crop*(diff_vap_press))/
             (slope_vap_pressure_curve+(psychometric_constant*(1+0.34*self.ws_crop))))*self.one_matrix)    
    
    ind = np.where(ET0<0)
    ET0[ind] = 0     # if net_radiation_in is negative or first term of Penman < second term
                     #https://hal.inrae.fr/hal-02593413/document, chap 3.3.6, Seuillage des différents termes de l'ET0
                     # In north hemisphere, net radiation in negative in winter (https://earthobservatory.nasa.gov/global-maps/CERES_NETFLUX_M#:~:text=Earth's%20net%20radiation%2C%20sometimes%20called,the%20top%20of%20the%20atmosphere.&text=Places%20where%20more%20energy%20was,negative%20net%20radiation)%20are%20purple.)
    return ET0

    # These climatic methods to calculate ETo were all calibrated for ten-day or monthly calculations, 
    # not for daily or hourly calculations ==> problem of negative values. 
    # (<http://www.fao.org/3/x0490e/x0490e07.htm#latent%20heat%20of%20vaporization%20(l)>.)        