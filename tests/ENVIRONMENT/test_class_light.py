#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 23 11:20:22 2025

@author: roxane
"""

import numpy as np
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from pase.DATA_MANAGEMENT.weather_data_provider import Weather_data
from pase.ENVIRONMENT.light import Sun_positions, Light


Loc_1 = YAML_Inputs_provider(file='Siguesol_loc.yaml', subpath='SCENARIOS').inputs
WD = Weather_data(Loc_1['Latitude'],
                  Loc_1['Longitude'],
                  Loc_1['SimulationStartingYear'],
                  Loc_1['SimulationEndingYear'],
                  Loc_1['WeatherDataOption'],
                  Loc_1['WeatherFileName'],
                  Loc_1['DailyWeatherFileName'])
Sun_positions_complete = Sun_positions(Loc_1['Latitude'],
                                       Loc_1['Longitude'],
                                       len(WD.nyears_data[str(Loc_1['SimulationStartingYear'])]),
                                       Loc_1['TimeZone'])

light_test = Light(WD.nyears_data, Sun_positions_complete)


def test_get_anisotropy_index():
    
    rad_top_atm = np.array([0, 0, 0, 52.01, 215.54, 453.69, 273.43, 127.08, 0, 0, 0])
    BHI = np.array([0, 0, 0, 1.123, 1.18, 138.43, 250.21, 126.54, 0, 0, 0])
        
    assert (light_test.get_anisotropy_index(rad_top_atm, BHI) == np.array([0, 0, 0, 1.123/52.01, 1.18/215.54, 138.43/453.69, 250.21/273.43, 126.54/127.08, 0, 0, 0])).all()