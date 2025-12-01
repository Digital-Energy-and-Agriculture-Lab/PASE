from abc import ABC, abstractmethod
import pyvista as pyv
import math

from pase.pase_math import compute_block_centers, compute_panel_grid_positions


def build_structure(config_dict):
    if config_dict['StructureType'].lower() == 'agrivoltaic fence':
        return AgrivoltaicFence(config_dict).build_structure()


class PVStructurePart(ABC):
    """Abstract interface for PV structures (panels, poles, trackers, etc.)."""

    def __init__(self, shape_type, length, **kwargs):
        self.shape_type = shape_type  # {circle, square, rectangle}

        self.length = length

        self.parse_kwargs(kwargs)

        self.make_polydata()

    def parse_kwargs(self, kwargs):
        keys = kwargs.keys()

        if 'radius' in keys:
            self.radius = kwargs['radius']

        if 'side' in keys:
            self.side = kwargs['side']

        if 'width' in keys:
            self.width = kwargs['width']
            self.height = kwargs['height']

        if 'positioning' in keys:
            self.pole_ground_positioning = kwargs['positioning']
        else:
            self.pole_ground_positioning = 0

    def make_polydata(self):
        """
        Create a polydata attribute of shape self.shape_type, that is vertical.
        It will be rotated in the extension classes.
        """
        if self.shape_type.lower() in ['circle', 'cylinder']:
            self.polydata = pyv.Cylinder(center=(0, 0, 0),
                                         direction=(0, 0, 1),
                                         radius=self.radius,
                                         height=self.length).triangulate()
        elif self.shape_type.lower() == 'square':
            self.polydata = pyv.Cube(center=(0, 0, 0),
                                     x_length=self.side,
                                     y_length=self.side,
                                     z_length=self.length
                                     ).triangulate()
        elif self.shape_type.lower() == 'rectangle':
            self.polydata = pyv.Cube(center=(0, 0, 0),
                                     x_length=self.width,
                                     y_length=self.height,
                                     z_length=self.length).triangulate()


class Pole(PVStructurePart):
    def __init__(self, shape_type, length, **kwargs):
        """
        Create a vertical pole of shape shape_type and given length in meters.
        Everything is handled by the parent class PVStructurePart.

        :param shape_type: shape of the profile, choices :
                           {'circle', 'cylinder', 'square', 'rectangle'}
        :param length: length in meters [m]
        :param kwargs: contains parameters of the profile : radius if it's a
                       cylinder, width and height if rectangle, side if square
        """
        super().__init__(shape_type, length, **kwargs)

        self.orientation = 'vertical'
        self.polydata.translate((0, 0, length/2 + self.pole_ground_positioning), inplace=True)


class Purlin(PVStructurePart):
    def __init__(self, shape_type, length, panel_tilt_Y, **kwargs):
        super().__init__(shape_type, length, **kwargs)

        # Rotate to make horizontal along y
        self.orientation = 'horizontal_y'
        self.polydata.rotate_x(90, inplace=True)

        # Tilt the purlin
        self.tilt = panel_tilt_Y  # [°]
        self.polydata.rotate_y(self.tilt, inplace=True)


class Rafter(PVStructurePart):
    def __init__(self, shape_type, length, panel_tilt_Y, **kwargs):
        super().__init__(shape_type, length, **kwargs)

        # Rotate to make horizontal along x
        self.orientation = 'horizontal_x'
        self.polydata.rotate_y(90, inplace=True)

        # Tilt the rafter
        self.tilt = panel_tilt_Y  # [°]
        self.polydata.rotate_y(self.tilt, inplace=True)


class HorizontalBar(PVStructurePart):
    def __init__(self, shape_type, length, **kwargs):
        super().__init__(shape_type, length, **kwargs)

        # Rotate to make horizontal along y
        self.orientation = 'horizontal_y'
        self.polydata.rotate_x(90, inplace=True)


class PVStructure(ABC):
    """Abstract interface for PV structures (panels, poles, trackers, etc.)."""
    def __init__(self, PV_i):
        
        self.panels_per_group = PV_i['PanelsPerGroup']
        self.n_groups_in_block  = int(PV_i['NumberOfPanelsY']
                                      * PV_i['NumberOfPanelsX']
                                      /self.panels_per_group)
        self.vertical_spacing = PV_i['RepetitionDistanceOfPanelsX']
        self.structure_spacing_x = 0
        self.structure_spacing_y = ((PV_i['RepetitionDistanceOfPanelsY']
                                    * PV_i['NumberOfPanelsY'])
                                    /self.n_groups_in_block)
        self.structure_height = PV_i['StructureHeight']

        self.pole_shape = PV_i['PoleShape']
        self.pole_width    = PV_i['PoleWidth']
        self.pole_height    = PV_i['PoleHeight']
        self.pole_side = PV_i['PoleSide']
        self.pole_radius = PV_i['PoleRadius']
        self.pole_length    = PV_i['PoleLength']
        self.pole_ground_positioning = PV_i['PoleGroundPositioning']

        self.purlin_shape = PV_i['PurlinShape']
        self.purlin_width = PV_i['PurlinWidth']
        self.purlin_height = PV_i['PurlinHeight']
        self.purlin_side = PV_i['PurlinSide']
        self.purlin_length = self.structure_spacing_y
        self.purlin_radius = PV_i['PurlinRadius']
        self.numbers_of_purlin = PV_i['NumberOfPurlins']

        self.rafter_shape = PV_i['RafterShape']
        self.rafter_width = PV_i['RafterWidth']
        self.rafter_height = PV_i['RafterHeight']
        self.rafter_side = PV_i['RafterSide']
        self.rafter_length = PV_i['RafterLength']
        self.rafter_radius = PV_i['RafterRadius']

        self.material = PV_i['Material']

        self.panel_width = float(PV_i["PanelDimensionX"])  # X
        self.panel_height = float(PV_i["PanelDimensionY"])  # Y

        self.panel_spacing_x = float(
            PV_i["RepetitionDistanceOfPanelsX"])  # pitch X
        self.panel_spacing_y = float(
            PV_i["RepetitionDistanceOfPanelsY"])  # pitch Y
        self.panels_per_block_x = int(PV_i["NumberOfPanelsX"])  # per block
        self.panels_per_block_y = int(PV_i["NumberOfPanelsY"])  # per block

        self.block_spacing_x = float(
            PV_i["RepetitionDistanceOfPVBlocksX"])  # block pitch X
        self.block_spacing_y = float(
            PV_i["RepetitionDistanceOfPVBlocksY"])  # block pitch Y
        self.num_blocks_x = int(PV_i["NumberOfPVBlocksX"])  # blocks
        self.num_blocks_y = int(PV_i["NumberOfPVBlocksY"])  # blocks

        self.base_height = float(PV_i["Height"])  # elevation
        self.pole_spacing = float(PV_i["PoleSpacingX"])
        self.tilt = float(PV_i["TiltY"])


class AgrivoltaicFence(PVStructure):
    def __init__(self, PV_i, **kwargs):
        super().__init__(PV_i, **kwargs)



    def make_elementary_group(self) -> pyv.PolyData:
        '''
        creates a structure by combining vertical and horizontal bars 
        '''

        pole = Pole(self.pole_shape,
                    length=self.pole_length,
                    width=self.pole_width,
                    height=self.pole_height,
                    side=self.pole_side,
                    radius=self.pole_radius,
                    positioning=self.pole_ground_positioning)
        pole.polydata.translate((0, -self.purlin_length/2, 0), inplace=True)
        
        horizontal_bar_top = HorizontalBar(self.purlin_shape,
                          length=self.purlin_length,
                          side=self.purlin_side,
                          width=self.purlin_width,
                          height=self.purlin_height,
                          radius=self.purlin_radius)
        horizontal_bar_top.polydata.translate((0.0,
                                     0,
                                     self.structure_height),
                                    inplace=True)

        # 2nd horizontal bar is a copy of horizontal_bar_top,
        # translated downwards
        horizontal_bar_bottom = (horizontal_bar_top.polydata
                                 .copy().
                                 translate((0, 0, -self.vertical_spacing),
                                           inplace=True))
        
        combined = (pole.polydata
                    + horizontal_bar_top.polydata
                    + horizontal_bar_bottom).triangulate()

        return combined

    def build_structure(self) -> pyv.MultiBlock:

        # Compute position of groups
        positions, block_centers, grid_indices = compute_panel_grid_positions(
            self.num_blocks_x, self.num_blocks_y,
            self.panels_per_block_x, self.panels_per_block_y,
            self.block_spacing_x, self.block_spacing_y,
            self.panel_spacing_x, self.panel_spacing_y,
            self.base_height,
        )

        blocks = pyv.MultiBlock()

        for idx in range(self.n_groups_in_block):
            g = self.make_elementary_group()
            offx, offy, offz = map(float, positions[idx])

            g.translate((0, offy, 0),
                        inplace=True)
            blocks.append(g)

        end_pole = Pole(self.pole_shape,
                        length=self.pole_length,
                        width=self.pole_width,
                        height=self.pole_height,
                        side=self.pole_side,
                        radius=self.pole_radius,
                        positioning=self.pole_ground_positioning)

        end_pole.polydata.translate((0,
                                     offy+self.panel_spacing_y/2,
                                     0.0),
                                    inplace=True)
        blocks.append(end_pole.polydata)
        combined_blocks = blocks.combine()
        combined_blocks.user_dict = {'Material': self.material}

        return combined_blocks

class PVTable (PVStructure):
    def __init__(self, PV_i, **kwargs):
        super().__init__(PV_i, **kwargs)

        
        self.tilt_rad = math.radians(self.tilt)
        self.half_span = self.pole_spacing
        
        #set rafter lenght condition to avoid rafter to be smaller that distance between two poles
        self.required_length = 2 * self.half_span / math.cos(self.tilt_rad) 
        self.rafter_length = max(self.rafter_length, 
                                 self.required_length)
        self.height_offset = self.half_span * math.tan(self.tilt_rad)

    def make_elementary_group(self) -> pyv.PolyData:
        PRS = self.make_start_and_end_block()
        PG = self.make_purlin_group()

        combined = PRS + PG

        return combined

        
    def make_start_and_end_block(self) -> pyv.PolyData:
        """
            PR is for Pole and rafter
        """
        

        pole = Pole(self.pole_shape,
                    length=(self.base_height + self.height_offset),
                    width=self.pole_width,
                    height=self.pole_height,
                    side=self.pole_side,
                    radius=self.pole_radius,
                    positioning=self.pole_ground_positioning)
        pole.polydata.translate((-self.pole_spacing, 
                                 -self.purlin_length/2,
                                 0), 
                                inplace=True)

        pole_2 = Pole(self.pole_shape,
                    length=(self.base_height - self.height_offset),
                    width=self.pole_width,
                    height=self.pole_height,
                    side=self.pole_side,
                    radius=self.pole_radius,
                    positioning=self.pole_ground_positioning)
        pole_2.polydata.translate((self.pole_spacing, 
                                 -self.purlin_length/2,
                                 0), 
                                inplace=True)
        
        rafter = Rafter(self.rafter_shape,
                        length=self.rafter_length,
                        radius=self.rafter_radius,
                        panel_tilt_Y=self.tilt,
                        positioning=self.pole_ground_positioning)
        rafter.polydata.translate((0,
                                   -self.purlin_length/2,
                                   self.base_height),
                                   inplace= True)

        combine = pole.polydata + pole_2.polydata + rafter.polydata

        return combine

    def make_purlin_group(self) -> pyv.PolyData:
        nb_purlin = self.numbers_of_purlin
        span_purlin = self.rafter_length

        if nb_purlin <= 0:
            return pyv.PolyData()

        if nb_purlin == 1:
            offsets_x = [0.0]
        else:
            start = -span_purlin / 2.0
            step = span_purlin / (nb_purlin - 1)
            offsets_x = [start + i * step for i in range(nb_purlin)]

        purlin_group = []
        for offx in offsets_x:
            p = Purlin(self.purlin_shape,
                        length=self.purlin_length,
                        panel_tilt_Y=0,
                        side=self.purlin_side,
                        radius=self.purlin_radius,
                        positioning=self.pole_ground_positioning
                        )
            p.polydata.translate((offx, 
                                  0, 
                                  self.base_height),
                                  inplace=True)
            purlin_group.append(p.polydata)

        combined = purlin_group[0].copy()
        for mesh in purlin_group[1:]:
            combined = combined + mesh

        combined.rotate_y(self.tilt,
                          point=(0, 0, self.base_height),
                          inplace=True)
        
        return combined

    def build_structure(self) -> pyv.MultiBlock :

        positions, block_centers, grid_indices = compute_panel_grid_positions(
            self.num_blocks_x, self.num_blocks_y,
            self.panels_per_block_x, self.panels_per_block_y,
            self.block_spacing_x, self.block_spacing_y,
            self.panel_spacing_x, self.panel_spacing_y,
            self.base_height,
        )

        blocks = pyv.MultiBlock()

        for idx in range(self.n_groups_in_block):
            g = self.make_elementary_group()
            offx, offy, offz = map(float, positions[idx])

            g.translate((0, offy, 0),
                        inplace=True)
            blocks.append(g)

        end_pole = self.make_start_and_end_block()
        end_pole.translate((0,
                            offy+self.panel_spacing_y,
                            0.0),
                            inplace=True)
        
        blocks.append(end_pole)
        combined_blocks = blocks.combine()
        combined_blocks.user_dict = {'Material': self.material}

        return combined_blocks


class HSATS(PVStructure):
    """
        HSATS = Horizontal Single Axis Tracking Structure
    """
    def __init__(self, PV_i, **kwargs):
        super().__init__(PV_i, **kwargs)

    def make_elementary_group(self) -> pyv.PolyData:

        pole = Pole(self.pole_shape,
                    length=self.pole_length,
                    width=self.pole_width,
                    height=self.pole_height,
                    side=self.pole_side,
                    radius=self.pole_radius,
                    positioning=self.pole_ground_positioning)
        pole.polydata.translate((0, -self.purlin_length/2, 0), inplace=True)

        support = Pole("rectangle",
                    length=0.7,
                    width=0.5,
                    height=0.1,
                    side=self.pole_side,
                    radius=self.pole_radius,
                    positioning=self.pole_ground_positioning)
        support.polydata.translate((0, -self.purlin_length/2, self.pole_length), inplace=True)
        cx, cy, cz = support.polydata.center
        support.polydata.translate((-cx, -cy, -cz), inplace=True)
        support.polydata.rotate_x(90, inplace=True)
        support.polydata.translate((cx, cy, cz), inplace=True)

        combine = (pole.polydata + support.polydata)

        return combine
    
    def build_structure(self):
        return self.make_elementary_group()


if __name__ == "__main__":
    from pase.DATA_MANAGEMENT.yaml_inputs_provider import (YAML_Inputs_provider,
                                                           Inputs_aggregator)
    import os

    AV_1 = YAML_Inputs_provider(
        file="Example3_AV_agrivoltaic_fence.yaml",
        subpath="AV_CENTRAL",
        parentdir=2
    ).inputs

    PV_module_1 = YAML_Inputs_provider(
        file="Example1_PV_Module_landscape.yaml",
        subpath=os.path.join("HARDWARE", "PV_MODULES"),
        parentdir=2
    ).inputs

    Structure = YAML_Inputs_provider(
        file="PV_table.yaml",
        subpath=os.path.join("HARDWARE", "STRUCTURES"),
        parentdir=2
    ).inputs

    PV_params_dict = Inputs_aggregator([AV_1,
                                        PV_module_1,
                                        Structure]).aggregated_inputs

    blocks = HSATS(PV_params_dict).build_structure()

    pl = pyv.Plotter()
    pl.add_mesh(blocks, show_edges=True)
    pl.show_axes()
    pl.show_grid(color='gray')
    pl.show()
