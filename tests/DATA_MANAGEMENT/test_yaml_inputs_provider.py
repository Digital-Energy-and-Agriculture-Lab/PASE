import pytest

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider

PASE_Logger()


def _bare_provider():
    """Build a YAML_Inputs_provider instance without going through __init__/file loading."""
    provider = YAML_Inputs_provider.__new__(YAML_Inputs_provider)
    provider.inputs = {}
    return provider


# -----------------------
# check_possibilities
# -----------------------

def test_check_possibilities_numeric_value_passes():
    provider = _bare_provider()
    data = {"Value": 2, "Possibilities": [1, 2, 3]}

    provider.check_possibilities("MF", data)

    assert provider.inputs["MF"] == 2


def test_check_possibilities_string_is_normalized():
    provider = _bare_provider()
    data = {"Value": " StIcS ", "Possibilities": ["stics", "grassim", "simple", "pystics"]}

    provider.check_possibilities("CropModel", data)

    assert provider.inputs["CropModel"] == "stics"


def test_check_possibilities_invalid_value_raises():
    provider = _bare_provider()
    data = {"Value": "unknown_model", "Possibilities": ["stics", "grassim", "simple", "pystics"]}

    with pytest.raises(ValueError) as excinfo:
        provider.check_possibilities("CropModel", data)

    assert "CropModel" in str(excinfo.value)
    assert "stics" in str(excinfo.value)
    assert "unknown_model" in str(excinfo.value)


def test_check_possibilities_rejects_non_list_possibilities():
    provider = _bare_provider()
    data = {"Value": "stics", "Possibilities": "stics, grassim, simple, pystics"}

    with pytest.raises(TypeError, match="square brackets"):
        provider.check_possibilities("CropModel", data)


def test_check_possibilities_mixed_type_list():
    provider = _bare_provider()
    data = {"Value": "a", "Possibilities": ["A", 1]}

    provider.check_possibilities("Key", data)

    assert provider.inputs["Key"] == "a"


def test_check_possibilities_boolean_value_not_normalized():
    provider = _bare_provider()
    data = {"Value": True, "Possibilities": [True, False]}

    provider.check_possibilities("Flag", data)

    assert provider.inputs["Flag"] is True


# -----------------------
# check_value_str
# -----------------------

def test_check_value_str_with_possibilities_valid():
    provider = _bare_provider()
    data = {"Value": " StIcS ", "Type": "string", "Possibilities": ["stics", "grassim", "simple", "pystics"]}

    provider.check_value_str("CropModel", data, {})

    assert provider.inputs["CropModel"] == "stics"


def test_check_value_str_with_possibilities_invalid_raises():
    provider = _bare_provider()
    data = {"Value": "unknown_model", "Type": "string", "Possibilities": ["stics", "grassim", "simple", "pystics"]}

    with pytest.raises(ValueError):
        provider.check_value_str("CropModel", data, {})


def test_check_value_str_without_possibilities_is_not_normalized():
    # Documents current behavior: stripping/lowering only happens inside
    # check_possibilities, so a string without a Possibilities list is stored verbatim.
    provider = _bare_provider()
    data = {"Value": " Chanco_Chile_WD ", "Type": "string"}

    provider.check_value_str("WeatherFileName", data, {})

    assert provider.inputs["WeatherFileName"] == " Chanco_Chile_WD "


# -----------------------
# check_value_bool
# -----------------------

def test_check_value_bool_with_possibilities_valid():
    provider = _bare_provider()
    data = {"Value": True, "Type": "boolean", "Possibilities": [True, False]}

    provider.check_value_bool("Flag", data, {})

    assert provider.inputs["Flag"] is True


def test_check_value_bool_with_possibilities_invalid_raises():
    provider = _bare_provider()
    data = {"Value": True, "Type": "boolean", "Possibilities": [False]}

    with pytest.raises(ValueError):
        provider.check_value_bool("Flag", data, {})


# -----------------------
# check_value_list
# -----------------------

def test_check_value_list_with_possibilities_valid():
    provider = _bare_provider()
    data = {"Value": [1, 2], "Type": "list", "Possibilities": [[1, 2], [3, 4]]}

    provider.check_value_list("Coords", data, {})

    assert provider.inputs["Coords"] == [1, 2]


def test_check_value_list_with_possibilities_invalid_raises():
    provider = _bare_provider()
    data = {"Value": [9, 9], "Type": "list", "Possibilities": [[1, 2], [3, 4]]}

    with pytest.raises(ValueError):
        provider.check_value_list("Coords", data, {})


# -----------------------
# check_value_float (Limit is checked before Possibilities)
# -----------------------

def test_check_value_float_with_limits_and_possibilities_valid():
    provider = _bare_provider()
    data = {"Value": 15.0, "Type": "float", "Limit": [0, 100], "Possibilities": [15.0, 30.0]}

    provider.check_value_float("Tilt", data, {})

    assert provider.inputs["Tilt"] == 15.0


def test_check_value_float_limits_pass_possibilities_fail_raises():
    provider = _bare_provider()
    data = {"Value": 20.0, "Type": "float", "Limit": [0, 100], "Possibilities": [15.0, 30.0]}

    with pytest.raises(ValueError):
        provider.check_value_float("Tilt", data, {})


# -----------------------
# check_value_int (Limit is checked before Possibilities)
# -----------------------

def test_check_value_int_with_limits_and_possibilities_valid():
    provider = _bare_provider()
    data = {"Value": 2, "Type": "integer", "Limit": [1, 5], "Possibilities": [1, 2, 3]}

    provider.check_value_int("Option", data, {})

    assert provider.inputs["Option"] == 2


def test_check_value_int_limits_pass_possibilities_fail_raises():
    provider = _bare_provider()
    data = {"Value": 4, "Type": "integer", "Limit": [1, 5], "Possibilities": [1, 2, 3]}

    with pytest.raises(ValueError):
        provider.check_value_int("Option", data, {})


# -----------------------
# End-to-end through __init__ / real YAML file
# -----------------------

def test_end_to_end_yaml_with_valid_possibilities_list(tmp_path):
    # Mirrors the real CropModel field in INPUTS/CROPS/config/simple_example.yml
    yaml_content = (
        "CropModel:\n"
        "  Value: Stics\n"
        "  Type: string\n"
        "  Possibilities: [stics, grassim, simple, pystics]\n"
    )
    (tmp_path / "test_inputs.yaml").write_text(yaml_content)

    provider = YAML_Inputs_provider(file="test_inputs.yaml", path=str(tmp_path))

    assert provider.inputs["CropModel"] == "stics"


def test_end_to_end_yaml_possibilities_missing_brackets_raises(tmp_path):
    yaml_content = (
        "CropModel:\n"
        "  Value: stics\n"
        "  Type: string\n"
        "  Possibilities: stics, grassim, simple, pystics\n"
    )
    (tmp_path / "test_inputs.yaml").write_text(yaml_content)

    with pytest.raises(TypeError, match="square brackets"):
        YAML_Inputs_provider(file="test_inputs.yaml", path=str(tmp_path))
