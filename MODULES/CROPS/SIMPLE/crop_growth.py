# -*- coding: utf-8 -*-
"""

Code developped within the agrivoltaic modeling framework project.
The model calculates the growth of the crop and its yield.

The implemented model was taken from:
"A SIMPLE crop model (C. Zhao, B. Liu, L. Xiao et al., 2019)"

"""

# import public packages

import math
import numpy as np

class Crop:
    
    def __init__(self, crop_par=None, crop_init=None):
        
        self.P = crop_par
        self.I = crop_init
        self.init_crop()       
        self.nyears_data = {}
        
    def initiate_one_year_data_dictionaries(self):
        
        self.dict_biomass_rate = {}
        self.dict_biomass = {}
        self.dict_dryyield = {}
        self.dict_freshyield = {}
        self.dict_LAI = {}
        self.dict_height = {}
        
        self.data_dict = {}
        
    def fill_nyears_data_dict(self, year):
        
        self.data_dict['Biomass_rate'] = self.dict_biomass_rate
        self.data_dict['Biomass'] = self.dict_biomass
        self.data_dict['Dry_yield'] = self.dict_dryyield
        self.data_dict['Fresh_yield'] = self.dict_freshyield
        self.data_dict['LAI'] = self.dict_LAI
        self.data_dict['Height'] = self.dict_height
        
        self.nyears_data[year] = self.data_dict
        
    def init_crop(self):
        
        self.LAI = self.I['InitialLAI']
        self.cum_T = self.I['InitialCumTemp']
        self.biomass = self.I['InitialBiomass']
        
    def growth(self, avg_T, max_T, CO2, irrad, ET0, transpi, day_index):
        
        if str(self.P['I50C']) == 'nan':   
            I50C = ((self.P['Tsum']
                     -self.P['I50B']
                     -self.P['I50A'])/2)+self.P['I50A']   #cum_T où survient fSolar max
        else:
            I50C = self.P['I50C']
        
        self.get_cum_temp(avg_T)
        fTemp = self.get_fTemp(avg_T)
        fHeat = self.get_fheat(max_T)
        I50B_Hstressed = self.get_I50B_heat_stressed(fHeat)
        ARID = self.get_ARID_index(ET0, transpi)
        fWater = self.get_fWater(ARID)
        I50B_Wstressed = self.get_I50B_water_stressed(fWater, I50B_Hstressed)
        fSolar = self.get_fSolar(I50B_Wstressed, I50C)
        fSolar_Wstressed = self.get_fSolar_water_stressed(fSolar, fWater)
        fCO2 = self.get_fCO2(CO2)
        
        biomass_rate = (irrad*fSolar*fSolar_Wstressed*self.P['RUE']*fCO2*
                        fTemp*np.minimum(fHeat,fWater))
        
        self.biomass = self.biomass + biomass_rate
        
        self.get_LAI()
        
        height = self.get_height()
        
        dry_yield = self.get_dry_yield()
        fresh_yield = self.get_fresh_yield(dry_yield)
        
        self.dict_biomass_rate[str(day_index)] = biomass_rate
        self.dict_biomass[str(day_index)] = self.biomass
        self.dict_dryyield[str(day_index)] = dry_yield
        self.dict_freshyield[str(day_index)] = fresh_yield
        self.dict_LAI[str(day_index)] = self.LAI
        self.dict_height[str(day_index)] = height
        
    def get_cum_temp(self, avg_T):
        
        if avg_T > self.P['Tbase'] :
            delta_T = avg_T - self.P['Tbase']
        else :
            delta_T = 0

        self.cum_T = self.cum_T + delta_T
        
    def get_fTemp(self, avg_T):
        
        # Computation of the impact of temperature on biomass growth (fTemp)

        if avg_T < self.P['Tbase'] :
            fTemp = 0
        elif ((avg_T >= self.P['Tbase']) & (avg_T < self.P['Topt'])) :
            fTemp = (avg_T-self.P['Tbase'])/(self.P['Topt']-self.P['Tbase'])
        else:
            fTemp = 1
            
        return fTemp    
    
    def get_fheat(self, max_T):
        
        # Computation of the heat stress factor (fheat)

        if max_T < self.P['Tmax'] :
            fHeat = 1
        elif ((max_T >= self.P['Tmax']) & (max_T < self.Text)) :
            fHeat = 1 - ((max_T-self.P['Tmax'])/(self.P['Text']-self.P['Tmax']))
        else :
            fHeat = 0
    
        return fHeat
    
    def get_I50B_heat_stressed(self, fHeat):
        
        # Computation of I50B increased by heat stress
        if self.P['I50B'] != 'NaN' :
            I50B_Hstressed = self.P['I50B'] + self.P['I50maxH']*(1-fHeat)
        else:
            I50B_Hstressed = 'NaN'
            
        return I50B_Hstressed
    
    
    def get_ARID_index(self, ET0, transpi):
        
        # Computation of ARID index
        if type(ET0) is np.float64 or type(ET0) is int:
            if ET0 != 0 :
                ARID = 1-(transpi/ET0)
            else :
                ARID = 0
                
        else:
            ARID = np.zeros(len(ET0))
            ind = np.where(ET0!=0)
            ARID[ind] = 1-(transpi[ind]/ET0[ind])
            
        return ARID
    
    def get_fWater(self, ARID):
        
        # Computation of impact of soil available water content

        fWater = 1-(self.P['Swater']*ARID)
        
        if type(fWater) is np.float64 or type(fWater) is float:
            if fWater < 0 :
                fWater = 0
        else:
            ind = np.where(fWater<0)
            fWater[ind] = 0
            
        return fWater
    
    def get_I50B_water_stressed(self, fWater, I50B_Hstressed):
        
        #Computation of I50B  increased by drought stress
        if I50B_Hstressed != 'NaN' :
            I50B_Wstressed = I50B_Hstressed+self.P['I50maxW']*(1-fWater)
        else:
            I50B_Wstressed = 'NaN'
        
        return I50B_Wstressed
        
    def get_fSolar(self, I50B_Wstressed, I50C):
        
        # Computation of the fraction of solar radiation intercepted by the crop canopy (fSolar)
        
        fSolar_max = 0.95
        if self.cum_T <= I50C:
            fSolar = fSolar_max/(1+(math.exp(-0.01*(self.cum_T
                                                    -self.P['I50A']))))
        elif self.cum_T > I50C:
            fSolar = fSolar_max/(1+(np.exp(0.01*(self.cum_T
                                                 -(self.P['Tsum']-I50B_Wstressed)))))
            
        return fSolar
            
    def get_fSolar_water_stressed(self, fSolar, fWater):
        
        # Computation of fSolar increased by drought stress

        if type(fWater) is np.float64 or type(fWater) is float:
            if fWater < 0.1 :
                fSolar_Wstressed = 0.9 + fWater
            elif fWater >= 0.1 :
                fSolar_Wstressed = 1
                
        else:
            fSolar_Wstressed = np.ones(len(fWater))
            ind = np.where(fWater<0.1)
            fSolar_Wstressed[ind] = 0.9 + fWater[ind]
            
        return fSolar_Wstressed
    
    def get_fCO2(self, CO2):
        
        # Computation of impact of CO2 on radiation use efficiency (fCO2)

        if ((CO2 >= 350) & (CO2 < 700)) :
            fCO2 = 1+self.P['SCO2']*(CO2-350)
        elif CO2 >= 700 :
            fCO2 = 1+self.P['SCO2']*350
            
        return fCO2
    
    def get_dry_yield(self):
        
        #Specific potential harvest index
        dry_yield = self.biomass*self.P['HI']

        return dry_yield
    
    def get_fresh_yield(self, dry_yield):
        
        fresh_yield = dry_yield*self.P['Fw/Dw']
    
        return fresh_yield
    
    def get_LAI(self):
        
        self.LAI = self.P['LAI_a_factor']*self.biomass + self.P['LAI_b_factor']
        
    def get_height(self):
        
        LAI_max = 7
        height_parameter = self.P['H_max']/LAI_max

        height = self.LAI*height_parameter

        return height
