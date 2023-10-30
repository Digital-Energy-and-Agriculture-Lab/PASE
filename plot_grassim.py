# -*- coding: utf-8 -*-
"""
Created on Mon Oct 30 13:34:51 2023

@author: lloui
"""

import pickle
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt

with open('OUTPUTS\\GRASSIM\\Crop_plot.pkl', 'rb') as handle:
    Crop_plot = pickle.load(handle)
    
data = Crop_plot.nyears_data['2005']

    
def plot_variable(data_variable, start=0, end=365):
    
    list_of_arrays = []
    for key in data_variable:
        list_of_arrays.append(data_variable[key])
        
    vmin, vmax = np.min(list_of_arrays[start:end]), np.max(list_of_arrays[start:end])
    
    levels = np.linspace(vmin,vmax,100)
    
    for i in range(start, end):
        print(i)
        contour = plt.contourf(list_of_arrays[i], levels=levels, vmin=vmin, vmax=vmax, extend='min')
        colorbar = plt.colorbar(contour)
    
        plt.axis('scaled')
        plt.show()
    
plot_variable(data['BMDV']) 
