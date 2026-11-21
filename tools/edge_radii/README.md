# tools/edge_radii: phase 6c, radii of the eased edges

Result: `parts/edge_radii.json` (record only; the model stays sharp). Figures: `figures/edge_radii/`.

| Script | Does | Run |
|---|---|---|
| `edges.json` | inputs: every profile line, corner seed, tape scale, and the by-eye verdict | |
| `run_all.py` | reruns all single-photo measurements below, writes `work/edge_radii/results.json` | `tools/py.sh tools/edge_radii/run_all.py` (0.3 GB, 6 s) |
| `prof.py` | L* profile square to an edge, averaged along a line drawn on the photo | via run_all |
| `band.py` | tone-band widths B10/B50, blur, r bracket [B10, 2 B10] | via run_all |
| `cornerfit.py` | radius of a corner seen square-on (outline, middle 70 % of the turn) | via run_all |
| `tick.py` | tape scale (px/mm) from the 1/16 in marks, refined on 2-16 periods | `work/toolkit/rk.sh tools/edge_radii/tick.py IMG X0 Y0 X1 Y1` |
| `pairs.py`, `fit_pairs.py` | pose-free fit of r per member from opposite silhouette pairs of the critique (93 photos, 2 px/mm): not resolved, kept as a bound | `tools/py.sh -t 15 tools/edge_radii/pairs.py parts/model_v24.glb work/critique/v24 work/edge_radii/pairs_v24.npz` (0.4 GB, 10 s), then `work/toolkit/rk.sh tools/edge_radii/fit_pairs.py work/edge_radii/pairs_v24.npz work/edge_radii/fit_v24.json --boot 100` |
| `fig.py` | `bands.png`, `corners.png`, `radii.png` | `tools/py.sh tools/edge_radii/fig.py` |

Geometry. A round of radius r on a square arris, seen square to one face, shows its whole curve as a band r wide between
the face's tangent line and the silhouette (the other face's plane). The tone departs visibly from the face's only some
way into the curve, so r >= B10 and, if it departs within 30 degrees, r <= B10 / (1 - sin 30) = 2 B10. A tone-edge trace
of the face sits about B50 inside the silhouette. A silhouette seen obliquely lies k r outside the sharp model
(the critique's ease factor k, 0 to 0.41).

Pitfall met here: which side of the step is wood. Pick the side with the wood's grain texture on the crop, not the darker
or lighter side; a background's smooth lighting slope beside a step looks like a band if the windows are swapped
(`fig.py` draws the B10 line on the crop, so a swap shows as a blue line on the background).
