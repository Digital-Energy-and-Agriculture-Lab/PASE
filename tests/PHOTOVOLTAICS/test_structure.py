import pytest
from pase.PHOTOVOLTAICS.structure import PVStructurePart, PVStructure
import yaml
from pathlib import Path

def test_yaml_keys_match_pvstructure():
    yaml_path = (
        Path(__file__).resolve()
        .parents[2]
        / "INPUTS"
        / "HARDWARE"
        / "STRUCTURES"
        / "Example1_PV_structure.yaml"
    )
    assert yaml_path.exists(), f"YAML file not found at {yaml_path}"

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    expected_keys = {
        "StructureType",
        "Material",
        "PanelsPerGroup",
        "PoleShape",
        "PoleWidth",
        "PoleHeight",
        "PoleSide",
        "PoleRadius",
        "PoleLength",
        "PoleGroundPositioning",
        "PurlinShape",
        "PurlinWidth",
        "PurlinHeight",
        "PurlinSide",
        "PurlinRadius",
        "StructureSpacingY",
        "StructureHeight",
    }

    if isinstance(data, dict) and len(data) == 1:
        data = next(iter(data.values()))

    yaml_keys = set(data.keys())
    missing = expected_keys - yaml_keys
    extra = yaml_keys - expected_keys

    assert not missing, f"Missing keys in YAML: {missing}"
    assert not extra, f"Unexpected keys in YAML: {extra}"