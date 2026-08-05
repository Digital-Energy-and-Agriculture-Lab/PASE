"""Import hygiene and backend dispatch of the crop-model orchestrator.

The STICS backends are excluded from the wheel (#267) and, in a source
checkout, pySTICS lives in a submodule that may not be initialized. So
``pase.CROPS.run_crop_simulations`` must import — and must still drive the
shipped pure-Python models SIMPLE and Gras-Sim — with those backends
absent (#271). Each backend's dependencies are required only when that
backend is selected, and selecting a missing one must say so clearly.

``_ImportBlocker`` reproduces the installed-package situation in-process by
making ``pase.CROPS.STICS`` unimportable, so no built wheel is needed. The
orchestrator is imported once at module level like every other test in the
suite, and re-executed with ``importlib.reload`` where a fresh module body
is what is under test — importing ``pase.*`` inside a test body would
instead re-resolve the package against a ``sys.path`` that pytest has
already extended.
"""

import contextlib
import importlib
import sys

import pytest

from pase.CROPS import run_crop_simulations as orchestrator
from pase.CROPS.GRASSIM import run_grassim as grassim_module
from pase.CROPS.SIMPLE import run_simple

BACKEND_MODULES = ("pase.CROPS.SIMPLE", "pase.CROPS.STICS",
                   "pase.CROPS.GRASSIM")


class _ImportBlocker:
    """Meta-path finder making selected packages unimportable.

    Stands in for a wheel from which the STICS sources were excluded.
    """

    def __init__(self, *prefixes):
        self.prefixes = prefixes

    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == prefix or fullname.startswith(f"{prefix}.")
               for prefix in self.prefixes):
            raise ModuleNotFoundError(
                f"No module named {fullname!r} (blocked by test)",
                name=fullname)
        return None


class _FakePlot:
    """Minimal stand-in for a crop/soil plot object."""

    def __init__(self, nyears_data):
        self.nyears_data = nyears_data


@contextlib.contextmanager
def _unloaded(*prefixes):
    """Temporarily drop matching modules from ``sys.modules``."""
    saved = {name: module for name, module in sys.modules.items()
             if name.startswith(prefixes)}
    for name in saved:
        del sys.modules[name]
    try:
        yield
    finally:
        sys.modules.update(saved)


@pytest.fixture
def without_stics():
    """Import state of a PASE install that carries no STICS backend."""
    blocker = _ImportBlocker("pase.CROPS.STICS")
    with _unloaded("pase.CROPS.STICS"):
        sys.meta_path.insert(0, blocker)
        try:
            yield
        finally:
            sys.meta_path.remove(blocker)


@pytest.fixture
def reimport_orchestrator():
    """Re-execute the orchestrator's module body, then restore it.

    Request this fixture *before* ``without_stics`` so the restoring
    reload runs after the blocker has been uninstalled.
    """
    yield lambda: importlib.reload(orchestrator)
    importlib.reload(orchestrator)


def test_orchestrator_imports_without_stics(reimport_orchestrator,
                                            without_stics):
    """The regression from #271: the module itself must import."""
    with pytest.raises(ModuleNotFoundError, match="blocked by test"):
        importlib.import_module("pase.CROPS.STICS.JAVASTICS.run_java_stics")

    module = reimport_orchestrator()

    assert callable(module.run_crop_simu)
    assert callable(module.visualize_map_of_a_variable)


def test_importing_the_orchestrator_loads_no_backend(reimport_orchestrator):
    """No backend is imported until one is actually selected."""
    with _unloaded(*BACKEND_MODULES):
        reimport_orchestrator()
        loaded = sorted(name for name in sys.modules
                        if name.startswith(BACKEND_MODULES))

    assert loaded == []


def test_simple_dispatches_with_stics_absent(without_stics, monkeypatch):
    """SIMPLE runs through the orchestrator although STICS is missing."""
    calls = []

    def fake_runner(config, option_2D, WD, daily_irr, latitude, altitude):
        calls.append((config, option_2D, WD, daily_irr, latitude, altitude))
        return (_FakePlot({"2020": {"soil_water": 1.0}}),
                _FakePlot({"2020": {"yield": 2.0}}))

    monkeypatch.setattr(run_simple, "run_independant_years_of_crop",
                        fake_runner)

    results = orchestrator.run_crop_simu({"CropModel": "simple"}, False,
                                         "weather", "irradiation",
                                         {"Latitude": 50.6, "Altitude": 100})

    assert results == {"2020": {"soil_water": 1.0, "yield": 2.0}}
    assert len(calls) == 1
    assert calls[0][4:] == (50.6, 100)


def test_grassim_dispatches_with_stics_absent(without_stics, monkeypatch):
    """Gras-Sim likewise runs, and its three plots are merged."""

    def fake_runner(config, WD, daily_irr, latitude, altitude):
        return (_FakePlot({"2020": {"soil_water": 1.0}}),
                _FakePlot({"2020": {"biomass": 2.0}}),
                _FakePlot({"2020": {"cuts": 3}}))

    monkeypatch.setattr(grassim_module, "run_grassim", fake_runner)

    results = orchestrator.run_crop_simu({"CropModel": "grassim"}, False,
                                         "weather", "irradiation",
                                         {"Latitude": 50.6, "Altitude": 100})

    assert results == {"2020": {"soil_water": 1.0, "biomass": 2.0, "cuts": 3}}


@pytest.mark.parametrize("model", ["stics", "pystics"])
def test_selecting_a_missing_backend_raises_an_actionable_error(without_stics,
                                                               model):
    """The error names the backend and points at its setup instructions."""
    with pytest.raises(ImportError) as excinfo:
        orchestrator.run_crop_simu({"CropModel": model}, False, "weather",
                                   "irradiation", {})

    message = str(excinfo.value)
    assert model in message
    assert "pase.CROPS.STICS" in message
    assert "wiki" in message.lower() or "documentation" in message.lower()
    # The original ModuleNotFoundError stays available for debugging.
    assert isinstance(excinfo.value.__cause__, ImportError)


def test_unknown_crop_model_raises_before_importing_anything():
    """An unsupported CropModel fails loudly instead of returning {}."""
    with _unloaded(*BACKEND_MODULES):
        with pytest.raises(ValueError) as excinfo:
            orchestrator.run_crop_simu({"CropModel": "triticale"}, False,
                                       "weather", "irradiation", {})
        loaded = sorted(name for name in sys.modules
                        if name.startswith(BACKEND_MODULES))

    message = str(excinfo.value)
    assert "triticale" in message
    for supported in ("simple", "stics", "pystics", "grassim"):
        assert supported in message
    assert loaded == []
