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

Terrain parameters (defined in the AV YAML file — see Example_SlopedTerrain.yaml)
---------------------------------------------------------------------------------
TerrainSlopeAngle  : terrain inclination w.r.t. horizontal [°]
                     (0°=flat, larger values = steeper slope)
TerrainSlopeAspect : downhill direction in meteorological convention
                     (0°=North, 90°=East, 180°=South, 270°=West)

The slope is no longer hardcoded in this script: it is read from the YAML
configuration and the ground object is built via ``ground_from_config``.
The same keys also drive the legacy ``PV_Configuration_3D`` path automatically.

    TerrainSlopeAngle:
      Value: 10
      Type: float
      Unit: degrees [°]
    TerrainSlopeAspect:
      Value: 180
      Type: float
      Unit: degrees [°]
"""

import os

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider, Inputs_aggregator
from pase.ENVIRONMENT.ground import ground_from_config
from pase.ENVIRONMENT.mesh import Mesh
from pase.PHOTOVOLTAICS.configuration import PVConfiguration3D

PASE_Logger()

###############
# Load inputs #
###############
Loc_1 = YAML_Inputs_provider(file='Example1_loc.yaml',
                              subpath='SCENARIOS').inputs
AV_1 = YAML_Inputs_provider(file='Example_SlopedTerrain.yaml',
                             subpath='AV_CENTRAL').inputs
PV_module_1 = YAML_Inputs_provider(file='Example1_PV_Module_landscape.yaml',
                                   subpath=os.path.join('HARDWARE',
                                                        'PV_MODULES')).inputs
Structure = YAML_Inputs_provider(file='HSATS.yaml',
                                 subpath=os.path.join('HARDWARE',
                                                      'STRUCTURES')).inputs

pv_config = Inputs_aggregator([AV_1, PV_module_1, Structure]).aggregated_inputs

#######################
# Terrain definition  #
#######################
# The slope is read from the YAML configuration (TerrainSlopeAngle /
# TerrainSlopeAspect in Example_SlopedTerrain.yaml) — no hardcoded value here.
# Edit those keys in the YAML to change the slope (TerrainSlopeAngle: 0 → flat).
ground = ground_from_config(pv_config)

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
