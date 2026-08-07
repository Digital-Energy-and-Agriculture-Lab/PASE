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
### For users

#### Added
- Sloped and real-terrain support: a scene can now sit on inclined ground or on real
  SRTM topography instead of a horizontal plane. Driven by new **optional** terrain
  parameters, readable from either the scenario or the central AV file —
  `TerrainSource` (`flat` | `sloped` | `srtm`, default `flat`), `TerrainSlopeAngle`,
  `TerrainSlopeAspect`, and `TerrainExtentRadius`. Existing input files are
  unaffected and keep running on flat ground. (#248)
  - PV blocks, mounting structures and support poles follow the terrain: each block
    is anchored at the maximum elevation of its footprint, and the table diagonal is
    kept clear of sloped ground.
  - The ground sampling mesh is tilted to the terrain normal.
  - Two new examples demonstrate the modes: `example_sloped_terrain.py` and
    `example_dem_terrain.py`.
  - Real DEMs (SRTM1) are handled defensively: nodata voids are filled from the nearest
    valid elevation, an entirely-nodata tile is rejected with an actionable message
    rather than producing a broken mesh, the terrain is centered on the scenario
    location, and vertically exaggerated terrain (`z_exaggeration != 1.0`) is
    refused for simulation because the exaggeration would distort the physics.
  - The structure footprint is padded by the purlin half-length along Y, keeping
    support poles inside it.
  - The `srtm` mode needs the optional geospatial stack (`rasterio`, `pyproj`),
    included in the conda environment files, and downloads ~25 MB of SRTM tiles on
    first use (cached in `~/.cache/pase/dem/`). PASE fetches those tiles itself, so
    the mode runs wherever PASE does. (#286)

#### Changed
- Diffuse irradiation is computed substantially faster on large grids (vectorized
  `compute_daily_diff_irradiation`). Results are unchanged — an equivalence test
  pins this. (#258)

#### Fixed
- The crop-model orchestrator (`run_crop_simu`) can again be imported from a
  `pip`-installed PASE, so the SIMPLE and Gras-Sim crop models are usable without a
  source checkout: the STICS backends, which are not distributed with PASE, are no
  longer required just to import the module. Selecting a crop model whose backend is
  missing now fails with a message naming the backend and its setup instructions, and
  an unrecognized `CropModel` value is rejected instead of silently producing no
  agronomic results. (#271)

### For developers

#### Build & packaging
- The environment files (unix, windows, CI) gained the geospatial dependencies
  `rasterio` and `pyproj` for the DEM terrain path. (#248)
- Resolved the PyVista `extract_surface()` deprecation warning.
- Updated authors and maintainers in `pyproject.toml`.

#### Internal (refactors, tests, architecture)
- New `pase/ENVIRONMENT/ground.py` — a `Ground` / `SlopedGround` / `DEMGround`
  hierarchy plus `ground_from_config()` — and `pase/ENVIRONMENT/terrain_pipeline.py`,
  which turns a GPS bounding box into a PyVista terrain surface via a cached SRTM
  download. (#248)
- Tests: ground-aware panel placement, the layout-within-ground coverage check,
  ground mesh source points following the terrain, an end-to-end build against a
  bounded `DEMGround`, and the flat-ground regression extended to HSATS and the
  fence structure. (#248)
- Removed dead `PanelOffset` references and an unreachable `raise` in
  `build_structure`. (#248)
- Translated the remaining French text in `mesh.py` and the terrain modules to
  English; `terrain_pipeline` now logs instead of printing. (#248)
- New `pase/ENVIRONMENT/srtm.py`: SRTM tiles are fetched, decoded and mosaicked in
  Python (standard library + numpy, rasterio only for the GeoTIFF write). Samples are placed on the global 1/3600° lattice, so
  mosaicking is exact array copying. Only `SRTM1` is supported (#286).
- The crop backends are imported through a `_CROP_BACKENDS` registry when their
  `CropModel` is selected, instead of at `run_crop_simulations` import time. Tests
  reproduce the installed-package situation in-process by making `pase.CROPS.STICS`
  unimportable, so they need no built wheel. (#271)
- `AGENTS.md`: pinned down the allowed commit categories, required the issue ID in
  commit messages, and allowed lazy imports for optional backends.
- Stopped tracking `logging_file.log` and `dev_script_outputs_manager.py`, and
  gitignored `.claude/` — agent working documents (plans, notes, commit drafts) stay
  local and are never committed. (#276)

## [2.0.0] - 2026-07-22
### For users

#### Added
- Far/distant shadings: the scene can now account for shading cast by distant objects (terrain, remote obstacles) beyond the immediate PV array. (#105)
- Lenticular diffuser modeling via BSDF, letting simulations represent light-diffusing sheets between PV panels. (#168)
- Multiple sky models, with Perez now the default anisotropic diffuse sky model. Sky type derived from weather data per timestep. (#117)
- Daily sky-type classification (clear/intermediate/overcast per day). (#158)
- STICS crop model support through co-simulation with pySTICS. (#135)
- MoSt-GG (2025) modifications to the Gras-Sim grassland model. (#142)
- Structures:
  - Mounting structures included in the 3D PV configuration. (#156)
  - Support poles included in the 3D PV configuration. (#178)
  - Additional mounting-structure geometries (structures alpha release). (#223, #216)
  - The structures are thoroughly documented in the PASE wiki.
- Time-varying (time-series) albedo input, with fallback to a default value when the albedo file is invalid. (#207)
- `OutputsManager`:
  - centralized management of simulation outputs, caching, and result variants. (#203, #82)
  - can compute and report the parameter diff between simulation variants. (#209)
  - variant creation extended to cover crop-model parameters. (#211)
  - The `OutputsManager` is included in the examples but is subject to a retro-compatible refactor (robustness improvements) in the near future.
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
- Corrected daily diffuse irradiance that was reported too low. (#242)
- The scene horizon now correctly reduces diffuse irradiance in the normal simulation flow (previously the horizon had no effect on diffuse light, and a horizon-related indexing error could occur). (#257)
- Fixed a Reinhart sky-discretization rounding error (detected at MF=5 but occurring more widely). (#212)
- Corrected the distance check in `Light.get_sky_type` for more accurate and robust sky type determination. (#238)
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
- GRASSIM: 
  - corrected the temperature threshold used in the ST computation. (#191)
  - state variables are now updated daily as intended. (#198)
- Added the missing `Hinge` parameter to `None.yaml` so `example_nopanels.py` runs (#202); the parameter was later removed, making this moot.

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
- Repaired the CI pipeline after infrastructure maintenance: increase number of file descriptors on the runner's Docker instance (#189)
- Made the PVGIS request in the CI/CD pipeline more robust against frequent failures; added a `network` pytest marker to deselect live-PVGIS tests on the release path. (#243, #268)

#### Internal (refactors, tests, architecture)
- Simplified and vectorized the `Mesh` internals. (#236)
- Refactored `PVConfiguration` and fixed associated bugs. (#234)
- Reworked/improved the scene mesh implementation. (#118)
- Replaced the legacy `MultiBlock_PASE` with a typed `PVConfiguration3D` and helper functions. (#184)
- Made `get_sun_vector` a module-level function in `light.py`. (#230)
- Skipped a superfluous limit check in `YAML_Inputs_provider`. (#262)
- Fixed a git case conflict for `DATA_MANAGEMENT/OUTPUT/`. (#213)
- Repaired broken example scripts and added `run_all_example_scripts.py` to run all `example*.py` scripts before pushing/merging changes. (#220)
- Added project-wide agent context and permissions (`CLAUDE.md`/`AGENTS.md`, `.claude/`). (#240)
- Completed the GRASSIM documentation. (#197)
- Added unit tests: aerodynamics module (#169), GRASSIM `subtract_with_min_values` (#170), GRASSIM `compute_fT` (#171), GRASSIM `compute_N_immobilization` (#172), `ReinhartSky` class (#174), `Light` class (#175).


## Earlier releases

Releases up to and including `v1.3.0` predate this changelog. See the annotated
git tags (`git tag -n`) and the GitLab release/tag history for their notes.
