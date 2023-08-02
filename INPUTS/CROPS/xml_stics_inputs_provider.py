#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  1 14:12:53 2023

@author: roxane
"""

import xmltodict
            
class XML_STICS_Inputs_Provider(dict):
    
    def __init__(self, file=None, soil_name=None):
        
        dict.__init__(self)
        
        rfile = open(file,"r")
        xml_dict = xmltodict.parse(rfile.read())
        
        if ('plt.xml' in file or 'tec.xml' in file or 'sta.xml' in file) and soil_name is None:
            file_type = next(iter(xml_dict))
            for formalism in xml_dict[file_type]['formalisme']:
                self.retrieve_parameters(formalism)
                
        elif 'sols.xml' in file and soil_name is not None:          
            for soil in xml_dict['sols']['sol']:
                if soil['@nom'] == soil_name:
                    self.retrieve_parameters(soil)
                    
        elif 'ini.xml' in file and soil_name is None:
            self.retrieve_init_parameters(xml_dict)
            
                    
    def retrieve_parameters(self, dictionnary=None):
        
        for key, data in dictionnary.items():
                       
            if key == 'param' and type(data) is list:
                for parameter in data:
                    dict.__setitem__(self, parameter['@nom'], num(parameter['#text']))
                    
                    
            elif key == 'param' and type(data) is dict:
                dict.__setitem__(self, data['@nom'], num(data['#text']))
                
                
            elif key == 'option' and type(data) is list:
                for model_choice in data:
                    dict.__setitem__(self, model_choice['@nomParam'], num(model_choice['@choix']))
                    for choice in model_choice['choix']:
                        for key2, data2 in choice.items():
                            if key2 == 'param' and type(data2) is list:
                                for parameter2 in data2:
                                    dict.__setitem__(self, parameter2['@nom'], num(parameter2['#text']))
                            elif key2 == 'param' and type(data2) is dict:
                                dict.__setitem__(self, data2['@nom'], num(data2['#text']))
                    
            elif key == 'option' and type(data) is dict:
                dict.__setitem__(self, data['@nomParam'], num(data['@choix']))
                for choice in data['choix']:
                    for key2, data2 in choice.items():
                        if key2 == 'param' and type(data2) is list:
                            for parameter2 in data2:
                                dict.__setitem__(self, parameter2['@nom'], num(parameter2['#text']))
                        elif key2 == 'param' and type(data2) is dict:
                            dict.__setitem__(self, data2['@nom'], num(data2['#text']))
             
                
            elif key == 'ta':
                interventions_dict = {}
                if type(data['intervention']) is list:
                    for inter in data['intervention']:
                        params = {}
                        for par in inter['colonne']:
                            params[par['@nom']] = num(par['#text'])
                        interventions_dict[inter['colonne'][0]['#text']] = params
                elif type(data['intervention']) is dict:
                    params = {}
                    for par in data['intervention']['colonne']:
                        params[par['@nom']] = num(par['#text'])
                    interventions_dict[data['intervention']['colonne'][0]['#text']] = params
                dict.__setitem__(self, dictionnary['@nom'], interventions_dict)
                
    
    def retrieve_init_parameters(self, dictionnary):
        
        dict.__setitem__(self, 'nbplantes', num(dictionnary['initialisations']['nbplantes']))
        for key, data in dictionnary['initialisations']['plante'][0].items():
            if type(data) is str:
                dict.__setitem__(self, key, num(data))
            else:
                layer_dic = {}
                for layer in data['horizon']:
                    layer_dic[layer['@nh']] = num(layer['#text'])
                dict.__setitem__(self, key, layer_dic)
                
        for key, data in dictionnary['initialisations']['sol'].items():
            layer_dic = {}
            for layer in data['horizon']:
                layer_dic[layer['@nh']] = num(layer['#text'])
            dict.__setitem__(self, key, layer_dic)

        if num(dictionnary['initialisations']['nbplantes']) == 2:
            dic_2nd_plant = {}
            for key, data in dictionnary['initialisations']['plante'][1].items():
                if type(data) is str:
                    dic_2nd_plant[key] = num(data)
                elif type(data) is type(None):
                    dic_2nd_plant[key] = data
                else:
                    layer_dic = {}
                    for layer in data['horizon']:
                        layer_dic[layer['@nh']] = num(layer['#text'])
                    dic_2nd_plant[key] = layer_dic
            dict.__setitem__(self, '2nd_plant', dic_2nd_plant)
        
        
def num(x):
    try:
        return int(x)
    except ValueError:
        try: 
            return float(x)
        except ValueError:
            return str(x)
    
    
    
cropdata = XML_STICS_Inputs_Provider("wheat_plt.xml")
agromanagement = XML_STICS_Inputs_Provider("Ble_tec.xml")
soildata = XML_STICS_Inputs_Provider("sols.xml", 'solcanne')
init_data = XML_STICS_Inputs_Provider("ble_ini.xml")
station_data = XML_STICS_Inputs_Provider("climblej_sta.xml")

            
