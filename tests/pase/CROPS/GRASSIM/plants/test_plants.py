import pytest
import pandas as pd
from pase.CROPS.GRASSIM.plants.plants import Plants
import os
if os.environ.get("CI")=="true":
    fname="tests/pase/CROPS/GRASSIM/plants/Parameters_values_PFT.csv"
    pft_values = pd.read_csv(fname, header=0, sep=";", decimal='.')
else:
    try:
        fname="Parameters_values_PFT.csv"
        pft_values = pd.read_csv(fname, header=0, sep=";", decimal='.')
    except FileNotFoundError:
        fname="tests/pase/CROPS/GRASSIM/plants/Parameters_values_PFT.csv"
        pft_values = pd.read_csv(fname, header=0, sep=";", decimal='.')


def test_interval_fT ():
    grid=(2,2)
    pft_comp={'A': 1,'B': 0,'C': 0,'D': 0}
    inits={'BMDR': 0.0, 'BMDV': 250.0, 'BMGR': 0.0, 'BMGV': 1000.0, 'BM_init_type': 'InitialBM', 'InitialHeight': 0.05, 'Tmax': 18, 'Tmin': 0, 'ageDR': 0, 'ageDV': 0, 'ageGR': 0, 'ageGV': 0, 'apex_grazed': 0}
    kc_values={'April': 0.4, 'August': 0.47, 'December': 0.15, 'February': 0.15, 'January': 0.11, 'July': 0.6, 'June': 0.6, 'March': 0.24, 'May': 0.49, 'November': 0.23, 'October': 0.36, 'September': 0.37}
    variables_to_save=[]
    crop = Plants(grid=grid, pft_composition=pft_comp, inits=inits, kc_values=kc_values, pft_values=pft_values, variables_to_save=variables_to_save)
    crop.Temp=15
    crop.compute_fT()
    assert 0 <= float(crop.fT) <= 1
