# Plan and conventions

## Decisions (Joe, 2026-11-20)
- **Design intent, not as-built**: the model is symmetric about the chair's centre plane; left/right are averaged, curves are faired.
- **Tolerance**: 1/32" (0.8 mm) on joints and hard points, 1/16" (1.6 mm) on free curves.
- Rockers (and probably slats) are **bent laminations** clamped to a form, so they need bending-form templates.
- Shop templates hanging in IMG_1507 probably belong to this chair; flat photos of them would be a strong cross-check.

## Conventions
- Internal units: **millimetres**. Reports show inches (fractions to 1/32) alongside.
- Chair frame: origin on the table top (the "floor") under the centre of the seat front edge; **+X = chair's right** (as you sit
  in it), **+Y = forward**, **+Z = up**. Table top is Z = 0.
- Left/right always mean as you sit in the chair.
- Pixel coordinates are **raw sensor pixels** (4032 x 3024, EXIF orientation NOT applied), the grid COLMAP solved on.
- Every dimension carries a provenance tag: `measured` (calipers/tape by hand), `triangulated` (multi-photo point),
  `fitted` (outline fit), `assumed`; and a tolerance.

## Phases
1. Catalogue: `catalogue/photos.csv`, `catalogue/parts.md`; tape close-up readings in `measurements/`.
2. Camera solve (COLMAP, full res) -> `solve/`.
3. Metric frame: scale from the framing square, checked by the black ruler; table plane = Z 0 -> `solve/metric_frame.json`.
4. Hard-point skeleton: ~100-150 points marked in several photos each, triangulated, with error estimates.
5. Parts: each part = planar template outline in its own plane + thickness + shaping, placed in 3D. Edge types tried in
   order: line, single-radius arc, fair spline; keep the simplest within tolerance. Model is generated from a parameters file.
6. Critique loop: project the model into every photo through the solved cameras; measure edge gaps per part; fix the worst;
   repeat. ~15% of photos and Joe's check dimensions (K1-K6) are held out for validation only.
7. Deliverables: CAD model, dimensioned drawing, accuracy report, then 1:1 tiled PDF/DXF templates with a print-scale check square.

## Compute safety (Joe, 2026-11-20; this machine is a shared hub and was crashed twice)
Full-resolution COLMAP solves run in parallel used about 40 GB each and exhausted the machine's 64 GB.
- **No full-resolution COLMAP feature extraction, matching or bundle adjustment on this machine.** The camera model in
  `work/solve/model` is final; do not re-solve. New photos are added by registering them into that model at half
  resolution, one job, thread-capped.
- **One compute job at a time**, always through `tools/safe_run.sh` (low priority, 2 threads, killed above 6 GB or 20 min
  unless a higher cap is justified in writing first). Never in the background, never from parallel agents.
- **Audit before running** any script that loads the COLMAP model, many images or runs an optimiser: state expected peak
  memory, threads and runtime; process photos one at a time (a decoded photo is ~36 MB); never hold all 94 in memory.
- Agents may read, view images and write code in parallel, but only one of them (or the coordinator) runs compute.
