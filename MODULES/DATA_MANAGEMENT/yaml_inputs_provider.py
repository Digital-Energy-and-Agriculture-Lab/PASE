#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 11:49:51 2023

@author: Roxane Bruhwyler
"""

import yaml
import os
from MODULES.user_support_tools import PASE_Logger


class YAML_Inputs_provider:
    
    def __init__(self, file=None, path='INPUTS/'):
        
        with open (path+file, 'r') as inputs_file:
            
            inputs = yaml.load(inputs_file, Loader=yaml.FullLoader)
            
        self.i = {}
   
        for key, data in inputs.items():   

            if data['Value'] is not list:
                if data['Type'] == 'float':
                    self.check_value_float(key, data, inputs)
            
                elif data['Type'] == 'integer':
                    self.check_value_int(key, data, inputs)
                
                elif data['Type'] == 'string':
                    self.check_value_str(key, data, inputs)
                    
                elif data['Type'] == 'boolean':
                    self.check_value_bool(key, data, inputs)
        
        PASE_Logger('Input values from '+file+' have been imported successfully', 'INFO')

                
            
    def error_message(self, var_name=None, var_type=None, var_limit=None):
       
        if var_type is not None:        
            self.msg = 'Input "' + var_name + '" value should be a ' + str(var_type)        
        else:        
            self.msg = 'Input "' + var_name + '" value is outside the limits: ' + str(var_limit)
            
    
    def check_value_float(self, key, data, inputs):
        
        if (type(data['Value']) is not int) and (type(data['Value']) is not float):           
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.i[key] = data['Value']
            
        self.check_limits(key, data, inputs)
                
                
    def check_value_int(self, key, data, inputs):
        
        if type(data['Value']) is not int:           
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.i[key] = data['Value']
            
        self.check_limits(key, data, inputs)        


    def check_value_str(self, key, data, inputs):
            
        if type(data['Value']) is not str:           
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.i[key] = data['Value']    
            

    def check_value_bool(self, key, data, inputs):
            
        if type(data['Value']) is not bool:           
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.i[key] = data['Value'] 


    def check_limits(self, key, data, inputs):
        
        ## In the case there is an input paramater that has the upper and lower limits 
        ## that are other inputs value    
        #if ((type(data['Limit'][0]) is str) and (type(data['Limit'][1]) is str)):
        #    if ((data['Value']<inputs[data['Limit'][0]]['Value']) or 
        #        (data['Value']>inputs[data['Limit'][1]]['Value'])):               
        #        self.error_message(key, None, data['Limit'])
        #        PASE_Logger(self.msg, 'ERROR', 'value')
        #    else:
        #        i[key] = data['Value']

        if ((type(data['Limit'][0]) is str) and (type(data['Limit'][1]) is not str)):
            
            if '*' in data['Limit'][0]:
                factors = data['Limit'][0].split('*')
                if (data['Value']<(inputs[factors[0]]['Value']*inputs[factors[1]]['Value']) or
                    data['Value']>data['Limit'][1]):
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.i[key] = data['Value']
                    
            elif '/' in data['Limit'][0]:
                factors = data['Limit'][0].split('*')
                if (data['Value']<(inputs[factors[0]]['Value']/inputs[factors[1]]['Value']) or
                    data['Value']>data['Limit'][1]):
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.i[key] = data['Value']
                
            else:
                if data['Value']<inputs[data['Limit'][0]]['Value'] or data['Value']>data['Limit'][1]:                
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                   self.i[key] = data['Value']
    
        elif ((type(data['Limit'][0]) is not str) and (type(data['Limit'][1]) is str)):
            
            if '*' in data['Limit'][1]:
                factors = data['Limit'][1].split('*')
                if (data['Value']<data['Limit'][0] or
                    data['Value']>(inputs[factors[0]]['Value']*inputs[factors[1]]['Value'])):
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.i[key] = data['Value']
                    
            elif '/' in data['Limit'][1]:
                factors = data['Limit'][1].split('*')
                if (data['Value']<data['Limit'][0] or
                    data['Value']>(inputs[factors[0]]['Value']/inputs[factors[1]]['Value'])):
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.i[key] = data['Value']

            else:
                if ((data['Value']<data['Limit'][0]) or (data['Value']>inputs[data['Limit'][1]]['Value'])):               
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.i[key] = data['Value']
                
        else:
            if ((data['Value'] > float(data['Limit'][1])) or (data['Value'] < float(data['Limit'][0]))):
                self.error_message(key, None, data['Limit'])
                PASE_Logger(self.msg, 'ERROR', 'value')
            else:
                self.i[key] = data['Value']



    

