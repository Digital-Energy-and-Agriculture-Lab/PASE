#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 17 14:29:46 2023

@author: roxane
"""

import logging
import os

class PASE_Logger:
    
    def __init__(self, msg=None, level=None):
        
        log_file = 'logging_file.log'
        logging.basicConfig(filename=log_file, filemode='a', level=logging.DEBUG,
                            format='%(asctime)s  (%(levelname)s)  -  %(message)s',
                            datefmt='%I:%M:%S %p')
        
        if level is None and msg is None:
            self.initialization()
        
        if level == 'DEBUG':
            self.write_debug(msg)
        elif level == 'INFO':
            self.write_info(msg)
        elif level == 'WARNING':
            self.write_warning(msg)
        elif level == 'ERROR':
            self.write_error(msg)
        elif level == 'CRITICAL':
            self.write_critical(msg)
            
            
    def initialization(self, msg='START OF THE SIMULATION'):
        
        with open('logging_file.log', 'w'):
            pass
        log_file = 'logging_file.log'
        logging.basicConfig(filename=log_file, filemode='a', level=logging.DEBUG,
                            format='%(asctime)s  (%(levelname)s)  -  %(message)s',
                            datefmt='%I:%M:%S %p') 
        self.write_info(msg)
        
            
    def write_debug(self, msg):      
        logging.debug(msg)
        print(msg)
        
        
    def write_info(self, msg):
        logging.info(msg)
        print(msg)
        
        
    def write_warning(self, msg):
        logging.warning(msg)
        print(msg)
        
        
    def write_error(self, msg):
        logging.error(msg)
        raise ValueError(msg)
        
        
    def write_critical(self, msg):
        logging.critical(msg)
        print(msg)
        
    
        
        