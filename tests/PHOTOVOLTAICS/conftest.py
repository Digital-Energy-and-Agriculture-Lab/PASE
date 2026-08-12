import pytest


@pytest.fixture
def structure_inputs():
    """Provide a minimal yet coherent configuration for structure classes."""

    base = {
        "PanelsPerGroup": 2,
        "NumberOfStructureGroups": 2,
        "RepetitionDistanceGroupY": 2.0,
        "NumberOfPanelsX": 2,
        "NumberOfPanelsY": 2,
        "RepetitionDistanceOfPanelsX": 2.0,
        "RepetitionDistanceOfPanelsY": 2.0,
        "StructureHeight": 3.0,
        "PoleShape": "circle",
        "PoleWidth": 0.2,
        "PoleHeight": 0.2,
        "PoleSide": 0.2,
        "PoleRadius": 0.1,
        "PoleLength": 3.0,
        "PoleGroundPositioning": 0.0,
        "PurlinShape": "rectangle",
        "PurlinWidth": 0.1,
        "PurlinHeight": 0.05,
        "PurlinSide": 0.1,
        "PurlinRadius": 0.05,
        "NumberOfPurlins": 2,
        "RafterShape": "rectangle",
        "RafterWidth": 0.1,
        "RafterHeight": 0.05,
        "RafterSide": 0.1,
        "RafterLength": 4.0,
        "RafterRadius": 0.05,
        "NumberOfRafters": 2,
        "DiagonalShape": "rectangle",
        "DiagonalWidth": 0.05,
        "DiagonalHeight": 1.0,
        "DiagonalSide": 0.05,
        "DiagonalRadius": 0.05,
        "DiagonalGroundGuard": 0.1,
        "Material": "steel",
        "PanelDimensionX": 1.6,
        "PanelDimensionY": 1.0,
        "RepetitionDistanceOfPVBlocksX": 4.0,
        "RepetitionDistanceOfPVBlocksY": 3.0,
        "NumberOfPVBlocksX": 1,
        "NumberOfPVBlocksY": 1,
        "Height": 2.0,
        "PoleSpacingX": 1.0,
        "TiltY": 15.0,
        "DiagonalEpsilon": 0.000001,
        "RepetitionDistanceGroupYMode": "manual",
    }

    def _factory(**overrides):
        data = base.copy()
        data.update(overrides)
        return data

    return _factory
