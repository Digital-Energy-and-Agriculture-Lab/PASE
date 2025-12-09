from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.PHOTOVOLTAICS.configuration import PVConfiguration3D
from pase.ENVIRONMENT.sky_model import ReinhartSky
from pase.ENVIRONMENT.mesh import Mesh
from pase.ENVIRONMENT.diffuser import LenticularDiffuser
import numpy as np
def _create_example_centrale():
    cfg = [PVConfiguration3D(), PVConfiguration3D(), PVConfiguration3D()]

    base_dict = dict(
        PanelDimensionX=1.6, PanelDimensionY=1.0, PanelThickness=False,
        RepetitionDistanceOfPanelsX=1.8, RepetitionDistanceOfPanelsY=2.1,
        RepetitionDistanceOfPVBlocksX=3.6, RepetitionDistanceOfPVBlocksY=2.4,
        NumberOfPVBlocksX=1, NumberOfPVBlocksY=1,RotationAxisNumber=0,
        CentralAzimut=0.0, TiltY=10.0, Height=2.0,NumberOfPanelsX=2, NumberOfPanelsY=2
    )
    variants ={"PV_A":dict(),
               "PV_B":dict(DiffuserDimensionZ=0.003,DiffuserDimensionX=1.6,
                           DiffuserDimensionY=1, DiffusersBetweenPanels=True,
                           DiffusersAtRowEnds=False,DiffusersFillXAxis=True),
               "PV_C":dict(NumberOfPanelsX=0, NumberOfPanelsY=0)}
    cfg[0].create_regular_central(base_dict|variants["PV_A"])
    cfg[1].create_regular_central(base_dict|variants["PV_B"])
    return cfg
sky = ReinhartSky(MF=1).reinhart_patches
M = Mesh()
M.add_plane_ground_regular_meshes(-1, 1, -1, 1, 0.5, 0.5, flag="crop")
suns  = np.array([np.array([i, j, 1]).reshape((1,3))/np.sqrt(i**2+j**2+1) for i in range(-1, 2, 1) for j in range(-1, 2, 1)]).reshape((9, 3))
Diffusers = LenticularDiffuser(0, 10, omega = 30)
def test_check_mask_Ray_casting_scene():
    geometry = _create_example_centrale()
    L = Ray_casting_scene(M, geometry[0], sky)
    L.get_light_maps(suns,visualization=False,Sun_P_map_to_visualize=3)
    assert list(L.masks.keys()) == ['Diffuse', 'PV']
    L = Ray_casting_scene(M, geometry[1], sky, diffusers=Diffusers)
    L.get_light_maps(suns, visualization=False, Sun_P_map_to_visualize=3)
    assert list(L.masks.keys()) == ['Diffuse', 'Diffuser', 'PV']
    assert L.masks['Diffuser'].shape == (25, 145)
    assert L.masks['PV'].shape == (25, 145)
    assert L.masks['Diffuse'].shape == (25, 145)

def test_self_intersept():
    geometry = _create_example_centrale()
    L = Ray_casting_scene(M, geometry[0], sky)
    sourcepoints = M.sourcepoints[:, :3]
    Delta = np.zeros(sourcepoints.shape)
    Delta[5:, 0] = 0.005
    Delta[10:20, 1] = 0.01
    Delta[20:, 2] = 0.005
    Rays = np.arange(0, 25, 1)
    Cells = np.zeros_like(Rays)
    R_filt, C_filt = L.self_intercept(sourcepoints, sourcepoints+Delta, Rays, Cells)
    ind  = np.where(np.linalg.norm(Delta, axis=1)>0.01)
    assert (R_filt == Rays[ind]).all()







