import numpy as np 

def GrasSim_spatial(input_args, parameters, weather, cond_soil, management):
    '''
    Parameters
    ----------
    input args : NumPy array of shape (21, nx, ny)
    

    parameters : TYPE
        DESCRIPTION.
        
    CUT_DAY : TYPE
        DESCRIPTION.
        
    weather : TYPE
        DESCRIPTION.
        
    cond_soil : NumPy array shape (6, nx, ny) 
        with values : numpy.rec.recarray object, 
        and dtype : dtype((numpy.record, [('sand', '<i8'), ('clay', '<i8'), ('org', '<i8'),
                                          ('WaterCapacity', '<f8'), ('WaterSaturation', '<f8'), 
                                          ('Wiltingpoint', '<f8')]))

    management : TYPE
        DESCRIPTION.

    Returns
    -------
    
    How to read nested np.where() expression :
        
        np.where(condition, value_if_True, value_if_False)  <---> if condition : 
                                                                      value_if_True
                                                                  else:
                                                                      value_if_False
        np.where(condition1, value_if_True1, 
        np.where(condition2, value_if_True2,value_if_False)  <---> if condition1 : 
                                                                       value_if_True
                                                                   elif condition2:
                                                                       value_if_True2
                                                                   else:
                                                                       value_if_False

    '''

    waterCapacity = cond_soil['WaterCapacity']
    waterSaturation = cond_soil['WaterSaturation']
    Wiltingpoint = cond_soil['Wiltingpoint']
    
    SLA = parameters['SLA']
    percentageLAM = parameters['percentageLAM']
    ST1 = parameters['ST1']
    ST2 = parameters['ST2']
    maxSEA = parameters['maxSEA']
    minSEA = parameters['minSEA']
    LLS = parameters['LLS']
    maxOMDGV = parameters['maxOMDGV']
    minOMDGV = parameters['minOMDGV']
    maxOMDGR = parameters['maxOMDGR']
    minOMDGR = parameters['minOMDGR']
    BDGV = parameters['BDGV']
    BDDV = parameters['BDDV']
    BDGR = parameters['BDGR']
    BDDR = parameters['BDDR']
    sigmaGV = parameters['sigmaGV']
    sigmaGR = parameters['sigmaGR']
    T0 = parameters['T0']
    T1 = parameters['T1']
    T2 = parameters['T2']
    Tlimit = parameters['Tlimit']
    STmin = parameters['STmin']
    KGV = parameters['KGV']
    KGR = parameters['KGR']
    KlDV = parameters['KlDV']
    KlDR = parameters['KlDR']
    OMDDV = parameters['OMDDV']
    OMDDR = parameters['OMDDR']
    RUEmax = parameters['RUEmax']
    Tref = parameters['Tref']#reference T for fT in RUelle et al. 2018 for soil activity
    K = parameters['K'] #parameter for fT RUelle et al. 2018 for soil activity
    repartitionN2NO2 = parameters['repartitionN2NO2']
    percentageofNmin = parameters['percentageofNmin']
    NH3volatfactor = parameters['NH3volatfactor']
    a_Ncrit = parameters['a_Ncrit']
    b_Ncrit = parameters['b_Ncrit']
    a_Nmax = parameters['a_Nmax']
    b_Nmax = parameters['b_Nmax'] 
    FNH_coef1 = parameters['FNH_coef1']
    FNH_coef2 = parameters['FNH_coef2']
    
    
    BMGV = input_args['BMGV']#kgDM/ha (Standing green vegetative biomass)
    BMGR = input_args['BMGR']#kgDM/ha (Standing green reproductive biomass)
    BMDV = input_args['BMDV']#kgDM/ha (Standing dead vegetative biomass)
    BMDR = input_args['BMDR']#kgDM/ha (Standing dead reproductive biomass)
    AGEGV = input_args['AGEGV']#?C.d (mean age of biomass in GV compartment)
    AGEGR = input_args['AGEGR']#?C.d (mean age of biomass in GR compartment)
    AGEDV = input_args['AGEDV']#?C.d (mean age of biomass in DV compartment)
    AGEDR = input_args['AGEDR']#?C.d (mean age of biomass in DR compartment)
    water = input_args['water']# mm (soil water content)
    OMDGV =  input_args['OMDGV']# g/g (organic matter digestibility of green vegetative biomass)
    OMDGR = input_args['OMDGR']# g/g (organic matter digestibility of green reproductive biomass)
    days = input_args['days']# d (sum of days since Jan 1st)
    apex_grazed = input_args['apex_grazed']
    notRunoff = input_args['notRunoff'] # mm water remaining on the paddock after heavy rain from the day before
    Norg = input_args['Norg']# Soil organic N (kg N/ha)
    Nmin = input_args['Nmin']# Soil mineral N (kg N/ha)
    QNGV = input_args['QNGV']# GV grass N content (kg N/ha)
    QNGR = input_args['QNGR']# GR grass N content (kg N/ha)
    QNDV = input_args['QNDV']# DV grass N content (kg N/ha)
    QNDR = input_args['QNDR']# DR grass N content (kg N/ha)
    sward_height = input_args['sward_height']
       
    LAI = (SLA*BMGV/10*percentageLAM)# eq 12 (m?/m?) leaf area index
    
    NGV = QNGV/BMGV# GV grass N concentration (kg N/kgDM)
    NGR = QNGR/BMGR# GR grass N concentration (kg N/kgDM)
    NDV = QNDV/BMDV# DV grass N concentration (kg N/kgDM)
    NDR = QNDR/BMDR# DR grass N concentration (kg N/kgDM)
    
    # Weather parameters for this day
    #---------------------------------
    j = days # convert the state variable J (giving days since Jan 1st into an integar)  
    PP = weather['Rainfall'] # mm (rainfall)
    Temp = weather['T'] # ?C average T
    PET  = weather['ETP']# mm (potential evapotranspiration)
    PPmPET = PP-PET
    PARi  =  weather['PARi']# MJ/m?/d
    ST  = weather['ST_grass']# ?C.d
    Kc = weather['Kc']#crop coefficient for grassland 


    cut_height = management['cut_height']
    #*****************************************************************************
            #Growth Reduction Factors (form Jouven et al., 2006 & Ruelle et al., 2018)
    #*****************************************************************************
    
    #adjustment for water stress
    #-----------------------------
     
    AET = PET*Kc #could depend on GV
    
    water_transient = (water+(PP-AET)+notRunoff)
    
    waterLeached = np.where(water_transient<waterCapacity, 0, 0.2*(water_transient-waterCapacity))
    notRunoff = np.where(water_transient<waterSaturation, 0, 0.2*(water_transient-waterSaturation))

    water_transient=water_transient - waterLeached
    
    #setting the lower and upper boundaries for water content
    water_transient = water_transient.clip(Wiltingpoint,waterSaturation)
    
     # W is the % of available water     
    W = (water_transient-Wiltingpoint)/(waterCapacity-Wiltingpoint)
    W = W.clip(0,1)
     
    # this comes from McCall & Bishop-Hurley 2003: eq 6 in their paper.  
    fW = np.where(PET<3.81, 
        
         np.where(W<0.2, 4*W,
         np.where(W<0.4, 0.75*W+0.65,
         np.where(W<0.6, 0.25*W+0.85,
         1))),
         
         np.where(PET<6.35,
         
        
         np.where(W<0.2, 2*W,
         np.where(W<0.4, 1.5*W+0.1,
         np.where(W<0.6, W+0.3,
         np.where(W<0.8, 0.5*W+0.6,
         1)))),
      
         W
    ))
    
    #adjustment for T
    #-----------------
    fT = np.where(Temp<0, 0,                 
         np.where(Temp<=T1, (Temp-T0)/(T1-T0),
         np.where(Temp<=T2, 1,
         np.where(Temp<=Tlimit, (Tlimit-Temp)/(Tlimit-T2),
         0
         ))))
    
     
    #adjustment for RUE decrease with PAR intensity
    #-----------------------------------------------
    
    fPARi = np.where(PARi<=5, 1, (1/22*-PARi)+27/22)
    
    
    #Seasonal effect
    #----------------
    SEA = np.where(ST<STmin, minSEA,
          np.where(ST<=ST1-200, (maxSEA-minSEA)/(ST1-100-STmin)*(ST-STmin)+minSEA,
          np.where(ST<=ST1-100, maxSEA,
          np.where(ST<=ST2, (minSEA-maxSEA)/(ST2-ST1)*(ST-ST1)+maxSEA,
          minSEA
          ))))
    
    
    
    #*****************************************************************************
                #Senescence and abscission (form Jouven et al., 2006)
    #*****************************************************************************

    fAGEGV = np.where(AGEGV/LLS<1/3, 1,
             np.where(AGEGV/LLS<1, 3*(AGEGV/LLS),
                      3))
    
    fAGEGR = np.where(AGEGV/(ST2-ST1)<1/3, 1,
             np.where(AGEGV/(ST2-ST1)<1, 3*(AGEGV/(ST2-ST1)),
                      3))

    fAGEDV = np.where(AGEDV/LLS<1/3, 1,
             np.where(AGEDV/LLS<2/3, 2,
                      3))
 
    fAGEDR = np.where(AGEGV/(ST2-ST1)<1/3, 1,
             np.where(AGEGV/(ST2-ST1)<2/3, 2,
                      3))

    
    ABSDV = np.where(Temp>0, KlDV*BMDV*Temp*fAGEDV, 0)
    ABSDR = np.where(Temp>0, KlDR*BMDR*Temp*fAGEDR, 0)

    SENGV = np.where(Temp>T0, KGV*BMGV*Temp*fAGEGV,
            np.where(Temp<0, KGV*BMGV*-Temp,
            0))
    
    SENGR = np.where(Temp>T0, KGR*BMGR*Temp*fAGEGR,
            np.where(Temp<0, KGR*BMGR*abs(Temp),
            0))
    
    
    

#*******************************************************************************
             #Mineralization and immobilization (from Ruelle et al., 2018)
#*******************************************************************************
    g0=(1-0.2)*W+0.2
    fTnitro=np.exp(K*(Temp-Tref))
    
    Vp=(0.0929+(0.1833-0.0929)*np.exp(-0.2173*Norg/1000))*Norg/1000
    
    mineralisation=Vp*fTnitro*g0
    Ip=4/1000*Nmin
    Ip=Ip.clip(0)
    immobilization = Ip*fTnitro*g0
  
  
  
#*******************************************************************************
    #Soil N supply and Plant N status (Adapted from Patrico Sandana et. al 2018 & Helge Bonesmo et Gilles B?langer 2002(CATIMO model))
#*******************************************************************************

    #soil N supply
    #--------------
    
    FNAmax =  0.07# 0.02  #Maximum fraction of available soil N - range from 0 to 1
    
    #(0.00012 - 0.00014 in (Ruelle et al., 2018))
    
    NSc = 270#280#250#(kg N/ha) Soil N content (0-45 cm) for maximum N availability (20.3 g N/m2)- range fom 50 to 400
    
    FNA = FNAmax*(Nmin/NSc)
    FNA = FNA.clip(max=FNAmax)
    
    Nsupply = FNA*Nmin
    Nsupply  =  np.where(Nmin<0, 0, Nsupply) #(to avoid going below 0 with Nmin)
    # Nsupply  =  ifelse (Nmin<250, ifelse(Nmin>25,(4-0)/(250)*(Nmin-25)+0.5 ,0.5),4)
    
    
    
    #Total biomass
    #----------- 
    BM = BMGV+BMGR+BMDV+BMDR
    
    #Green biomass
    #-----------
    BMG = BMGV+BMGR
    
    # #Biomass over 5 cm 
    #------------
    cut_off_BM = 0.05*10*BDGV+0.05*10*BDGR+0.05*10*BDDV+0.05*10*BDDR
    
    cut_off_BMGV = 0.05*10*BDGV
    cut_off_BMDV = 0.05*10*BDGR
    cut_off_BMGR = 0.05*10*BDDV
    cut_off_BMDR = 0.05*10*BDDR
    
    BMGR_over5 = BMGR-0.05*10*BDGR
    BMDV_over5 = BMDV-0.05*10*BDDV
    BMDR_over5 = BMDR-0.05*10*BDDR
    
    BMGV_over5 = np.where(BMGV>cut_off_BMGV, BMGV-cut_off_BMGV, 0)
    BMGR_over5 = np.where(BMGR>cut_off_BMGR, BMGR-cut_off_BMGR, 0)
    BMDV_over5 = np.where(BMDV>cut_off_BMDV, BMDV-cut_off_BMDV, 0)
    BMDR_over5 = np.where(BMDR>cut_off_BMDR, BMDR-cut_off_BMDR, 0)
    
    
    #for all the biomass
    #----------------------
    
    BMover5 = np.where(BM>cut_off_BM, BM-cut_off_BM, 0)
    
    
    #Critical N dilution curve according for the different plant functional types
    #--------------------------------------------------------
    Ncrit = np.where(BMover5<=1000, a_Ncrit*0.01, a_Ncrit*0.01*(BMover5/1000)**(-b_Ncrit))
    
    #Maximum plant N content 
    #--------------------------
    
    Nmax = np.where(BMover5<=1000, a_Nmax*0.01, a_Nmax*0.01*(BMover5/1000)**(-b_Nmax))
    
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
    Nact = np.where(BMover5<=0, RNCmin*Ncrit, (NGV*BMGV_over5+NGR*BMGR_over5+NDV*BMDV_over5+NDR*BMDR_over5)/BMover5)
       
    Nactlim = Ncrit*RNCmax
    
    Nact = Nact.clip(max=Nactlim)
    
    #Relative N concentration (RNC)(CATIMO model)
    #-------------------
    RNC = (Nact/Ncrit)
    
    RNC= RNC.clip(min=0.25, max=1)
    
    
    
    
    ##################################################################
    
    # RNC = 0.6
  
  
  
#***********************************************************************************************
  # Plant growth (Adapted from Jouven et al., 2006 & Helge Bonesmo et Gilles B?langer 2002(CATIMO model))
#***********************************************************************************************
  
    #The effect of N status on RUE (fN)(adapted from CATIMO model)
    #--------------------------
    
    fN = 0.99*(1-(3.78*np.exp(-5.36*RNC)))
    fN = fN.clip(min=0, max=1)
    
    #Environmental limitations
    #----------------------
    fWfN = np.where(fW<fN, fW, fN)
    ENV = fPARi*fT*fWfN
    
    #Potential growth 
    #--------------
    PGRO = PARi*RUEmax*(1-np.exp(-0.6*LAI))*10 # eq 12 (kgDM/ha) potential growth
     
    #Total growth
    #----------
    GRO = PGRO*ENV*SEA# eq 11 (kgDM/ha) 
    
    #Vegetative and reproductive growth 
    
    apex_grazed = np.where(np.logical_and(ST>ST1, np.logical_and(ST<ST2, cut_height != 0)), 1, 0)
    
    REP = np.where(ST<ST1, 0,
          np.where(np.logical_and(ST<ST2, np.logical_and(apex_grazed==0, cut_height ==0, RNC>0.35)), 0.25+((1-0.25)*(RNC-0.35))/(1-0.35),
          0
          ))
    
    GROGV = GRO*(1-REP)# eq 1
    GROGR = GRO*REP # eq 2
    
    
    
    #*****************************************************************************
          #Biomass balance, nutritional value and age (from Jouven et al., 2006)
    #*****************************************************************************
    
    #Total biomass after the growth
    #------------
    BMGV = BMGV+GROGV-SENGV# eq 1
    BMGR = BMGR+GROGR-SENGR# eq 2
    BMDV = BMDV+(1-sigmaGV)*SENGV-ABSDV# eq 3
    BMDR = BMDR+(1-sigmaGR)*SENGR-ABSDR# eq 4
    
    BM = BMGV+BMGR+BMDV+BMDR
    
    #Green biomass
    #-----------
    BMG = BMGV+BMGR
  
    
    #sward_height
    #-----------
    
    sward_height =  np.maximum.reduce([BMGV/10/BDGV,BMGR/10/BDGR,BMDV/10/BDDV,BMDR/10/BDDR])#sward_height recalculated from biomass components
    
    
    #Mean age of the biomass
    #----------------
    AGEGV = np.where(Temp>0, AGEGV+(((BMGV-SENGV)/(BMGV-SENGV+GROGV))*(AGEGV+Temp))-AGEGV, AGEGV)
    AGEGR = np.where(Temp>0, AGEGR+(((BMGR-SENGR)/(BMGR-SENGR+GROGR))*(AGEGR+Temp))-AGEGR, AGEGR)
    AGEDV = np.where(Temp>0, AGEDV+(((BMDV-ABSDV)/(BMDV-ABSDV+(1-sigmaGV)*SENGV))*(AGEDV+Temp))-AGEDV, AGEDV)
    AGEDR = np.where(Temp>0, AGEDR+(((BMDR-ABSDR)/(BMDR-ABSDR+(1-sigmaGR)*SENGR))*(AGEDR+Temp))-AGEDR, AGEDR)
    
    
    #Green biomass nutritional value
    #----------------------
    OMDGV = maxOMDGV-(AGEGV*(maxOMDGV-minOMDGV))/LLS
    
    OMDGR = np.where(ST<ST1, maxOMDGR, 
            np.where(ST>ST2, minOMDGR,
            maxOMDGR-(AGEGR*(maxOMDGR-minOMDGR)/(ST2-ST1))
            ))
      
  
#*******************************************************************************
      # N balance plant-sol (Adapted from Ruelle et al., 2018 & Helge Bonesmo et Gilles B?langer 2002(CATIMO model))
#*******************************************************************************
  
    #FNH:The fraction of absorbed N that remains in the aboveground biomas
    #-------------
    FNHmax =  0.8  #Maximum proportion of absorbed N in harvestable biomass (No unit)
    
    FNH = FNHmax*np.maximum(FNH_coef1,FNH_coef2*(1+RNC))
    
    #Plant N demand
    #----------------
    # Nact = min(Nact,Nmax)
    Ndemand = BMover5*((Nmax-Nact))/FNH
     
    #Plant N uptake
    #-------------
    Nuptake = np.minimum(Ndemand,Nsupply)
       
       
    # Plant N content (kg N/ha) 
    #----------------------------
    Nplantlitter = ((ABSDV+ABSDR)*0.008) # from Ruelle 
    QNDV = (QNDV+((1-sigmaGV)*SENGV-ABSDV)*0.008)
    QNDR = (QNDR+((1-sigmaGR)*SENGR-ABSDR)*0.008)
    
    QNGV = np.where(GRO>0, QNGV+ (Nuptake*FNH*GROGV/GRO - SENGV*0.008), QNGV - SENGV*0.008)
    QNGR = np.where(GRO>0, QNGR+ (Nuptake*FNH*GROGR/GRO - SENGR*0.008), QNGR - SENGR*0.008)
    
    
    QNGV = QNGV.clip(min=0)  
    QNGR = QNGR.clip(min=0)
    
    # Total plant N content 
    #----------------
    TotalplantN = QNDV+QNDR+QNGV+QNGR 
    
    #Biomass N concentration
    #------------------
    PropNplant = TotalplantN/BM # kg N/kg DM
    NDV=QNDV/BMDV
    NDR=QNDR/BMDR
    NGV=QNGV/BMGV
    NGR=QNGR/BMGR
  
  
#*********************************************************************************
             #Global N balance (Adapted from Ruelle et al., 2018)
#********************************************************************************
    #N loss by emission and leaching 
    #------------------------------
    globalemission=Nmin/1000*fT*g0
    N2Oemisson  =  (1-repartitionN2NO2)*globalemission
    N2Oemisson = N2Oemisson.clip(min=0)
    NLeached = (Nmin/water_transient)*waterLeached # From Ruelle 
    
    #N supply through rain
    #-----------------
    Nfromrain = 0.009*PP
    # position = days%in%c(start:time)
    
    
    Norg = Norg+immobilization-mineralisation+(1-percentageofNmin)*management["fert_org"]+Nplantlitter# the N content of dead material was ascribed the fixed value of 8 g N/kg DM (Delagarde et al., 2000).(DOI: 10.1080/01431160110114529 and Leconte et Laissus, 1985)  
    Nmin = Nmin +Nfromrain+mineralisation +management["fert_min"] +percentageofNmin*(1-NH3volatfactor)*management["fert_org"] -immobilization-Nuptake -NLeached
    
    # Cut day conditions
    #-------------------
    
    cutBMGV = cut_height*10*BMGV
    cutBMGR = cut_height*10*BMGR
    cutBMDV  = cut_height*10*BMDV
    cutBMDR  = cut_height*10*BMDR
    
    sward_height = np.where(cut_height != 0, cut_height, sward_height)
    resBMGV = np.where(cut_height != 0, cutBMGV, BMGV)
    resBMGR = np.where(cut_height != 0, cutBMGR, BMGR)
    resBMDV = np.where(cut_height != 0, cutBMDV, BMDV)
    resBMDR = np.where(cut_height != 0, cutBMDR, BMDR)
    resQNGV = resBMGV*NGV
    resQNGR = resBMGR*NGR
    resQNDV = resBMDV*NDV
    resQNDR = resBMDR*NDR

        
    exported_biomass = BMGV-resBMGV + BMGR-resBMGR + BMDV-resBMDV + BMDR-resBMDR
    exported_digestibleOM = (BMGV-resBMGV)*OMDGV + (BMGR-resBMGR)*OMDGR + (BMDV-resBMDV)*OMDDV + (BMDR-resBMDR)*OMDDR
    forage_quality = np.where(cut_height != 0, exported_digestibleOM/exported_biomass, np.zeros_like(BMGV))
    exported_N = QNGV-resQNGV + QNGR-resQNGR + QNDV-resQNDV + QNDR-resQNDR
        
        
    
    days += 1
    
    water = water_transient
    output_args =  [resBMGV, resBMGR, resBMDV, resBMDR, AGEGV, AGEGR, AGEDV, AGEDR,
                    water, OMDGV, OMDGR, days, apex_grazed, notRunoff,
                    Norg,Nmin,QNGV,QNGR,QNDV,QNDR,sward_height,
                    LAI,PP,Temp,PET,PARi, ST, SEA, AET, waterLeached, W, 
                    fW, fT, fPARi, fAGEGV,fAGEGR, fAGEDV, fAGEDR, ABSDV, 
                    ABSDR, SENGV, SENGR,g0, fTnitro, Vp,mineralisation, 
                    Ip, immobilization, globalemission, N2Oemisson, Nfromrain, 
                    Nsupply, FNA,Ndemand,RNC,ENV, PGRO, GRO, Nuptake, 
                    REP,GROGV, GROGR,Kc,Nplantlitter,TotalplantN,PropNplant,
                    FNH,PPmPET,Ncrit,Nact,fN,NGV,NGR,NDV,NDR,BMover5,
                    waterCapacity,waterSaturation,Wiltingpoint,
                    exported_biomass, exported_digestibleOM, forage_quality, exported_N]

    output_args_names =  ['BMGV', 'BMGR', 'BMDV', 'BMDR', 'AGEGV', 'AGEGR', 'AGEDV', 'AGEDR',
                        'water', 'OMDGV', 'OMDGR', 'days', 'apex_grazed', 'notRunoff',
                        'Norg', 'Nmin', 'QNGV', 'QNGR', 'QNDV', 'QNDR', 'sward_height',
                        'LAI', 'PP', 'Temp', 'PET', 'PARi', 'ST', 'SEA', 'AET', 'waterLeached', 'W', 
                        'fW', 'fT', 'fPARi', 'fAGEGV', 'fAGEGR', 'fAGEDV', 'fAGEDR', 'ABSDV', 
                        'ABSDR', 'SENGV', 'SENGR', 'g0', 'fTnitro', 'Vp', 'mineralisation', 
                        'Ip', 'immobilization', 'globalemission', 'N2Oemisson', 'Nfromrain', 
                        'Nsupply', 'FNA', 'Ndemand', 'RNC', 'ENV', 'PGRO', 'GRO', 'Nuptake', 
                        'REP', 'GROGV', 'GROGR', 'Kc', 'Nplantlitter', 'TotalplantN', 'PropNplant',
                        'FNH', 'PPmPET', 'Ncrit', 'Nact', 'fN', 'NGV', 'NGR', 'NDV', 'NDR', 'BMover5',
                        'waterCapacity', 'waterSaturation', 'Wiltingpoint',
                        'exported_biomass', 'exported_digestibleOM', 'forage_quality', 'exported_N']
    
    pc_names = output_args_names[0:21]
    pc = output_args[0:21]
    
    cv_names = output_args_names[21:79]
    cv = output_args[21:79]
    
    aux_var_names = output_args_names[79:]
    aux_var = output_args[79:]
    
    pc = np.core.records.fromarrays(pc, names=pc_names)
    cv = np.core.records.fromarrays(cv, names=cv_names)
    aux_var = np.core.records.fromarrays(aux_var, names=aux_var_names)
    
    
    output_args  =  np.core.records.fromarrays(output_args, names = output_args_names)

    return(pc, cv, aux_var)
  



##THE MODEL ENDS HERE