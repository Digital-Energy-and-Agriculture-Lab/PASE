#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 11 09:49:59 2023

@author: roxane
"""

import xmltodict

rfile = open('param_gen.xml',"r")
xml_dict = xmltodict.parse(rfile.read())

rfile2 = open('Ble_tec.xml',"r")
xml_dict2 = xmltodict.parse(rfile2.read())