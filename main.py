#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 17 16:06:55 2023

@author: Roxane Bruhwyler
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from windrose import WindroseAxes 
from MODULES.user_support_tools import PASE_Logger
from MODULES.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from MODULES.DATA_MANAGEMENT.weather_data_provider import Weather_data
from MODULES.PHOTOVOLTAICS.configurations import PV_Configuration_3D
from MODULES.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from MODULES.ENVIRONMENT.environment_config import Plane_Ground_regular_meshes
from MODULES.ENVIRONMENT.light import show_light_map, Light_shade_scene
from MODULES.PHOTOVOLTAICS.photovoltaic_systems import PV_system
from MODULES.CROP.evapotranspiration import ET0_FAO56_PM, get_ETo_0D
from MODULES.ENVIRONMENT import Windbreak2D
from MODULES.DATA_MANAGEMENT import graphs


PASE_Logger()

Loc_1 = YAML_Inputs_provider(file='Chanco.yaml').i

PV_1 = YAML_Inputs_provider(file='PV_central.yaml').i

WD = Weather_data(Loc_1['Latitude'],
                  Loc_1['Longitude'],
                  Loc_1['SimulationStartingYear'],
                  Loc_1['SimulationEndingYear'],
                  Loc_1['WeatherDataOption'],
                  Loc_1['WeatherFileName'],
                  Loc_1['DailyWeatherFileName'])

Sun_positions_samp = Sun_positions_sampled(Loc_1['Latitude'],
                                      Loc_1['Longitude'],
                                      Loc_1['PrecisionLevelOnSunPosition'],
                                      Loc_1['LocationName'],
                                      len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                                      Loc_1['TimeZone'])



PV_1_3Dconfig = PV_Configuration_3D(PV_1, Sun_positions_samp.solar_vector,
                                    visualization=False)                        # !!!! Problem with rotation angle that are negative

msh_grid = Plane_Ground_regular_meshes(Loc_1['Xmin_InterestZone'], Loc_1['Xmax_InterestZone'],
                                       Loc_1['Ymin_InterestZone'], Loc_1['Ymax_InterestZone'],
                                       Loc_1['dX_InterestZone'], Loc_1['dY_InterestZone'])



Sun_positions = Sun_positions(Loc_1['Latitude'],
                              Loc_1['Longitude'],
                              len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                              Loc_1['TimeZone'])

Light = Light(WD.nyears, Sun_positions)

PV_central = PV_system(PV_1)


shade_scene = Light_shade_scene(msh_grid,PV_1_3Dconfig.PV_central)
shade_scene.get_light_map(2160, Sun_positions_samp.solar_vector)

shade_scene.get_daily_irradiation_map(Sun_positions_samp.SP,
                                      len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                                      Light.data)



PV_central.get_electricity_production(Sun_positions, Light.data, WD.nyears)


### VISUALISATION (temporary)

show_light_map(shade_scene.dir_map[:,:,40], msh_grid, PV_1_3Dconfig.PV_central, 0, 1, "Relative direct light reaching the ground [-]")
# IF there is one rotation axis
#show_light_map(shade_scene.dir_map[:,:,5], msh_grid, PV_1_3Dconfig.PV_central[5])

show_light_map(shade_scene.diff_map.astype(np.float32), msh_grid, PV_1_3Dconfig.PV_central, 0, 1, "Sky visibility factor [-]")


#temporary lines
j=2
show_light_map(shade_scene.daily_irr_spat['2021'][:,:,j],
               msh_grid,
               PV_1_3Dconfig.PV_central,
               shade_scene.daily_irr_spat['2021'][:,:,j].min(),
               shade_scene.daily_irr_spat['2021'][:,:,j].max(),
               "Total irradiation reaching the ground on the julian day "+str(j)+" [MJ/m²]")

###### LINES FOR THE PAPER !!!! ##### 

porosity = 0.284
#X & Y MESHES
DH = np.arange(Loc_1['Xmin_InterestZone'],Loc_1['Xmax_InterestZone'], Loc_1['dX_InterestZone'])
nY = len(np.arange(Loc_1['Ymin_InterestZone'],Loc_1['Ymax_InterestZone'], Loc_1['dY_InterestZone']))

#Reading of the meteo DB
DB = pd.read_csv(r"DATABASE/METEO/Chanco_Chile_WD.csv").drop(columns=['date','G(h)', 'T2m', 'RH2m',  'PRECIP', 'Gb(n)','Gd(h)'])
WindAngle = np.tile(DB['WD10m'].to_numpy(),(len(DH),1)).reshape((len(DH),365,96))
WindSpeed = np.tile(DB['WS10m'].to_numpy(),(len(DH),1)).reshape((len(DH),365,96))
#WindAngle(DH,day,quarter/hour)

#Projection of the windspeed at 2m
WindSpeed = Windbreak2D.get_wind_speed(WindSpeed)

#Creation of the 2D vector of DH
DH_2D = np.tile(DH,(96,365,1)).transpose()

#Computation of the 2D map of windspeed
WindMap_2D = Windbreak2D.get_ru_Chanco(WindAngle,porosity,DH_2D, WindSpeed, yrep=nY)


#Visualization of the results : mean on the year
plt.imshow(np.mean(WindMap_2D,2).transpose())
ax = plt.gca();
plt.colorbar()
ax.plot()
print('average windspeed at 2m: ' + str(np.mean(WindSpeed)))
print('average windspeed at 2m with the windbreaks :'  + str(np.mean(WindMap_2D)))



# Computation of ET0 for the whole year
ET0_2D = ET0_FAO56_PM(Loc_1['Altitude'], Loc_1['Latitude'], 
                      WD.nyears_daily_WD['2021'], 
                      shade_scene.daily_irr_spat['2021'],
                      WindMap_2D)

pixel_size = Loc_1['dX_InterestZone']*Loc_1['dY_InterestZone']

ET0_2D = ET0_2D*pixel_size #transfo de mm ou L/m² à L sur chaque pixel
index = pd.date_range("01-01-2021"+" 00:00:00", "31-12-2021"+" 23:00:00",
                          freq='D')



#### Graph of annual residual irradiance (direct, diffus and total) on the transect
tsct_daily_dir_irr = shade_scene.daily_dir_irr_spat['2021'][36:105, 49, :]    #34:104
tsct_annual_dir_irr = np.sum(tsct_daily_dir_irr, 1)
tsct_daily_diff_irr = shade_scene.daily_diff_irr_spat['2021'][36:105, 49, :]
tsct_annual_diff_irr = np.sum(tsct_daily_diff_irr, 1)
tsct_daily_tot_irr = shade_scene.daily_irr_spat['2021'][36:105, 49, :]
tsct_annual_tot_irr = np.sum(tsct_daily_tot_irr, 1)

control_annual_dir_irr = np.sum(Light.data['2021']['BHI'])*10**-6*60*60/4
control_annual_diff_irr = np.sum(Light.data['2021']['DHI'])*10**-6*60*60/4
control_annual_tot_irr = np.sum(Light.data['2021']['GHI'])*10**-6*60*60/4

tsct_annual_rel_dir_irr = tsct_annual_dir_irr/control_annual_dir_irr
tsct_annual_rel_diff_irr = tsct_annual_diff_irr/control_annual_diff_irr
tsct_annual_rel_tot_irr = tsct_annual_tot_irr/control_annual_tot_irr

interest_zone_total_irr = np.sum(shade_scene.daily_irr_spat['2021'])*pixel_size  #MJ

interest_zone_control_total_irr = control_annual_tot_irr*28*50
info1 = interest_zone_total_irr/interest_zone_control_total_irr

d = np.arange(0.2,14,0.2)
h = PV_1['Height']+PV_1['PanelDimensionX']
d_h = d/h

graphs.graph_1_Yaxis(d_h, tsct_annual_rel_dir_irr, tsct_annual_rel_tot_irr,
                     tsct_annual_rel_diff_irr, data_x_name='D/H (-)', 
                     data1_name='Direct', 
                     data2_name='Total',
                     data3_name='Diffuse',
                     c1 = '#F0CD4B',
                     c2 ='#F3460B',
                     c3 ='#59A4DE',
                     ax1_name='Irradiation ratio between AgriPV facility and control zone (-)',
                     graph_name='Rel_irradiation_on_tsct', gd_color='#CBCBCB',
                     x_inf=d_h[0], x_sup=d_h[len(d_h)-1])

### Gaph of seasonal irradiation

df_tot_irradiation_tsct = pd.DataFrame(np.transpose(shade_scene.daily_irr_spat['2021'][36:105, 49, :]))

df_tot_irradiation_tsct = df_tot_irradiation_tsct.set_index(index)

tot_irr_1 = np.sum(Light.data['2021']['GHI'].loc[(Light.data['2021']['GHI'].index.month==1) |
                                                 (Light.data['2021']['GHI'].index.month==2) |
                                                 (Light.data['2021']['GHI'].index.month==3)].to_numpy())*10**-6*60*60/4
tot_irr_2 = np.sum(Light.data['2021']['GHI'].loc[(Light.data['2021']['GHI'].index.month==4) |
                                                 (Light.data['2021']['GHI'].index.month==5) |
                                                 (Light.data['2021']['GHI'].index.month==6)].to_numpy())*10**-6*60*60/4
tot_irr_3 = np.sum(Light.data['2021']['GHI'].loc[(Light.data['2021']['GHI'].index.month==7) |
                                                 (Light.data['2021']['GHI'].index.month==8) |
                                                 (Light.data['2021']['GHI'].index.month==9)].to_numpy())*10**-6*60*60/4
tot_irr_4 = np.sum(Light.data['2021']['GHI'].loc[(Light.data['2021']['GHI'].index.month==10) |
                                                 (Light.data['2021']['GHI'].index.month==11) |
                                                 (Light.data['2021']['GHI'].index.month==12)].to_numpy())*10**-6*60*60/4


tot_rel_irrad_tsct_1 = np.sum(df_tot_irradiation_tsct.loc[(df_tot_irradiation_tsct.index.month == 1) | 
                                  (df_tot_irradiation_tsct.index.month == 2) | 
                                  (df_tot_irradiation_tsct.index.month == 3)].to_numpy(), 0)/tot_irr_1
tot_rel_irrad_tsct_2 = np.sum(df_tot_irradiation_tsct.loc[(df_tot_irradiation_tsct.index.month == 4) | 
                                  (df_tot_irradiation_tsct.index.month == 5) | 
                                  (df_tot_irradiation_tsct.index.month == 6)].to_numpy(), 0)/tot_irr_2
tot_rel_irrad_tsct_3 = np.sum(df_tot_irradiation_tsct.loc[(df_tot_irradiation_tsct.index.month == 7) | 
                                  (df_tot_irradiation_tsct.index.month == 8) | 
                                  (df_tot_irradiation_tsct.index.month == 9)].to_numpy(), 0)/tot_irr_3
tot_rel_irrad_tsct_4 = np.sum(df_tot_irradiation_tsct.loc[(df_tot_irradiation_tsct.index.month == 10) | 
                                  (df_tot_irradiation_tsct.index.month == 11) | 
                                  (df_tot_irradiation_tsct.index.month == 12)].to_numpy(), 0)/tot_irr_4




graphs.graph_1_Yaxis(d_h, tot_rel_irrad_tsct_1, tot_rel_irrad_tsct_2, tot_rel_irrad_tsct_3, tot_rel_irrad_tsct_4,
                     data_x_name='D/H (-)', 
                     data1_name='Jan-Feb-Mar', 
                     data2_name='Apr-May-June',
                     data3_name='July-Aug-Sept',
                     data4_name='Oct-Nov-Dec',
                     c1 = '#F0CD4B',
                     c2 ='#A891D4',
                     c3 ='#59A4DE',
                     c4 ='#F3660B',
                     ax1_name='Total irradiation ratio between AgriPV facility and control zone (-)',
                     graph_name='rel_tot_irr_seasonal_tsct', gd_color='#CBCBCB',
                     x_inf=d_h[0], x_sup=d_h[len(d_h)-1])


### Graph of annual mean wind speed on the transect compared with control zone

mean_annual_WS_2D = np.mean(WindMap_2D, 2)
tsct_mean_annual_WS = mean_annual_WS_2D[36:105, 49]
mean_WS_control = np.mean(WindSpeed, 2)
mean_WS_control = np.mean(mean_WS_control,1)[36:105]
tsct_mean_annual_Ru = tsct_mean_annual_WS/mean_WS_control

graphs.graph_1_Yaxis(d_h, tsct_mean_annual_WS, data3 = tsct_mean_annual_Ru,
                     data_x_name='D/H (-)', 
                     data1_name='Wind speed at 2 m height in the AgriPV facility (m/s)', 
                     data3_name='Wind speed ratio between AgriPV and control zone (-)',
                     c1 ='#59A4DE',
                     c3 ='#F3660B',
                     ax1_name=' ',
                     graph_name='Wind_speed_and_Rucoeff_tsct', gd_color='#CBCBCB',
                     x_inf=d_h[0], x_sup=d_h[len(d_h)-1])

## Gaph of seasonal wind speed on the transect

wind_speed_tsct_df = pd.DataFrame(np.transpose(WindMap_2D[36:105, 49, :]))

wind_speed_tsct_df = wind_speed_tsct_df.set_index(index)

df_mean_WS_control = pd.DataFrame(np.transpose(np.mean(WindSpeed, 2))).set_index(index)
mean_WS_control_1 = np.mean(df_mean_WS_control.loc[(df_mean_WS_control.index.month==1) |
                                                   (df_mean_WS_control.index.month==2) |
                                                   (df_mean_WS_control.index.month==3)].to_numpy())
mean_WS_control_2 = np.mean(df_mean_WS_control.loc[(df_mean_WS_control.index.month==4) |
                                                   (df_mean_WS_control.index.month==5) |
                                                   (df_mean_WS_control.index.month==6)].to_numpy())
mean_WS_control_3 = np.mean(df_mean_WS_control.loc[(df_mean_WS_control.index.month==7) |
                                                   (df_mean_WS_control.index.month==8) |
                                                   (df_mean_WS_control.index.month==9)].to_numpy())
mean_WS_control_4 = np.mean(df_mean_WS_control.loc[(df_mean_WS_control.index.month==10) |
                                                   (df_mean_WS_control.index.month==11) |
                                                   (df_mean_WS_control.index.month==12)].to_numpy())

rel_WS_tsct_1 = np.mean(wind_speed_tsct_df.loc[(wind_speed_tsct_df.index.month == 1) | 
                                  (wind_speed_tsct_df.index.month == 2) | 
                                  (wind_speed_tsct_df.index.month == 3)].to_numpy(), 0)/mean_WS_control_1
rel_WS_tsct_2 = np.mean(wind_speed_tsct_df.loc[(wind_speed_tsct_df.index.month == 4) | 
                                  (wind_speed_tsct_df.index.month == 5) | 
                                  (wind_speed_tsct_df.index.month == 6)].to_numpy(), 0)/mean_WS_control_2
rel_WS_tsct_3 = np.mean(wind_speed_tsct_df.loc[(wind_speed_tsct_df.index.month == 7) | 
                                  (wind_speed_tsct_df.index.month == 8) | 
                                  (wind_speed_tsct_df.index.month == 9)].to_numpy(), 0)/mean_WS_control_3
rel_WS_tsct_4 = np.mean(wind_speed_tsct_df.loc[(wind_speed_tsct_df.index.month == 10) | 
                                  (wind_speed_tsct_df.index.month == 11) | 
                                  (wind_speed_tsct_df.index.month == 12)].to_numpy(), 0)/mean_WS_control_4

graphs.graph_1_Yaxis(d_h, rel_WS_tsct_1, rel_WS_tsct_2, rel_WS_tsct_3, rel_WS_tsct_4,
                     data_x_name='D/H (-)', 
                     data1_name='Jan-Feb-Mar', 
                     data2_name='Apr-May-June',
                     data3_name='July-Aug-Sept',
                     data4_name='Oct-Nov-Dec',
                     c1 = '#F0CD4B',
                     c2 ='#A891D4',
                     c3 ='#59A4DE',
                     c4 ='#F3660B',
                     ax1_name='Wind speed ratio between AgriPV facility and control zone (-)',
                     graph_name='rel_WS_tsct_season', gd_color='#CBCBCB',
                     x_inf=d_h[0], x_sup=d_h[len(d_h)-1])



### Graph of annual relative ET0 along the transect

ET0_tsct = pd.DataFrame(np.transpose(ET0_2D[36:105, 49, :]/pixel_size))  # L to L/m² ou mm

ET0_tsct = ET0_tsct.set_index(index)

ET0_controle = np.zeros(len(index))
daily_WS_2m = Windbreak2D.get_wind_speed(WD.nyears_daily_WD['2021']['Avg_WS_10m'])

for day in range(len(index)):
    
    ET0_controle[day] = get_ETo_0D(WD.nyears_daily_WD['2021']['Min_temp'][day],
                                   WD.nyears_daily_WD['2021']['Max_temp'][day],
                                   WD.nyears_daily_WD['2021']['Avg_temp'][day],
                                   WD.nyears_daily_WD['2021']['Min_RH'][day],
                                   WD.nyears_daily_WD['2021']['Max_RH'][day],
                                   WD.nyears_daily_WD['2021']['Daily_rad'][day],
                                   daily_WS_2m[day],
                                   Loc_1['Altitude'], Loc_1['Latitude'], day+1, len(index))
    
ET0_controle = pd.DataFrame(ET0_controle).set_index(index)
ET0_controle1 = np.sum(ET0_controle.loc[(ET0_controle.index.month == 1) | 
                                  (ET0_controle.index.month == 2) | 
                                  (ET0_controle.index.month == 3)].to_numpy(), 0)
ET0_controle2 = np.sum(ET0_controle.loc[(ET0_controle.index.month == 4) | 
                                  (ET0_controle.index.month == 5) | 
                                  (ET0_controle.index.month == 6)].to_numpy(), 0)
ET0_controle3 = np.sum(ET0_controle.loc[(ET0_controle.index.month == 7) | 
                                  (ET0_controle.index.month == 8) | 
                                  (ET0_controle.index.month == 9)].to_numpy(), 0)
ET0_controle4 = np.sum(ET0_controle.loc[(ET0_controle.index.month == 10) | 
                                  (ET0_controle.index.month == 11) | 
                                  (ET0_controle.index.month == 12)].to_numpy(), 0)


ET0_tsct_1 = np.sum(ET0_tsct.loc[(ET0_tsct.index.month == 1) | 
                                  (ET0_tsct.index.month == 2) | 
                                  (ET0_tsct.index.month == 3)].to_numpy(), 0)
ET0_tsct_2 = np.sum(ET0_tsct.loc[(ET0_tsct.index.month == 4) | 
                                  (ET0_tsct.index.month == 5) | 
                                  (ET0_tsct.index.month == 6)].to_numpy(), 0)
ET0_tsct_3 = np.sum(ET0_tsct.loc[(ET0_tsct.index.month == 7) | 
                                  (ET0_tsct.index.month == 8) | 
                                  (ET0_tsct.index.month == 9)].to_numpy(), 0)
ET0_tsct_4 = np.sum(ET0_tsct.loc[(ET0_tsct.index.month == 10) | 
                                  (ET0_tsct.index.month == 11) | 
                                  (ET0_tsct.index.month == 12)].to_numpy(), 0)

ET0_tsct_1_rel = ET0_tsct_1/ET0_controle1
ET0_tsct_2_rel = ET0_tsct_2/ET0_controle2
ET0_tsct_3_rel = ET0_tsct_3/ET0_controle3
ET0_tsct_4_rel = ET0_tsct_4/ET0_controle4


graphs.graph_1_Yaxis(d_h, ET0_tsct_1_rel, ET0_tsct_2_rel, ET0_tsct_3_rel, ET0_tsct_4_rel,
                     data_x_name='D/H (-)', 
                     data1_name='Jan-Feb-Mar', 
                     data2_name='Apr-May-June',
                     data3_name='July-Aug-Sept',
                     data4_name='Oct-Nov-Dec',
                     c1 = '#F0CD4B',
                     c2 ='#A891D4',
                     c3 ='#59A4DE',
                     c4 ='#F3660B',
                     ax1_name='ET0 ratio between AgriPV facility and control zone (-)',
                     graph_name='rel_ET0_seasonal_tsct', gd_color='#CBCBCB',
                     x_inf=d_h[0], x_sup=d_h[len(d_h)-1])

# Mean wind speed for each season

daily_WS_2m_df = pd.DataFrame(
    ).set_index(index)
daily_WS_2m_1 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 1) | 
                                  (daily_WS_2m_df.index.month == 2) | 
                                  (daily_WS_2m_df.index.month == 3)].to_numpy(), 0)
daily_WS_2m_2 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 4) | 
                                  (daily_WS_2m_df.index.month == 5) | 
                                  (daily_WS_2m_df.index.month == 6)].to_numpy(), 0)
daily_WS_2m_3 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 7) | 
                                  (daily_WS_2m_df.index.month == 8) | 
                                  (daily_WS_2m_df.index.month == 9)].to_numpy(), 0)
daily_WS_2m_4 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 10) | 
                                  (daily_WS_2m_df.index.month == 11) | 
                                  (daily_WS_2m_df.index.month == 12)].to_numpy(), 0)
"""
test1 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 1)].to_numpy(), 0)
test2 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 2)].to_numpy(), 0)
test3 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 3)].to_numpy(), 0)
test4 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 4)].to_numpy(), 0)
test5 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 5)].to_numpy(), 0)
test6 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 6)].to_numpy(), 0)
test7 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 7)].to_numpy(), 0)
test8 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 8)].to_numpy(), 0)
test9 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 9)].to_numpy(), 0)
test10 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 10)].to_numpy(), 0)
test11 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 11)].to_numpy(), 0)
test12 = np.mean(daily_WS_2m_df.loc[(daily_WS_2m_df.index.month == 12)].to_numpy(), 0)
"""


# Graph monthly ET0 control, irr reduction and wind reduction

ET0_tot_interest_zone = pd.DataFrame(np.sum(np.sum(ET0_2D, 0), 0)/(28*50)).set_index(index)   # mm for each day

monthly_ET0_agriPV = ET0_tot_interest_zone.resample('M').sum().to_numpy().reshape(12)
monthly_ET0_control = ET0_controle.resample('M').sum().to_numpy().reshape(12)

wind_2D_noreduction = np.zeros((140,100,365))
test = np.mean(WindSpeed, 2)
for i in range(len(wind_2D_noreduction[0,:,0])):
    wind_2D_noreduction[:,i,:] = test

ET0_agriPV_withoutwindreduction = ET0_FAO56_PM(Loc_1['Altitude'], Loc_1['Latitude'], 
                                               WD.nyears_daily_WD['2021'], 
                                               shade_scene.daily_irr_spat['2021'],
                                               wind_2D_noreduction)*pixel_size      # L

ET0_tot_interest_zone_wth_windred = pd.DataFrame(np.sum(np.sum(ET0_agriPV_withoutwindreduction, 0), 0)/(28*50)).set_index(index)   # mm for each day
monthly_ET0_agriPV_wthout_windred = ET0_tot_interest_zone_wth_windred.resample('M').sum().to_numpy().reshape(12)

month_list = ['Jan', 'Feb', 'Mar', 'Apr', 'May','June','July','Aug','Sept','Oct','Nov','Dec']

monthly_ET0_df = pd.DataFrame()
monthly_ET0_df['month'] = month_list
monthly_ET0_df['ET0_controle'] = monthly_ET0_control
monthly_ET0_df['ET0_rad_red'] = monthly_ET0_agriPV_wthout_windred
monthly_ET0_df['ET0_rad_wind_red'] = monthly_ET0_agriPV
  
graphs.histogram_3or4_series(monthly_ET0_df['month'], monthly_ET0_df['ET0_controle'], 
                             monthly_ET0_df['ET0_rad_red'],
                             monthly_ET0_df['ET0_rad_wind_red'], 'Control',
                          'Irradiation reduced', 'Irradiation and wind speed reduced', 
                          'Cumulated ET0 (mm)', 'MonthlyET0_compared')

annual_ET0_control = np.sum(monthly_ET0_control)
annual_ET0_irr_red = np.sum(monthly_ET0_agriPV_wthout_windred)
annual_ET0_irr_wind_red = np.sum(monthly_ET0_agriPV)
info2 = annual_ET0_irr_red/annual_ET0_control
info3 = 1-(monthly_ET0_agriPV_wthout_windred/monthly_ET0_control)
info4 = 1-(annual_ET0_irr_wind_red/annual_ET0_control)
info5 = 1-(monthly_ET0_agriPV/monthly_ET0_control)
info6 = 1-(monthly_ET0_agriPV/monthly_ET0_agriPV_wthout_windred)


#### WINDROSE wind direction with wind speed  ####
wind_QH = DB['WD10m'].to_numpy()
ind = np.where(wind_QH>180)
wind_QH = wind_QH+180
wind_QH[ind] = wind_QH[ind]-360

fig = plt.figure()
ax = WindroseAxes.from_ax()
ax.bar(wind_QH, DB['WS10m'], normed=True, opening=1, edgecolor="black", bins=[0, 2, 4, 5, 6, 8, 10])
ax.set_legend(loc='lower left', title='Wind speed (m/s)', title_fontsize=20, labelspacing=0.8, handleheight=2.5, handlelength=4.5)
plt.setp(plt.gca().get_legend().get_texts(), fontsize='18')
ax.set_xticklabels(['E', 'NE','N', 'NW', 'W', 'SW', 'S', 'SE'], fontsize=18)
ax.set_yticklabels(['4.6 %', '9.2 %','13.8 %', '18.4 %', '23.0 %'], fontsize=18, verticalalignment='bottom', horizontalalignment='right')
plt.savefig('OUTPUTS/GRAPHS/windrose.png')



# Windrose with wind direction in function of the month

new_index = pd.date_range(f"01-01-2021 00:00:00",
                          f"31-12-2021 23:45:00",
                          freq='15Min')
M = new_index.month

ax = WindroseAxes.from_ax()
ax.bar(wind_QH, M, normed=True, opening=0.9, edgecolor="white", bins=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
ax.set_legend(loc='lower left', title='Month ID')
ax.set_xticklabels(['E', 'NE','N', 'NW', 'W', 'SW', 'S', 'SE'])
plt.savefig('windrose_month.png')



"""
from datetime import datetime
test = pd.read_csv('DATABASE/METEO/Chili_WD.csv', ';')
test['date'] = pd.to_datetime(test['date'])
test['date'] = pd.to_datetime(test['date'], format='%d-%m-%Y %H:%M:%S')
test = test.set_index(test['date'])
mask = ((test['date']>='01-01-2021 00:00:00') & 
       (test['date']<'01-01-2022 00:00:00'))

test = test.set_index(test['date'])
test = test.drop(['date'], axis=1)
test.index = pd.to_datetime(test.index)
test.index = test.index.strftime('%d-%m-%Y %H:%M:%S')
test2 = test.loc[test.index.year == 2021]
mask = ((test.index>='01-01-2021 00:00:00') & 
       (test.index<'01-01-2022 00:00:00'))

"""
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pvlib

fig = plt.figure()        
ax = plt.subplot(1, 1, 1, projection='polar')
points = ax.scatter(np.radians(Sun_positions.SP.azimuth), Sun_positions.SP.apparent_zenith,
                    s=2, label=None, c=Sun_positions.SP.J_day.round(0))
ax.figure.colorbar(points)

Sun_positions.SP = Sun_positions.SP.reset_index(level='hour')

# draw hour labels
SP_june = Sun_positions.SP.query("month == 6")
for h in np.unique(SP_june.hour):
    # choose label position by the smallest radius for each hour
    subset = SP_june.loc[SP_june['hour'] == h]
    r = subset.apparent_zenith
    print(r)
    pos = subset.loc[r.idxmin(),:]
    ax.text(np.radians(pos['azimuth']), pos['apparent_zenith'], str(h))
 
# draw individual days
for date in pd.to_datetime(['2019-03-21', '2019-06-21', '2019-12-21']):
    times = pd.date_range(date, date+pd.Timedelta('24h'), freq='5min')
    solpos = pvlib.solarposition.get_solarposition(times, 
                                                   Sun_positions.lat,
                                                   Sun_positions.long)
    solpos = solpos.loc[solpos['apparent_elevation'] > 0, :]
    label = date.strftime('%Y-%m-%d')
    ax.plot(np.radians(solpos.azimuth), solpos.apparent_zenith, label=label)

ax.figure.legend(loc='upper left')

# change coordinates to be like a compass
ax.set_theta_zero_location('N')
ax.set_theta_direction(-1)
ax.set_rmax(90)

fig.savefig('OUTPUTS/GRAPHS/SunPathDiagram_'+Sun_positions.loc_name+'.svg')

"""

















"""

import pyvista as pv
import numpy as np

grid = pv.StructuredGrid(msh_grid.X, msh_grid.Y, np.ones((len(msh_grid.X[:,0]),len(msh_grid.X[0,:])))*0.05)

test1 = Direct_light_map.direct_map_hours[0,:,:].ravel()

plotter = pv.Plotter()

plotter.add_mesh(PV_1_3Dconfig.PV_central, color='black')
ground = np.array([[-100, 100, 0],
                   [100, 100, 0],
                   [-100, -100, 0],
                   [100, -100, 0]])

ground_m = np.hstack([[3, 0, 1, 2],    
                      [3, 1, 2, 3],])

grnd = pv.PolyData(ground, ground_m)

plotter.add_mesh(grnd, color='green')
plotter.show_axes()

plotter.add_mesh(
    grid,
    scalars=test1,
    lighting=False,
    show_edges=True,
    scalar_bar_args={"title": "Height"},
    clim=[0, 1])

#plotter.show()

# Open a gif
plotter.open_gif(filename="shade.gif", loop=0, fps=1)

pts = grid.points.copy()

# Update Z and write a frame for each updated position
nframe = 146
for s in range(nframe)[:nframe]:
    plotter.update_coordinates(pts, render=False)
    test = Direct_light_map.direct_map_hours[s,:,:].ravel()
    plotter.update_scalars(test, render=False)

    # Write a frame. This triggers a render.
    plotter.write_frame()

# Closes and finalizes movie
plotter.close()

"""
