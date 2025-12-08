import math
from pathlib import Path

import pyvista as pyv
import pytest
import yaml

from pase.PHOTOVOLTAICS.structure import AgrivoltaicFence, HSATS, PVTable


def _load_yaml_values(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return {key: values["Value"] for key, values in raw.items()}


@pytest.fixture(scope="module")
def inputs_factory():
    """
    Build a callable that merges AV, module and structure YAML inputs
    into the single dictionary expected by PV structures.
    """
    repo_root = Path(__file__).resolve().parents[2]
    av_inputs = _load_yaml_values(
        repo_root 
        / "INPUTS" 
        / "AV_CENTRAL" 
        / "Example4_HSATS.yaml"
    )
    module_inputs = _load_yaml_values(
        repo_root
        / "INPUTS"
        / "HARDWARE"
        / "PV_MODULES"
        / "Example1_PV_Module_landscape.yaml"
    )

    def _builder(structure_filename: str) -> dict:
        structure_inputs = _load_yaml_values(
            repo_root 
            / "INPUTS" 
            / "HARDWARE" 
            / "STRUCTURES" 
            / structure_filename
        )
        merged = {**av_inputs, **module_inputs, **structure_inputs}
        return merged

    return _builder


def test_agrivoltaic_fence_structure_height_affects_mesh(inputs_factory):
    params = inputs_factory("PV_table.yaml")
    params["StructureType"] = "Agrivoltaic Fence"

    base_fence = AgrivoltaicFence(params.copy())
    base_mesh = base_fence.build_structure()

    taller_params = params.copy()
    taller_params["StructureHeight"] += 1.0
    taller_fence = AgrivoltaicFence(taller_params)
    taller_mesh = taller_fence.build_structure()

    assert isinstance(base_mesh, pyv.DataSet)
    assert base_mesh.user_dict["Material"] == params["Material"]
    assert base_mesh.n_points > 0

    def _min_distance_to_height(mesh, target):
        return min(abs(p[2] - target) for p in mesh.points)

    base_offset = _min_distance_to_height(base_mesh, params["StructureHeight"])
    taller_offset = _min_distance_to_height(
        taller_mesh, taller_params["StructureHeight"]
    )
    assert base_offset < 5e-3
    assert taller_offset < 5e-3


def test_pv_table_rafter_length_extends_to_span(inputs_factory):
    params = inputs_factory("PV_table.yaml")
    params["RafterLength"] = 1.0

    pv_table = PVTable(params)
    required_length = (
        2 * params["PoleSpacingX"] / math.cos(math.radians(params["TiltY"]))
    )

    assert pytest.approx(pv_table.rafter_length, rel=1e-6) == required_length

    mesh = pv_table.build_structure()
    assert isinstance(mesh, pyv.DataSet)
    assert mesh.user_dict["Material"] == params["Material"]
    assert mesh.n_cells > 0


def test_hsats_component_counts_influence_geometry(inputs_factory):
    params = inputs_factory("HSATS.yaml")

    tracker_full = HSATS(params)
    mesh_full = tracker_full.build_structure()

    reduced_params = params.copy()
    reduced_params["NumberOfPurlins"] = 2
    reduced_params["NumberOfRafters"] = 2
    tracker_reduced = HSATS(reduced_params)
    mesh_reduced = tracker_reduced.build_structure()

    assert isinstance(mesh_full, pyv.DataSet)
    assert mesh_full.n_points > mesh_reduced.n_points
    assert mesh_full.n_cells > mesh_reduced.n_cells
