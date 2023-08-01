#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  1 14:12:53 2023

@author: roxane
"""

import xmltodict
            
class XML_STICS_Inputs_Provider(dict):
    
    def __init__(self, file=None):
        
        dict.__init__(self)
        dict.__setitem__(self, 'coucou', 25)
        
        rfile = open(file,"r")
        xml_dict = xmltodict.parse(rfile.read())
        
        for formalism in xml_dict['fichierplt']['formalisme']:
            
            for key, data in formalism.items():
                
                if key == 'param' and type(data) is list:
                    for parameter in data:
                        dict.__setitem__(self, parameter['@nom'], num(parameter['#text']))
                elif key == 'param' and type(data) is dict:
                    dict.__setitem__(self, data['@nom'], num(data['#text']))
                elif key == 'option' and type(data) is list:
                    for parameter in data:
                        dict.__setitem__(self, parameter['@nomParam'], num(parameter['@choix']))
                elif key == 'option' and type(data) is dict:
                    dict.__setitem__(self, data['@nomParam'], num(data['@choix']))
                                    
def num(x):
    try:
        return int(x)
    except ValueError:
        try: 
            return float(x)
        except ValueError:
            return str(x)
    
    
    
cropdata = XML_STICS_Inputs_Provider("wheat_plt.xml")