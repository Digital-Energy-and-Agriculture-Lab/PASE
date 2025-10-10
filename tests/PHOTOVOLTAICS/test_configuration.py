from itertools import product
import numpy as np
import pytest
from random import uniform

from pase.DATA_MANAGEMENT.yaml_inputs_provider import (YAML_Inputs_provider,
                                                       Inputs_aggregator)

from pase.PHOTOVOLTAICS.configuration import PV_Configuration_3D

pv_module_params = YAML_Inputs_provider(file= 'Example1_PV_Module.yaml',
                                        path='tests',
                                        subpath='PHOTOVOLTAICS',
                                        parentdir=True).inputs
pv_central_params = YAML_Inputs_provider(file= 'Example1_AV.yaml',
                                        path='tests',
                                        subpath='PHOTOVOLTAICS',
                                        parentdir=True).inputs

pv_dict = Inputs_aggregator([pv_module_params, pv_central_params]).aggregated_inputs

pv_central = PV_Configuration_3D(pv_dict, np.array([0, 0, 1]))
first_panel = pv_central.create_first_panel()
PV_block_polydata, xyz = pv_central.create_block_of_panels(first_panel)

lower_bound_panel_x = pv_central.repet_dist_panels_x
upper_bound_panel_x = pv_central.repet_dist_panels_x * 1.1

lower_bound_panel_y = pv_central.repet_dist_panels_y
upper_bound_panel_y = pv_central.repet_dist_panels_y * 1.1

lower_bound_block_x = pv_central.repet_dist_block_x
upper_bound_block_x = pv_central.repet_dist_block_x * 1.1

lower_bound_block_y = pv_central.repet_dist_block_y
upper_bound_block_y = pv_central.repet_dist_block_y * 1.1

@pytest.mark.parametrize('n_blocks_x, n_blocks_y',
                         list(product(range(1, 9), range(1, 9))))
def test_num_blocks_in_central(n_blocks_x, n_blocks_y):
    pv_central.n_blocks_x = n_blocks_x
    pv_central.n_blocks_y = n_blocks_y

    # Generate random block repetition distances to challenge the implementation
    pv_central.repet_dist_block_x = uniform(lower_bound_block_x,
                                            upper_bound_block_x)
    pv_central.repet_dist_block_y = uniform(lower_bound_block_y,
                                            upper_bound_block_y)

    print(f'\n{pv_central.repet_dist_block_x=}')
    print(f'{pv_central.repet_dist_block_y=}')

    polydata, multiblock = pv_central.create_central(PV_block_polydata,
                                                     fst_panel=first_panel,
                                                     xyz_block=xyz)

    assert (multiblock.n_blocks == (n_blocks_x*n_blocks_y)*
            (pv_central.n_panels_x*pv_central.n_panels_y))

@pytest.mark.parametrize('n_panels_x, n_panels_y',
                         list(product(range(1, 9), range(1, 9))))
def test_num_panel_in_block(n_panels_x, n_panels_y):
    pv_central.n_panels_x = n_panels_x
    pv_central.n_panels_y = n_panels_y

    pv_central.repet_dist_panels_x = uniform(lower_bound_panel_x, upper_bound_panel_x)
    pv_central.repet_dist_panels_y = uniform(lower_bound_panel_y, upper_bound_panel_y)

    _, xyz = pv_central.create_block_of_panels(first_panel)

    assert len(xyz) == n_panels_x*n_panels_y
