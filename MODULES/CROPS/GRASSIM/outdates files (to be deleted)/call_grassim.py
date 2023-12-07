PATH = "C:/Users/lloui/Desktop/Gembloux/Recherche/ROBHERB/Gras-Sim/Python_agrivoltaics_framework/"
import sys
sys.path.append(PATH)

import numpy as np
from GrasSim_spatialized_V2 import GrasSim_spatial
from MODULES.DATA_MANAGEMENT.get_parameters import get_parameters
from MODULES.DATA_MANAGEMENT.save_output import save_array
from MODULES.DATA_MANAGEMENT.save_graphs import GrasSim_graph_saver

PARAMETERS = get_parameters(PATH)
duration = PARAMETERS.duration
management = PARAMETERS.management
weather = PARAMETERS.weather
soil_conditions = PARAMETERS.soil_conditions
PFT_parameters = PARAMETERS.PFT_parameters
pasture_conditions = PARAMETERS.pasture_conditions
convenience_variables = PARAMETERS.convenience_variables



#auxiliary variables
names = ['exported_biomass', 'exported_digestibleOM', 'forage_quality', 'exported_N']
auxiliary_variables = [np.zeros((duration, PARAMETERS.nx, PARAMETERS.ny)) for i in range(len(names))]
auxiliary_variables = np.core.records.fromarrays(auxiliary_variables, names=names)


#initiation of the day-by-day integration loop
print('starting simulation')
for i in range(duration-1): 
    #get model output for day i
    pc, cv, aux_var = GrasSim_spatial(pasture_conditions[i], PFT_parameters, weather[i], soil_conditions, management[i])
    #save model output for next iteration
    pasture_conditions[i+1] = pc  
    convenience_variables[i+1] = cv
    auxiliary_variables[i] = aux_var


#Compute for analytics
#THIS SHOULD BE DONE IN ANOTER MODULE
total_production = pasture_conditions['BMGV'] + pasture_conditions['BMGR'] + pasture_conditions['BMDV'] + pasture_conditions['BMDR']
total_N = pasture_conditions['QNGV'] + pasture_conditions['QNGR'] + pasture_conditions['QNDV'] + pasture_conditions['QNDR']

#Yieldpercut = [i for i in exported_biomass if (type(i) != int)]
#TotalNpercut = [i for i in exported_Ncont if (type(i) != int)]
Annualyield = np.mean(np.sum(auxiliary_variables['exported_biomass'], axis=0))
exported_digestibleOM = np.mean(np.sum(auxiliary_variables['exported_digestibleOM'], axis=0))


#************************************************************#
#                   #Save Data and graphs#                   #
#************************************************************#
save_array(pasture_conditions, PATH+'OUTPUTS/DATA/pc_spatial.npy')
save_array(convenience_variables, PATH+'OUTPUTS/DATA/cv_spatial.npy')
save_array(total_production, PATH+'OUTPUTS/DATA/total_production.npy')
save_array(exported_digestibleOM, 'OUTPUTS/DATA/exported_digestibleOM.npy')
