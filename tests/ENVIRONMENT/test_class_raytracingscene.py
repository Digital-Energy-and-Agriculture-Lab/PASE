from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.PHOTOVOLTAICS.configuration import PVConfiguration3D
from pase.ENVIRONMENT.sky_model import ReinhartSky
from pase.ENVIRONMENT.mesh import Mesh
from pase.ENVIRONMENT.diffuser import LenticularDiffuser
import numpy as np
import pandas as pd

def _diffuser_trace(x, x0, a, l, DB):
    alpha = np.maximum(x0-l*np.ones(len(x))/2, x-a*np.tan(DB/2))
    beta = np.minimum(x0 + l * np.ones(len(x)) / 2, x + a * np.tan(DB / 2))
    I = np.arctan(a*(beta-alpha)/(a**2+x**2-x*(beta+alpha)+alpha*beta))/DB
    ind = np.where(I<0)
    I[ind] = 0
    return I

def _create_example_centrale():
    cfg = [PVConfiguration3D(), PVConfiguration3D(), PVConfiguration3D()]

    base_dict = dict(
        PanelDimensionX=1.6, PanelDimensionY=1.0, PanelThickness=False,
        RepetitionDistanceOfPanelsX=1.8, RepetitionDistanceOfPanelsY=2.1,
        RepetitionDistanceOfPVBlocksX=3.6, RepetitionDistanceOfPVBlocksY=2.4,
        NumberOfPVBlocksX=1, NumberOfPVBlocksY=1,RotationAxisNumber=0,
        CentralAzimut=0.0, TiltY=10.0, Height=2.0,NumberOfPanelsX=2, NumberOfPanelsY=2, Hinge='Center'
    )
    variants ={"PV_A":dict(),
               "PV_B":dict(DiffuserDimensionZ=0.003,DiffuserDimensionX=1,
                           DiffuserDimensionY=1.6, DiffusersBetweenPanels=True,
                           DiffusersAtRowEnds=False,DiffusersFillXAxis=True),
               "PV_C":dict(DiffuserDimensionZ=0.003,DiffuserDimensionX=1,
                           DiffuserDimensionY=1.6, DiffusersBetweenPanels=True,
                           DiffusersAtRowEnds=False,DiffusersFillXAxis=True, TiltY=0.0)}
    M = Mesh()
    loc = dict(InterestZoneOrientationMode='custom',InterestZoneCustomAngle=0)
    M.set_interest_zone_orientation(loc, base_dict|variants["PV_C"])
    M.add_oriented_plane_ground_mesh(-1, 1, -1, 1, 0.1, 0.1, flag="crop")
    cfg[0].create_regular_central(base_dict|variants["PV_A"])
    cfg[1].create_regular_central(base_dict|variants["PV_B"])
    cfg[2].create_regular_central(base_dict|variants["PV_C"])
    return cfg, M
sky = ReinhartSky(MF=1).reinhart_patches
suns  = np.array([np.array([i, j, 1]).reshape((1,3))/np.sqrt(i**2+j**2+1) for i in range(-1, 2, 1) for j in range(-1, 2, 1)]).reshape((9, 3))
Diffusers = LenticularDiffuser(0, 10, omega = 30)
Diffusers2 = LenticularDiffuser(0, 0, omega = 30)
def test_check_mask_Ray_casting_scene():
    geometry,M = _create_example_centrale()
    L = Ray_casting_scene(M, geometry[0], sky)
    L.get_light_maps(suns,visualization=False,Sun_P_map_to_visualize=3)
    assert list(L.masks.keys()) == ['Diffuse', 'PV']
    L = Ray_casting_scene(M, geometry[1], sky, diffusers=Diffusers)
    L.get_light_maps(suns, visualization=False, Sun_P_map_to_visualize=3)
    assert list(L.masks.keys()) == ['Diffuse', 'Diffuser', 'PV']
    assert L.masks['Diffuser'].shape == (M.sourcepoints.shape[0], len(sky))
    assert L.masks['PV'].shape == (M.sourcepoints.shape[0], len(sky))
    assert L.masks['Diffuse'].shape == (M.sourcepoints.shape[0], len(sky))

def test_self_intercept():
    geometry, M = _create_example_centrale()
    L = Ray_casting_scene(M, geometry[0], sky)
    sourcepoints = M.sourcepoints[:, :3]
    Delta = np.zeros(sourcepoints.shape)
    Delta[5:, 0] = 0.005
    Delta[10:20, 1] = 0.01
    Delta[20:, 2] = 0.005
    Rays = np.arange(0, sourcepoints.shape[0], 1)
    Cells = np.zeros_like(Rays)
    R_filt, C_filt = L.self_intercept(sourcepoints, sourcepoints+Delta, Rays, Cells)
    ind  = np.where(np.linalg.norm(Delta, axis=1)>0.01)
    assert (R_filt == Rays[ind]).all()

def test_compute_diffuser_map():
    geometry, M = _create_example_centrale()
    L = Ray_casting_scene(M, geometry[2], sky, diffusers=Diffusers2)
    L.get_light_maps(suns,visualization=False)
    maps = L.diffuser_map
    pTarget  = np.column_stack([sky.x, sky.y, sky.z])
    weight = Diffusers2.get_light_direction(suns, pTarget, sky['Normalized surf area'], np.sqrt(np.min(sky['solid_angle_sr'])))
    _cos_elev_patch = sky['cos(z)']
    diffuser_map = np.zeros((weight.shape[0], L.masks['Diffuser'].shape[0]))
    for i in range(weight.shape[0]):
        for k in range(L.masks['Diffuser'].shape[0]):
            for j in range(weight.shape[1]):
                diffuser_map[i, k]+=weight[i, j]*_cos_elev_patch[j]*L.masks['Diffuser'][k, j]
    assert np.allclose(maps, diffuser_map, rtol=1e-05)
    assert (np.sum(diffuser_map, axis=1)*0.1*0.1 <= 1.6).all()

def test_diffuser_map_theory():
    sky = ReinhartSky(MF=8).reinhart_patches
    geometry, M = _create_example_centrale()
    L = Ray_casting_scene(M, geometry[2], sky, diffusers=Diffusers2)
    L.get_light_maps(np.array([0,0,1]).reshape((1,3)), visualization=False)
    maps = L.diffuser_map
    ind  = np.where(np.isclose(M.sourcepoints[:,0],np.unique(M.sourcepoints[:,0])[5]))
    maps = maps[0, ind]
    x = np.arange(-1, 1.1, 0.1)
    F = _diffuser_trace(x, 0, 2,1, np.radians(60))
    print(maps, F)
    assert np.allclose(maps, F, atol=1e-1)

def test_compute_daily_diffuser_irradiation():
    geometry, M = _create_example_centrale()
    L = Ray_casting_scene(M, geometry[2], sky, diffusers=Diffusers2)
    L.get_light_maps(suns,visualization=False)
    ghi = np.arange(1, 25, 1)
    sunIndex = np.random.randint(0,9, 24)
    df = pd.DataFrame({'GHI': ghi, 'SolPosInd': sunIndex})
    Irr = L.compute_daily_diffuser_irradiation(df, 1)
    Irr2 = np.sum(L.diffuser_map[sunIndex, :]*ghi[:, np.newaxis], axis=0) * 3600.0 * 1e-6
    assert np.allclose(Irr, Irr2)
