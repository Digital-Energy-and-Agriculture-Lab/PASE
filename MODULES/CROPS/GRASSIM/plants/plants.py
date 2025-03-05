import numpy as np
import copy

class Plants():
    def __init__(self, grid, pft_composition, inits, kc_values, pft_values, variables_to_save):
        self.grid = grid
        self.pft_composition = pft_composition
        self.inits = inits
        self.kc_values = kc_values
        self.pft_values = pft_values
        self.variables_to_save = variables_to_save

        self.nyears_data = {}
        
        self.compute_pft_params()
        self.init_spatialized_crop()


    def compute_pft_params(self):
        # Weighted sum of PFT parameters based on PFT composition
        self.pft_values['Weight'] = self.pft_values['PFT'].map(self.pft_composition)
        self.pft_params = self.pft_values.drop(columns=['PFT']).multiply(self.pft_values['Weight'], axis=0).sum().to_dict()
        self.pft_params.pop('Weight', None)
        for key, value in self.pft_params.items():
            setattr(self, key, value)


    def init_spatialized_crop(self):
        if self.inits['BM_init_type'] == "InitialHeight":
            self.init_with_height()
        elif self.inits['BM_init_type'] == "InitialBM":
            self.init_with_BM()
        else :
            raise ValueError(f"BM_init_type '{self.inits['BM_init_type']}' is not valid")
        
        for variable_name in ['ageGV', 'ageGR', 'ageDV', 'ageDR', 'apex_grazed', 'Tmin', 'Tmax']:
            setattr(self, variable_name, np.full(self.grid, self.inits[variable_name]))
        
        self.BM = self.BMGV+self.BMGR+self.BMDV+self.BMDR
        self.OMDGV = self.maxOMDGV-(self.ageGV*(self.maxOMDGV-self.minOMDGV)/self.LLS) #organic mater digestibility of green vegetative biomass
        self.OMDGR = self.maxOMDGV-(self.ageGR*(self.maxOMDGV-self.minOMDGV)/(self.ST2-self.ST1)) #organic mater digestibility of green reproductive biomass
        
        #we assume that at the beginning of the season the plant has at least the minimum amount of N needed for maximum growth
        self.Nconc = self.a_Ncrit*0.01 #*(BMGV+BMGR/1000)^-b_Ncrit

        #We assume that at the beginning of the season the N concentration is the same for the green compartments. The same for the dead ones
        self.QNGV = self.Nconc*self.BMGV
        self.QNGR = self.Nconc*self.BMGR
        self.QNDV = 0.008*self.BMDV
        self.QNDR = 0.008*self.BMDR

        self.LAI = (self.SLA*self.BMGV/10*self.percentageLAM)

        self.NGV = np.divide(self.QNGV, self.BMGV, where=self.BMGV > 0, out=np.zeros_like(self.BMGV)) # GV grass N concentration (kg N/kgDM)
        self.NGR = np.divide(self.QNGR, self.BMGR, where=self.BMGR > 0, out=np.zeros_like(self.BMGR)) # GR grass N concentration (kg N/kgDM)
        self.NDV = np.divide(self.QNDV, self.BMDV, where=self.BMDV > 0, out=np.zeros_like(self.BMDV)) # DV grass N concentration (kg N/kgDM)
        self.NDR = np.divide(self.QNDR, self.BMDR, where=self.BMDR > 0, out=np.zeros_like(self.BMDR)) # DR grass N concentration (kg N/kgDM)
        self.ST = np.zeros(self.grid)


    def init_with_height(self):
        self.sward_height = np.full(self.grid, self.inits['InitialHeight']) # sward height
        self.BMGV = self.sward_height*10*self.BDGV # Green vegetative biomass
        self.BMGR = self.sward_height*10*self.BDGR  # Green reproductive biomass
        self.BMDV = self.sward_height*10*self.BDDV  # Dead vegetative biomass
        self.BMDR = self.sward_height*10*self.BDDR  # Dead reproductive biomass


    def init_with_BM(self):
        self.BMGV = np.full(self.grid, self.inits['BMGV'])
        self.BMDV = np.full(self.grid, self.inits['BMDV'])
        self.BMGR = np.full(self.grid, self.inits['BMGR'])
        self.BMDR = np.full(self.grid, self.inits['BMDR'])
        self.sward_height = np.maximum.reduce([
            self.BMGV/10/self.BDGV, 
            self.BMGR/10/self.BDGR, 
            self.BMDV/10/self.BDDV, 
            self.BMDR/10/self.BDDR
            ])


    def init_daily_loop(self, day, WD, ET0, day_irr):
        self.day = day
        self.year = str(day.year)
        self.PP = np.full(self.grid, WD['Rain'])
        self.Temp = np.full(self.grid, WD['Avg_temp'])
        self.PARi = day_irr*0.48
        self.ET0 = ET0

        if self.day.dayofyear == 1:
            self.ST = np.zeros(self.grid)
            self.nyears_data[self.year] = {}
            self.init_one_year_variables()


    def init_one_year_variables(self):
        for var in self.variables_to_save:
            self.nyears_data[self.year][var] = {}


    def compute_aet(self):
        # get today's Kc value
        month = self.day.month_name()
        self.kc = self.kc_values[month]

        self.AET = self.ET0*self.kc


    def compute_potential_growth(self):
        self.PGRO = self.PARi*self.RUEmax*(1-np.exp(-0.6*self.LAI))*10


    def compute_st(self):
        # For spatialized temperatures : use numpy masks
        mask_in_range = (self.Temp >= self.Tmin) & (self.Temp <= self.Tmax)
        mask_above_Tmax = (self.Temp > self.Tmax)

        self.ST[mask_in_range] += self.Temp[mask_in_range] - self.Tmin[mask_in_range]
        self.ST[mask_above_Tmax] += self.Tmax[mask_above_Tmax] - self.Tmin[mask_above_Tmax]
    

    def compute_fAge(self):
        ratioGV = self.ageGV / self.LLS
        conditions_GV = [ratioGV < 1/3, ratioGV < 1]
        values_GV = [1, 3 * ratioGV]
        self.fageGV = np.select(conditions_GV, values_GV, default=3)
        
        ratioGR = self.ageGR / (self.ST2 - self.ST1)
        conditions_GR = [ratioGR < 1/3, ratioGR < 1]
        values_GR = [1, 3 * ratioGR]
        self.fageGR = np.select(conditions_GR, values_GR, default=3)

        ratioDV = self.ageDV / self.LLS
        conditions_DV = [ratioDV < 1/3, ratioDV < 2/3]
        values_DV = [1, 2]
        self.fageDV = np.select(conditions_DV, values_DV, default=3)

        ratioDR = self.ageDR / (self.ST2 - self.ST1)
        conditions_DR = [ratioDR < 1/3, ratioDR < 2/3]
        values_DR = [1, 2]
        self.fageDR = np.select(conditions_DR, values_DR, default=3)


    def compute_senescence_abscission(self):
        conditions_ABS = [self.Temp > 0]
        values_ABSDV = [self.KlDV * self.BMDV * self.Temp * self.fageDV]
        values_ABSDR = [self.KlDR * self.BMDR * self.Temp * self.fageDR]

        self.ABSDV = np.select(conditions_ABS, values_ABSDV, default=0)
        self.ABSDR = np.select(conditions_ABS, values_ABSDR, default=0)

        conditions_SEN = [self.Temp > self.T0, self.Temp < 0]
        values_SENGV = [
            self.KGV * self.BMGV * self.Temp * self.fageGV,   # Case: Temp > T0
            self.KGV * self.BMGV * abs(self.Temp)          # Case: Temp < 0
        ]
        values_SENGR = [
            self.KGR * self.BMGR * self.Temp * self.fageGR,   # Case: Temp > T0
            self.KGR * self.BMGR * abs(self.Temp)        # Case: Temp < 0
        ]

        self.SENGV = np.select(conditions_SEN, values_SENGV, default=0)
        self.SENGR = np.select(conditions_SEN, values_SENGR, default=0)


    def compute_N_plant_litter(self):
        self.N_plant_litter = (self.ABSDV + self.ABSDR) * 0.008


    def compute_fT(self):
        conditions_fT = [
        self.Temp <= self.T0,                     # Temp <= T0
        self.Temp <= self.T1,                     # Temp <= T1
        self.Temp <= self.T2,                     # Temp <= T2
        self.Temp <= self.Tlimit                  # Temp <= Tlim
            ]
        
        values_fT = [
        0,                                                      # Case: Temp <= T0
        (self.Temp - self.T0) / (self.T1 - self.T0),            # Case: T0 < Temp <= T1
        1,                                                      # Case: T1 < Temp <= T2
        (self.Tlimit - self.Temp) / (self.Tlimit - self.T2),    # Case: T2 < Temp <= Tlim
            ]
        
        self.fT = np.select(conditions_fT, values_fT, default=0)


    def compute_fPARi(self):
        conditions_fPARi = [self.PARi <= 5]

        values_fPARi = [
            1,                              # Case: PARi <= 5
        ]

        self.fPARi = np.select(conditions_fPARi, values_fPARi, default=(1 / 22 * -self.PARi) + 27 / 22)

    def compute_fW(self, W):
        conditions_fW = [
            self.ET0 < 3.81,                        # ET0 < 3.81
            (self.ET0 >= 3.81) & (self.ET0 < 6.35),  # 3.81 <= ET0 < 6.35
        ]

        # Define corresponding values for each condition
        values_fW = [
            np.select(
                [
                    W < 0.2,                # W < 0.2
                    W < 0.4,                # 0.2 <= W < 0.4
                    W < 0.6,                # 0.4 <= W < 0.6
                ],
                [
                    4 * W,                  # W < 0.2
                    0.75 * W + 0.65,        # 0.2 <= W < 0.4
                    0.25 * W + 0.85,        # 0.4 <= W < 0.6
                ],
                default=1                           # W >= 0.6
            ),
            np.select(
                [
                    W < 0.2,                # W < 0.2
                    W < 0.4,                # 0.2 <= W < 0.4
                    W < 0.6,                # 0.4 <= W < 0.6
                    W < 0.8,                # 0.6 <= W < 0.8
                ],
                [
                    2 * W,                  # W < 0.2
                    1.5 * W + 0.1,          # 0.2 <= W < 0.4
                    W + 0.3,                # 0.4 <= W < 0.6
                    0.5 * W + 0.6,          # 0.6 <= W < 0.8
                ],
                default=W                    # W >= 0.8
            )
        ]

        # Apply np.select for the final result
        self.fW = np.select(conditions_fW, values_fW, default=W)
    

    def compute_N_supply(self, Nmin, FNAmax, NSc):
        FNA = FNAmax*(Nmin/NSc)
        FNA = np.clip(FNA, a_min=None, a_max=FNAmax)
        
        self.N_supply = FNA*Nmin


    def compute_fN(self):
        cut_off_BMGV = 0.05*10*self.BDGV
        cut_off_BMDV = 0.05*10*self.BDGR
        cut_off_BMGR = 0.05*10*self.BDDV
        cut_off_BMDR = 0.05*10*self.BDDR
        cut_off_BM = cut_off_BMGV + cut_off_BMDV + cut_off_BMGR + cut_off_BMDR
        
        BMGV_over5 = np.where(self.BMGV>cut_off_BMGV, self.BMGV-cut_off_BMGV, 0)
        BMGR_over5 = np.where(self.BMGR>cut_off_BMGR, self.BMGR-cut_off_BMGR, 0)
        BMDV_over5 = np.where(self.BMDV>cut_off_BMDV, self.BMDV-cut_off_BMDV, 0)
        BMDR_over5 = np.where(self.BMDR>cut_off_BMDR, self.BMDR-cut_off_BMDR, 0)
        self.BMover5 = np.where(self.BM>cut_off_BM, self.BM-cut_off_BM, 0)

        self.Ncrit = np.where(self.BMover5<=1000, self.a_Ncrit*0.01, self.a_Ncrit*0.01*(self.BMover5/1000)**(-self.b_Ncrit))
        self.Nmax = np.where(self.BMover5<=1000, self.a_Nmax*0.01, self.a_Nmax*0.01*(self.BMover5/1000)**(-self.b_Nmax))
        
        RNCmax = 0.9
        RNCmin = 0.4
        
        self.Nact = np.where(self.BMover5<=0, RNCmin*self.Ncrit, (self.NGV*BMGV_over5+self.NGR*BMGR_over5+self.NDV*BMDV_over5+self.NDR*BMDR_over5)/self.BMover5)
        Nactlim = self.Ncrit*RNCmax
        self.Nact = np.clip(self.Nact, a_min=None, a_max=Nactlim)
        
        self.RNC = (self.Nact/self.Ncrit)
        self.RNC= self.RNC.clip(min=RNCmin, max=RNCmax)
        
        self.fN = 0.99*(1-(3.78*np.exp(-5.36*self.RNC)))
        self.fN = self.fN.clip(min=0, max=1)
        
        self.RNC = 0.4
        self.fN = 0.35


    def compute_N_demand(self):
        FNHmax = 0.8
        self.FNH = FNHmax * np.maximum(self.FNH_coef1, self.FNH_coef2 * (1 + self.RNC))
        self.N_demand = self.BMover5 * (self.Nmax - self.Nact) / self.FNH


    def compute_N_uptake(self):
        self.N_uptake = np.minimum(self.N_demand, self.N_supply)


    def compute_environmental_stress(self):
        self.fWfN = np.minimum(self.fN, self.fW)
        self.ENV = self.fPARi * self.fT * self.fWfN

    def compute_seasonal_effect(self):
        conditions_SEA = [
            self.ST < self.STmin,                                       # ST < STmin
            (self.ST >= self.STmin) & (self.ST <= self.ST1 - 200),      # STmin <= ST <= ST1 - 200
            (self.ST > self.ST1 - 200) & (self.ST <= self.ST1 - 100),   # ST1 - 200 < ST <= ST1 - 100
            (self.ST > self.ST1 - 100) & (self.ST <= self.ST2),         # ST1 - 100 < ST <= ST2
        ]

        values_SEA = [
            self.minSEA,  # Case: ST < STmin
            (self.maxSEA - self.minSEA) / (self.ST1 - 100 - self.STmin) * (self.ST - self.STmin) + self.minSEA,  # Case: STmin <= ST <= ST1 - 200
            self.maxSEA,  # Case: ST1 - 200 < ST <= ST1 - 100
            (self.minSEA - self.maxSEA) / (self.ST2 - self.ST1) * (self.ST - self.ST1) + self.maxSEA,  # Case: ST1 - 100 < ST <= ST2
        ]

        self.SEA = np.select(conditions_SEA, values_SEA, default=self.minSEA)

    def compute_actual_growth(self):
        self.GRO = self.PGRO * self.ENV * self.SEA

        conditions_REP = [
        self.ST < self.ST1,
        (self.ST >= self.ST1) & (self.ST < self.ST2) & np.logical_not(self.apex_grazed) & (self.RNC > 0.35)
        ]

        values_REP = [
            0,  # Case: ST < ST1
            0.25 + ((1 - 0.25) * (self.RNC - 0.35)) / (1 - 0.35),  # Case: ST1 <= ST < ST2, apex_grazed is False, RNC > 0.35
        ]       

        self.REP = np.select(conditions_REP, values_REP, default=0)

        self.GROGV = self.GRO * (1 - self.REP)
        self.GROGR = self.GRO * self.REP
            
    def update(self):
        self.BMGV += self.GROGV - self.SENGV
        self.BMGR += self.GROGR - self.SENGR
        self.BMDV += (1-self.sigmaGV) * self.SENGV - self.ABSDV
        self.BMDR += (1-self.sigmaGR) * self.SENGR - self.ABSDR
        self.BM = self.BMGV + self.BMGR + self.BMDV + self.BMDR
        self.sward_height =  np.maximum.reduce([self.BMGV/10/self.BDGV,
                                                self.BMGR/10/self.BDGR,
                                                self.BMDV/10/self.BDDV,
                                                self.BMDR/10/self.BDDR])
        
        self.OMDGV = self.maxOMDGV - (self.ageGV * (self.maxOMDGV - self.minOMDGV)) / self.LLS
        
        conditions_OMDGR = [
            self.ST < self.ST1,  # ST < ST1
            self.ST > self.ST2,  # ST > ST2
        ]

        values_OMDGR = [
            self.maxOMDGR,  # Case: ST < ST1
            self.minOMDGR,  # Case: ST > ST2
        ]

        self.OMDGR = np.select(conditions_OMDGR, values_OMDGR, default=self.maxOMDGR - (self.ageGR * (self.maxOMDGR - self.minOMDGR) / (self.ST2 - self.ST1)))

        self.digestibleOM = self.BMGV * self.OMDGV + self.BMGR * self.OMDGR + self.BMDV * self.OMDDV + self.BMDR * self.OMDDR

        self.QNDV += ((1-self.sigmaGV) * self.SENGV - self.ABSDV) * 0.008
        self.QNDR += ((1-self.sigmaGR) * self.SENGR - self.ABSDR) * 0.008
        mask = self.GRO > 0.0001  # Create a boolean mask
        self.QNGV[mask] += (self.N_uptake[mask] * self.FNH * self.GROGV[mask] / self.GRO[mask]) - self.SENGV[mask] * 0.008
        self.QNGV[~mask] -= self.SENGV[~mask] * 0.008

        self.QNGR[mask] += (self.N_uptake[mask] * self.FNH * self.GROGR[mask] / self.GRO[mask]) - self.SENGR[mask] * 0.008
        self.QNGR[~mask] -= self.SENGR[~mask] * 0.008

        self.QNGV = self.QNGV.clip(min=0)  
        self.QNGR = self.QNGR.clip(min=0)

        TotalplantN = self.QNDV + self.QNDR + self.QNGV + self.QNGR 
        self.PropNplant = TotalplantN/self.BM # kg N/kg DM
        
        self.NGV = np.divide(self.QNGV, self.BMGV, where=self.BMGV > 0, out=np.zeros_like(self.BMGV)) # GV grass N concentration (kg N/kgDM)
        self.NGR = np.divide(self.QNGR, self.BMGR, where=self.BMGR > 0, out=np.zeros_like(self.BMGR)) # GR grass N concentration (kg N/kgDM)
        self.NDV = np.divide(self.QNDV, self.BMDV, where=self.BMDV > 0, out=np.zeros_like(self.BMDV)) # DV grass N concentration (kg N/kgDM)
        self.NDR = np.divide(self.QNDR, self.BMDR, where=self.BMDR > 0, out=np.zeros_like(self.BMDR)) # DR grass N concentration (kg N/kgDM)


    def save_variables(self):
        for var in self.variables_to_save:
            try:
                self.nyears_data[self.year][var][self.day] = copy.deepcopy(getattr(self, var))
            except AttributeError:
                pass
