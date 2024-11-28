# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Louis Lemaire (Louis.Lemaire@uliege.be)
#This file is part of the PASE software, and is distributed under the MIT license.

import numpy as np
import pandas as pd
import datetime
import calendar

class Grassland:
    
    def __init__(self, crop_init=None, Kc_values=None, PFT_composition=None, PFT_values=None, Management=None):
        '''
        Crop_init : dictionnary from yaml file
            {'Parameter_name':parameter_value}
            
        Kc_values : dictionnary from yaml file
            {'Month':Kc_value}
            
        PFT_composition : dictionnary from yaml file
            {'PFT_group':proportion(0 -> 1)}
            
        PFT_values : pandas dataframe from csv file
            columns : parameters names
            index : PFT group
            fill : parameter values
        
        Management : dictionnary from yaml file
            {'cut/fertilization date/height_quantity':[values]}
            
        '''
        
        self.inits = crop_init
        self.Kc_values = Kc_values
        self.PFT_composition = PFT_composition
        self.PFT_values = PFT_values
        self.management = Management
        
        #initialization of the output 
        self.nyears_data = {}
        
        
    def get_PFT_param(self):
        '''
        Extracting PFT parameters and computing their weighted average depending on PFT composition
        '''

        
        #normalize PFT composition in case the sum of PFT composition is not 1
        #---------------------------------------------------------------------
        sum_PFT= sum(self.PFT_composition.values())
        self.PFT_composition = {k:(v/sum_PFT) for k,v in self.PFT_composition.items()}
        
        self.A = self.PFT_composition['A']
        self.B = self.PFT_composition['B']
        self.C = self.PFT_composition['C']
        self.D = self.PFT_composition['D']
        
        #Extract individual parameters for each PFT group
        #------------------------------------------------
        self.SLA_V  =  self.PFT_values['SLA']# (specific leaf area), Adapted from Cruz et al (2010)
        self.percentageLAM_V  =  self.PFT_values['percentageLAM'] # # (percentage of laminae)
        self.ST1_V  =  self.PFT_values['ST1']# oC (initial reproductive growth T), Adapted from Cruz et al (2010)
        self.ST2_V  =  self.PFT_values['ST2']# oC (end reproductive growth T), Adapted from Cruz et al (2010)
        self.maxSEA_V  =  self.PFT_values['maxSEA'] # - (maximum seasonal effect)
        self.minSEA_V  =  self.PFT_values['minSEA'] # - (minimum seasonal effect)
        self.LLS_V  =  self.PFT_values['LLS']# oC.d (leaf lifespan), Adapted from Cruz et al (2010)
        self.maxOMDGV_V  =  self.PFT_values['maxOMDGV']# - (max organic matter digestibility of green vegetative)
        self.minOMDGV_V  =  self.PFT_values['minOMDGV'] # - (min organic matter digestibility of green vegetative)
        self.maxOMDGR_V  =  self.PFT_values['maxOMDGR'] # - (max organic matter digestibility of green reproductive)
        self.minOMDGR_V  =  self.PFT_values['minOMDGR'] # - (min organic matter digestibility of green reproductive)
        self.BDGV_V  =  self.PFT_values['BDGV']# g DM/m^3 (bulk density of green vegetative)
        self.BDDV_V  =  self.PFT_values['BDDV']# g DM/m^3 (bulk density of dead vegetative)
        self.BDGR_V  =  self.PFT_values['BDGR']# g DM/m^3 (bulk density of green reproductive)
        self.BDDR_V  =  self.PFT_values['BDDR'] # g DM/m^3 (bulk density of dead reproductive)
        self.RUEmax_V = self.PFT_values['RUEmax']#maximim radiation use efficiency
        self.a_Ncrit_V = self.PFT_values['a_Ncrit']
        self.b_Ncrit_V = self.PFT_values['b_Ncrit']
        self.a_Nmax_V = self.PFT_values['a_Nmax']
        self.b_Nmax_V = self.PFT_values['b_Nmax']
        self.FNH_coef1_V = self.PFT_values['FNH_coef1']
        self.FNH_coef2_V = self.PFT_values['FNH_coef2']
        
        # Computing the average value 
        # --------------------------
        self.SLA  =  self.SLA_V[0]*self.A+self.SLA_V[1]*self.B+self.SLA_V[2]*self.C+self.SLA_V[3]*self.D # m^2/g [specific leaf area]
        self.percentageLAM  =  self.percentageLAM_V[0]*self.A+self.percentageLAM_V[1]*self.B+self.percentageLAM_V[2]*self.C+self.percentageLAM_V[3]*self.D # # [percentage of laminae]
        
        self.ST1  =  self.ST1_V[0]*self.A+self.ST1_V[1]*self.B+self.ST1_V[2]*self.C+self.ST1_V[3]*self.D # oC [initial reproductive growth T]
        self.ST2  =  self.ST2_V[0]*self.A+self.ST2_V[1]*self.B+self.ST2_V[2]*self.C+self.ST2_V[3]*self.D # oC [end reproductive growth T]

        self.maxSEA  = self.maxSEA_V[0]*self.A+self.maxSEA_V[1]*self.B+self.maxSEA_V[2]*self.C+self.maxSEA_V[3]*self.D  # - [maximum seasonal effect]
        self.minSEA  =  self.minSEA_V[0]*self.A+self.minSEA_V[1]*self.B+self.minSEA_V[2]*self.C+self.minSEA_V[3]*self.D # - [minimum seasonal effect]
        self.LLS  =  self.LLS_V[0]*self.A+self.LLS_V[1]*self.B+self.LLS_V[2]*self.C+self.LLS_V[3]*self.D # oC.d [leaf lifespan]
        self.maxOMDGV =  self.maxOMDGV_V[0]*self.A+self.maxOMDGV_V[1]*self.B+self.maxOMDGV_V[2]*self.C+self.maxOMDGV_V[3]*self.D # - [max organic matter digestibility of green vegetative]
        self.minOMDGV =  self.minOMDGV_V[0]*self.A+self.minOMDGV_V[1]*self.B+self.minOMDGV_V[2]*self.C+self.minOMDGV_V[3]*self.D # - [min organic matter digestibility of green vegetative]
        self.maxOMDGR =  self.maxOMDGR_V[0]*self.A+self.maxOMDGR_V[1]*self.B+self.maxOMDGR_V[2]*self.C+self.maxOMDGR_V[3]*self.D # - [max organic matter digestibility of green reproductive]
        self.minOMDGR =  self.minOMDGR_V[0]*self.A+self.minOMDGR_V[1]*self.B+self.minOMDGR_V[2]*self.C+self.minOMDGR_V[3]*self.D # - [min organic matter digestibility of green reproductive]
        self.BDGV = self.BDGV_V[0]*self.A+self.BDGV_V[1]*self.B+self.BDGV_V[2]*self.C+self.BDGV_V[3]*self.D # g DM/m^3 [bulk density of green vegetative]
        self.BDDV = self.BDDV_V[0]*self.A+self.BDDV_V[1]*self.B+self.BDDV_V[2]*self.C+self.BDDV_V[3]*self.D # g DM/m^3 [bulk density of dead vegetative]
        self.BDGR = self.BDGR_V[0]*self.A+self.BDGR_V[1]*self.B+self.BDGR_V[2]*self.C+self.BDGR_V[3]*self.D # g DM/m^3 [bulk density of green reproductive]
        self.BDDR = self.BDDR_V[0]*self.A+self.BDDR_V[1]*self.B+self.BDDR_V[2]*self.C+self.BDDR_V[3]*self.D # g DM/m^3 (bulk density of dead reproductive)
        self.RUEmax = self.RUEmax_V[0]*self.A+self.RUEmax_V[1]*self.B+self.RUEmax_V[2]*self.C+self.RUEmax_V[3]*self.D #Maximum radiation use efficiency
        self.a_Ncrit = self.a_Ncrit_V[0]*self.A+self.a_Ncrit_V[1]*self.B+self.a_Ncrit_V[2]*self.C+self.a_Ncrit_V[3]*self.D
        self.b_Ncrit = self.b_Ncrit_V[0]*self.A+self.b_Ncrit_V[1]*self.B+self.b_Ncrit_V[2]*self.C+self.b_Ncrit_V[3]*self.D
        self.a_Nmax = self.a_Nmax_V[0]*self.A+self.a_Nmax_V[1]*self.B+self.a_Nmax_V[2]*self.C+self.a_Nmax_V[3]*self.D
        self.b_Nmax = self.b_Nmax_V[0]*self.A+self.b_Nmax_V[1]*self.B+self.b_Nmax_V[2]*self.C+self.b_Nmax_V[3]*self.D
        self.FNH_coef1 = self.FNH_coef1_V[0]*self.A+self.FNH_coef1_V[1]*self.B+self.FNH_coef1_V[2]*self.C+self.FNH_coef1_V[3]*self.D
        self.FNH_coef2 = self.FNH_coef2_V[0]*self.A+self.FNH_coef2_V[1]*self.B+self.FNH_coef2_V[2]*self.C+self.FNH_coef2_V[3]*self.D
        
        #Non-specific parameters : no need to average
        # -------------------------------------------
        self.sigmaGV  =  self.PFT_values['sigmaGV'][0] # - rate of biomass losses with respiration
        self.sigmaGR  =  self.PFT_values['sigmaGR'][0] # - rate of biomass losses with respiration
        self.T0 =  self.PFT_values['T0'][0] # oC (min growth air T)
        self.T1 =  self.PFT_values['T1'][0] # oC (air T at which plateau is reached) 
        self.T2 =  self.PFT_values['T2'][0]# oC (air T at which growth starts decreasing) 
        self.Tlimit  =  self.PFT_values['Tlimit'][0] #oC (air T at which growth ends) 
        self.Tmin = 0
        self.Tmax = 18
        self.STmin = self.PFT_values['STmin'][0] # oC (min sum of temperature for growth)
        self.KGV =  self.PFT_values['KGV'][0]# basic senescence rate for green vegetative
        self.KGR  =  self.PFT_values['KGR'][0]# basic senescence rate for green reproductive
        self.KlDV  =  self.PFT_values['KlDV'][0]# basic abscission rate for dead vegetative
        self.KlDR  =  self.PFT_values['KlDR'][0]# basic abscission rate for dead reproductive
        self.OMDDV  =  self.PFT_values['OMDDV'][0]# organic matter digestibility of dead vegetative
        self.OMDDR  =  self.PFT_values['OMDDR'][0]# organic matter digestibility of dead reproductive
        self.Tref = self.PFT_values['Tref'][0]#reference T for fT in RUelle et al. 2018 for soil activity
        self.K = self.PFT_values['K'][0]#parameter for fT RUelle et al. 2018 for soil activity
        self.percentageofNmin = self.PFT_values['percentageofNmin'][0]
        self.NH3volatfactor = self.PFT_values['NH3volatfactor'][0]#The NH3 volat factor depends on the quality of the fertiliser application methods and conditions and is equal to 0.45 if the quality is bad; 0.6 ? 0.45 if it is average, and 0.1 ? 0.45 if it is good
        self.clay = self.inits['clay']
        self.repartitionN2NO2 = 0.189+(1.171*self.clay/(1+0.136*self.clay))#parameters in Ruelle 2018 for denitrificatoin pathways (N2 vs NO2)
        
    def init_crop(self, daily_irr):
        '''
        Initialization of crop with plant-related and soil-related parameters.
        Some are given in crop_init, some are computed.
        
        number of cell depends on daily irradiance data.

        '''
        #Get grid size
        # ------------
        self.grid_shape = daily_irr.shape[0]
        
        #get PFT parameters
        # -----------------
        self.get_PFT_param()
        
        #get initial conditions
        # ---------------------
        self.sward_height = np.full(self.grid_shape, self.inits['InitialHeight']) # sward height
        self.ageGV = np.full(self.grid_shape, self.inits['AgeGV']) # age of green vegetative biomass
        self.ageGR = np.full(self.grid_shape, self.inits['AgeGR']) # age of green reproductive biomass
        self.ageDV = np.full(self.grid_shape, self.inits['AgeDV']) # age of dead vegetative biomass
        self.ageDR = np.full(self.grid_shape, self.inits['AgeDR']) # age of dead reproductive biomass
        self.apex_grazed = np.full(self.grid_shape, self.inits['apex_grazed']) #or 1 depending on previous cuts or grazing events
        self.notRunoff = np.full(self.grid_shape, self.inits['notRunoff']) # water that has not run off the soil
        self.sand = np.full(self.grid_shape, self.inits['sand']) # sand fraction of soil
        self.clay = np.full(self.grid_shape, self.inits['clay']) # clay fraction of soil
        self.org = np.full(self.grid_shape, self.inits['org']) # organic matter fraction of soil
        self.Norg = np.full(self.grid_shape, self.inits['Norg']) # Organic Nitrogen in soil
        self.Nmin = np.full(self.grid_shape, self.inits['Nmin']) # Mineral Nitrogen in soil
        
        #compute initial conditions that depend on PFT parameters
        # -------------------------------------------------------
        self.BMGV = self.sward_height*10*self.BDGV # Green vegetative biomass
        self.BMGR = self.sward_height*10*self.BDGR # Green reproductive biomass
        self.BMDV = self.sward_height*10*self.BDDV # Dead vegetative biomass
        self.BMDR = self.sward_height*10*self.BDDR # Dead reproductive biomass
        self.BM = self.BMGV+self.BMGR+self.BMDV+self.BMDR 
        self.diffBMGV = self.BMGV
        self.diffBMGR = self.BMGR
        self.diffBMDV = self.BMDV
        self.diffBMDR = self.BMDR
        self.diffBM = self.BM
        if self.inits['soil_depth'] >= 1000:
            self.WaterCapacity = (0.2576 - 0.002 * self.sand + 0.0036 * self.clay + 0.0299 * self.org) * 1000
            self.Wiltingpoint = (0.026 + 0.005 * self.clay + 0.0158 * self.org) * 1000
        else:
            self.WaterCapacity = (0.2576 - 0.002 * self.sand + 0.0036 * self.clay + 0.0299 * self.org) * self.inits[
                'soil_depth']
            self.Wiltingpoint = (0.026 + 0.005 * self.clay + 0.0158 * self.org) * self.inits['soil_depth']
        self.WaterSaturation = 100 / 88 * self.WaterCapacity
        
        #initial water content is arbitrarily set to soil water capacity
        self.water = self.WaterCapacity
        
        self.OMDGV = self.maxOMDGV-(self.ageGV*(self.maxOMDGV-self.minOMDGV)/self.LLS) #organic mater digestibility of green vegetative biomass
        self.OMDGR = self.maxOMDGR-(self.ageGR*(self.maxOMDGR-self.minOMDGR)/(self.ST2-self.ST1)) #organic mater digestibility of green reproductive biomass
        
        #we assume that at the beginning of the season the plant has at least the minimum amount of N needed for maximum growth
        self.Nconc = self.a_Ncrit*0.01 #*(BMGV+BMGR/1000)^-b_Ncrit

        #We assume that at the beginning of the season the N concentration is the same for the green compartments. The same for the dead ones
        self.QNGV = self.Nconc*self.BMGV
        self.QNGR = self.Nconc*self.BMGR
        self.QNDV = 0.008*self.BMDV
        self.QNDR = 0.008*self.BMDR
        
        self.LAI = (self.SLA*self.BMGV/10*self.percentageLAM)
        
        self.NGV = self.QNGV/self.BMGV# GV grass N concentration (kg N/kgDM)
        self.NGR = self.QNGR/self.BMGR# GR grass N concentration (kg N/kgDM)
        self.NDV = self.QNDV/self.BMDV# DV grass N concentration (kg N/kgDM)
        self.NDR = self.QNDR/self.BMDR# DR grass N concentration (kg N/kgDM)
        
        self.ST = 0
        

        
    def initiate_one_year_variables(self, year):
        '''
        Initiate dictionnaries containing values of variables of interest. 
        This list can be extended at will.
        '''
        self.days_since_cut = None
        
        self.dict_sward_height = {}
        self.dict_BMGV = {}
        self.dict_BMGR = {}
        self.dict_BMDV = {}
        self.dict_BMDR = {}
        self.dict_BM = {}
        self.dict_BMG = {}
        self.dict_diffBMGV = {}
        self.dict_diffBMGR = {}
        self.dict_diffBMDV = {}
        self.dict_diffBMDR = {}
        self.dict_diffBM = {}
        self.dict_diffBMG = {}
        self.dict_ageGV = {}
        self.dict_ageGR = {}
        self.dict_ageDV = {}
        self.dict_ageDR = {}     
        self.dict_apex_grazed = {}
        self.dict_notRunoff = {}
        self.dict_water = {}
        self.dict_Norg = {}
        self.dict_Nmin = {}
        self.dict_QNGV = {}
        self.dict_QNGR = {}
        self.dict_QNDV = {}
        self.dict_QNDR = {}
        self.dict_OMDGV = {}
        self.dict_OMDGR = {}
        self.dict_LAI = {}
        self.dict_ST = {}
        self.dict_irradiation = {}
        self.dict_BMover5 = {}
        
        self.dict_Nact = {}
        self.dict_Ncrit = {}
        self.dict_Nmax = {}
        
        self.dict_NGV = {}
        self.dict_NGR = {}
        self.dict_NDV = {}
        self.dict_NDR = {}

        #Auxiliary variables
        self.dict_exportedBM = {}
        self.dict_exported_digestibleOM = {}
        self.dict_forage_quality = {}
        self.dict_exported_Ncontent = {}
        
        self.data_dict = {}
        
        #get management_input
        # -------------------
        self.get_management_input()
        
        
    def fill_nyears_data_dict(self, year):
        '''
        Fill output dictionnary nyears_data with data from 1 year
        '''
        
        self.data_dict['sward_height'] = self.dict_sward_height
        self.data_dict['BMGV'] = self.dict_BMGV
        self.data_dict['BMGR'] = self.dict_BMGR
        self.data_dict['BMDV'] = self.dict_BMDV
        self.data_dict['BMDR'] = self.dict_BMDR 
        self.data_dict['BM'] = self.dict_BM
        self.data_dict['BMG'] = self.dict_BMG
        self.data_dict['diffBMGV'] = self.dict_diffBMGV
        self.data_dict['diffBMGR'] = self.dict_diffBMGR
        self.data_dict['diffBMDV'] = self.dict_diffBMDV
        self.data_dict['diffBMDR'] = self.dict_diffBMDR 
        self.data_dict['diffBM'] = self.dict_diffBM
        self.data_dict['diffBMG'] = self.dict_diffBMG
        self.data_dict['ageGV'] = self.dict_ageGV
        self.data_dict['ageGR'] = self.dict_ageGV
        self.data_dict['ageDV'] = self.dict_ageGR
        self.data_dict['ageGV'] = self.dict_ageDV
        self.data_dict['ageDR'] = self.dict_ageDR     
        self.data_dict['apex_grazed'] = self.dict_apex_grazed
        self.data_dict['notRunoff'] = self.dict_notRunoff
        self.data_dict['water'] = self.dict_water
        self.data_dict['Norg'] = self.dict_Norg
        self.data_dict['Nmin'] = self.dict_Nmin
        self.data_dict['QNGV'] =  self.dict_QNGV
        self.data_dict['QNGR'] = self.dict_QNGR
        self.data_dict['QNDV'] = self.dict_QNDV
        self.data_dict['QNDR'] = self.dict_QNDR
        self.data_dict['OMDGV'] = self.dict_OMDGV
        self.data_dict['OMDGR'] = self.dict_OMDGR
        self.data_dict['LAI'] = self.dict_LAI
        self.data_dict['ST'] = self.dict_ST
        self.data_dict['irradiation'] = self.dict_irradiation
        self.data_dict['BMover5'] = self.dict_BMover5
        
        self.data_dict['Nact'] = self.dict_Nact
        self.data_dict['Ncrit'] = self.dict_Ncrit
        self.data_dict['Nmax'] = self.dict_Nmax
        
        self.data_dict['NGV'] = self.dict_NGV
        self.data_dict['NGR'] = self.dict_NGR
        self.data_dict['NDV'] = self.dict_NDV
        self.data_dict['NDR'] = self.dict_NDR
        
        #Auxiliary variables
        self.data_dict['exportedBM'] = self.dict_exportedBM
        self.data_dict['exported_digestibleOM'] = self.dict_exported_digestibleOM
        self.data_dict['forage_quality'] = self.dict_forage_quality
        self.data_dict['exported_Ncontent'] = self.dict_exported_Ncontent
        
        self.data_dict['total_cumulated_BM'] = np.array(list(self.dict_diffBM.values())).sum(axis=0) #cumulated biomass for this year
        self.data_dict['total_cumulated_BMGV'] = np.array(list(self.dict_diffBMGV.values())).sum(axis=0)
        self.data_dict['total_cumulated_BMGR'] = np.array(list(self.dict_diffBMGR.values())).sum(axis=0)
        self.data_dict['total_cumulated_BMDV'] = np.array(list(self.dict_diffBMDV.values())).sum(axis=0)
        self.data_dict['total_cumulated_BMDR'] = np.array(list(self.dict_diffBMDR.values())).sum(axis=0)
        self.data_dict['total_cumulated_BMG'] = np.array(list(self.dict_diffBMG.values())).sum(axis=0)
        
        self.nyears_data[year] = self.data_dict
        
    def get_management_input(self):
        '''
        Get management inputs with type of management and date of application
        
        3 management types :
            - grass cutting
            - mineral fertilization
            - organic fertilization
        '''
        
        self.cutHeight = self.management['cutHeight']
        self.maxHeight = self.management['maxHeight']
        self.cutToFertDays = self.management['cutToFertDays']
        self.fertOrg = self.management['fertOrg']
        self.fertMin = self.management['fertMin']
              
    def growth(self, WD, ET0, irradiation, day):
        '''
        GrasSim model (Urbain Kokah)
        Computes new values for crop and soil parameters.
        Adds values to one year dictionnaries

        WD : pandas DataFrame of weather data for 1 year
            
        ET0 : float
            Potential evapotranspiration. 
            
        irradiation : pandas DataFrame of irradiance data for 1 year
            shape : (n_cells, 365)
            Computed using ray casting simulation
            
        day : datetime Timestamp 
            day of simulation

        '''
        
        # Management variables setting 
        self.mean_sward_height = np.mean(self.sward_height)
        
        ## cut decision
        if self.mean_sward_height > self.maxHeight :
            cut_height = self.cutHeight
            self.days_since_cut = 0
        else :
            cut_height = 0
        ## fertilization decision
        if self.days_since_cut == self.cutToFertDays:
            fert_org = self.fertOrg
            fert_min = self.fertMin
        else :
            fert_org = 0
            fert_min = 0
        
        if self.days_since_cut != None:
            self.days_since_cut += 1
            
        
        self.irradiation = irradiation

        
        self.day = day
        
        self.PP = WD['Rain']
        self.Temp = WD['Avg_temp']
        self.PET = ET0
        self.PARi = irradiation*0.48
        
        self.Tmin = 0
        self.Tmax = 18
        
        #compute cumulated temperature value for day i
        if  (self.Temp >= self.Tmin) and  (self.Temp <= self.Tmax) : 
            self.ST = self.ST + self.Temp - self.Tmin
        elif (self.Temp > self.Tmax) :
            self.ST = self.ST + self.Tmax - self.Tmin
        else:
            self.ST = self.ST
        
        #get Kc value of the day
        self.month = day.month_name()
        self.Kc_value = self.Kc_values[self.month]
        
        
        
        #*****************************************************************************
                #Growth Reduction Factors (form Jouven et al., 2006 & Ruelle et al., 2018)
        #*****************************************************************************
        
        #adjustment for water stress
        #-----------------------------
         
        AET = self.PET*self.Kc_value #could depend on GV
        
        water_transient = (self.water+(self.PP-AET)+self.notRunoff)
        
        waterLeached = np.where(water_transient<self.WaterCapacity, 0, 0.2*(water_transient-self.WaterCapacity))
        self.notRunoff = np.where(water_transient<self.WaterSaturation, 0, 0.2*(water_transient-self.WaterSaturation))

        water_transient = water_transient - waterLeached
        
        #setting the lower and upper boundaries for water content
        water_transient = water_transient.clip(self.Wiltingpoint,self.WaterSaturation)
        
         # W is the % of available water     
        W = (water_transient-self.Wiltingpoint)/(self.WaterCapacity-self.Wiltingpoint)
        W = W.clip(0,1)
         
        # this comes from McCall & Bishop-Hurley 2003: eq 6 in their paper.  
        fW = np.where(self.PET<3.81, 
            
             np.where(W<0.2, 4*W,
             np.where(W<0.4, 0.75*W+0.65,
             np.where(W<0.6, 0.25*W+0.85,
             1))),
             
             np.where(self.PET<6.35,
             
            
             np.where(W<0.2, 2*W,
             np.where(W<0.4, 1.5*W+0.1,
             np.where(W<0.6, W+0.3,
             np.where(W<0.8, 0.5*W+0.6,
             1)))),
          
             W
        ))
        
        #adjustment for T
        #-----------------
        fT = np.where(self.Temp<=self.T0, 0,                 
             np.where(self.Temp<=self.T1, (self.Temp-self.T0)/(self.T1-self.T0),
             np.where(self.Temp<=self.T2, 1,
             np.where(self.Temp<=self.Tlimit, (self.Tlimit-self.Temp)/(self.Tlimit-self.T2),
             0
             ))))
        
        
        #adjustment for RUE decrease with PAR intensity
        #-----------------------------------------------
        
        fPARi = np.where(self.PARi<=5, 1, (1/22*-self.PARi)+27/22)
        
        
        #Seasonal effect
        #----------------
        SEA = np.where(self.ST<self.STmin, self.minSEA,
              np.where(self.ST<=self.ST1-200, (self.maxSEA-self.minSEA)/(self.ST1-100-self.STmin)*(self.ST-self.STmin)+self.minSEA,
              np.where(self.ST<=self.ST1-100, self.maxSEA,
              np.where(self.ST<=self.ST2, (self.minSEA-self.maxSEA)/(self.ST2-self.ST1)*(self.ST-self.ST1)+self.maxSEA,
              self.minSEA
              ))))
        
        
        
        #*****************************************************************************
                    #Senescence and abscission (form Jouven et al., 2006)
        #*****************************************************************************

        fageGV = np.where(self.ageGV/self.LLS<1/3, 1,
                 np.where(self.ageGV/self.LLS<1, 3*(self.ageGV/self.LLS),
                          3))
        
        fageGR = np.where(self.ageGR/(self.ST2-self.ST1)<1/3, 1,
                 np.where(self.ageGR/(self.ST2-self.ST1)<1, 3*(self.ageGR/(self.ST2-self.ST1)),
                          3))

        fageDV = np.where(self.ageDV/self.LLS<1/3, 1,
                 np.where(self.ageDV/self.LLS<2/3, 2,
                          3))
     
        fageDR = np.where(self.ageDR/(self.ST2-self.ST1)<1/3, 1,
                 np.where(self.ageDR/(self.ST2-self.ST1)<2/3, 2,
                          3))

        
        ABSDV = np.where(self.Temp>0, self.KlDV*self.BMDV*self.Temp*fageDV, 0)
        ABSDR = np.where(self.Temp>0, self.KlDR*self.BMDR*self.Temp*fageDR, 0)
        
        

        SENGV = np.where(self.Temp>self.T0, self.KGV*self.BMGV*self.Temp*fageGV,
                np.where(self.Temp<0, self.KGV*self.BMGV*-(self.Temp),
                0))
        
        SENGR = np.where(self.Temp>self.T0, self.KGR*self.BMGR*self.Temp*fageGR,
                np.where(self.Temp<0, self.KGR*self.BMGR*abs(self.Temp),
                0))
        
        

    #*******************************************************************************
                 #Mineralization and immobilization (from Ruelle et al., 2018)
    #*******************************************************************************
        g0=(1-0.2)*W+0.2
        fTnitro=np.exp(self.K*(self.Temp-self.Tref))
        
        Vp=(0.0929+(0.1833-0.0929)*np.exp(-0.2173*self.Norg/1000))*self.Norg/1000
  
   
        mineralisation=Vp*fTnitro*g0
        Ip = 4/1000*self.Nmin
        Ip = np.clip(Ip, a_min=0, a_max=None)
        immobilization = Ip*fTnitro*g0
      
      
      
    #*******************************************************************************
        #Soil N supply and Plant N status (Adapted from Patrico Sandana et. al 2018 & Helge Bonesmo et Gilles B?langer 2002(CATIMO model))
    #*******************************************************************************

        #soil N supply
        #--------------
        
        FNAmax =  0.07# 0.02  #Maximum fraction of available soil N - range from 0 to 1
        
        #(0.00012 - 0.00014 in (Ruelle et al., 2018))
        
        NSc = 270#280#250#(kg N/ha) Soil N content (0-45 cm) for maximum N availability (20.3 g N/m2)- range fom 50 to 400
        
        FNA = FNAmax*(self.Nmin/NSc)
        FNA = np.clip(FNA, a_min=None, a_max=FNAmax)
        
        Nsupply = FNA*self.Nmin
        Nsupply  =  np.where(self.Nmin<0, 0, Nsupply) #(to avoid going below 0 with Nmin)
        # Nsupply  =  ifelse (Nmin<250, ifelse(Nmin>25,(4-0)/(250)*(Nmin-25)+0.5 ,0.5),4)
        
        
        
        #Total biomass
        #----------- 
        BM = self.BMGV+self.BMGR+self.BMDV+self.BMDR
        
        #Green biomass
        #-----------
        self.BMG = self.BMGV + self.BMGR
        
        # #Biomass over 5 cm 
        #------------
        cut_off_BM = 0.05*10*self.BDGV+0.05*10*self.BDGR+0.05*10*self.BDDV+0.05*10*self.BDDR
        
        cut_off_BMGV = 0.05*10*self.BDGV
        cut_off_BMDV = 0.05*10*self.BDGR
        cut_off_BMGR = 0.05*10*self.BDDV
        cut_off_BMDR = 0.05*10*self.BDDR
        
        #BMGR_over5 = self.BMGR-0.05*10*self.BDGR
        #BMDV_over5 = self.BMDV-0.05*10*self.BDDV
        #BMDR_over5 = self.BMDR-0.05*10*self.BDDR
        
        BMGV_over5 = np.where(self.BMGV>cut_off_BMGV, self.BMGV-cut_off_BMGV, 0)
        BMGR_over5 = np.where(self.BMGR>cut_off_BMGR, self.BMGR-cut_off_BMGR, 0)
        BMDV_over5 = np.where(self.BMDV>cut_off_BMDV, self.BMDV-cut_off_BMDV, 0)
        BMDR_over5 = np.where(self.BMDR>cut_off_BMDR, self.BMDR-cut_off_BMDR, 0)
        
        
        
        #for all the biomass
        #----------------------
        
        self.BMover5 = np.where(BM>cut_off_BM, BM-cut_off_BM, 0)

        #Critical N dilution curve according for the different plant functional types
        #--------------------------------------------------------
        self.Ncrit = np.where(self.BMover5<=1000, self.a_Ncrit*0.01, self.a_Ncrit*0.01*(self.BMover5/1000)**(-self.b_Ncrit))
        
        #Maximum plant N content 
        #--------------------------
        
        self.Nmax = np.where(self.BMover5<=1000, self.a_Nmax*0.01, self.a_Nmax*0.01*(self.BMover5/1000)**(-self.b_Nmax))
        
        #From Maria A. Marino et al.,2004
        
        #Actual Plant N content 
        #--------------------
        
        
        #--------------------
        #************************************************
        #Max RNC
        #***********************************************
        
        RNCmax = 0.9
        RNCmin = 0.4
        
        # Nact_optm = 0.65
        self.Nact = np.where(self.BMover5<=0, RNCmin*self.Ncrit, (self.NGV*BMGV_over5+self.NGR*BMGR_over5+self.NDV*BMDV_over5+self.NDR*BMDR_over5)/self.BMover5)
           
        Nactlim = self.Ncrit*RNCmax
        
        self.Nact = np.clip(self.Nact, a_min=None, a_max=Nactlim)
        
        #Relative N concentration (RNC)(CATIMO model)
        #-------------------
        RNC = (self.Nact/self.Ncrit)
        
        RNC= RNC.clip(min=0.25, max=1)
        
        
        ##################################################################
        
        # RNC = np.full_like(RNC, 0.4)
           
      
    #***********************************************************************************************
      # Plant growth (Adapted from Jouven et al., 2006 & Helge Bonesmo et Gilles B?langer 2002(CATIMO model))
    #***********************************************************************************************
      
        #The effect of N status on RUE (fN)(adapted from CATIMO model)
        #--------------------------
        
        # fN = 0.99*(1-(3.78*np.exp(-5.36*RNC)))
        # fN = fN.clip(min=0, max=1)
        fN=0.8
        #Environmental limitations
        #----------------------
        fWfN = np.where(fW<fN, fW, fN)
        
        ENV = fPARi*fT*fWfN
        
        #Potential growth 
        #--------------
        PGRO = self.PARi*self.RUEmax*(1-np.exp(-0.6*self.LAI))*10 # eq 12 (kgDM/ha) potential growth
         
        #Total growth
        #----------
        GRO = PGRO*ENV*SEA# eq 11 (kgDM/ha) 
        
        #Vegetative and reproductive growth 
        
        self.apex_grazed = np.where(np.logical_and(self.ST>self.ST1, np.logical_and(self.ST<self.ST2, cut_height != 0)), 1, 0)
        
        REP = np.where(self.ST<self.ST1, 0,
              np.where(np.logical_and(self.ST<self.ST2, np.logical_and(self.apex_grazed==0, np.logical_and(cut_height==0, RNC>0.35))), 0.25+((1-0.25)*(RNC-0.35))/(1-0.35),
              0
              ))

        GROGV = GRO*(1-REP)# eq 1
        GROGR = GRO*REP # eq 2
            
        #*****************************************************************************
              #Biomass balance, nutritional value and age (from Jouven et al., 2006)
        #*****************************************************************************
        
        #Total biomass after the growth
        #------------
        self.diffBMGV = GROGV-SENGV
        self.diffBMGR = GROGR-SENGR
        self.diffBMDV = (1-self.sigmaGV)*SENGV-ABSDV
        self.diffBMDR = (1-self.sigmaGR)*SENGR-ABSDR
        self.diffBM = self.diffBMGV+self.diffBMGR+self.diffBMDV+self.diffBMDR 
        self.diffBMG = self.diffBMGV+self.diffBMGR
        
        self.BMGV = self.BMGV + self.diffBMGV # eq 1
        self.BMGR = self.BMGR + self.diffBMGR # eq 2
        self.BMDV = self.BMDV + self.diffBMDV # eq 3
        self.BMDR = self.BMDR + self.diffBMDR # eq 4
        self.BM = self.BMGV+self.BMGR+self.BMDV+self.BMDR
        self.BMG = self.BMGV + self.BMGR
        
        
        #Green biomass
        #-----------
        self.BMG = self.BMGV+self.BMGR
      
        
        #sward_height
        #-----------
        self.sward_height =  np.maximum.reduce([self.BMGV/10/self.BDGV, self.BMGR/10/self.BDGR, self.BMDV/10/self.BDDV, self.BMDR/10/self.BDDR])#sward_height recalculated from biomass components
        
        
        #Mean age of the biomass
        #----------------
        self.ageGV = np.where(self.Temp>0, self.ageGV+(((self.BMGV-SENGV)/(self.BMGV-SENGV+GROGV))*(self.ageGV+self.Temp))-self.ageGV, self.ageGV)
        self.ageGR = np.where(self.Temp>0, self.ageGR+(((self.BMGR-SENGR)/(self.BMGR-SENGR+GROGR))*(self.ageGR+self.Temp))-self.ageGR, self.ageGR)
        self.ageDV = np.where(self.Temp>0, self.ageDV+(((self.BMDV-ABSDV)/(self.BMDV-ABSDV+(1-self.sigmaGV)*SENGV))*(self.ageDV+self.Temp))-self.ageDV, self.ageDV)
        self.ageDR = np.where(self.Temp>0, self.ageDR+(((self.BMDR-ABSDR)/(self.BMDR-ABSDR+(1-self.sigmaGR)*SENGR))*(self.ageDR+self.Temp))-self.ageDR, self.ageDR)
        
        
        #Green biomass nutritional value
        #----------------------
        self.OMDGV = self.maxOMDGV-(self.ageGV*(self.maxOMDGV-self.minOMDGV))/self.LLS
        
        self.OMDGR = np.where(self.ST<self.ST1, self.maxOMDGR, 
                np.where(self.ST>self.ST2, self.minOMDGR,
                self.maxOMDGR-(self.ageGR*(self.maxOMDGR-self.minOMDGR)/(self.ST2-self.ST1))
                ))
          
      
    #*******************************************************************************
          # N balance plant-sol (Adapted from Ruelle et al., 2018 & Helge Bonesmo et Gilles B?langer 2002(CATIMO model))
    #*******************************************************************************
      
        #FNH:The fraction of absorbed N that remains in the aboveground biomas
        #-------------
        FNHmax =  0.8  #Maximum proportion of absorbed N in harvestable biomass (No unit)
        
        FNH = FNHmax*np.maximum(self.FNH_coef1,self.FNH_coef2*(1+RNC))
        
        #Plant N demand
        #----------------
        # Nact = min(Nact,Nmax)
        Ndemand = self.BMover5*(self.Nmax-self.Nact)/FNH
         
        #Plant N uptake
        #-------------
        Nuptake = np.minimum(Ndemand,Nsupply)
           
           
        # Plant N content (kg N/ha) 
        #----------------------------
        Nplantlitter = ((ABSDV+ABSDR)*0.008) # from Ruelle 
        self.QNDV = (self.QNDV+((1-self.sigmaGV)*SENGV-ABSDV)*0.008)
        self.QNDR = (self.QNDR+((1-self.sigmaGR)*SENGR-ABSDR)*0.008)
        
        self.QNGV = np.where(GRO>0, self.QNGV+ (Nuptake*FNH*GROGV/GRO - SENGV*0.008), self.QNGV - SENGV*0.008)
        self.QNGR = np.where(GRO>0, self.QNGR+ (Nuptake*FNH*GROGR/GRO - SENGR*0.008), self.QNGR - SENGR*0.008)
        
        
        self.QNGV = self.QNGV.clip(min=0)  
        self.QNGR = self.QNGR.clip(min=0)
        
        # Total plant N content 
        #----------------
        TotalplantN = self.QNDV + self.QNDR + self.QNGV + self.QNGR 
        
        #Biomass N concentration
        #------------------
        PropNplant = TotalplantN/BM # kg N/kg DM
        self.NDV = self.QNDV/self.BMDV
        self.NDR = self.QNDR/self.BMDR
        self.NGV = self.QNGV/self.BMGV
        self.NGR = self.QNGR/self.BMGR
      
      
    #*********************************************************************************
                 #Global N balance (Adapted from Ruelle et al., 2018)
    #********************************************************************************
        #N loss by emission and leaching 
        #------------------------------
        globalemission = self.Nmin/1000*fT*g0
        N2Oemisson  =  (1-self.repartitionN2NO2)*globalemission
        N2Oemisson = N2Oemisson.clip(min=0)
        NLeached = (self.Nmin/water_transient)*waterLeached # From Ruelle 
        
        #N supply through rain
        #-----------------
        Nfromrain = 0.009*self.PP
          
        #Soil N
        #------
        self.Norg = self.Norg + immobilization - mineralisation + (1-self.percentageofNmin)*fert_org + Nplantlitter# the N content of dead material was ascribed the fixed value of 8 g N/kg DM (Delagarde et al., 2000).(DOI: 10.1080/01431160110114529 and Leconte et Laissus, 1985)  
        self.Nmin = self.Nmin + Nfromrain + mineralisation + fert_min + self.percentageofNmin*(1-self.NH3volatfactor)*fert_org - immobilization - Nuptake - NLeached

        # Cut day conditions
        #-------------------    
        cutBMGV = cut_height*10*self.BDGV
        cutBMGR = cut_height*10*self.BDGR
        cutBMDV = cut_height*10*self.BDDV
        cutBMDR = cut_height*10*self.BDDR
        
        # If cut height is smaller than current height, BM value is set to min(cut value, current value)
        resBMGV = np.where(np.logical_and(cut_height != 0, cut_height < self.sward_height), np.minimum(cutBMGV, self.BMGV), self.BMGV)
        resBMGR = np.where(np.logical_and(cut_height != 0, cut_height < self.sward_height), np.minimum(cutBMGR, self.BMGR), self.BMGR)
        resBMDV = np.where(np.logical_and(cut_height != 0, cut_height < self.sward_height), np.minimum(cutBMDV, self.BMDV), self.BMDV)
        resBMDR = np.where(np.logical_and(cut_height != 0, cut_height < self.sward_height), np.minimum(cutBMDR, self.BMDR), self.BMDR)
        resQNGV = resBMGV*self.NGV
        resQNGR = resBMGR*self.NGR
        resQNDV = resBMDV*self.NDV
        resQNDR = resBMDR*self.NDR
        self.sward_height = np.where(cut_height != 0, cut_height, self.sward_height)
        
        self.exported_biomass = self.BMGV-resBMGV + self.BMGR-resBMGR + self.BMDV-resBMDV + self.BMDR-resBMDR
        self.exported_digestibleOM = (self.BMGV-resBMGV)*self.OMDGV + (self.BMGR-resBMGR)*self.OMDGR + (self.BMDV-resBMDV)*self.OMDDV + (self.BMDR-resBMDR)*self.OMDDR
        self.forage_quality = np.where(cut_height != 0, self.exported_digestibleOM/self.exported_biomass, np.zeros_like(self.BMGV))
        self.exported_Ncontent = self.QNGV-resQNGV + self.QNGR-resQNGR + self.QNDV-resQNDV + self.QNDR-resQNDR
     
        
        self.BMGV = resBMGV
        self.BMGR = resBMGR
        self.BMDV = resBMDV
        self.BMDR = resBMDR
        self.BM = self.BMGV+self.BMGR+self.BMDV+self.BMDR 
        self.BMG = self.BMGV+self.BMGR
        self.QNGV = resQNGV
        self.QNGR = resQNGR
        self.QNDV = resQNDV
        self.QNDR = resQNDR
        
        
        #output =  input for the next day
        self.water = water_transient
        self.LAI = (self.SLA*self.BMGV/10*self.percentageLAM)
        
        self.dict_sward_height[str(day)] = self.sward_height
        self.dict_BMGV[str(day)] = self.BMGV
        self.dict_BMGR[str(day)] = self.BMGR
        self.dict_BMDV[str(day)] = self.BMDV
        self.dict_BMDR[str(day)] = self.BMDR
        self.dict_BM[str(day)] = self.BM
        self.dict_BMG[str(day)] = self.BMG
        self.dict_diffBMGV[str(day)] = self.diffBMGV
        self.dict_diffBMGR[str(day)] = self.diffBMGR
        self.dict_diffBMDV[str(day)] = self.diffBMDV
        self.dict_diffBMDR[str(day)] = self.diffBMDR
        self.dict_diffBM[str(day)] = self.diffBM
        self.dict_diffBMG[str(day)] = self.diffBMG
        self.dict_ageGV[str(day)] = self.ageGV
        self.dict_ageGR[str(day)] = self.ageGV
        self.dict_ageDV[str(day)] = self.ageGV
        self.dict_ageDR[str(day)] = self.ageGV  
        self.dict_apex_grazed[str(day)] = self.apex_grazed
        self.dict_notRunoff[str(day)] = self.notRunoff
        self.dict_water[str(day)] = self.water
        self.dict_Norg[str(day)] = self.Norg
        self.dict_Nmin[str(day)] = self.Nmin
        self.dict_QNGV[str(day)] = self.QNGV
        self.dict_QNGR[str(day)] = self.QNGR
        self.dict_QNDV[str(day)] = self.QNDV
        self.dict_QNDR[str(day)] = self.QNDR
        self.dict_OMDGV[str(day)] = self.OMDGV
        self.dict_OMDGR[str(day)] = self.OMDGR
        self.dict_LAI[str(day)] = self.LAI
        self.dict_ST[str(day)] = self.ST
        
        self.dict_irradiation[str(day)] = self.irradiation
        self.dict_BMover5[str(day)] = self.BMover5
        
        self.dict_Nact[str(day)] = self.Nact
        self.dict_Ncrit[str(day)] = self.Ncrit
        self.dict_Nmax[str(day)] = self.Nmax
        
        self.dict_NGV[str(day)] = self.NGV
        self.dict_NGR[str(day)] = self.NGR
        self.dict_NDV[str(day)] = self.NDV
        self.dict_NDR[str(day)] = self.NDR
        
        #Auxiliary variables
        self.dict_exportedBM[str(day)] = self.exported_biomass
        self.dict_exported_digestibleOM[str(day)] = self.exported_digestibleOM
        self.dict_forage_quality[str(day)] = self.forage_quality
        self.dict_exported_Ncontent[str(day)] = self.exported_Ncontent
