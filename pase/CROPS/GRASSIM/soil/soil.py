import numpy as np
import copy 
from datetime import datetime

from pase.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization

class Soil():
    def __init__(self, grid, inits, variables_to_save):
        """
        Initialize the soil.
        Set the grid, the initial variables, the variables to save. 
        Initialize the output dictionary and initialize the spatialized soil.

        Args:
            grid: shape of the grid
            grid type: tuple (x, y)
            inits: initial values of variables
            inity type: dictionary
            variables_to_save: names of variables to save in the output dictionary
            variables_to_save type: list
        """
        self.grid = grid
        self.inits = inits
        self.variables_to_save = variables_to_save
        self.nyears_data = {}
        self.init_spatialized_soil()


    def init_spatialized_soil(self):
        """
        Initialize the soil at the start of the simulation.
        Create a numpy array attribute for each init variable.
        Compute the N2/N2O repartition [-], the water capacity [mm], the wilting point [mm], the water saturation [mm], the water content [mm], the water content relative to the water capacity [-].
        """
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
        """
        Initialize the daily loop.
        Set the day, and the year.
        If the first day of the year initialize the output dictionary for the year.

        Args:
            day: today's date
            day type: datetime object
        """
        self.day = day
        self.year = str(day.year)

        if self.day.dayofyear == 1:
            self.nyears_data[self.year] = {}
            self.init_one_year_variables()


    def init_one_year_variables(self):
        """ Initialize the output dictionary of each variable to save for the year. """
        for var in self.variables_to_save:
            self.nyears_data[self.year][var] = {}


    def compute_water_balance(self, PP, AET):
        """Compute water balance (water) [mm] and water stress (W) [%].

        From Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.

        Args:
            PP: daily precipitations [mm].
            PP type: numpy array of shape (grid)
            AET: daily actual evapotranspiration [mm].
            AET type: numpy array of shape (grid)
        """
        self.water += PP - AET + self.not_runoff
        self.water_leached = np.where(self.water < self.water_capacity, 0, 0.2*(self.water - self.water_capacity))
        self.not_runoff = np.where(self.water < self.water_saturation, 0, 0.2*(self.water - self.water_saturation))

        self.water -= self.water_leached
        # water content limits
        self.water = self.water.clip(0, self.water_saturation)

        # Water (%)
        self.W = (self.water - self.wilting_point) / (self.water_capacity - self.wilting_point)
        self.W = self.W.clip(0, 1)

    
    def compute_N_mineralization(self, K, Tref, Temp):
        """Compute nitrogen mineralization based on water stress (W) air temperature (Temp) and soil organic nitrogen (Norg) [kgNorg ha^-1].

        From Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.

        Args:
            K: parameter influencing temperature influence on mineralization [-].
            K type: float
            Tref: reference temperature for mineralization [°C].
            Tref type: float
            Temp: average daily temperature [°C].
            Temp type: numpy array of shape (grid)
        """
        self.g0 = (1 - 0.2) * self.W + 0.2
        self.fT_nitro = np.exp(K * (Temp - Tref))
        self.Vp = (0.0929 + (0.1833-0.0929) * np.exp(-0.2173*self.Norg/1000)) * (self.Norg/1000)
        self.mineralization = self.g0 * self.fT_nitro * self.Vp


    def compute_N_immobilization(self):
        """Compute nitrogen immobilization based on water stress (W), air temperature (Temp) and soil mineral nitrogen (Nmin) [kgN ha^-1].

        From Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.
        """
        self.Ip = 4. * self.Nmin / 1000
        self.Ip = self.Ip.clip(0, None)
        self.immobilization = self.g0 * self.fT_nitro * self.Ip


    def compute_N_leached(self):
        """Compute nitrogen leaching (N_leached) [kgN ha^-1] based on proportion of water leached [mm].

        From Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.
        """
        self.N_leached = self.Nmin * (self.water_leached / self.water)


    def compute_N2O_emissions(self):
        """ Compute nitrogen dioxide emission based on mineral nitrogen (Nmin), water stress (W) and temperature (Temp) influencing denitrification.

         From Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.
        """
        self.globalemission = (self.Nmin/1000) * self.fT_nitro * self.g0
        self.N2Oemisson  =  (1 - self.repartitionN2N2O) * self.globalemission
        self.N2Oemisson = self.N2Oemisson.clip(0, None)
    

    def compute_N_from_rain(self, PP):
        """Compute nitrogen suplly through rain (N_from_rain) [kgN ha^-1].

        From Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.

        Args:
            PP: daily precipitations [mm].
            PP type: numpy array of shape (grid)
        """
        self.N_from_rain = 0.009 * PP


    def compute_Norg(self, percentageofNmin, N_plant_litter, fert_org):
        """Compute soil organic nitrogen balance with inputs and outputs.

        Args:
            percentageofNmin: part of mineral nitrogen in organic fertilizer [-].
            percentageofNmin type: float
            N_plant_litter: amount of organic nitrogen coming from material undergoing abscission [kgNorg ha^-1].
            N_plant_litter type: numpy array of shape (grid)
            fert_org: amount of nitrogen in organic fertilizer [kgN ha^-1].
            fert_org type: float
        """
        self.Norg += \
                    self.immobilization \
                    - self.mineralization \
                    + (1. - percentageofNmin) * fert_org \
                    + N_plant_litter


    def compute_Nmin(self, percentageofNmin, NH3volatfactor, N_uptake, fert_org, fert_min):
        """Compute soil mineral nitrogen balance with inputs and outputs.

        Args:
            percentageofNmin: part of mineral nitrogen in organic fertilizer [-].
            percentageofNmin type: float
            NH3volatfactor: factor allowing to consider amount of N lost by volatilization [-].
            NH3volatfactor type: float
            N_uptake: mineral nitrogen absorbed by plants [kgN ha^-1].
            N_uptake type: dictionary
            fert_org: amount of nitrogen in organic fertilizer [kgN ha^-1].
            fert_org type: float
            fert_min: amount of mineral nitrogen from mineral fertilization [kgN ha^-1].
            fert_min type: float
        """
        self.Nmin += \
                    self.mineralization \
                    - self.immobilization \
                    + self.N_from_rain \
                    + fert_min \
                    + percentageofNmin * (1 - NH3volatfactor) * fert_org \
                    - N_uptake \
                    - self.N_leached
        

    def save_variables(self):
        """ Save the variables in the output dictionary. """
        for var in self.variables_to_save:
            self.nyears_data[self.year][var][self.day] = copy.deepcopy(getattr(self, var))
            
            
    def visualize_map_of_a_variable(self, variable, scene_3D, meshes, year, MM_DD=None, unit=''):
        """
        Visualize a specific spatialized variable in the 3D scene.

        Parameters
        ----------
        variable : string
            Name of the variable to visualize.
        scene_3D : Pyvista Polydata
            3D scene as a pyvista polydata.
        meshes : Mesh object
            Mesh object containing the coordinates of the points of interest.
        year : int
            Year fo which results will be visualized.
        MM_DD : string
            Date as a format 'MM-DD'
        unit : string
            Unit of the variable to visualize.

        Returns
        -------
        None.

        """ 
        
        if type(scene_3D) == list:
            geo = scene_3D[0]
        else:
            geo = scene_3D
        
        open_pyvista_3D_visualization(meshes.sourcepoints[:,:-1], 
                                      self.nyears_data[str(year)][variable][datetime.strptime(str(year)+'-'+MM_DD+' 00:00:00', '%Y-%m-%d %H:%M:%S')], 
                                      geo,
                                      variable+' map GRASSIM '+str(year)+'-'+MM_DD+' ['+unit+']')