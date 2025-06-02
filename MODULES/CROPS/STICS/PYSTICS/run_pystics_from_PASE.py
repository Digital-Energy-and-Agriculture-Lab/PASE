#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2025 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from MODULES.CROPS.STICS.generate_java_stics_files import \
    generate_weather_data_file, generate_USMS_file
from MODULES.CROPS.STICS.get_java_stics_outputs import Crop_outputs
import os
import subprocess
import platform
import pandas as pd
import numpy as np


def run_independant_usms_in_pystics(config, WD, daily_irr, scenario_P):
    
    Simu_init = YAML_Inputs_provider(f"CROPS/pySTICS/{config['SimuInit']}").inputs
    
    WD_files_dict = generate_weather_data_file(WD, daily_irr,
                                               scenario_P['LocationName'],
                                               'MODULES/CROPS/STICS/PYSTICS/pySTICS/pystics/parametrization_files/example/')
    
    Crop_plot = Crop_outputs()
    
    for year, WD_files_positions in WD_files_dict.items():
        
        n_positions = len(daily_irr[str(scenario_P['SimulationStartingYear'])][:,0])
        Crop_plot.initiate_one_year_variables(n_positions)        
        
        if (int(year) == scenario_P['SimulationStartingYear'] 
            and Simu_init['AnnualCropOption'] == 0):         # If bisannual crop and first year of simulation, crop development can not be computed as it was sown on the previous year
            pass
        
        else:                 
            
            count = 0                               
            for WD_file in WD_files_positions:
                
                if Simu_init['AnnualCropOption'] == 0:
                    WD_file_previous_year = WD_files_dict[str(int(year)-1)][count]
                else:
                    WD_file_previous_year = WD_file
                
                # Write the usms file containing this unit of simulation (for one position of one year)
                generate_USMS_file(WD_file, WD_file_previous_year,
                                   Simu_init, year, 'MODULES/CROPS/STICS/PYSTICS/pySTICS/pystics/parametrization_files/example/')
                
                os.chdir("MODULES/CROPS/STICS/PYSTICS/pySTICS")
                
                from pystics.params import parametrization_from_stics_example_files
                from pystics.simulation import run_pystics_simulation
                
                # Read input files from pystics/parametrization_files/example folder for the USM associated to chosen species and variety
                weather, crop, manage, soil, station, constants, initial = parametrization_from_stics_example_files(WD_file, Simu_init['Variety'])
                
                # Run the simulation
                pystics_df, pystics_mat_list = run_pystics_simulation(weather, crop, soil, constants, manage, station, initial)
                
                
                """
                daily_results_stics = pd.read_csv('param_files/mod_s'+WD_file+'.sti', sep=';', decimal='.')
                daily_results_stics['jul_day'] = daily_results_stics['jul']
                nd_year = max(daily_results_stics['ian'])
                st_year = min(daily_results_stics['ian'])
                if st_year%4==0:
                    supp_day = 1
                else:
                    supp_day = 0
                    
                if Simu_init['AnnualCropOption'] == 0:
                    daily_results_stics.loc[daily_results_stics['ian']
                                                   ==nd_year, 'jul_day'] = (daily_results_stics.loc[daily_results_stics['ian']==nd_year, 'jul_day'] 
                                                                                         + 365 + supp_day)
                else:
                    pass
                harvest_jul_day = max(daily_results_stics['irecs'])
                sowing_jul_day = min(daily_results_stics['iplts'])

                daily_results_stics = daily_results_stics.set_index('jul_day')

                Fresh_yield = float(daily_results_stics.loc[daily_results_stics.index==harvest_jul_day, 'pdsfruitfrais'])
                H2Ocontent_fruit = float(daily_results_stics.loc[daily_results_stics.index==harvest_jul_day, 'H2Orec'])
                Dry_yield = float(daily_results_stics.loc[daily_results_stics.index==harvest_jul_day, 'mafruit'])
                Total_ET = sum(daily_results_stics.loc[(daily_results_stics.index<=harvest_jul_day) & 
                                                       (daily_results_stics.index>=sowing_jul_day), 'et'])
                
                Crop_plot.fill_np_variables_for_each_position(count, Fresh_yield,
                                                              Dry_yield, Total_ET)
                
                count+=1
                
            Crop_plot.fill_dict_variables_for_each_year(year)
            """
                os.chdir("../../../../..")
                
    return Crop_plot
        
