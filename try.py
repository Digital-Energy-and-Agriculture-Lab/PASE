#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 15 14:07:41 2023

@author: roxane
"""

from MODULES.DATA_MANAGEMENT.weather_data_provider import Weather_data
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from MODULES.ENVIRONMENT.light import Sun_positions, Light
from MODULES.user_support_tools import PASE_Logger
from MODULES.PHOTOVOLTAICS.photovoltaic_systems import PV_system

PASE_Logger()

Loc_i = YAML_Inputs_provider(file='Wallhausen.yaml').i

PV_i = YAML_Inputs_provider(file='PV_central.yaml').i

WD = Weather_data(Loc_i['Latitude'],
                  Loc_i['Longitude'],
                  Loc_i['SimulationStartingYear'],
                  Loc_i['SimulationEndingYear'],
                  Loc_i['WeatherDataOption'])

Sun_positions = Sun_positions(Loc_i['Latitude'],
                              Loc_i['Longitude'],
                              len(WD.nyears[str(Loc_i['SimulationStartingYear'])]))

Light = Light(WD.nyears, Sun_positions)

PV_central = PV_system(PV_i)

PV_central.get_electricity_production(Sun_positions, Light.data, WD.nyears)

