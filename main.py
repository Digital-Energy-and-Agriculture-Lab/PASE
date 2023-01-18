#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 17 16:06:55 2023

@author: roxane
"""

from MODULES.user_support_tools import PASE_Logger
from MODULES.data_management.yaml_inputs_provider import YAML_Inputs_provider



PASE_Logger()

Loc_1 = YAML_Inputs_provider(file='Wallhaussen.yaml')

PV_1 = YAML_Inputs_provider(file='PV_central.yaml')

print(PV_1.i)
