import pytest 
import numpy as np
from pase.CROPS.GRASSIM.soil.soil import Soil

def test_compute_N_immobilization():
    grid=(1,1)
    init=dict(not_runoff=0,Nmin=50,Norg=50,sand=25,clay=25,coarse=15,org=3,soil_depth=1000,max_soil_depth=1000,albedo=0.2)
    variables_to_save=[]
    soil=Soil(grid,init,variables_to_save)
    soil.compute_water_balance(2, 0.2)
    soil.compute_N_mineralization(0.115, 15, 13) #K=0.115, Tref= 15, Temp=13
    soil.compute_N_immobilization()
    assert np.isclose(soil.immobilization[0,0],0.158906720500667,rtol=1e-8)