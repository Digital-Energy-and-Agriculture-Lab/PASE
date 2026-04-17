#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Selim Grote (selim.grote@uliege.be)
#This file is part of the PASE software, and is distributed under the MIT license.

"""
Sloped terrain example (issue #248).

Demonstrates how to simulate a PV Table system on a south-facing inclined terrain
using SlopedGround.  Pole feet are adjusted to the terrain elevation while panel
tilt and azimuth remain unchanged.

Terrain parameters
------------------
TerrainNormalAzimuth   : downhill direction in meteorological convention
                         (0°=North, 90°=East, 180°=South, 270°=West)
TerrainNormalElevation : angle of the terrain normal w.r.t. horizontal
                         (90°=flat, smaller values = steeper slope)

Alternative — YAML-based configuration (PV_Configuration_3D legacy path)
-------------------------------------------------------------------------
Add the following keys to your scenario or AV YAML file and use
PV_Configuration_3D as usual; the ground object is built automatically:

    TerrainNormalAzimuth:
      Value: 180
      Type: float
      Unit: degrees [°]
    TerrainNormalElevation:
      Value: 80
      Type: float
      Unit: degrees [°]
"""

import os

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider, Inputs_aggregator
from pase.ENVIRONMENT.ground import SlopedGround
from pase.ENVIRONMENT.mesh import Mesh
from pase.PHOTOVOLTAICS.configuration import PVConfiguration3D

PASE_Logger()

###############
# Load inputs #
###############
Loc_1 = YAML_Inputs_provider(file='Example1_loc.yaml',
                              subpath='SCENARIOS').inputs
AV_1 = YAML_Inputs_provider(file='Example5_PVTable.yaml',
                             subpath='AV_CENTRAL').inputs
PV_module_1 = YAML_Inputs_provider(file='Example1_PV_Module_landscape.yaml',
                                   subpath=os.path.join('HARDWARE',
                                                        'PV_MODULES')).inputs
Structure = YAML_Inputs_provider(file='PV_table.yaml',
                                 subpath=os.path.join('HARDWARE',
                                                      'STRUCTURES')).inputs

pv_config = Inputs_aggregator([AV_1, PV_module_1, Structure]).aggregated_inputs

#######################
# Terrain definition  #
#######################
# South-facing slope: downhill azimuth 180°, terrain normal elevation 80°
# → ~10° slope angle.  All pole feet are lifted to match the terrain elevation.
# Replace with SlopedGround(90, 85) for a gentler east-facing 5° slope, or
# use Ground() (imported from pase.ENVIRONMENT.ground) for flat terrain.
ground = SlopedGround(terrain_normal_azimuth=180, terrain_normal_elevation=80)

##############################
# Build and visualize scene  #
##############################
scene = PVConfiguration3D(ground=ground)
scene.create_regular_central(pv_config=pv_config)
scene.visualize_simple()

######################################
# Ground mesh for light/crop models  #
######################################
M = Mesh()
M.set_interest_zone_orientation(Loc_1, AV_1)
M.add_oriented_plane_ground_mesh(
    Loc_1['Xmin_InterestZone'],
    Loc_1['Xmax_InterestZone'],
    Loc_1['Ymin_InterestZone'],
    Loc_1['Ymax_InterestZone'],
    Loc_1['dX_InterestZone'],
    Loc_1['dY_InterestZone'],
    flag="crop",
    ground=ground,
)
