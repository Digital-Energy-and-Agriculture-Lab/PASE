#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  8 15:26:36 2023

@author: roxane
"""

from cal_rnet import net_radiation_calculation

def tcult_calculation(Wstion, Crop, Agromngmt, Soil, tmin, tmax, tmoy):
    
    sigma = 5.67*10**-8
       
    ### AJOUTER condition si on tient compte d'une culture sous abri (caltcult.f90, ligne 130)
    """if Agromngmt.codabri == 2:
        tcult = tmoy
        tcultmin = tmin
        tcultmax = tmax
        return"""
      
#    et = eptcult + esol + Emd + Emulch


    tcult = tmoy
    tcultmin = tmin
    tcultmax = tmax
    
    Niter = 0
    
    while Niter <= 5:
        
        if Crop.codebeso == 1: # P_codebeso to 1 means crop coefficient method is used for water requirements (2 for resistive methode, S&W)
        
            net_radiation_calculation()
        
        Niter+=1
        