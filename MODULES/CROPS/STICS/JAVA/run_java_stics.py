#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 28 17:13:22 2023

@author: roxane
"""

from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from MODULES.CROPS.STICS.JAVA.generate_java_stics_files import \
    generate_weather_data_file, generate_USMS_file
import os
import subprocess
import platform


def run_independants_usms(WD, daily_irr, scenario_P):
    
    Simu_init = YAML_Inputs_provider('CROPS/STICS/simu_init.yaml').i
    
    WD_files_dict = generate_weather_data_file(WD, daily_irr,
                                               scenario_P['LocationName'])
    
    for year, WD_files_positions in WD_files_dict.items():
        
        if (int(year) == scenario_P['SimulationStartingYear'] 
            and Simu_init['AnnualCropOption'] == 0):                
            pass
        
        else:     
            count = 0                               
            for WD_file in WD_files_positions:
                
                if Simu_init['AnnualCropOption'] == 0:
                    WD_file_previous_year = WD_files_dict[str(int(year)-1)][count]
                else:
                    WD_file_previous_year = WD_file
                
                generate_USMS_file(WD_file, WD_file_previous_year,
                                   Simu_init, year)
                
                count+=1
                
                os.chdir("INPUTS/CROPS/STICS") #Mettre le chemin d'accès avant l'exécutable pour ne pas devoir naviguer dans les dossiers.

                if platform.system() == "Linux" or platform.system() == "Darwin":
                    subprocess.call(["java", "-jar","JavaSticsCmd.exe",
                                     "--run", "param_files", WD_file])
                else : 
                    subprocess.call(["java", "-jar","JavaSticsCmd.exe",
                                     "--run", "param_files", WD_file], shell=True)

                os.chdir("../../..")
                
                """os.chdir("..")
                os.chdir("..")"""