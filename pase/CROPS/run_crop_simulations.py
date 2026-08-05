#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

from datetime import datetime
import importlib

import numpy as np

from pase.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization


# Backend runners are imported lazily: STICS and pySTICS are not shipped in
# the PyPI wheel, so importing them eagerly made this module - and with it the
# pure-Python SIMPLE and Gras-Sim models - unusable from an install (#271).
_CROP_BACKENDS = {
    'simple': ('pase.CROPS.SIMPLE.run_simple',
               'run_independant_years_of_crop'),
    'stics': ('pase.CROPS.STICS.JAVASTICS.run_java_stics',
              'run_independant_usms'),
    'pystics': ('pase.CROPS.STICS.PYSTICS.run_pystics_from_PASE',
                'run_independant_usms_in_pystics'),
    'grassim': ('pase.CROPS.GRASSIM.run_grassim', 'run_grassim'),
}

_INSTALLATION_GUIDE = ('https://gitlab.uliege.be/deal-public/pase/-/wikis/'
                       'documentation/installation')

_BACKEND_SETUP_HINTS = {
    'stics': ("The STICS backends are not distributed with PASE: download "
              "JavaStics 1.5.1 from https://stics.inrae.fr/telechargement and "
              "place 'JavaSticsCmd.exe' under INPUTS/CROPS/STICS, from a "
              "source checkout of PASE."),
    'pystics': ("The STICS backends are not distributed with PASE: pySTICS is "
                "a git submodule of a source checkout, initialized with "
                "'git submodule update --init --recursive'."),
}
_DEFAULT_SETUP_HINT = ("This backend ships with PASE, so its absence points at "
                       "an incomplete installation.")


def _load_backend(crop_model):
    """Import the simulation runner of a crop backend, on demand.

    Parameters
    ----------
    crop_model : string
        Value of the ``CropModel`` configuration parameter.

    Returns
    -------
    callable
        The backend function running the simulation.

    Raises
    ------
    ValueError
        If `crop_model` is not one of the supported backends.
    ImportError
        If the backend is supported but its module cannot be imported,
        with the setup instructions for that backend.

    """
    try:
        module_name, function_name = _CROP_BACKENDS[crop_model]
    except KeyError:
        raise ValueError(
            f"Unsupported CropModel {crop_model!r}: expected one of "
            f"{', '.join(sorted(_CROP_BACKENDS))}.") from None

    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        hint = _BACKEND_SETUP_HINTS.get(crop_model, _DEFAULT_SETUP_HINT)
        raise ImportError(
            f"CropModel {crop_model!r} needs '{module_name}', which could not "
            f"be imported ({error}). {hint} See the installation guide: "
            f"{_INSTALLATION_GUIDE}") from error

    return getattr(module, function_name)


def run_crop_simu(config, option_2D, WD, daily_irr, scenario_P):
    """Run the crop simulation with the backend selected in `config`.

    The backend module is imported here rather than at module level, so
    that an absent optional backend only affects the simulations that
    actually need it.

    Parameters
    ----------
    config : dict
        Dictionnary with the configuration parameters of the crop model.
    option_2D : bool
        Whether the crop simulation is spatialized in 2D.
    WD : dict
        Dictionnary with the weather data, per year.
    daily_irr : dict
        Dictionnary with the daily irradiation maps.
    scenario_P : dict
        Dictionnary with the scenario parameters.

    Returns
    -------
    results : dict
        Dictionnary with the agronomic results, per year.

    Raises
    ------
    ValueError
        If ``config['CropModel']`` is not a supported backend.
    ImportError
        If the selected backend is not installed.

    """
    crop_model = config['CropModel']
    run_backend = _load_backend(crop_model)

    results = {}

    if crop_model == 'simple':
        Soil_plot, Crop_plot = run_backend(config, option_2D, WD, daily_irr,
                                           scenario_P['Latitude'],
                                           scenario_P['Altitude'])
        results = merge_results([Soil_plot, Crop_plot])

    if crop_model == 'stics':
        Crop_plot = run_backend(config, WD, daily_irr, scenario_P)
        results = Crop_plot.nyears_data

    if crop_model == 'pystics':
        Crop_plot = run_backend(config, WD, daily_irr, scenario_P)
        results = Crop_plot.nyears_data

    if crop_model == 'grassim':
        Soil_plot, Crop_plot, Management_plot = run_backend(
            config, WD, daily_irr, scenario_P['Latitude'],
            scenario_P['Altitude'])
        results = merge_results([Soil_plot, Crop_plot, Management_plot])

    return results


def merge_results(objects):
    results = {}
    years = objects[0].nyears_data.keys()
    for year in years:
        merged_dict = {}
        for object in objects:
            merged_dict.update(object.nyears_data[year])
        results[year] = merged_dict
    return results


def visualize_map_of_a_variable(config, results, variable, scene_3D, meshes, year, MM_DD=np.nan, unit=''):
    """
    Visualize a specific spatialized variable in the 3D scene.

    Parameters
    ----------
    config : dict
        Dictionnary with the configuration parameters of the crop model
    results : dict
        Dictionnary with the output of the crop model
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
        
    if config['CropModel'] == 'simple':
        data = results[str(year)][variable][str(year)+'-'+MM_DD+' 00:00:00']
        
    if config['CropModel'] == 'grassim':
        data = results[str(year)][variable][datetime.strptime(str(year)+'-'+MM_DD+' 00:00:00', '%Y-%m-%d %H:%M:%S')]
        
    if config['CropModel'] == 'stics':
        data = results[str(year)][variable]

    if config['CropModel'] == 'pystics':
        data = results[str(year)][variable]

    open_pyvista_3D_visualization(meshes.sourcepoints[:,:],
                                  data, 
                                  geo,
                                  variable+' map '+ config['CropModel']+' '+ str(year)+'-'+MM_DD+' ['+unit+']')
