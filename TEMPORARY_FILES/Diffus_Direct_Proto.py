# -*- coding: utf-8 -*-
"""
Created on Thu Jan 26 15:36:25 2023

@author: Nicolas.DeCock
"""
import numpy as np
import numpy as np
import pyvista as pv


def fibonacci_half_sphere(samples=18):
    
    phi = np.pi * (3. - np.sqrt(5.))
    i = np.linspace(0,samples-1,num=samples)
    yp = (1 - i/float(samples-1))
    radius = np.sqrt(1-yp**2) 
    theta = phi * i 
    xp = np.cos(theta) * radius
    zp = np.sin(theta) * radius
    return np.column_stack([xp,yp,zp])

def get_sun_position():
    
    return [0,0,1]


def Get_Geometry():
    
    # PV PolyData

    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]])
    faces = np.hstack(
        [
            [3, 0, 1, 2],  # triangle
            [3, 1, 2, 3],  # triangle
        ]
        )
    sPV = pv.PolyData(vertices, faces)

    #Rotation of the PV
    sPV.rotate_x(0)

    # Local PV array creation
    x,y,z = np.mgrid[-3:3, -3:3, 0:1]
    Localmesh = pv.StructuredGrid(x, y, z)
    LocalPVArray = Localmesh.glyph(geom=sPV, factor=0.75)
    LocalPVArray.rotate_x(90)



    # Global PV array creation
    x,y,z = np.mgrid[-3:3, -3:3, 1:2]*5
    GlobalMesh = pv.StructuredGrid(x, y, z)
    GlobalPVArray  = GlobalMesh.glyph(geom=LocalPVArray, factor=0.75)
    return GlobalPVArray




# %% Diffuse light casting


Geometry = Get_Geometry() #PolyData Geometry

# Sky sampling; sky location toward which a ray will be casted
diffuseray=36
pTarget = fibonacci_half_sphere(diffuseray)*100
nSkyRay= len(pTarget)


#Mesh 
xs = np.linspace(-5, 5, 6)
ys = np.linspace(-5, 5, 6)
X,Y = np.meshgrid(xs,ys)

# Creation of the array of source points and target points
# The code may be more explicit by dividing the steps
SourcePoints = np.repeat(np.column_stack((X.flatten(),Y.flatten(),np.zeros(len(X.flatten())))),nSkyRay,axis=0)
TargetPoints = np.tile(pTarget,[len(X.flatten()),1])

#Creation of the source index mapper 
SourceI = np.repeat(np.linspace(0,len(X.flatten())-1,len(X.flatten())),nSkyRay,axis=0)

#Ray Casting
_, ind_ray, _ = Geometry.multi_ray_trace(SourcePoints,TargetPoints,first_point=True,retry=False)

#Creation of the light map (1D vector but linked by index to the X.flatten(),Y.flatten())
#1D vector allows easier implementation
Diffu = np.ones(len(X.flatten()))

Touched = SourceI[ind_ray]
unique, counts = np.unique(Touched, return_counts=True)

#Computation of a 1D vector giving the diffuse light
Diffu[unique.astype("int")] = 1 - counts/nSkyRay
Diffu = Diffu.reshape(len(xs),len(ys))

# %% Direct light casting


Geometry = Get_Geometry() #PolyData Geometry

# Sky sampling; sky location toward which a ray will be casted
pTarget = get_sun_position() #Sun with zenithal angle = 0
nSkyRay= 1


#Mesh 
xs = np.linspace(-5, 5, 6)
ys = np.linspace(-5, 5, 6)
X,Y = np.meshgrid(xs,ys)

# Creation of the array of source points and target points
# The code may be more explicit by dividing the steps
SourcePoints = np.repeat(np.column_stack((X.flatten(),Y.flatten(),np.zeros(len(X.flatten())))),nSkyRay,axis=0)
TargetPoints = np.tile(pTarget,[len(X.flatten()),1])

#Creation of the source index mapper 
SourceI = np.repeat(np.linspace(0,len(X.flatten())-1,len(X.flatten())),nSkyRay,axis=0)

#Ray Casting
_, ind_ray, _ = Geometry.multi_ray_trace(SourcePoints,TargetPoints,first_point=True,retry=False)

#Creation of the light map (1D vector but linked by index to the X.flatten(),Y.flatten())
#1D vector allows easier implementation
Direct = np.ones(len(X.flatten()))

Touched = SourceI[ind_ray]
unique, counts = np.unique(Touched, return_counts=True)

#Computation of a 1D vector giving the direct light
Direct[unique.astype("int")] = 1 - counts/nSkyRay
Direct = Direct.reshape(len(xs),len(ys))


