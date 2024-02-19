#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 16 18:02:05 2024

@author: roxane
"""

import numpy as np

class Crop:
    
    def __init__(self):
        
        self.nyears_data = {}
        
    def initiate_one_year_variables(self, n_positions):
        
        self.dict_variables_one_year = {}
        self.np_fresh_yield = np.zeros(n_positions)
        self.np_dry_yield = np.zeros(n_positions)
        self.np_total_ET = np.zeros(n_positions)
        
    def fill_np_variables_for_each_position(self, position, fresh_yield, dry_yield,
                                            total_ET):
        
        self.np_fresh_yield[position] = fresh_yield
        self.np_dry_yield[position] = dry_yield
        self.np_total_ET[position] = total_ET
        
    def fill_dict_variables_for_each_year(self, year):
        
        self.dict_variables_one_year['Fresh_yield'] = self.np_fresh_yield
        self.dict_variables_one_year['Dry_yield'] = self.np_dry_yield
        self.dict_variables_one_year['Total_ET'] = self.np_total_ET
        
        self.nyears_data[year] = self.dict_variables_one_year