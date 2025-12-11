# -*- coding: utf-8 -*-
"""
Created on Fri Oct 10 10:21:53 2025

@author: Romain Vandekerckhove
"""

import numpy as np
from pase.ENVIRONMENT.mesh import Mesh

def test_interest_zone_rotation_mode():
    """
    Test azimuth rotation of interest zone.
    Checks 3 modes:
    - default
    - auto
    - custom
    """
    # instantiate Mesh
    M = Mesh()

    # base parameters
    Xmin, Xmax = -1, 1
    Ymin, Ymax = -1, 1
    dX, dY = 1, 1

    # Case 1 : 'default' → azimuth = 0°
    M.add_oriented_plane_ground_mesh(
        Xmin, Xmax, Ymin, Ymax, dX, dY, azimuth_deg=0, flag="default"
    )
    pts_default = M.get_sourcepoints(GetFlagId=False)
    # Expected points (no rotation)
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
    assert np.allclose(pts_default, expected_default), "Error: default mode"

    # Case 2 : 'custom' → azimuth = 90° (clockwise rotation)
    M = Mesh()  # nouvelle instance
    M.add_oriented_plane_ground_mesh(
        Xmin, Xmax, Ymin, Ymax, dX, dY, azimuth_deg=90, flag="custom"
    )
    pts_90 = M.get_sourcepoints(GetFlagId=False)

    # Theoretically, +90° rotation about origin results in (x', y') = (-y, x)
    expected_90 = np.array([[y, -x, 0] for x, y, _ in expected_default])
    assert np.allclose(pts_90, expected_90, atol=1e-6), \
        "Error: custom mode (90°)"

    # Case 3 : 'auto' → simulate PV central azimuth=45°
    azimuth_pv = 45
    M = Mesh()
    M.add_oriented_plane_ground_mesh(
        Xmin, Xmax, Ymin, Ymax, dX, dY, azimuth_deg=azimuth_pv, flag="auto"
    )
    pts_45 = M.get_sourcepoints(GetFlagId=False)

    # check that distance conservation
    dist_before = np.linalg.norm(expected_default[:, :2], axis=1)
    dist_after = np.linalg.norm(pts_45[:, :2], axis=1)
    assert np.allclose(dist_before, dist_after, atol=1e-6), \
        "Distances changed after rotation"

def test_interest_zone_rotation_angle():
    """
    Test several custom angles to check that rotation is applied correctly.
    """

    # Base parameters
    Xmin, Xmax = -1, 1
    Ymin, Ymax = -1, 1
    dX, dY = 1, 1

    # Reference points (no rotation)
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

    # List of angles to test (degrees)
    angles = [0, 45, 90, 135, 180, -45, -140]

    for angle in angles:
        M = Mesh()
        M.add_oriented_plane_ground_mesh(
            Xmin, Xmax, Ymin, Ymax, dX, dY, azimuth_deg=angle, flag=f"angle_{angle}"
        )
        pts_rot = M.get_sourcepoints(GetFlagId=False)

        # Apply same theoretical rotation
        theta = np.deg2rad(-angle)
        R = np.array([
            [np.cos(theta), -np.sin(theta)],
            [np.sin(theta),  np.cos(theta)]
        ])

        expected_rot = np.array([
            [R[0, 0]*x + R[0, 1]*y, R[1, 0]*x + R[1, 1]*y, 0]
            for x, y, _ in expected_default
        ])

        # Check coordinates
        assert np.allclose(pts_rot, expected_rot, atol=1e-6), \
            f"Error for angle: {angle}°"

        # Check distance conservation
        dist_before = np.linalg.norm(expected_default[:, :2], axis=1)
        dist_after = np.linalg.norm(pts_rot[:, :2], axis=1)
        assert np.allclose(dist_before, dist_after, atol=1e-6), \
            f"Distance modified for angle: {angle}°"
    