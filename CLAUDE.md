# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PASE (Python Agrivoltaic Simulation Environment)** simulates agrivoltaic systems — calculating both photovoltaic (PV) electricity production and agricultural outputs by modeling how PV panels shade crops. Developed at the University of Liège's DEAL lab.

## Environment Setup

```bash
conda env create -f environment_unix.yml   # macOS/Linux
conda env create -f environment_windows.yml  # Windows
conda activate pase-2026-07  # env name comes from the yml's `name:` field, can be overridden with -n
```

Key dependencies: python 3.12, numpy, pandas (2.2+, uses lowercase freq aliases e.g. `"h"` not `"H"`), vtk, trimesh, pyvista, pvlib>0.15, embreex (replaces pyembree), pyyaml.

## Commands

```bash
# Run all tests with coverage
pytest -vv --junitxml=junit.xml

# Run a single test file
pytest tests/ENVIRONMENT/test_light.py -vv

# Run a single test function
pytest tests/ENVIRONMENT/test_light.py::TestLight::test_get_sky_type -vv

# Code formatting
black pase/
isort pase/

# Type checking
mypy pase/
```

## Architecture

### Data Flow

```
YAML Inputs → InputsEvaluator (validation) → Weather_data (PVGIS API)
    → Sun_positions → PV_Configuration_3D (PyVista 3D geometry)
    → Mesh (sampling points) → Ray_casting_scene (PyEmbree ray tracing)
    → PV_Production (electricity) + run_crop_simu (SIMPLE/STICS/GRASSIM)
    → OutputsManager (CSV export, caching, visualization)
```

### Package Structure

- **`pase/PHOTOVOLTAICS/`** — 3D PV scene generation (`configuration.py`), power output (`production.py`), lenticular diffuser BSDF modeling (`diffuser.py`), panel geometry builders (`structure.py`)
- **`pase/ENVIRONMENT/`** — Solar positions + irradiance decomposition with HDKR/Erbs model (`light.py`), Reinhart/CIE sky discretization (`sky_model.py`), scene sampling points (`mesh.py`), logarithmic wind profile + windbreaks (`aerodynamics.py`)
- **`pase/DATA_MANAGEMENT/`** — YAML parsing + validation (`yaml_inputs_provider.py`), PVGIS weather API (`weather_data_provider.py`), output directory/cache management (`OUTPUT/outputs_manager.py`)
- **`pase/CROPS/`** — Crop model orchestrator (`run_crop_simulations.py`), SIMPLE model (pure Python), STICS (co-simulation via JavaStics 1.5.1), Gras-Sim grassland model
- **`pase/pase_math.py`** — Vectorized grid layout and rotation math (coordinate system: East=X, North=Y, Zenith=Z)

### Key Architectural Patterns

**Configuration is YAML-based.** Three input file categories under `INPUTS/`:
- `SCENARIOS/` — location, time period, weather
- `AV_CENTRAL/` — PV layout (spacing, tilt, azimuth, row count)
- `HARDWARE/PV_MODULES/` — panel properties (dimensions, power, bifaciality)

Each YAML parameter has `Type/Value/Limits/Unit/Definition` fields. `InputsEvaluator` validates all inputs at runtime.

**3D geometry uses PyVista PolyData** throughout. `PV_Configuration_3D` builds the panel scene; `Mesh` manages sampling point MultiBlocks. Ray casting uses PyEmbree (Intel Embree acceleration) for shadow computation.

**`Light` vs `Ray_casting_scene`:** `Light` computes irradiance components (GHI/DNI/DHI) and solar vectors. `Ray_casting_scene` uses those vectors plus the 3D geometry to compute shading maps and diffuse sky view factors.

**Output caching:** `OutputsManager` tracks simulation variants and caches results under `OUTPUTS/`. Results are stored as CSV + pickle.

### Branch Strategy

- `main` — stable releases
- `develop` — integration branch
- Feature branches: `<issue-number>-<short-description>`

## Conventions 

- Entry points use `if __name__ == "__main__": sys.exit(main())`
- Docstrings: numpy style
- No print() statements for logging, use `logging` library with custom PASE_Logger instance
- use American english
- unit tests rely on pytest only (avoid unittest as much as possible)
- no lazy imports

## Instructions
- PASE is hosted on a Gitlab repository ; use glab to access the repository (e.g. list issues, read or write an issue, etc.)
- When writing an issue, follow the templates located under .gitlab/issue_templates/ (there is one for feature requests, and one for bugs)

### Writing commit messages guidelines
The standard commit structure is : 
- a title line with the type of commit in square brackets, e.g. : [feature]
- followed by a blank line
- followed by the body of the commit message

The message should inform on :
- what was done
- why was it done

Write the commit message in .claude/commit.txt so i can copy/paste it in my IDE's commit text box.