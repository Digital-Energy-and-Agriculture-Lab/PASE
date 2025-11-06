# -*- coding: utf-8 -*-
"""
Created on Fri Oct 10 10:21:53 2025

@author: Romain
"""

import numpy as np
from pase.ENVIRONMENT.mesh import Mesh

def test_interest_zone_rotation_mode():
    """
    Test de la rotation de la zone d'intérêt selon l'azimut.
    Vérifie les 3 modes : default, auto, custom.
    """
    # Création d'une instance de Mesh
    M = Mesh()

    # Paramètres de base
    Xmin, Xmax = -1, 1
    Ymin, Ymax = -1, 1
    dX, dY = 1, 1

    # Cas 1 : mode 'default' → azimut = 0°
    M.add_oriented_plane_ground_mesh(
        Xmin, Xmax, Ymin, Ymax, dX, dY, azimuth_deg=0, flag="default"
    )
    pts_default = M.get_sourcepoints(GetFlagId=False)
    # Points attendus (pas de rotation)
    expected_default = np.array([
        [-1, -1, 0],
        [-1,  0, 0],
        [-1,  1, 0],
        [ 0, -1, 0],
        [ 0,  0, 0],
        [ 0,  1, 0],
        [ 1, -1, 0],
        [ 1,  0, 0],
        [ 1,  1, 0]
    ])
    assert np.allclose(pts_default, expected_default), "Erreur sur le mode default"

    # Cas 2 : mode 'custom' → azimut = 90° (rotation horaire)
    M = Mesh()  # nouvelle instance
    M.add_oriented_plane_ground_mesh(
        Xmin, Xmax, Ymin, Ymax, dX, dY, azimuth_deg=90, flag="custom"
    )
    pts_90 = M.get_sourcepoints(GetFlagId=False)

    # Théoriquement, une rotation de +90° autour de l'origine donne (x', y') = (-y, x)
    expected_90 = np.array([[y, -x, 0] for x, y, _ in expected_default])
    assert np.allclose(pts_90, expected_90, atol=1e-6), "Erreur sur le mode custom (90°)"

    # Cas 3 : mode 'auto' → simulons un azimut PV central à 45°
    azimut_pv = 45
    M = Mesh()
    M.add_oriented_plane_ground_mesh(
        Xmin, Xmax, Ymin, Ymax, dX, dY, azimuth_deg=azimut_pv, flag="auto"
    )
    pts_45 = M.get_sourcepoints(GetFlagId=False)

    # On vérifie juste que les points sont bien tournés (distance conservée)
    dist_before = np.linalg.norm(expected_default[:, :2], axis=1)
    dist_after = np.linalg.norm(pts_45[:, :2], axis=1)
    assert np.allclose(dist_before, dist_after, atol=1e-6), "Distances non conservées après rotation"

def test_interest_zone_rotation_angle():
    """
    Teste plusieurs angles dans le même mode (custom) pour vérifier
    que la rotation est appliquée correctement pour différentes valeurs.
    """

    # Paramètres de base
    Xmin, Xmax = -1, 1
    Ymin, Ymax = -1, 1
    dX, dY = 1, 1

    # Points de référence (pas de rotation)
    expected_default = np.array([
        [-1, -1, 0],
        [-1,  0, 0],
        [-1,  1, 0],
        [ 0, -1, 0],
        [ 0,  0, 0],
        [ 0,  1, 0],
        [ 1, -1, 0],
        [ 1,  0, 0],
        [ 1,  1, 0]
    ])

    # Liste d'angles à tester (en degrés)
    angles = [0, 45, 90, 135, 180, -45, -140]

    for angle in angles:
        M = Mesh()
        M.add_oriented_plane_ground_mesh(
            Xmin, Xmax, Ymin, Ymax, dX, dY, azimuth_deg=angle, flag=f"angle_{angle}"
        )
        pts_rot = M.get_sourcepoints(GetFlagId=False)

        # Applique la même rotation théorique (sens horaire)
        theta = np.deg2rad(-angle)
        R = np.array([
            [np.cos(theta), -np.sin(theta)],
            [np.sin(theta),  np.cos(theta)]
        ])

        expected_rot = np.array([
            [R[0, 0]*x + R[0, 1]*y, R[1, 0]*x + R[1, 1]*y, 0]
            for x, y, _ in expected_default
        ])

        # Vérifie que les coordonnées correspondent à la rotation
        assert np.allclose(pts_rot, expected_rot, atol=1e-6), f"Erreur pour angle {angle}°"

        # Vérifie que les distances à l'origine sont conservées
        dist_before = np.linalg.norm(expected_default[:, :2], axis=1)
        dist_after = np.linalg.norm(pts_rot[:, :2], axis=1)
        assert np.allclose(dist_before, dist_after, atol=1e-6), f"Distance modifiée pour angle {angle}°"
    