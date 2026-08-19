#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2026 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Selim Grote (selim.grote@uliege.be)
#This file is part of the PASE software, and is distributed under the MIT license.

"""
Real-terrain (DEM) example (issue #248).

Demonstrates a PV system placed on a realistic relief downloaded from SRTM
around the scenario location, using DEMGround.  Each pole foot is anchored to
the terrain elevation while panel tilt and azimuth stay unchanged.

Terrain parameters (defined in the SCENARIO YAML — see Example_DEM_loc.yaml)
---------------------------------------------------------------------------
TerrainSource       : flat | sloped | srtm  (here: srtm)
TerrainExtentRadius : half-size [m] of the terrain box around the location;
                      it must cover the whole PV installation.
Latitude/Longitude  : location around which the SRTM tile is downloaded.

Requirements
------------
The ``srtm`` mode downloads elevation data on first run and needs an internet
connection plus the optional geospatial deps:

    pip install elevation rasterio pyproj

Subsequent runs reuse the disk cache (~/.cache/pase/dem/).  Set
``TerrainSource: flat`` (or ``sloped``) in the YAML to run without these.
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
Loc_1 = YAML_Inputs_provider(file='Example_DEM_loc.yaml',
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
# The terrain is built from the YAML configuration: TerrainSource='srtm' triggers
# an SRTM download around (Latitude, Longitude) over a TerrainExtentRadius box.
# The location config (Loc_1) carries those keys, so it is passed explicitly.
ground = ground_from_config(pv_config, location=Loc_1)

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
