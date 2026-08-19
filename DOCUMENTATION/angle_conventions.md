# Angle conventions in PASE

Normative. This page defines how angles are named and interpreted in PASE. It applies to
new code and to code you touch; it is not a mandate to rename the whole repository.

Why it exists: PASE mixes two azimuth frames, and for ten months it mixed them silently.
Sky patches were placed at the heading `90 − azimuth` because a compass azimuth was handed
to a function that reads its argument as a mathematical angle, which corrupted anisotropic
diffuse light, horizon masking and the diffuser map (issue 300). Nothing named either
frame, so nothing could notice.

## The world frame

One frame, right-handed, fixed:

| axis | direction |
| --- | --- |
| **X** | East |
| **Y** | North |
| **Z** | Zenith (up) |

Every direction below is expressed in it.

## The two azimuth frames

| | **compass azimuth** | **trigonometric azimuth** |
| --- | --- | --- |
| zero at | North | East |
| positive towards | East (clockwise, seen from above) | North (counterclockwise) |
| unit vector | `(sin A, cos A)` | `(cos A, sin A)` |
| identifier | `az_compass_deg`, `az_compass_rad` | `az_trig_deg`, `az_trig_rad` |
| used by | `get_sun_vector`, the horizon mask, the CIE sky radiance model, `CentralAzimut`, terrain aspect, PVGIS, pvlib | `sph_to_cart` / `cart_to_sph`, pyvista's `rotate_z`, the diffuser's internal frame |

Conversion, in degrees:

```
az_trig = 90 − az_compass
az_compass = 90 − az_trig
```

One formula both ways: the conversion is a **reflection**, so it is its own inverse. Three
consequences worth knowing:

- **45° (NE) and 225° (SW) are fixed points.** A direction on that diagonal is unchanged by
  a frame mix-up, so a test with the sun there cannot detect one. Keep test suns away from
  it — `tests/test_angle_conventions.py` asserts the fixed points explicitly so nobody
  rediscovers this the hard way.
- **N ↔ E and S ↔ W trade places**, and SE ↔ NW end up half a turn apart. Misreading a frame
  is not a small error except near the diagonal.
- **It flips handedness.** Walking clockwise through compass azimuths walks
  counterclockwise through trigonometric ones. A mirrored sky dome cannot be repaired by
  rotating it.

## Rotating *by* an azimuth is a different operation

Do not confuse the two conversions:

| purpose | operation |
| --- | --- |
| relabel a **direction** from one frame to the other | `90 − A` (a reflection) |
| rotate a **scene** by a compass azimuth | `rotate_z(−A)` (a sign flip) |

pyvista's `rotate_z` turns counterclockwise, so placing a block at compass azimuth `A` is
`rotate_z(-A)`. That negation is idiomatic and allowed; write it with a comment naming the
reason at first use in a function, as in `PVConfiguration3D._build_panels_for_central`.
Replacing it with `90 - A` would be wrong.

To tilt about a rotated axis, conjugate — rotate back to the unrotated frame, tilt, rotate
out again — as `configuration.py` does for tracking panels:

```python
panel.rotate_z(azimuth_deg, ...).rotate_y(tilt_deg, ...).rotate_z(-azimuth_deg, ...)
```

Applying the tilt about the global Y axis *after* the azimuth spin instead tilts every
object due East whatever its azimuth. That is a real defect the diffuser carried.

## Vertical angles

- **elevation** — above the horizon, 0° at the horizon, 90° at the zenith. Preferred.
- **zenith angle** — from the vertical, 0° at the zenith. Allowed, but the identifier must
  say `zenith`: never `z` (a coordinate) and never `el`.

## Naming

Anything frame-bearing that crosses a function, class, dataframe or file boundary:

```
<quantity>_<frame>_<unit>      az_compass_deg, az_trig_rad
```

Anything else that carries an angle:

```
<quantity>_<unit>              el_deg, zenith_deg, tilt_deg
```

**Banned**

- the French spelling `azimut`
- a bare `az` or `azimuth` in a public signature or a dataframe column: it states no frame
- inline frame arithmetic (`90 - az`, `-az + 270`) outside the helpers below

**Not banned.** `theta` and `phi` in the diffuser BSDF and in local mesh frames are local
spherical angles, not compass-bearing, and stay as they are. This page is a ratchet, not a
repo-wide rename.

## The only sanctioned way to cross frames

`pase/conversion_functions.py`:

| function | purpose |
| --- | --- |
| `compass_to_unit_vector(az_compass_deg, el_deg=…)` | compass direction → `(x, y, z)`. Prefer it to calling a primitive |
| `unit_vector_to_compass_deg(x, y)` | `(x, y)` → compass heading, wrapped into `[0, 360)` |
| `compass_to_trig(a)` / `trig_to_compass(a)` | the `90 − a` involution, written once |
| `sph_to_cart(units, azimuth, …, frame=…)` | the primitive. `frame` is keyword-only and **mandatory** |
| `cart_to_sph(x, y, z, frame=…)` | the inverse. `frame` mandatory; the azimuth is returned unwrapped, in radians |

`frame` takes `COMPASS` or `TRIGONOMETRIC` from the same module. It has no default on
purpose: the same number means two different directions, so an undeclared frame is a
`TypeError` rather than a coin flip.

## Documenting an angle

Every angle parameter states its frame and unit in its docstring. Two examples already in
the codebase worth copying:

- `SlopedGround.__init__` (`pase/ENVIRONMENT/ground.py`) — states the convention and derives
  the normal from it in a comment.
- `get_horizon_mask` (`pase/ENVIRONMENT/shading.py`) — states the convention and what it is
  consistent with.

## Testing an angle

A round-trip test is **not** enough. `sph_to_cart` and `cart_to_sph` were mutually
consistent throughout issue 300, because that property holds equally in either frame.
Assert **absolute** directions instead:

```python
compass_to_unit_vector(0.0, el_deg=0.0)   # -> (0, 1, 0), due North
compass_to_unit_vector(90.0, el_deg=0.0)  # -> (1, 0, 0), due East
```

`tests/test_angle_conventions.py` is the reference set: cardinals, the frames disagreeing as
documented, the mandatory `frame=`, the involution, the fixed points, and agreement between
`compass_to_unit_vector` and `get_sun_vector` — two independent implementations of the
compass frame that must not drift apart.

## Legacy names

Still in circulation. Resolve them here rather than guessing:

| name | where | frame / unit |
| --- | --- | --- |
| `az`, `el` | sky patch tables (`ReinhartSky.reinhart_patches`) | compass / degrees, elevation / degrees |
| `azimut` | `sph_to_cart` before this page | trigonometric |
| `gamma`, `beta` | `get_sun_vector` | compass / degrees, elevation / degrees |
| `Z`, `Z_s` | `CIEStandardSky` | zenith angle / degrees |
| `CentralAzimut` | YAML input | compass / degrees |
| `TerrainSlopeAspect` | YAML input | compass / degrees, downhill direction |
| `azimuth_diff` | `LenticularDiffuser.__init__` | **trap**: the argument is a compass azimuth in degrees, the attribute stores a trigonometric angle in radians |
| `zone_azimut` | `Mesh.set_interest_zone_orientation` | a counterclockwise *rotation angle*, i.e. a negated compass azimuth — not an azimuth |

## YAML inputs

Input keys keep their current names; each angle-bearing key states its frame and sign
convention in its `Definition` field. If you add one, do the same.
