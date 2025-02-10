import numpy as np
import copy 

class Soil():
    def __init__(self, grid, inits, variables_to_save):
        self.grid = grid
        self.inits = inits
        self.variables_to_save = variables_to_save
        self.nyears_data = {}
        self.init_spatialized_soil()


    def init_spatialized_soil(self):
        for key, value in self.inits.items():
            setattr(self, key, np.full(self.grid, value))

        self.repartitionN2N2O = 0.189+(1.171*self.clay/(1+0.136*self.clay))
        # limit soil depth to maximum useful depth (usually 1 meter)
        self.soil_depth = self.soil_depth.clip(0, self.max_soil_depth)
        self.water_capacity = (0.2576 - 0.002 * self.sand + 0.0036 * self.clay + 0.0299 * self.org) * self.soil_depth * (1 - self.coarse/100)
        self.wilting_point = (0.026 + 0.005 * self.clay + 0.0158 * self.org) * self.soil_depth * (1 - self.coarse/100)
        self.water_saturation = (100 / 88) * self.water_capacity

        # Initiate water content (arbitrary)
        self.water = self.water_capacity
        self.W = (self.water - self.wilting_point) / (self.water_capacity - self.wilting_point)


    def init_daily_loop(self, day):
        self.day = day
        self.year = str(day.year)

        if self.day.dayofyear == 1:
            self.nyears_data[self.year] = {}
            self.init_one_year_variables()


    def init_one_year_variables(self):
        for var in self.variables_to_save:
            self.nyears_data[self.year][var] = {}


    def compute_water_balance(self, PP, AET):
        self.water += PP - AET + self.not_runoff
        self.water_leached = np.where(self.water < self.water_capacity, 0, 0.2*(self.water - self.water_capacity))
        self.not_runoff = np.where(self.water < self.water_saturation, 0, 0.2*(self.water - self.water_saturation))

        self.water -= self.water_leached
        # water content limits
        self.water = self.water.clip(self.wilting_point, self.water_saturation)

        # Water (%)
        self.W = (self.water - self.wilting_point) / (self.water_capacity - self.wilting_point)
        self.W = self.W.clip(0, 1)

    
    def compute_N_mineralization(self, K, Tref, Temp):
        # Ruelle et al., 2018
        self.g0 = (1 - 0.2) * self.W + 0.2
        self.fT_nitro = np.exp(K * (Temp - Tref))
        self.Vp = (0.0929 + (0.1833-0.0929) * np.exp(-0.2173*self.Norg/1000)) * (self.Norg/1000)
        self.mineralization = self.g0 * self.fT_nitro * self.Vp


    def compute_N_immobilization(self):
        self.Ip = 4. * self.Nmin / 1000
        self.Ip = self.Ip.clip(0, None)
        self.immobilization = self.g0 * self.fT_nitro * self.Ip


    def compute_N_leached(self):
        self.N_leached = self.Nmin * (self.water_leached / self.water)


    def compute_N2O_emissions(self):
        self.globalemission = (self.Nmin/1000) * self.fT_nitro * self.g0
        self.N2Oemisson  =  (1 - self.repartitionN2N2O) * self.globalemission
        self.N2Oemisson = self.N2Oemisson.clip(0, None)
    

    def compute_N_from_rain(self, PP):
        self.N_from_rain = 0.009 * PP


    def compute_Norg(self, percentageofNmin, N_plant_litter, fert_org):
        self.Norg += \
                    self.immobilization \
                    - self.mineralization \
                    + (1. - percentageofNmin) * fert_org \
                    + N_plant_litter


    def compute_Nmin(self, percentageofNmin, NH3volatfactor, N_uptake, fert_org, fert_min):
        self.Nmin += \
                    self.mineralization \
                    - self.immobilization \
                    + self.N_from_rain \
                    + fert_min \
                    + percentageofNmin * (1 - NH3volatfactor) * fert_org \
                    - N_uptake \
                    - self.N_leached
        

    def save_variables(self):
        for var in self.variables_to_save:
            self.nyears_data[self.year][var][self.day] = copy.deepcopy(getattr(self, var))