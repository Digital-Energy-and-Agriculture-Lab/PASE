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
- `CIEStandardSky.plot_radiance_map()` draws the radiance (or luminance) distribution
  of a CIE standard sky as a continuous polar or cartesian map. It is evaluated on its
  own azimuth-elevation grid rather than on the Reinhart patches, so the sky model can
  be inspected independently of how finely the dome is discretized, either relative to
  the zenith or scaled by an absolute zenith radiance, and the figure is labelled with
  the CIE description of the sky type. (#300)

#### Changed
- Diffuse irradiation is computed substantially faster on large grids (vectorized
  `compute_daily_diff_irradiation`). Results are unchanged — an equivalence test
  pins this. (#258)
- Angle inputs now say what they mean. Every angle-bearing key in the input files states
  its convention in its `Definition` field, so you no longer have to infer it from the
  code. In particular `CentralAzimut` is the compass azimuth of the **row axis**, not the
  direction the panels face: they face `CentralAzimut + 90` when `TiltY` is positive and
  `CentralAzimut - 90` when it is negative, which makes a south-facing array
  `CentralAzimut 90` with a positive tilt. The definitions point at the wiki page that
  illustrates the combination with figures. No key was renamed and no value changed, so
  existing input files keep working and results are unaffected. (#301)
- The `Hinge` parameter is gone from the `INPUTS/AV_CENTRAL/` files. It stopped being a
  user-facing choice when panel placement was reworked — it is now derived from
  `StructureType` — and the leftover entries could still override that derivation. Most
  of them already agreed with the derived value, but `Example1_AV.yaml` carried
  `Hinge: Top` against a derived `center`, so that example's array now sits centred on
  the axis height it declares, moving down by 1.37 m (z-range [1.55, 2.46] becomes
  [0.77, 1.68]). If you had copied that example as a starting point, expect the same
  shift. (#301)

#### Fixed
- The crop-model orchestrator (`run_crop_simu`) can again be imported from a
  `pip`-installed PASE, so the SIMPLE and Gras-Sim crop models are usable without a
  source checkout: the STICS backends, which are not distributed with PASE, are no
  longer required just to import the module. Selecting a crop model whose backend is
  missing now fails with a message naming the backend and its setup instructions, and
  an unrecognized `CropModel` value is rejected instead of silently producing no
  agronomic results. (#271)
- Diffuse light now reaches the scene from the right part of the sky. The discretized
  sky held every patch direction twice — as a compass azimuth, read by the sky radiance
  model and by the horizon mask, and as a 3D vector, used as the ray direction — and
  the two disagreed: each patch was placed at the heading `90 − azimuth`, a mirror
  image about the north-east diagonal. North and east were interchanged, as were south
  and west, and south-east and north-west ended up half a turn apart; the north-east
  and south-west directions happened to fall on the mirror and were unaffected. (#300)
  - Under a non-uniform sky (`sky_type_source='From weather data'`), the bright
    circumsolar region was applied more than 130° away from the sun for a south-east
    sun, while the patch actually facing the sun received a tenth of the radiance it
    should have.
  - With a far-horizon profile loaded — on any sky, the uniform default included — 22%
    of the sky dome received the visibility belonging to another direction: patches
    hidden although nothing occludes them, patches lit although the relief blocks them.
  - Runs using lenticular diffusers were affected too, on any sky and with no horizon
    profile needed.
  - Runs on the uniform default sky with no horizon profile keep essentially the same
    totals, moving by well under a percent, because the diffuse weighting depends only
    on elevation. That insensitivity is why the defect went unnoticed for ten months.
  - Results computed before this fix no longer match for the affected cases: cached
    runs under `OUTPUTS/` should be recomputed.
- Sky dome figures are no longer point-reflected. `ReinhartSky.patch_plot_value` drew
  each patch half a turn away from the direction its own compass labels announce, so a
  patch due east appeared where the plot reads west. Every sky figure produced with it
  was mirrored; the underlying radiance values were correct. (#300)

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
- Witnesses for the sky patch azimuth pairing. `TestSkyPatchAzimuthPairing`
  (`tests/ENVIRONMENT/test_sky_model.py`) crosses the `az` column with the cartesian
  columns of the same patches, and asserts that the brightest patch of an anisotropic
  sky lies towards the solar vector and that the patch nearest the sun carries
  near-peak radiance. `tests/ENVIRONMENT/test_shading.py` gained an azimuth-dependent
  horizon profile helper and a witness that the relief hides the patches whose rays it
  occludes. Nothing in the suite crossed those two representations before, and every
  horizon test used a flat profile, which masks the same elevations in all directions
  and so cannot see an azimuth defect. The sun azimuths are deliberately kept away from
  the north-east and south-west diagonals, the fixed points of the reflection, where
  the defect is invisible. (#300)
- `CIEStandardSky.compute_rel_radiance()` now honours its `az`/`el` arguments under a
  uniform sky (type 5), where it returned an array shaped like the instance's own
  patches regardless of what was asked. (#300)
- Angles have a normative vocabulary: `DOCUMENTATION/angle_conventions.md`, with the short
  version in `AGENTS.md`. Two azimuth frames are named rather than implied — **compass**
  (0 = North, clockwise, `(sin A, cos A)`) and **trigonometric** (0 = East,
  counterclockwise, `(cos A, sin A)`) — along with the `90 - A` involution between them,
  its fixed points at NE and SW, the naming grammar `<quantity>_<frame>_<unit>`, and a
  table resolving the legacy names still in circulation. It also separates two conversions
  that were nowhere distinguished: relabelling a direction between frames (`90 - A`) and
  rotating a scene by a compass azimuth (`rotate_z(-A)`). (#301)
- `sph_to_cart` and `cart_to_sph` require a keyword-only `frame=` (`COMPASS` or
  `TRIGONOMETRIC`) with no default, so an undeclared frame raises `TypeError` instead of
  silently picking one — the mechanism that would have caught #300 at its call site. Frame
  crossings go through `compass_to_unit_vector`, `unit_vector_to_compass_deg` and
  `compass_to_trig` rather than inline arithmetic. `sph_to_cart`'s misspelled `azimut`
  parameter is now `azimuth`, and `Mesh.default_azimut` is `default_zone_az_trig_deg`.
  Behaviour is unchanged throughout. (#301)
- `tests/test_angle_conventions.py` witnesses the frames with **absolute** assertions
  (north → `(0,1,0)`) instead of round-trips. A round-trip between `sph_to_cart` and
  `cart_to_sph` is frame-blind — it holds in either convention — which is why the suite
  stayed green throughout #300. It also pins `compass_to_unit_vector` against
  `get_sun_vector`, the two independent implementations of the compass frame whose drift
  was that defect. (#301)
- `TEMPORARY_FILES/sky_subdivision.py` no longer calls a zenith angle an elevation, and
  drops a local `cart_to_sph` that shadowed the package one with a wrong formula. (#301)
  
## [2.0.1] - 2026-08-12
### For users

#### Fixed
- PV panels rest flush on their mounting structure again on PV Table and HSATS centrals. They were being placed at the rafter axis instead of on top of the purlins, so every panel sat inside the structure rather than on it, displacing the whole array by the rafter + purlin offset and distorting the scene geometry the shading computation runs on. (#299)
- Parameter value `TiltY` in `Example5_PVTable.yaml` raised an error, the default value is now within bounds to generate a valid PV configuration.
- Tolerance factor added in structure.py for the HSATS structure type (`self.OPTIONAL['HsatsOverhangTolFactor']`) to allow HSATS geometries with `RafterLength = 0`.

#### Changed
- `Example5_PVTable.yaml` now uses a 35° tilt (was 80°), a realistic value for a fixed table. (#299)

### For developers

#### Internal (refactors, tests, architecture)
- Added panel-on-structure placement tests (`tests/PHOTOVOLTAICS/test_panel_structure_placement.py`), covering an interface that had no coverage: no test built panels and a structure together, so the #299 misplacement went undetected. The flush contract is asserted on the built geometry, measured along the panel normal — an axis-aligned bounding-box check cannot express it, since a tilted rafter's box contains the panels even when placement is correct. (#299)
- Removed the dead `PanelOffset` default from `PVConfiguration3D._apply_defaults`. Nothing read the key and no input file defines it, so it silently supplied `0.0` to the call site that #299 clobbered instead of raising. (#299)
- Moved the `structure_inputs` fixture to `tests/PHOTOVOLTAICS/conftest.py` to share it across structure and placement tests. (#299)

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
