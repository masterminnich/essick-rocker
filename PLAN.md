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
   repeat. ~15% of photos are held out for validation only; Joe's M7/M8 (below) are independent checks if he supplies them.
7. Deliverables: CAD model, dimensioned drawing, accuracy report, then 1:1 tiled PDF/DXF templates with a print-scale check square.

## Hand measurements (Joe, 2026-11-20: optional, small list; never block on them)
The original 35-item caliper sheet (R/F/B/A/C/S/T codes, K1-K6, seat depth grid, far photos) is retired: photogrammetry now
covers it. Only these remain, because no photo sees them or two sources disagree. Fold them in whenever Joe sends them.
Required:
- M1 seat edge thickness, front centre. M2 seat edge thickness, middle of one side. (Since PR #8 the side edge is triangulated:
  42.0 mm square to the seat plane, +-3 mm, parts/seat_edge.json. M2 is now a CHECK on that number; M1, the front edge, is still
  not measured. The underside between the edges is an assumed plane; IMG_1570, 1572, 1573, 1576 see it but are not used yet.)
- M3 crest rail height at the centre. (Photos 74.7 mm vs tape IMG_1555 77.5: 2.8 mm conflict.)
- M4 centre slat thickness. (~10 mm from photo consistency, weak; it is the lamination stock / bending-form thickness.)
- M5 centre slat width just under the crest. (Trace 100.0-100.5 vs tape IMG_1553 98.3: 1.7-2.2 mm conflict.)
Optional:
- M6 arm thickness at the front end (assumed 25 mm; try the side photos first).
- M7 table to top of crest at the centre; M8 rocker tip to tip, straight line. The only independent check on the single
  framing-square scale; they make the accuracy report more than self-graded.
- Leg stock thickness across (now +-3 mm), only if Joe wants rough stock sizes; side templates do not depend on it.
Dropped as covered by photos: R1-R5, F1-F3, B1-B4, A1-A3 widths, C2-C4, S2/S3 (except M5), K2, K4-K6, the seat depth grid
(replaced by the tape-dot survey, leave-one-out 1.18 mm), the far photos (in: IMG_1588-1592). Every dimension that stays
photo-derived keeps its provenance tag and +- figure, so the accuracy report shows what was never hand-checked.

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
