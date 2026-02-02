import pyvista as pyv
import pytest

from pase.PHOTOVOLTAICS.structure import AgrivoltaicFence, HSATS, PVTable


@pytest.fixture
def structure_inputs():
    """Provide a minimal yet coherent configuration for structure classes."""

    base = {
        "PanelsPerGroup": 2,
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
        "HeightOffset": -0.5,
        "DiagonalEpsilon": 0.000001,
    }

    def _factory(**overrides):
        data = base.copy()
        data.update(overrides)
        return data

    return _factory


@pytest.mark.parametrize("structure_cls", [AgrivoltaicFence, HSATS, PVTable])
@pytest.mark.parametrize(
    "config_overrides",
    [
        {},
        pytest.param(
            {
                "NumberOfPanelsX": 4,
                "NumberOfPanelsY": 2,
                "PanelsPerGroup": 4,
                "NumberOfPVBlocksX": 2,
                "NumberOfPVBlocksY": 1,
                "RepetitionDistanceOfPVBlocksX": 6.0,
                "RepetitionDistanceOfPanelsY": 2.4,
                "NumberOfPurlins": 3,
                "NumberOfRafters": 3,
                "PoleSpacingX": 1.5,
                "PoleLength": 3.5,
                "TiltY": 5.0,
            },
            id="wider-layout",
        ),
    ],
)
def test_structure_builds_without_errors(structure_cls, structure_inputs, config_overrides):
    cfg = structure_inputs(**config_overrides)
    structure = structure_cls(cfg)
    
    # Check DiagonalEpsilon
    assert structure.diagonal_epsilon == 0.000001
    
    built = structure.build_structure()

    assert isinstance(built, pyv.DataSet)
    assert built.n_cells > 0
