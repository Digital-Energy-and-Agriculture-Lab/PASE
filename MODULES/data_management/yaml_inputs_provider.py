#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 11:49:51 2023

@author: roxane
"""

import yaml
import os
from MODULES.user_support_tools import PASE_Logger


def error_message(var_name=None, var_type=None, var_limit=None):
   
    if var_type is not None:        
        message = 'Input "' + var_name + '" value should be a ' + str(var_type)        
    else:        
        message = 'Input "' + var_name + '" value is outside the limits: ' + str(var_limit)
        
    print(message)

#os.chdir('..')
#os.chdir('..')

#print(os.getcwd())





class YAML_Inputs_provider:
    
    def __init__(self, file=None, path='INPUTS/'):
        
        with open (path+file, 'r') as file:
            
            inputs = yaml.load(file, Loader=yaml.FullLoader)
            
        inputs_dict = {}
   
        for key, data in inputs.items():   

    
            if ((data['Type'] == 'float') and (data['Value'] is not list)):
        
                    if (type(data['Value']) is not int) and (type(data['Value']) is not float):           
                        self.error_message(key, data['Type'])
                        PASE_Logger(self.msg, 'ERROR')
                    else:
                        inputs_dict[key] = data['Value']
            
                    if ((type(data['Limit'][0]) is str) and (type(data['Limit'][1]) is str)):
                        if ((data['Value']<inputs[data['Limit'][0]]['Value']) or 
                            (data['Value']>inputs[data['Limit'][1]]['Value'])):               
                            self.error_message(key, None, data['Limit'])
                            PASE_Logger(self.msg, 'ERROR')
                        else:
                            inputs_dict[key] = data['Value']
        
                    elif ((type(data['Limit'][0]) is str) and (type(data['Limit'][1]) is not str)):
                        if ((data['Value']<inputs[data['Limit'][0]]['Value']) or (data['Value']>data['Limit'][1])):                
                            self.error_message(key, None, data['Limit'])
                            PASE_Logger(self.msg, 'ERROR')
                        else:
                            inputs_dict[key] = data['Value']
                
                    elif ((type(data['Limit'][0]) is not str) and (type(data['Limit'][1]) is str)):
                        if ((data['Value']<data['Limit'][0]) or (data['Value']>inputs[data['Limit'][1]]['Value'])):               
                            self.error_message(key, None, data['Limit'])
                            PASE_Logger(self.msg, 'ERROR')
                        else:
                            inputs_dict[key] = data['Value']
            
                    else:
                        if ((data['Value'] > float(data['Limit'][1])) or (data['Value'] < float(data['Limit'][0]))):
                            self.error_message(key, None, data['Limit'])
                            PASE_Logger(self.msg, 'ERROR')
                        else:
                            inputs_dict[key] = data['Value']
                            
        self.inputs = inputs_dict                           
                
            
    def error_message(self, var_name=None, var_type=None, var_limit=None):
       
        if var_type is not None:        
            self.msg = 'Input "' + var_name + '" value should be a ' + str(var_type)        
        else:        
            self.msg = 'Input "' + var_name + '" value is outside the limits: ' + str(var_limit)



            

    

