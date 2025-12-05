from pase.ENVIRONMENT.diffuser import LenticularDiffuser, rotation_coordinate

import numpy as np

az = [0, 45, 90, 135, 180, 225, 270, 315]
ti = [-90, -45, 0, 45, 90]
Diffusers = [LenticularDiffuser(azi, tii, omega = 30) for azi in az for tii in ti]
def test_LenticularDiffuser_configuration():
    for D in Diffusers:
            assert np.isclose(np.sum(D.len_vector*D.normal), 0, rtol=1e-08)

suns  = [np.array([i, j, 1]).reshape((1,3))/np.sqrt(i**2+j**2+1) for i in range(-1, 2, 1) for j in range(-1, 2, 1)]
def test_LenticularDiffuser_beta_gamma():
    for D in Diffusers:
        for sun in suns:
            print(sun)
            beta = D.get_beta_angle(sun, 0.1)
            gamma = D.get_gamma_angle(sun, 0.1)
            dot_gl = np.sum(sun*D.len_vector)
            cross_gl = np.array([sun[0,1]*D.len_vector[2] - sun[0,2]*D.len_vector[1],
                                 sun[0,2]*D.len_vector[0] - sun[0,0]*D.len_vector[2],
                                 sun[0,0]*D.len_vector[1] - sun[0,1]*D.len_vector[0]])
            dot_cgl_n = np.sum(cross_gl*D.normal)
            div = np.sqrt(np.sum(cross_gl*cross_gl)) if np.sqrt(np.sum(cross_gl*cross_gl)) !=0 else 1
            cos_b = max(min(dot_cgl_n/div, 1), -1)
            b =np.arccos(cos_b)
            beta_comp = b + np.arange(-D.omega+0.1/2, D.omega + 0.1/2, 0.1)
            cos_gamma = max(min(dot_gl, 1), -1)
            g = np.arccos(cos_gamma)
            gamma_comp = np.tile(g, (1, int((2 * D.omega + 0.1) // 0.1)))
            assert np.isclose(gamma, gamma_comp, rtol = 1e-5).all()
            assert np.isclose(beta, beta_comp, rtol=1e-5).all()

def test_rotation_coordinate():
    u1, u2, u3, v =  np.array([31, 0, 0]),  np.array([0, 31, 0]), np.array([-9,24,-6]), np.array([1, 0, 0])
    u1 = u1.reshape((3,1,1))
    u2 = u2.reshape((3, 1, 1))
    u32 = u3.reshape((3, 1, 1))
    angles = np.deg2rad([0, 13, 49, 87, 103, 176, 182, 209, 222, 273, 360])
    for a in angles:
        up1 = rotation_coordinate(u1, v, a)
        up2 = rotation_coordinate(u2, v, a)
        dot_2 = np.sum(up2*u2)
        angle2 = np.arccos(dot_2/(np.linalg.norm(up2)*np.linalg.norm(u2)))
        angle2 =2*np.pi - angle2  if up2[2] < 0 else angle2
        up3 = rotation_coordinate(u32, v, a)
        up3p = (u3 - v*(np.dot(u3,v)))*np.cos(a) + np.cross(v, u3)*np.sin(a) + v*(np.dot(u3,v))
        print(up3.reshape((3,)), up3p)
        assert np.isclose(u1, up1, rtol=1e-5).all()
        assert np.isclose(angle2, a, rtol=1e-5).all()
        assert np.isclose(up3p, up3.reshape((3,)), rtol=1e-5).all()

