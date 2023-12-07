# -*- coding: utf-8 -*-
"""
Created on Mon Oct 30 16:27:04 2023

@author: lloui
"""

import pandas as pd

def weather_data_topandas(filename):
    

    weather = pd.read_csv(filename, header=0, sep=";", decimal='.')
    weather = weather.rename(columns={'PRECIPITATION':'Rain', 'TEMPERATURE_AVG':'Avg_temp'})
    weather = weather[weather['DAY'] != '29/02/2016']
    weather['DAY'] = pd.to_datetime(weather['DAY'], format='%d/%m/%Y') + pd.DateOffset(years=-11)
    weather = weather.set_index(weather['DAY'])
    
    #Cheating here for now, so we can use 2005 irrandiance data
    WD = {'2005':weather}
    
    
    return WD