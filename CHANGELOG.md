# Changelog

All notable changes to PASE are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and PASE adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Each release is split into two audiences:

- **For users** — features, behavioral changes, and the *implications* of bug
  fixes: things a modeller running PASE would notice.
- **For developers** — build/packaging, CI, tests, and internal refactors.

Every merge request should add its entry under `## [Unreleased]`; when a release
is cut, that section is retitled `## [X.Y.Z] - YYYY-MM-DD` (see `RELEASE.md`).

## [Unreleased]

> The changes below constitute the upcoming **1.4.0** release — the first
> release cut from the new pipeline and the catch-up for the `v1.3.0..develop`
> backlog. On release, retitle this section to `## [1.4.0] - YYYY-MM-DD`.

### For users

#### Added
- Far/distant shadings: the scene can now account for shading cast by distant objects (terrain, remote obstacles) beyond the immediate PV array. (#105)
- Lenticular diffuser modeling via BSDF, letting simulations represent light-diffusing sheets on panels. (#168)
- Multiple sky models, with Perez now the default anisotropic diffuse sky model. (#117)
- Daily sky-type classification (clear/intermediate/overcast per day). (#158)
- STICS crop model support through co-simulation with pySTICS. (#135)
- MoSt-GG (2025) modifications to the Gras-Sim grassland model. (#142)
- Mounting structures included in the 3D PV configuration. (#156)
- Support poles included in the 3D PV configuration. (#178)
- Additional mounting-structure geometries (structures alpha release). (#223, #216)
- Time-varying (time-series) albedo input, with fallback to a default value when the albedo file is invalid. (#207)
- `OutputsManager`: centralized management of simulation outputs, caching, and result variants. (#203, #82)
- `OutputsManager` can compute and report the parameter diff between simulation variants. (#209)
- `OutputsManager` variant creation extended to cover crop-model parameters. (#211)
- Zone of interest now rotates with the array azimuth so it always stays parallel to the transect. (#48)
- Stronger YAML input validation: allowed values/possibilities are now checked for input parameters. (#122)
- Benchmarking scripts for the GRASSIM grassland model. (#149)

#### Changed
- Weather-data sampling period is now adapted automatically to the simulation configuration. (#193)
- GRASSIM input files restructured/reformatted (input files must follow the new layout). (#199)

#### Fixed
- Importing `sky_model` no longer forces the TkAgg matplotlib backend at import time, so PASE runs on headless systems (servers, CI) without crashing. (#264)
- Guard against a GPS-coordinate mismatch between the scenario input file and the weather-data file, addressing spurious negative GTI values. (#167)
- Improved estimation of the GHI reaching the ground. (#208)
- Corrected daily irradiance that was reported too low. (#242)
- The scene horizon now correctly reduces diffuse irradiance in the normal simulation flow (previously the horizon had no effect on diffuse light, and a horizon-related indexing error could occur). (#257)
- Reinhart sky discretization issue with MF=5. (#212)
- Corrected the distance check in `Light.get_sky_type`. (#238)
- Fixed a missing bracket in the light module. (#237)
- Diffuse computations no longer error when the scene contains 0 panels. (#188)
- Simulations with 0 panels no longer crash under the new MultiBlock geometry. (#196)
- WeatherDataOption "Option 2" runs again (and the Chanco scenario file was updated). (#190)
- Certain simulation-year configurations no longer cause a crash. (#83)
- Generalized the shading-factor computation (previously not general). (#1)
- Corrected the interest-zone orientation direction. (#241)
- Fixed incorrect simulation metadata. (#222)
- Hardened the `NumberOfPVBlocks` handling in the PV configuration. (#183)
- Fixed the unfinished PVTable structure when built with a single panel. (#221)
- GRASSIM: corrected the temperature threshold used in the ST computation. (#191)
- GRASSIM: state variables are now updated daily as intended. (#198)
- Added the missing `Hinge` parameter to `None.yaml` so `example_nopanels.py` runs. (#202)

### For developers

#### Build & packaging
- Declared package metadata and dependencies; the version is now single-sourced and derived from the git tag (setuptools-scm). (#267)
- Published under the distribution name `pase-agrivoltaics` on PyPI (the import package stays `pase`; the name `pase` was taken by an unrelated project). (#268)
- `pip install` over `git+https` now works: the pySTICS submodule uses a relative URL instead of an SSH URL. (#263)
- Static model data is now shipped inside the `pase` package, and outputs/cache are written to the working directory instead of next to the installed package (site-packages). (#265)
- **BREAKING (environment):** migrated to Python 3.12; `embreex` replaces `pyembree`; pandas lowercase frequency aliases (e.g. `"h"` not `"H"`); pinned/upgraded trimesh, pyvista and vtk. (#256)
- Fixed the PyVista `n_faces` deprecation. (#179)

#### CI
- Added a `build`/`publish` release pipeline: on a `vX.Y.Z` tag, CI builds the sdist + wheel, uploads to TestPyPI (manual) and publishes to PyPI. (#268)
- Repaired the CI pipeline after infrastructure maintenance. (#189)
- Made the PVGIS request in the CI/CD pipeline more robust against frequent failures; added a `network` pytest marker to deselect live-PVGIS tests on the release path. (#243, #268)

#### Internal (refactors, tests, architecture)
- Simplified and vectorized the `Mesh` internals. (#236)
- Refactored `PVConfiguration` and fixed associated bugs. (#234)
- Reworked/improved the scene mesh implementation. (#118)
- Replaced the legacy `MultiBlock_PASE` with a typed `PVConfiguration3D` and helper functions. (#184)
- Made `get_sun_vector` a module-level function in `light.py`. (#230)
- Skipped a superfluous limit check in `YAML_Inputs_provider`. (#262)
- Fixed a git case conflict for `DATA_MANAGEMENT/OUTPUT/`. (#213)
- Repaired broken example scripts and added `run_all_example_scripts.py` to run all `example*.py` scripts before pushing. (#220)
- Added project-wide agent context and permissions (`CLAUDE.md`/`AGENTS.md`, `.claude/`). (#240)
- Completed the GRASSIM documentation. (#197)
- Added unit tests: aerodynamics module (#169), GRASSIM `subtract_with_min_values` (#170), GRASSIM `compute_fT` (#171), GRASSIM `compute_N_immobilization` (#172), `ReinhartSky` class (#174), `Light` class (#175).

### Needs human triage
- #234 ("Fix bugs and refactor PVConfiguration") is filed under developer refactors, but its bundled bug fixes may have user-visible effects on PV geometry — confirm whether any results-affecting fix should be surfaced under **For users → Fixed**.
- #223 (structures alpha) references #216 — verify #216 is fully covered by the structures work and does not warrant its own entry.

## [1.3.0] - 2025-09-17 and earlier

Releases up to and including `v1.3.0` predate this changelog. See the annotated
git tags (`git tag -n`) and the GitLab release/tag history for their notes.
