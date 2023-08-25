#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug  9 14:22:40 2023

@author: roxane
"""

import numpy as np

def net_radiation_calculation(Soil, Wstion, Crop, Agromngmt, Gen, hur, couvermulchres, lai):
    
    albsol = Soil.albedo*(1 - (0.517*(hur(1)-Soil.HMINF[0])/(Soil.HCCF[0]-Soil.HMINF[0])))   # eq 9.15
    albsolhum = 0.483*Soil.albedo
    
    if albsol < albsolhum:
        albsol = albsolhum
    if albsol > Soil.albedo:
        albsol = Soil.albedo
    
    if Gen.codetypres < 11: #Residues type put on the surface of the soil and therefore modifying the albedo
        albsol = albsol*(1 - couvermulchres)\
            + Gen.albedomulchresidus*couvermulchres
    
    if Agromngmt.codepaillage == 2: #Plastic mulch on the surface of the soil
        albsol = albsol*(1 - Agromngmt.couvermulchplastique) \
            + Agromngmt.albedomulchplastique*Agromngmt.couvermulchplastique
            
    if Crop.codelaitr == 1:
        albedolai =  Wstion.albveg - (Wstion.albveg - albsol) * np.exp(-0.75 * lai)