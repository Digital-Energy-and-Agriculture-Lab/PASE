#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 11:49:51 2023

@author: roxane
"""

import yaml

with open (r'PV_central.yaml') as file:
    
    PV_central_yaml = yaml.load(file, Loader=yaml.FullLoader)
    
for data in PV_central_yaml.values():

    print(type(data['Value']))
    print(data['Type'])
    
