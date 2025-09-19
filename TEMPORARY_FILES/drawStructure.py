import pyvista as pv
import numpy as np

length_m     = 1.0
side_m       = 0.05
n_bars       = 3
group_height = 1.0
clearance    = 0.5
rotation_x   = -90
support_y    = +side_m
n_groups     = 1
group_offset = 1.0
ground_z     = 0.0

spacing = group_height / (n_bars - 1) if n_bars > 1 else 0.0
theta = np.radians(rotation_x)

def make_group(x_offset=0.0, end=False):
    z_positions = [clearance + i * spacing for i in range(n_bars)]
    bars = [pv.Cube(center=(x_offset + length_m/2, 0, z),
                    x_length=length_m, y_length=side_m, z_length=side_m)
            for z in z_positions]
    assembly = bars[0]
    for b in bars[1:]:
        assembly = assembly.merge(b)

    z_min = min(z_positions) - side_m
    z_max = max(z_positions) + side_m
    support_height = z_max - z_min
    support_center_z = (z_max + z_min) / 2.0

    support_x_a = x_offset + side_m/2
    support_a = pv.Cube(center=(support_x_a, support_y, support_center_z),
                        x_length=side_m, y_length=side_m, z_length=support_height)
    assembly = assembly.merge(support_a)

    feet = None
    def foot_for(support_x):
        Ry = support_y*np.cos(theta) - support_center_z*np.sin(theta)
        Rz = support_y*np.sin(theta) + support_center_z*np.cos(theta)
        Rx = support_x
        foot_height = max(Rz - ground_z, side_m)
        foot_center_z = ground_z + foot_height/2.0
        return pv.Cube(center=(Rx, Ry, foot_center_z),
                       x_length=side_m, y_length=side_m, z_length=foot_height)

    if end:
        support_x_b = x_offset + length_m - side_m/2
        support_b = pv.Cube(center=(support_x_b, support_y, support_center_z),
                            x_length=side_m, y_length=side_m, z_length=support_height)
        assembly = assembly.merge(support_b)

    rotated = assembly.rotate_x(rotation_x, point=(x_offset, 0, 0), inplace=False)

    feet = foot_for(support_x_a)
    if end:
        feet = feet.merge(foot_for(x_offset + length_m - side_m/2))

    return rotated, feet

groups = [make_group(i * group_offset, end=(i == n_groups - 1)) for i in range(n_groups)]
rotated_all = groups[0][0]
feet_all = groups[0][1]
for g in groups[1:]:
    rotated_all = rotated_all.merge(g[0])
    feet_all = feet_all.merge(g[1])

ground = pv.Plane(center=(0,0,ground_z), direction=(0,0,1), i_size=10.0, j_size=10.0)

pl = pv.Plotter()
pl.add_mesh(ground, color="#d0d0d0", lighting=True)
pl.add_mesh(rotated_all, color="lightgrey", lighting=True)
pl.add_mesh(feet_all, color="lightgrey", lighting=True)
pl.add_axes()
pl.camera_position = "xz"
pl.show()
