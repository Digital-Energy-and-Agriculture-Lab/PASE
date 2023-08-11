#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug  9 14:22:40 2023

@author: roxane
"""

def net_radiation_calculation(Soil, Wstion, Crop, Agromngmt, Gen, hur, couvermulchres):
    
    albsol = Soil.albedo*(1 - (0.517*(hur(1)-Soil.HMINF[0])/(Soil.HCCF[0]-Soil.HMINF[0])))   # eq 9.15
    
    if Gen.codetypres < 11:
        albsol = albsol*(1 - couvermulchres)\
            + Gen.albedomulchresidus*couvermulchres
    
    if Agromngmt.codepaillage == 2:
        albsol = albsol*(1 - Agromngmt.couvermulchplastique) \
            + Agromngmt.albedomulchplastique*Agromngmt.couvermulchplastique
             