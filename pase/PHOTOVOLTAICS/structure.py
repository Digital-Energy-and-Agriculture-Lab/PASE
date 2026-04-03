from abc import ABC, abstractmethod
import pyvista as pyv
import math
import numpy as np

pyv.global_theme.allow_empty_mesh = True

def build_structure(config_dict):
    """
    Factory that selects the appropriate PV structure from the configuration.
    """
    struct_type = (config_dict.get('StructureType')
                   or config_dict.get('Structype'))
    if not struct_type:
        return None

    struct_type = struct_type.lower()

    if struct_type == 'agrivoltaic fence':
        return AgrivoltaicFence(config_dict).build_structure()
    if struct_type == 'pv table':
        return PVTable(config_dict).build_structure()
    if struct_type == 'hsats':
        return HSATS(config_dict).build_structure()

    raise ValueError(f"Unsupported StructureType '{struct_type}'")


class PVStructurePart(ABC):
    """Abstract interface for PV structures (panels, poles, trackers, etc.)."""

    def __init__(self, shape_type, length, **kwargs):
        """Store profile geometry then build the associated polydata mesh."""
        self.shape_type = shape_type  # {circle, square, rectangle}

        self.length = length

        self.parse_kwargs(kwargs)

        self.make_polydata()

    def parse_kwargs(self, kwargs):
        """Extract optional geometric dimensions and ground positioning."""
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
        Create a vertical polydata of the requested shape; subclasses rotate it
        """
        if self.length < 1e-6:
            self.polydata = pyv.PolyData()
        else:
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
    """Vertical post used as the main support for the PV structure."""

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
        self.polydata.translate((0, 
                                 0, 
                                 length/2 + self.pole_ground_positioning),
                                inplace=True)


class Purlin(PVStructurePart):
    """
    Horizontal purlins linking posts and supporting the panels.
    """

    def __init__(self, shape_type, length, panel_tilt_y, **kwargs):
        super().__init__(shape_type, length, **kwargs)

        # Rotate to make horizontal along y
        self.orientation = 'horizontal_y'
        self.polydata.rotate_x(90, inplace=True)

        # Tilt the purlin
        self.tilt = panel_tilt_y  # [°]
        self.polydata.rotate_y(self.tilt, inplace=True)


class Rafter(PVStructurePart):
    """Rafters oriented along the X-axis to carry purlins or panels."""

    def __init__(self, shape_type, length, panel_tilt_y, **kwargs):
        super().__init__(shape_type, length, **kwargs)

        # Rotate to make horizontal along x
        self.orientation = 'horizontal_x'
        self.polydata.rotate_z(90, inplace=True)
        self.polydata.rotate_y(90, inplace=True)

        # Tilt the rafter
        self.tilt = panel_tilt_y  # [°]
        self.polydata.rotate_y(self.tilt, inplace=True)


class HorizontalBar(PVStructurePart):
    """Simple horizontal bar, used for fence-like structures."""

    def __init__(self, shape_type, length, **kwargs):
        super().__init__(shape_type, length, **kwargs)

        # Rotate to make horizontal along y
        self.orientation = 'horizontal_y'
        self.polydata.rotate_x(90, inplace=True)


class Diagonal(PVStructurePart):
    """Diagonal bracing connecting two posts to stiffen the group."""

    def __init__(self, shape_type, length, **kwargs):
        super().__init__(shape_type, length, **kwargs)

        self.orientation = 'horizontal_x'

# --- Structures --- 

class PVStructure(ABC):
    """Abstract interface describing the common parameters of PV structures."""
    def __init__(self, PV_i):
        """Load common geometric, spacing, and material parameters for the PV layout."""
        
        self.number_of_structure_groups  = PV_i['NumberOfStructureGroups']
        self.vertical_spacing = PV_i['RepetitionDistanceOfPanelsX']

        self.pole_shape = PV_i['PoleShape']
        self.pole_width = PV_i['PoleWidth']
        self.pole_height = PV_i['PoleHeight']
        self.pole_side = PV_i['PoleSide']
        self.pole_radius = PV_i['PoleRadius']
        self.pole_ground_positioning = PV_i['PoleGroundPositioning']

        self.purlin_shape = PV_i['PurlinShape']
        self.purlin_width = PV_i['PurlinWidth']
        self.purlin_height = PV_i['PurlinHeight']
        self.purlin_side = PV_i['PurlinSide']
        self.purlin_radius = PV_i['PurlinRadius']
        self.numbers_of_purlin = PV_i['NumberOfPurlins']

        self.rafter_shape = PV_i['RafterShape']
        self.rafter_width = PV_i['RafterWidth']
        self.rafter_height = PV_i['RafterHeight']
        self.rafter_side = PV_i['RafterSide']
        self.rafter_length = PV_i['RafterLength']
        self.rafter_radius = PV_i['RafterRadius']
        self.numbers_of_rafter = PV_i['NumberOfRafters']
        
        self.diagonal_shape = PV_i['DiagonalShape']
        self.diagonal_width = PV_i['DiagonalWidth']
        self.diagonal_height = PV_i['DiagonalHeight']
        self.diagonal_side = PV_i['DiagonalSide']
        self.diagonal_radius = PV_i['DiagonalRadius']
        
        self.material = PV_i['Material']

        self.panel_height = float(PV_i["PanelDimensionX"])  # X
        self.panel_width = float(PV_i["PanelDimensionY"])  # Y

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
        self.panel_offset = float(PV_i["PanelOffset"])
        self.diagonal_epsilon = float(PV_i["DiagonalEpsilon"])

        self.repetition_distance_group_Y_mode = PV_i["RepetitionDistanceGroupYMode"]

        if self.repetition_distance_group_Y_mode.lower() == "auto":
            # Auto compute repetition_distance_group_Y based on panel layout
            self.repetition_distance_group_Y = (
                    self.panels_per_block_y*self.panel_spacing_y/self.number_of_structure_groups)
        elif self.repetition_distance_group_Y_mode.lower() == "manual":
            # Read repetition_distance_group_Y as a parameter
            self.repetition_distance_group_Y = PV_i['RepetitionDistanceGroupY']

        self.purlin_length = self.repetition_distance_group_Y


    def make_elementary_group(self):
        """
        Abstract method overridden in inherited classes.
        """
        pass

    def build_structure(self):
        """
        Abstract method overridden in inherited classes.
        """
        pass
    
    def get_characteristic_dim(self, part_type):
        """
        Get the characteristic dimension of a part of the structure, used to place
        parts on top of each other without clipping.

        :param part_type: type of part (should be "purlin" or "rafter")
        :type part_type: string
        :return: radius (if the part is a cylinder), half height (if the part has a
            rectangular section), half side (if the part has a square section)
        :rtype: float
        """
        shape = getattr(self, f"{part_type}_shape").lower()
        
        mapping = {
            'cylinder': getattr(self, f"{part_type}_radius"),
            'rectangle': getattr(self, f"{part_type}_height")/2,
            'square': getattr(self, f"{part_type}_side")/2
        }

        return mapping.get(shape, 0)

    def make_structure_part_group(self, part_group, nb_part, span):
        """
        Create and position a group of purlins or rafters across a span.
        part_group define if you want generate a purlin or rafter group.
        """

        # Short-circuit when there is nothing to build.
        if nb_part <= 0:
            return pyv.PolyData()

        # check if you want a purlin group or a rafter group
        if part_group == "purlin":
            # Compute evenly spaced X offsets centered on the span.
            if nb_part == 1:
                offsets_x = [0.0]
            else:
                start = -span / 2.0
                step = span / (nb_part - 1)
                offsets_x = [start + i * step for i in range(nb_part)]

            # Instantiate and place each purlin and translate it with offset value.
            purlin_group = []
            for offx in offsets_x:
                p = Purlin(self.purlin_shape, length=self.purlin_length,
                           panel_tilt_y=0,
                           side=self.purlin_side,
                           radius=self.purlin_radius,
                           width=self.purlin_width,
                           height=self.purlin_height,
                           positioning=self.pole_ground_positioning)

                dim_purlin = self.get_characteristic_dim("purlin")
                dim_rafter = self.get_characteristic_dim("rafter")
                p.polydata.translate((offx,
                                      0,
                                      self.base_height + dim_purlin + dim_rafter),
                                     inplace=True)
                purlin_group.append(p.polydata)

            # Merge meshes into a single polydata group for apply transform to the group. 
            # Need to precise the group height who's defined by the base_height.
            combined = purlin_group[0].copy()
            for mesh in purlin_group[1:]:
                combined = combined + mesh

            # Apply the table tilt around the new center of the group and the purlin offset.
            combined.rotate_y(self.tilt,
                              point=(0,
                                     0,                                     
                                     self.base_height),
                              inplace=True)
        # Same idea for the rafter
        elif part_group == "rafter":
            if nb_part == 1:
                offsets_y = [0.0] # instead of x axis the rafter need a translate offset on y axis
            else:
                start = -span / 2.0
                step = span / (nb_part - 1)
                offsets_y = [start + i * step for i in range(nb_part)]

            rafter_group = []
            for offy in offsets_y:
                p = Rafter(self.rafter_shape, length=self.rafter_length,
                           panel_tilt_y=0, side=self.rafter_side,
                           radius=self.rafter_radius, width=self.rafter_width,
                           height=self.rafter_height,
                           positioning=self.pole_ground_positioning)
                p.polydata.translate((0, 
                                      offy, 
                                      self.base_height),
                                      inplace=True)
                rafter_group.append(p.polydata)

            combined = rafter_group[0].copy()
            for mesh in rafter_group[1:]:
                combined = combined + mesh

            combined.rotate_y(self.tilt,
                              point=(0, 
                                     0, 
                                     self.base_height),
                              inplace=True)
        
        return combined
    
    def make_diagonal(self):
        """
        Build a diagonal brace connecting the two poles with the correct slope.
        """

        ground_offset = self.pole_ground_positioning
        left_pole_height = self.base_height + self.height_offset + ground_offset
        right_pole_height = self.base_height - self.height_offset + ground_offset

        if left_pole_height <= right_pole_height:
            high_x = -self.half_span
            high_z = left_pole_height
            low_x = self.half_span
        else:
            high_x = self.half_span
            high_z = right_pole_height
            low_x = -self.half_span

        low_z = min(self.diagonal_height + ground_offset, high_z - self.diagonal_epsilon)

        vertical_span = high_z - low_z
        horizontal_span = abs(high_x - low_x)
        diagonal_length = math.hypot(horizontal_span, vertical_span)

        diagonal = Diagonal(self.diagonal_shape,
                            length=diagonal_length,
                            width=self.diagonal_width,
                            height=self.diagonal_height,
                            radius=self.diagonal_radius,
                            side=self.diagonal_side,
                            positioning=self.pole_ground_positioning)

        angle = math.degrees(math.atan2(horizontal_span, vertical_span))
        if high_x < low_x:
            angle = -angle

        diagonal.polydata.rotate_y(angle, inplace=True)

        center = ((high_x + low_x) / 2.0,
                  -self.purlin_length / 2.0,
                  (high_z + low_z) / 2.0)
        diagonal.polydata.translate(center, inplace=True)

        return diagonal.polydata


class AgrivoltaicFence(PVStructure):
    """Agrivoltaic fence structure composed of posts and horizontal bars."""

    def __init__(self, PV_i, **kwargs):
        """Initialize agrivoltaic fence parameters from aggregated PV inputs."""
        super().__init__(PV_i, **kwargs)

        # Derive horizontal bar positions from Height (center of panel group),
        # analogous to how PVTable derives pole heights from tilt geometry.
        panel_span_x = (self.panels_per_block_x - 1) * self.panel_spacing_x + self.panel_height
        self.top_bar_height = self.base_height + panel_span_x / 2
        # self.bottom_bar_offset = panel_span_x/2
        self.bottom_bar_offset = panel_span_x - self.panel_height

        if self.top_bar_height - panel_span_x < self.pole_ground_positioning:
            raise ValueError(
                f"Invalid AgrivoltaicFence configuration: The panel group bottom "
                f"({self.top_bar_height - panel_span_x:.2f} m) is at or below ground level "
                f"({self.pole_ground_positioning:.2f} m). "
                f"Increase 'Height' or reduce 'NumberOfPanelsX' / "
                f"'RepetitionDistanceOfPanelsX'."
            )

        panel_span_y = ((self.panels_per_block_y - 1) * self.panel_spacing_y
                        + self.panel_width)
        structure_span_y = self.number_of_structure_groups * self.repetition_distance_group_Y
        if panel_span_y > structure_span_y:
            raise ValueError(
                f"Invalid AgrivoltaicFence configuration: The total panel width in Y "
                f"({panel_span_y:.2f}m) exceeds the structural span in Y "
                f"({structure_span_y:.2f}m). "
                f"Please change the panels configuration on Y axis or adjust "
                f"'NumberOfStructureGroups' or 'RepetitionDistanceGroupY'."
            )

    def make_elementary_group(self) -> pyv.PolyData:
        """Create a fence group by combining one post and two horizontal bars."""

        pole = Pole(self.pole_shape,
                    length=self.top_bar_height - self.pole_ground_positioning,
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

        _fine_positioning_offset = self.get_characteristic_dim("purlin")  # [m] vertical offset to avoid clipping between horizontal bars and PV modules
        horizontal_bar_top.polydata.translate((0, 0, self.top_bar_height),
                                              inplace=True)

        # 2nd horizontal bar is a copy of horizontal_bar_top,
        # translated downwards to the middle of the panel group (in the group's X axis)
        horizontal_bar_bottom = (horizontal_bar_top.polydata
                                 .copy().
                                 translate((0, 0, -self.bottom_bar_offset),
                                           inplace=True))

        # Fine positioning of both horizontal bars
        horizontal_bar_top.polydata.translate((0, 0, _fine_positioning_offset),
                                              inplace=True)
        horizontal_bar_bottom.translate((0, 0, _fine_positioning_offset),
                                                 inplace=True)


        combined = (pole.polydata
                    + horizontal_bar_top.polydata
                    + horizontal_bar_bottom).triangulate()

        return combined

    def build_structure(self) -> pyv.MultiBlock:
        """
        Assemble all fence groups along Y and add a terminal post.
        """
        half_span = (self.number_of_structure_groups - 1) * self.repetition_distance_group_Y / 2
        group_y_offsets = [
            -half_span + idx * self.repetition_distance_group_Y
            for idx in range(self.number_of_structure_groups)
        ]

        blocks = pyv.MultiBlock()

        for offy in group_y_offsets:
            g = self.make_elementary_group()
            g.translate((0, offy, 0), inplace=True)
            blocks.append(g)

        end_pole = Pole(self.pole_shape,
                        length=self.top_bar_height - self.pole_ground_positioning,
                        width=self.pole_width,
                        height=self.pole_height,
                        side=self.pole_side,
                        radius=self.pole_radius,
                        positioning=self.pole_ground_positioning)

        end_pole.polydata.translate((0,
                                     group_y_offsets[-1] + self.repetition_distance_group_Y / 2,
                                     0.0),
                                    inplace=True)
        blocks.append(end_pole.polydata)
        combined_blocks = blocks.combine()
        combined_blocks.user_dict = {'Material': self.material}

        return combined_blocks

class PVTable(PVStructure):
    """
    Fixed tilted table with posts, rafters, and diagonal bracing.
    """

    def __init__(self, PV_i, **kwargs):
        """
        Derive span, tilt, and minimum rafter length for the table geometry.
        """
        super().__init__(PV_i, **kwargs)

        self.tilt_rad = math.radians(self.tilt)
        self.half_span = self.pole_spacing/2

        self.required_length = 2 * self.half_span / math.cos(self.tilt_rad) 
        self.rafter_length = max(self.rafter_length, 
                                 self.required_length)

        panel_span_x = ((self.panels_per_block_x - 1) * self.panel_spacing_x
                        + self.panel_height)
        if panel_span_x > self.rafter_length:
            raise ValueError(
                f"Invalid PVTable configuration: The total panel height in X "
                f"({panel_span_x:.2f}m) exceeds the rafter length "
                f"({self.rafter_length:.2f}m). "
                f"Please change the panels configuration on X axis or increase the rafter length by increasing 'PoleSpacingX' or 'RafterLength'."
            )

        panel_span_y = ((self.panels_per_block_y - 1) * self.panel_spacing_y
                        + self.panel_width)
        structure_span_y = self.number_of_structure_groups * self.purlin_length
        if panel_span_y > structure_span_y:
            raise ValueError(
                f"Invalid PVTable configuration: The total panel width in Y "
                f"({panel_span_y:.2f}m) exceeds the structural span in Y "
                f"({structure_span_y:.2f}m). "
                f"Please change the panels configuration on Y axis or adjust 'NumberOfStructureGroups' or 'RepetitionDistanceOfPanelsY'."
            )

        self.height_offset = self.half_span * math.tan(self.tilt_rad)

        if self.base_height - self.height_offset < 0:
            raise ValueError(f"Invalid PVTable configuration: The tilt angle ({self.tilt}°) "
                             f"is too high for the given base height ({self.base_height}m). "
                             f"This results in the structure extending {abs(self.base_height - self.height_offset):.2f}m "
                             "below ground level. Please increase 'Height' or 'PoleSpacingX' or decrease 'TiltY'.")

    def make_elementary_group(self) -> pyv.PolyData:
        """Build one table group with poles, rafters, diagonals, and purlins."""
        pole_and_rafter_group = self.make_start_and_end_block()
        purlin_group = self.make_structure_part_group("purlin",
                                            self.numbers_of_purlin,
                                            self.rafter_length)

        combined = pole_and_rafter_group + purlin_group

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
        pole.polydata.translate((-self.half_span, 
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
        pole_2.polydata.translate((self.half_span,
                                   -self.purlin_length/2,
                                   0),
                                  inplace=True)
        
        rafter = Rafter(self.rafter_shape, length=self.rafter_length,
                        panel_tilt_y=self.tilt, radius=self.rafter_radius,
                        side=self.rafter_side, width=self.rafter_width,
                        height=self.rafter_height,
                        positioning=self.pole_ground_positioning)
        rafter.polydata.translate((0,
                                   -self.purlin_length/2,
                                   self.base_height),
                                  inplace=True)
        
        diagonal = self.make_diagonal()

        combine = (pole.polydata
                   + pole_2.polydata
                   + rafter.polydata
                   + diagonal)

        return combine

    def build_structure(self) -> pyv.MultiBlock :
        """Replicate groups across the Y grid and cap with an end group."""

        # group positions centered around 0, spaced by repetition_distance_group_Y
        half_span = (self.number_of_structure_groups - 1) * self.repetition_distance_group_Y / 2
        group_y_offsets = [
            -half_span + idx * self.repetition_distance_group_Y
            for idx in range(self.number_of_structure_groups)
        ]

        blocks = pyv.MultiBlock()

        for offy in group_y_offsets:
            g = self.make_elementary_group()
            g.translate((0, offy, 0), inplace=True)
            blocks.append(g)

        end_pole = self.make_start_and_end_block()
        end_pole.translate((0,
                            offy + self.repetition_distance_group_Y,
                            0.0),
                            inplace=True)
        
        blocks.append(end_pole)

        combined_blocks = blocks.combine()
        combined_blocks.user_dict = {'Material': self.material}

        return combined_blocks


class HSATS(PVStructure):
    """
    HSATS: horizontal single-axis tracker managing purlins and tilted rafters.
    """

    def __init__(self, PV_i, **kwargs):
        """Initialize HSATS with common PV inputs."""
        super().__init__(PV_i, **kwargs)

        panel_span_x = ((self.panels_per_block_x - 1) * self.panel_spacing_x
                        + self.panel_height)
        if panel_span_x > self.rafter_length + 2*self.panel_height:
            raise ValueError(
                f"Invalid HSATS configuration: The total panel height in X "
                f"({panel_span_x:.2f}m) far exceeds the rafter length "
                f"({self.rafter_length:.2f}m) and produces invalid overhang length. "
                f"Please change the panels configuration on X axis or increase "
                f"the rafter length by increasing 'RafterLength'. The total panel span along X must be at most equal to "
                f"the rafter length + 2 x panel_height. "
            )

        panel_span_y = ((self.panels_per_block_y - 1) * self.panel_spacing_y
                        + self.panel_width)
        structure_span_y = self.number_of_structure_groups * self.repetition_distance_group_Y
        if panel_span_y > structure_span_y:
            raise ValueError(
                f"Invalid HSATS configuration: The total panel width in Y "
                f"({panel_span_y:.2f}m) exceeds the structural span in Y "
                f"({structure_span_y:.2f}m). "
                f"Please change the panels configuration on Y axis or adjust "
                f"'NumberOfStructureGroups' or 'RepetitionDistanceGroupY'."
            )

    def make_elementary_group(self) -> pyv.PolyData:
        """
        Create the tracker group with central post plus purlin and rafter groups.
        """

        pole = Pole(self.pole_shape,
                    length=self.base_height,
                    width=self.pole_width,
                    height=self.pole_height,
                    side=self.pole_side,
                    radius=self.pole_radius,
                    positioning=self.pole_ground_positioning)

        purlin_group = self.make_structure_part_group("purlin", 
                                                      self.numbers_of_purlin,
                                                      self.rafter_length)
        
        rafter_group = self.make_structure_part_group("rafter",
                                                      self.numbers_of_rafter,
                                                      self.purlin_length)

        combine = (pole.polydata + purlin_group + rafter_group)

        return combine
    
    def build_structure(self):
        """Return the assembled HSATS group (single-axis tracker)."""
        half_span = (self.number_of_structure_groups - 1) * self.repetition_distance_group_Y / 2
        group_y_offsets = [
            -half_span + idx * self.repetition_distance_group_Y
            for idx in range(self.number_of_structure_groups)
        ]

        blocks = pyv.MultiBlock()

        for offy in group_y_offsets:
            group = self.make_elementary_group()
            group.translate((0.0, offy, 0.0), inplace=True)
            blocks.append(group)

        combined = blocks.combine()
        combined.user_dict = {'Material': self.material}

        return combined


if __name__ == "__main__":
    from pase.DATA_MANAGEMENT.yaml_inputs_provider import (YAML_Inputs_provider,
                                                           Inputs_aggregator)
    import os

    struct_type = "pv_table"  # "HSATS" or "pv_table" or "agrivoltaic_fence"
    panel_orientation = "landscape"  # "landscape" or "portrait"
    display_style = "lean"  # "lean", "nice" or "technical"

    if struct_type == "HSATS":
        av_file = "Example4_HSATS.yaml"
        struct_file = "HSATS.yaml"
    elif struct_type.lower() == "pv_table":
        av_file = "Example5_PVTable.yaml"
        struct_file = "PV_table.yaml"
    elif struct_type.lower() == "agrivoltaic_fence":
        av_file = "Example3_AV_agrivoltaic_fence.yaml"
        struct_file = "agrivoltaic_fence.yaml"

    if panel_orientation == "landscape":
        pv_file = "Example1_PV_Module_landscape.yaml"
    elif panel_orientation == "portrait":
        pv_file = "Example1_PV_Module.yaml"


    AV_1 = YAML_Inputs_provider(
        file=av_file,
        subpath="AV_CENTRAL",
        parentdir=2
    ).inputs

    PV_module_1 = YAML_Inputs_provider(
        file=pv_file,
        subpath=os.path.join("HARDWARE", "PV_MODULES"),
        parentdir=2
    ).inputs

    Structure = YAML_Inputs_provider(
        file=struct_file,
        subpath=os.path.join("HARDWARE", "STRUCTURES"),
        parentdir=2
    ).inputs

    PV_params_dict = Inputs_aggregator([AV_1,
                                        PV_module_1,
                                        Structure]).aggregated_inputs

    if struct_type == "HSATS":
        blocks = HSATS(PV_params_dict).build_structure()
    elif struct_type == "pv_table":
        blocks = PVTable(PV_params_dict).build_structure()
    elif struct_type == "agrivoltaic_fence":
        blocks = AgrivoltaicFence(PV_params_dict).build_structure()

    if display_style == "technical":
        show_edges = True
    else:
        show_edges = False

    pl = pyv.Plotter()
    pl.add_mesh(blocks, show_edges=show_edges)
    if display_style == "technical":
        pl.show_axes()
        pl.show_grid(color='gray')
    elif display_style == "nice":
        x_half_span = 5
        y_half_span = 10
        ground = np.array([[-x_half_span, y_half_span, 0],
                           [x_half_span, y_half_span, 0],
                           [-x_half_span, -y_half_span, 0],
                           [x_half_span, -y_half_span, 0]])

        ground_m = np.hstack([[3, 0, 1, 2],
                              [3, 1, 2, 3], ])

        grnd = pyv.PolyData(ground, ground_m)

        pl.add_mesh(grnd, color='green', opacity=0.5)

        light = pyv.Light(intensity=0.2,
                          position=(10, 10, 10))
        # light.set_direction_angle(30, 45)
        pl.add_light(light)
    pl.show()
