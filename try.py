#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 15 14:07:41 2023

@author: roxane
"""

from MODULES.DATA_MANAGEMENT.weather_data_provider import Weather_data
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from MODULES.ENVIRONMENT.light import Sun_positions
from MODULES.user_support_tools import PASE_Logger

PASE_Logger()

Loc_1 = YAML_Inputs_provider(file='Wallhausen.yaml').i

PV_1 = YAML_Inputs_provider(file='PV_central.yaml').i

WD = Weather_data(Loc_1['Latitude'],
                  Loc_1['Longitude'],
                  Loc_1['SimulationStartingYear'],
                  Loc_1['SimulationEndingYear'],
                  Loc_1['WeatherDataOption'])

Sun_positions = Sun_positions(Loc_1['Latitude'],
                              Loc_1['Longitude'],
                              len(WD.nyears[str(Loc_1['SimulationStartingYear'])]))

