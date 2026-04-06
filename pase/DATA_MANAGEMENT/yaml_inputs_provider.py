#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import os
import yaml

from pase.user_support_tools import PASE_Logger

VALID_TYPES = ['float', 'integer', 'string', 'boolean', 'list']

class YAML_Inputs_provider:
    
    def __init__(self, file=None, path='INPUTS', subpath=None, parentdir=None):
        if subpath is not None:
            if parentdir is not None:
                fname = os.path.join('..', '..', path, subpath, file)
            else:
                fname = os.path.join(path, subpath, file)
        else:
            if parentdir is not None:
                fname = os.path.join('..', '..', path, file)
            else:
                fname = os.path.join(path, file)


        with open (fname, 'r') as inputs_file:

            inputs = yaml.load(inputs_file, Loader=yaml.FullLoader)
            
        self.inputs = {}
   
        for key, data in inputs.items():

            if data['Type'] not in VALID_TYPES:
                msg = (f'Type not correctly defined for parameter {key} in file '
                       f'{inputs_file.name}. \nType was: {data["Type"]}'
                       f'\nType should be one of the '
                       f'following: {VALID_TYPES}.')
                raise ValueError(msg)

            if data['Value'] is not list:
                if data['Type'] == 'float':
                    self.check_value_float(key, data, inputs)
            
                elif data['Type'] == 'integer':
                    self.check_value_int(key, data, inputs)
                
                elif data['Type'] == 'string':
                    self.check_value_str(key, data, inputs)
                    
                elif data['Type'] == 'boolean':
                    self.check_value_bool(key, data, inputs)
                
                elif data['Type'] == 'list':
                    self.check_value_list(key, data, inputs)
        
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
            self.inputs[key] = data['Value']
            
        self.check_limits(key, data, inputs)

        if 'Possibilities' in data:
            self.check_possibilities(key, data, inputs) 

                
    def check_value_int(self, key, data, inputs):
        
        if type(data['Value']) is not int:           
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.inputs[key] = data['Value']
            
        self.check_limits(key, data, inputs)

        if 'Possibilities' in data:
            self.check_possibilities(key, data, inputs)        


    def check_value_str(self, key, data, inputs):
            
        if type(data['Value']) is not str:           
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.inputs[key] = data['Value']    

        if 'Possibilities' in data:
            self.check_possibilities(key, data, inputs)            


    def check_value_bool(self, key, data, inputs):
            
        if type(data['Value']) is not bool:           
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.inputs[key] = data['Value'] 

        if 'Possibilities' in data:
            self.check_possibilities(key, data, inputs) 

    
    def check_value_list(self, key, data, inputs):
        
        if type(data['Value']) is not list:
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.inputs[key] = data['Value']

        if 'Possibilities' in data:
            self.check_possibilities(key, data, inputs)


    def check_possibilities(self, key, data, inputs):
        if data['Value'] not in data['Possibilities']:
            self.msg = ('Input "' + key + '" value should be one of the '
                        'following possibilities: ' + str(data['Possibilities']))
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.inputs[key] = data['Value']


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
                    self.inputs[key] = data['Value']
                    
            elif '/' in data['Limit'][0]:
                factors = data['Limit'][0].split('*')
                if (data['Value']<(inputs[factors[0]]['Value']/inputs[factors[1]]['Value']) or
                    data['Value']>data['Limit'][1]):
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.inputs[key] = data['Value']
                
            else:
                if data['Value']<inputs[data['Limit'][0]]['Value'] or data['Value']>data['Limit'][1]:                
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                   self.inputs[key] = data['Value']
    
        elif ((type(data['Limit'][0]) is not str) and (type(data['Limit'][1]) is str)):
            
            if '*' in data['Limit'][1]:
                factors = data['Limit'][1].split('*')
                if (data['Value']<data['Limit'][0] or
                    data['Value']>(inputs[factors[0]]['Value']*inputs[factors[1]]['Value'])):
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.inputs[key] = data['Value']
                    
            elif '/' in data['Limit'][1]:
                factors = data['Limit'][1].split('*')
                if (data['Value']<data['Limit'][0] or
                    data['Value']>(inputs[factors[0]]['Value']/inputs[factors[1]]['Value'])):
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.inputs[key] = data['Value']

            else:
                if ((data['Value']<data['Limit'][0]) or (data['Value']>inputs[data['Limit'][1]]['Value'])):               
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.inputs[key] = data['Value']
                
        else:
            if ((data['Value'] > float(data['Limit'][1])) or (data['Value'] < float(data['Limit'][0]))):
                self.error_message(key, None, data['Limit'])
                PASE_Logger(self.msg, 'ERROR', 'value')
            else:
                self.inputs[key] = data['Value']


class Inputs_aggregator:

    def __init__(self, inputs: list):
        self.aggregated_inputs = dict()

        self.aggregate_inputs(inputs)

        self.inputs_sanity_check()  # check validity of input parameters


    def aggregate_inputs(self, inputs):

        for input in inputs:
            self.aggregated_inputs.update(input)


    def inputs_sanity_check(self):

        # check if RepetitionDistanceOfPanelsX >= PanelDimensionX
        if self.aggregated_inputs['RepetitionDistanceOfPanelsX'] < \
                self.aggregated_inputs['PanelDimensionX']:
            raise ValueError(
                "Repetition distance between panels in axis X is too short, "
                "panels are clipping into eachother. Fix it in yaml config file.")

        if self.aggregated_inputs['RepetitionDistanceOfPanelsY'] < \
                self.aggregated_inputs['PanelDimensionY']:
            raise ValueError(
                "Repetition distance between panels in axis Y is too short, "
                "panels are clipping into eachother. Fix it in yaml config file.")
