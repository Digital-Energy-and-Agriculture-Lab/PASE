# -*- coding: utf-8 -*-
cwd = 'C:\\Users\\lloui\\Desktop\\Gembloux\\Recherche\\ROBHERB\\Gras-Sim\\framework_agrivoltaics\\'
import numpy as np
import pandas as pd
import configparser


from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from MODULES.DATA_MANAGEMENT.weather_data_provider import Weather_data
from MODULES.CROPS.SIMPLE.evapotranspiration_FAO56_PM import get_ET0

class get_parameters():
    
    def __init__(self, PATH=cwd):
        
        #Are parameters already in spatialized format ?
        self.management_is_spatialized = False
        self.soil_conditions_is_spatialized = False
        self.PFT_composition_is_spatialized = False
        self.crop_init_is_spatialized = False
        
        self.PATH = PATH
        self.crop_init = YAML_Inputs_provider('crop_init_GEMBLOUX.yml', path=PATH+'INPUTS', subpath='CROPS\\GRASSIM').i
        self.PFT_composition = YAML_Inputs_provider('PFT_composition.yml', path=PATH+'INPUTS', subpath='CROPS\\GRASSIM').i
        
        self.config = self.get_config()
        #Crop dimentions (grid size)
        self.nx = int(self.config['Mesh']['x'])
        self.ny = int(self.config['Mesh']['y'])
        
        self.duration = self.get_duration()
        self.management = self.get_management()
        self.soil_conditions = self.get_soil_conditions()
        self.PFT_parameters = self.get_PFT_parameters()
        self.weather = self.get_weather()
        self.WD = self.get_WD()
        #self.ST = self.get_ST()
        #self.Kc = self.get_Kc()
        self.pasture_conditions = self.get_pasture_conditions()
        self.convenience_variables = self.get_convenience_variables()
        
        
        
    def get_config(self):
        
        config = configparser.ConfigParser()
        config.read(self.PATH+'INPUTS\\CROPS\\GRASSIM\\config.ini')
        
        return config

        

    def get_duration(self):
        
        config = self.config
        
        start = int(config['simulation.period']['Start'])
        end = int(config['simulation.period']['End'])
        duration = end - start
        
        return duration
        
        
        
    def get_management(self):
        
        duration = self.duration     
        management_input = YAML_Inputs_provider('Management.yml',path=self.PATH+'INPUTS', subpath='CROPS\\GRASSIM').i
        print(management_input)
        
        grazing_days = pd.to_datetime(management_input['CutDays']).dayofyear
        cut_height = management_input['CutHeight']
        FertlizationDateMin = pd.to_datetime(management_input['FertlizationDateMin']).dayofyear
        FertlizationQuantityMin = management_input['FertlizationQuantityMin']
        FertlizationDateOrg = pd.to_datetime(management_input['FertlizationDateOrg']).dayofyear
        FertlizationQuantityOrg = management_input['FertlizationQuantityOrg']
        print(cut_height)
        #management = pd.DataFrame(0, index=range(duration), columns=["fert_min", "fert_org", "cut_height"])
        cut_height_array = np.zeros((duration,self.nx, self.ny))
        fert_min_array = np.zeros((duration,self.nx, self.ny))
        fert_org_array = np.zeros((duration,self.nx, self.ny))
        
        for j, day in enumerate(FertlizationDateMin):
            fert_min_array[day] = FertlizationQuantityMin[j]
        for j, day in enumerate(FertlizationDateOrg):
            fert_org_array[day] = FertlizationQuantityOrg[j]
        for j, day in enumerate(grazing_days):
            cut_height_array[day] = cut_height[j]
            
        management = np.core.records.fromarrays([fert_min_array, fert_org_array, cut_height_array], names = ["fert_min", "fert_org", "cut_height"])
            
            
        return management
    
    
    
    def get_soil_conditions(self):
        
        crop_init = self.crop_init
        
        sand = crop_init['sand']
        clay = crop_init['clay']
        org = crop_init['org']
        
        if not self.soil_conditions_is_spatialized:
            nx = self.nx
            ny = self.ny
            
            sand = np.full((nx,ny), sand)
            clay = np.full((nx,ny), clay)
            org = np.full((nx,ny), org)

        WaterCapacity = (0.2576-0.002*sand+0.0036*clay+0.0299*org)*1000 
        WaterSaturation = 100/88*WaterCapacity
        Wiltingpoint = (0.026+0.005*clay+0.0158*org)*1000
        
        
        names = ['sand','clay','org','WaterCapacity','WaterSaturation','Wiltingpoint']
        values = [sand,clay,org,WaterCapacity,WaterSaturation,Wiltingpoint]
        
        #soil_conditions = dict(zip(names, values))
        soil_conditions = np.core.records.fromarrays(values, names=names)
        
        return soil_conditions
        
    
    
    def get_PFT_parameters(self):
        
        PFT_parameters = pd.read_csv(self.PATH+"INPUTS\\CROPS\\GRASSIM\\Parameters_values_PFTs.csv", header=0, sep=";", decimal='.')
        PFT_composition = YAML_Inputs_provider('PFT_composition.yml', path=self.PATH+'INPUTS', subpath='CROPS\\GRASSIM').i
        
        clay = self.soil_conditions['clay']
        
        #normalize PFT composition in case the sum of PFT composition is not 1 1
        sum_v= sum(PFT_composition.values())
        PFT_composition = {k:(v/sum_v) for k,v in PFT_composition.items()}

        A = PFT_composition['A']
        B = PFT_composition['B']
        C = PFT_composition['C']
        D = PFT_composition['D']
        
        if not self.PFT_composition_is_spatialized:
            nx = int(self.config['Mesh']['x'])
            ny = int(self.config['Mesh']['y'])
            
            A = np.full((nx,ny), A)
            B = np.full((nx,ny), B)
            C = np.full((nx,ny), C)
            D = np.full((nx,ny), D)
            
        
        #Extract individual parameters for each PFT group
        #------------------------------------------------
        SLA_V  =  PFT_parameters['SLA']# (specific leaf area), Adapted from Cruz et al (2010)
        percentageLAM_V  =  PFT_parameters['percentageLAM'] # # (percentage of laminae)
        ST1_V  =  PFT_parameters['ST1']# oC (initial reproductive growth T), Adapted from Cruz et al (2010)
        ST2_V  =  PFT_parameters['ST2']# oC (end reproductive growth T), Adapted from Cruz et al (2010)
        maxSEA_V  =  PFT_parameters['maxSEA'] # - (maximum seasonal effect)
        minSEA_V  =  PFT_parameters['minSEA'] # - (minimum seasonal effect)
        LLS_V  =  PFT_parameters['LLS']# oC.d (leaf lifespan), Adapted from Cruz et al (2010)
        maxOMDGV_V  =  PFT_parameters['maxOMDGV']# - (max organic matter digestibility of green vegetative)
        minOMDGV_V  =  PFT_parameters['minOMDGV'] # - (min organic matter digestibility of green vegetative)
        maxOMDGR_V  =  PFT_parameters['maxOMDGR'] # - (max organic matter digestibility of green reproductive)
        minOMDGR_V  =  PFT_parameters['minOMDGR'] # - (min organic matter digestibility of green reproductive)
        BDGV_V  =  PFT_parameters['BDGV']# g DM/m^3 (bulk density of green vegetative)
        BDDV_V  =  PFT_parameters['BDDV']# g DM/m^3 (bulk density of dead vegetative)
        BDGR_V  =  PFT_parameters['BDGR']# g DM/m^3 (bulk density of green reproductive)
        BDDR_V  =  PFT_parameters['BDDR'] # g DM/m^3 (bulk density of dead reproductive)

        RUEmax_V = PFT_parameters['RUEmax']
        a_Ncrit_V = PFT_parameters['a_Ncrit']
        b_Ncrit_V = PFT_parameters['b_Ncrit']
        a_Nmax_V = PFT_parameters['a_Nmax']
        b_Nmax_V = PFT_parameters['b_Nmax']
        FNH_coef1_V = PFT_parameters['FNH_coef1']
        FNH_coef2_V = PFT_parameters['FNH_coef2']
        
        # Computing the average value 
        # -----------------------
        SLA  =  SLA_V[0]*A+SLA_V[1]*B+SLA_V[2]*C+SLA_V[3]*D # m^2/g [specific leaf area]
        percentageLAM  =  percentageLAM_V[0]*A+percentageLAM_V[1]*B+percentageLAM_V[2]*C+percentageLAM_V[3]*D # # [percentage of laminae]
        ST1  =  ST1_V[0]*A+ST1_V[1]*B+ST1_V[2]*C+ST1_V[3]*D # oC [initial reproductive growth T]
        ST2  =  ST2_V[0]*A+ST2_V[1]*B+ST2_V[2]*C+ST2_V[3]*D # oC [end reproductive growth T]
        maxSEA  =  maxSEA_V[0]*A+maxSEA_V[1]*B+maxSEA_V[2]*C+maxSEA_V[3]*D  # - [maximum seasonal effect]
        minSEA  =  minSEA_V[0]*A+minSEA_V[1]*B+minSEA_V[2]*C+minSEA_V[3]*D # - [minimum seasonal effect]
        LLS  =  LLS_V[0]*A+LLS_V[1]*B+LLS_V[2]*C+LLS_V[3]*D # oC.d [leaf lifespan]
        maxOMDGV =  maxOMDGV_V[0]*A+maxOMDGV_V[1]*B+maxOMDGV_V[2]*C+maxOMDGV_V[3]*D # - [max organic matter digestibility of green vegetative]
        minOMDGV =  minOMDGV_V[0]*A+minOMDGV_V[1]*B+minOMDGV_V[2]*C+minOMDGV_V[3]*D # - [min organic matter digestibility of green vegetative]
        maxOMDGR =  maxOMDGR_V[0]*A+maxOMDGR_V[1]*B+maxOMDGR_V[2]*C+maxOMDGR_V[3]*D # - [max organic matter digestibility of green reproductive]
        minOMDGR =  minOMDGR_V[0]*A+minOMDGR_V[1]*B+minOMDGR_V[2]*C+minOMDGR_V[3]*D # - [min organic matter digestibility of green reproductive]
        BDGV = BDGV_V[0]*A+BDGV_V[1]*B+BDGV_V[2]*C+BDGV_V[3]*D # g DM/m^3 [bulk density of green vegetative]
        BDDV = BDDV_V[0]*A+BDDV_V[1]*B+BDDV_V[2]*C+BDDV_V[3]*D # g DM/m^3 [bulk density of dead vegetative]
        BDGR = BDGR_V[0]*A+BDGR_V[1]*B+BDGR_V[2]*C+BDGR_V[3]*D # g DM/m^3 [bulk density of green reproductive]
        BDDR = BDDR_V[0]*A+BDDR_V[1]*B+BDDR_V[2]*C+BDDR_V[3]*D # g DM/m^3 (bulk density of dead reproductive)

        RUEmax = RUEmax_V[0]*A+RUEmax_V[1]*B+RUEmax_V[2]*C+RUEmax_V[3]*D #Maximum radiation use efficiency
        a_Ncrit = a_Ncrit_V[0]*A+a_Ncrit_V[1]*B+a_Ncrit_V[2]*C+a_Ncrit_V[3]*D
        b_Ncrit = b_Ncrit_V[0]*A+b_Ncrit_V[1]*B+b_Ncrit_V[2]*C+b_Ncrit_V[3]*D
        a_Nmax = a_Nmax_V[0]*A+a_Nmax_V[1]*B+a_Nmax_V[2]*C+a_Nmax_V[3]*D
        b_Nmax = b_Nmax_V[0]*A+b_Nmax_V[1]*B+b_Nmax_V[2]*C+b_Nmax_V[3]*D
        FNH_coef1 = FNH_coef1_V[0]*A+FNH_coef1_V[1]*B+FNH_coef1_V[2]*C+FNH_coef1_V[3]*D
        FNH_coef2 = FNH_coef2_V[0]*A+FNH_coef2_V[1]*B+FNH_coef2_V[2]*C+FNH_coef2_V[3]*D
        
        #Non-specific parameters
        sigmaGV  =  PFT_parameters['sigmaGV'][0] # - rate of biomass losses with respiration
        sigmaGR  =  PFT_parameters['sigmaGR'][0] # - rate of biomass losses with respiration
        T0 =  PFT_parameters['T0'][0] # oC (min growth air T)
        T1 =  PFT_parameters['T1'][0] # oC (air T at which plateau is reached) 
        T2 =  PFT_parameters['T2'][0]# oC (air T at which growth starts decreasing) 
        Tlimit  =  PFT_parameters['Tlimit'][0] #oC (air T at which growth ends) 
        STmin = PFT_parameters['STmin'][0] # oC (min sum of temperature for growth)
        KGV =  PFT_parameters['KGV'][0]# basic senescence rate for green vegetative
        KGR  =  PFT_parameters['KGR'][0]# basic senescence rate for green reproductive
        KlDV  =  PFT_parameters['KlDV'][0]# basic abscission rate for dead vegetative
        KlDR  =  PFT_parameters['KlDR'][0]# basic abscission rate for dead reproductive
        OMDDV  =  PFT_parameters['OMDDV'][0]# organic matter digestibility of dead vegetative
        OMDDR  =  PFT_parameters['OMDDR'][0]# organic matter digestibility of dead reproductive
        Tref = PFT_parameters['Tref'][0]#reference T for fT in RUelle et al. 2018 for soil activity
        K = PFT_parameters['K'][0]#parameter for fT RUelle et al. 2018 for soil activity
        percentageofNmin = PFT_parameters['percentageofNmin'][0]
        NH3volatfactor = PFT_parameters['NH3volatfactor'][0]#The NH3 volat factor depends on the quality of the fertiliser application methods and conditions and is equal to 0.45 if the quality is bad; 0.6 ? 0.45 if it is average, and 0.1 ? 0.45 if it is good
        repartitionN2NO2 = 0.189+(1.171*clay/(1+0.136*clay))#parameters in Ruelle 2018 for denitrificatoin pathways (N2 vs NO2)
        
        names = ["SLA", "percentageLAM", "ST1", "ST2", "maxSEA", "minSEA", "LLS", "maxOMDGV", "minOMDGV", "maxOMDGR", "minOMDGR", 
                 "BDGV", "BDDV", "BDGR", "BDDR", "sigmaGV", "sigmaGR", "T0", "T1", "T2", "Tlimit", "STmin",
                 "KGV", "KGR", "KlDV", "KlDR", "OMDDV", "OMDDR", "RUEmax","Tref","K","repartitionN2NO2","percentageofNmin","NH3volatfactor",
                 'a_Ncrit','b_Ncrit','a_Nmax','b_Nmax','FNH_coef1','FNH_coef2']
        
        values = [SLA, percentageLAM, ST1, ST2, maxSEA, minSEA,LLS, maxOMDGV, minOMDGV, maxOMDGR, minOMDGR, 
                        BDGV, BDDV, BDGR, BDDR, sigmaGV, sigmaGR, T0, T1, T2, Tlimit, STmin,
                        KGV, KGR, KlDV, KlDR, OMDDV, OMDDR, RUEmax, Tref,K,repartitionN2NO2,percentageofNmin,NH3volatfactor,a_Ncrit,b_Ncrit,
                        a_Nmax,b_Nmax,FNH_coef1,FNH_coef2]
            
        for i, array in enumerate(values):
            values[i] = np.full((self.nx,self.ny), array)
        #PFT_parameters = dict(zip(names, values))
        PFT_parameters = np.core.records.fromarrays(values, names=names)
        
        return PFT_parameters
    
    def get_weather(self):
        weather = pd.read_csv(self.PATH + "/INPUTS/CROPS/Weather_Gembloux_2010.csv",header=0, sep=";", decimal='.')
        Kc = YAML_Inputs_provider('Kc values.yml', path=self.PATH+'INPUTS',subpath='CROPS').i
        
        weather['PARi'] = 0.48*weather['Radiation_MJ']

        #--- computation of ST value ---#
        Tmin = self.crop_init['T1']
        Tmax = self.crop_init['T2']

        #add ST column to weather
        weather['ST_grass'] = np.nan
        weather.loc[0,'ST_grass'] = 0
             
        #Compute ST values
        for j in range(1, len(weather['ST_grass'])):    
            if  ((weather["T"][j-1] >= Tmin) and  (weather["T"][j-1]<=Tmax)) : 
                weather.loc[j,'ST_grass'] = weather.loc[j-1,'ST_grass']+weather.loc[j-1,"T"]-Tmin
            elif (weather["T"][j-1] >Tmax) :
                weather.loc[j,'ST_grass'] = weather.loc[j-1,'ST_grass']+Tmax-Tmin
            else:
                weather.loc[j,'ST_grass'] = weather.loc[j-1,'ST_grass']
                
        #Add Kc to weather column
        #get Kc values for each month
        weather['Day'] = pd.to_datetime(weather['Day'])
        for k in range(0,weather.shape[0]):
            weather.loc[k,'Kc'] = Kc.get(weather['Day'][k].month_name())

        weather = weather.drop(['Day'],axis=1)
        
        #Assumption : weather is homogeneous, can be used for each point
        nx = self.nx
        ny = self.ny
        
        
        names = list(weather.columns)
        
        #values : Numpy array of shape (duration, nx, ny)
        values = []
        #append values with spatialized columns
        for colname in weather:
            spatial_col = np.full((weather.shape[0],nx,ny), np.nan)
            for i,value in enumerate(weather[colname]):
                spatial_value = np.full((nx,ny), value)
                spatial_col[i] = spatial_value
                
            values.append(spatial_col)
                
        #weather = dict(zip(names, values))
        weather = np.core.records.fromarrays(values, names=names)
        
        return weather
    
    
    def get_WD(self, file='Siguesol_loc.yaml'):
        
        '''
        OLD WEATHER FILES
        
        weather = pd.read_csv(self.PATH + "/INPUTS/CROPS/Weather_Gembloux_2010.csv",header=0, sep=";", decimal='.')
        Kc = YAML_Inputs_provider('Kc values.yml', path=self.PATH+'INPUTS',subpath='CROPS').i
        
        weather['PARi'] = 0.48*weather['Radiation_MJ']

        #--- computation of ST value ---#
        Tmin = self.crop_init['T1']
        Tmax = self.crop_init['T2']

        #add ST column to weather
        weather['ST_grass'] = np.nan
        weather.loc[0,'ST_grass'] = 0
             
        #Compute ST values
        for j in range(1, len(weather['ST_grass'])):    
            if  ((weather["T"][j-1] >= Tmin) and  (weather["T"][j-1]<=Tmax)) : 
                weather.loc[j,'ST_grass'] = weather.loc[j-1,'ST_grass']+weather.loc[j-1,"T"]-Tmin
            elif (weather["T"][j-1] >Tmax) :
                weather.loc[j,'ST_grass'] = weather.loc[j-1,'ST_grass']+Tmax-Tmin
            else:
                weather.loc[j,'ST_grass'] = weather.loc[j-1,'ST_grass']
                
        #Add Kc to weather column
        #get Kc values for each month
        weather['Day'] = pd.to_datetime(weather['Day'])
        for k in range(0,weather.shape[0]):
            weather.loc[k,'Kc'] = Kc.get(weather['Day'][k].month_name())

        weather = weather.drop(['Day'],axis=1)
        
        #Assumption : weather is homogeneous, can be used for each point
        nx = self.nx
        ny = self.ny
        
        
        names = list(weather.columns)
        
        #values : Numpy array of shape (duration, nx, ny)
        values = []
        #append values with spatialized columns
        for colname in weather:
            spatial_col = np.full((weather.shape[0],nx,ny), np.nan)
            for i,value in enumerate(weather[colname]):
                spatial_value = np.full((nx,ny), value)
                spatial_col[i] = spatial_value
                
            values.append(spatial_col)
                
        #weather = dict(zip(names, values))
        weather = np.core.records.fromarrays(values, names=names)
        
        return weather
        '''
    
        Loc_1 = YAML_Inputs_provider(file='Siguesol_loc.yaml',path=self.PATH+'INPUTS', subpath='SCENARIOS').i
        
        WD = Weather_data(Loc_1['Latitude'],
                          Loc_1['Longitude'],
                          Loc_1['SimulationStartingYear'],
                          Loc_1['SimulationEndingYear'],
                          Loc_1['WeatherDataOption'],
                          Loc_1['WeatherFileName'],
                          Loc_1['DailyWeatherFileName'])

        return WD.nyears_daily_WD['2005']
    
    def get_ST(self):
        ST = pd.DataFrame(np.nan, index=range(self.duration), columns=['ST'])
        ST.loc[0, 'ST'] = 0
        #--- computation of Sum of Temperature values ---#
        Tmin = self.crop_init['T1']
        Tmax = self.crop_init['T2']      
        WD = self.WD
        
        for j in range(1, len(ST['ST'])):    
            if  ((WD["Avg_temp"][j-1] >= Tmin) and  (WD["Avg_temp"][j-1]<=Tmax)) : 
                ST.loc[j,'ST'] = ST.loc[j-1, 'ST'] + WD.loc[j-1,"Avg_temp"]-Tmin
            elif (WD["T"][j-1] >Tmax) :
                ST.loc[j,'ST'] = ST.loc[j-1,'ST'] + Tmax-Tmin
            else:
                ST.loc[j,'ST'] = ST.loc[j-1,'ST']
                
        return ST
    
    
    
    def get_PARi(self):
        WD = self.WD
        
        PARi = WD['Daily_rad']*0.48
        
        return PARi
        
    def get_PET(self):
        WD = self.WD
        
        PET = get_ET0(WD[year]['Avg_temp'][day],
                      WD[year]['Min_temp'][day],
                      WD[year]['Max_temp'][day],
                      WD[year]['Avg_WS_2m'][day],
                      WD[year]['Vap_press'][day],
                      irradiation,
                      Crop_plot.LAI,
                      day.day_of_year,
                      len(WD[year]['Avg_temp']),
                      lat,
                      alt,
                      Soil_param['Albedo'])
        
        return PET
    
    def get_KC(self):
        Kc_values = YAML_Inputs_provider('Kc values.yml', path=self.PATH+'INPUTS',subpath='CROPS').i
        WD = self.WD
        Kc = pd.DataFrame(np.nan, index=range(self.duration), columns=['Kc'])
        #get Kc values for each month
        days = pd.to_datetime(WD.index)
        for k in range(days):
            Kc.loc[k,'Kc'] = Kc_values.get(days[k].month_name())

        return Kc
        

    def get_pasture_conditions(self):
        
        crop_init = self.crop_init
        print(crop_init)
        PFT_parameters = self.PFT_parameters
        soil_conditions = self.soil_conditions
        
        sward_height  = crop_init['InitialHeight'] #m (average sward height)
        
        BDGV = PFT_parameters['BDGV']
        BDGR = PFT_parameters['BDGR']
        BDDV = PFT_parameters['BDDV']
        BDDR = PFT_parameters['BDDR']
        maxOMDGV = PFT_parameters['maxOMDGV']
        maxOMDGR = PFT_parameters['maxOMDGR']
        minOMDGV = PFT_parameters['minOMDGV']
        minOMDGR = PFT_parameters['minOMDGR']
        LLS = PFT_parameters['LLS']
        ST1 = PFT_parameters['ST1']
        ST2 = PFT_parameters['ST2']
        a_Ncrit = PFT_parameters['a_Ncrit']
        
        WaterCapacity = soil_conditions['WaterCapacity']

        BMGV = sward_height*10*BDGV #[kg/ha] = [m]*[g/m³]*1/1000[kg/g]*10000[m²/ha]
        BMGR = sward_height*10*BDGR 
        BMDV = sward_height*10*BDDV 
        BMDR = sward_height*10*BDDR 
        AGEGV = crop_init['AgeGV']
        AGEGR = crop_init['AgeGR']
        AGEDV = crop_init['AgeDV']
        AGEDR = crop_init['AgeDR']
        water = WaterCapacity
        OMDGV = maxOMDGV-(AGEGV*(maxOMDGV-minOMDGV)/LLS)
        OMDGR = maxOMDGR-(AGEGR*(maxOMDGR-minOMDGR)/(ST2-ST1))
        days = int(self.config['simulation.period']['Start'])
        apex_grazed = crop_init['apex_grazed'] #or 1 depending on previous cuts or grazing events
        notRunoff = crop_init['notRunoff']

        #we assume that at the beginning of the season the plant has at least the minimum amount of N needed for maximum growth
        Nconc = a_Ncrit*0.01 #*(BMGV+BMGR/1000)^-b_Ncrit

        #We assume that at the beginning of the season the N concentration is the same for the green compartments. The same for the dead ones
        QNGV = Nconc*BMGV
        QNGR = Nconc*BMGR
        QNDV = 0.008*BMDV
        QNDR = 0.008*BMDR

        #Mineral and organic soil N
        Nmin = crop_init['Nmin']
        Norg = crop_init['Norg']
        
        names = ['BMGV', 'BMGR', 'BMDV', 'BMDR', 'AGEGV', 'AGEGR','AGEDV','AGEDR','water', 'OMDGV', 'OMDGR', 'days', 
                 'apex_grazed','notRunoff','Norg','Nmin','QNGV','QNGR','QNDV','QNDR','sward_height']
        
        init_values = [BMGV,BMGR,BMDV, BMDR,AGEGV,AGEGR,AGEDV,AGEDR,water,OMDGV,OMDGR,days,
                  apex_grazed,notRunoff,Norg,Nmin,QNGV,QNGR,QNDV,QNDR,sward_height]
        
        #values : Numpy array of shape (duration, nx, ny)
        values = []
        #append values with spatialized columns
        for value in init_values:
            spatial_col = np.full((self.duration,self.nx,self.ny), np.nan)
            spatial_col[0] = value
            values.append(spatial_col)

        #pasture_conditions = dict(zip(names,values))
        pasture_conditions = np.core.records.fromarrays(values, names=names)
        
        return pasture_conditions


    
    def get_convenience_variables(self):
        
        names = ['LAI','PP','Temp','PET','PARi', 'ST', 'SEA', 'AET', 'waterLeached', 'W','fW', 'fT', 'fPARi', 
                 'fAGEGV','fAGEGR', 'fAGEDV', 'fAGEDR', 'ABSDV', 'ABSDR', 'SENGV', 'SENGR','g0', 'fTnitro', 'Vp',
                 'mineralisation', 'Ip', 'immobilization', 'globalemission', 'N2Oemisson', 'Nfromrain', 'Nsupply', 
                 'FNA','Ndemand','RNC','ENV', 'PGRO', 'GRO', 'Nuptake', 'REP','GROGV','GROGR',
                 'Kc','Nplantlitter','TotalplantN','PropNplant','FNH','PPmPET','Ncrit','Nact','fN','NGV','NGR',
                 'NDV','NDR','BMover5','waterCapacity','waterSaturation','Wiltingpoint']
        
        values = []
        
        for i in range(len(names)):
            empty_col = np.full((self.duration+1, self.nx, self.ny), np.nan)
            values.append(empty_col)
            
        #convenience_variables = dict(zip(names, values))
        convenience_variables = np.core.records.fromarrays(values, names=names)
        
        return convenience_variables