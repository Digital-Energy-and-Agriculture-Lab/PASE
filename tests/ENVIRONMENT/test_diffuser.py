from pase.ENVIRONMENT.diffuser import LenticularDiffuser
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
            assert np.isclose(gamma, gamma_comp, rtol = 1e-5).any()
            assert np.isclose(beta, beta_comp, rtol=1e-5).any()
