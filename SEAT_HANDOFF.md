# Seat curvature: handoff for a separate session

You are picking up ONE part of a larger job: the scooped SEAT of a hand-made walnut rocking chair (ESSICK rocker).
The whole job: rebuild the chair as a dimensionally accurate 3D model from iPhone photos + hand measurements, then make
1:1 templates. Target tolerance 1/32" (0.8 mm) on hard points, 1/16" (1.6 mm) on free curves. The person is Joe.
Another session (the coordinator) is doing every other part; do not redo its work. Read PLAN.md, then LEDGER.md (newest
notes at the bottom) before starting.

## Your goal
The seat's top surface (the scoop) as a measured 3D surface in the chair frame, with honest error numbers, plus the seat's
plan outline if the dots allow it. Joe put BLUE TRACKING DOTS on the seat and photographed it for this purpose.
Deliver: `seat/` folder with dot coordinates (CSV, mm, chair frame, per-dot uncertainty), a fitted surface (grid + formula),
depth-below-rim map, cross-sections at 3 stations, and a short report with numbers. Design intent = left/right symmetric,
but report the as-measured asymmetry too.

## Where things are (this folder is a git worktree on branch `seat`; commit here, never in ../rocking-chair)
- `drive` -> photos (shared with the coordinator; synced from Google Drive, never edit). `manifest.json` lists them.
  New photos: `uv run --no-project --with gdown python tools/sync_drive.py "https://drive.google.com/drive/folders/1YgIhu9ZJOTl4V7alZy-BeoGzThgM7vd2" drive manifest.json`
  (prints NEW files). As of 2026-11-20 14:25 the folder had 100 photos and NONE show blue dots yet: IMG_1588-1592 are far
  views with the framing square stood upright (digitally zoomed: different focal length; chair possibly moved), IMG_1593 is
  a tape across the seat front. Ask Joe where the dot photos are if a sync finds none.
- `work/solve/model` (symlink): the solved cameras for the first 93 photos (COLMAP format, full-res pixel grid, one shared
  OPENCV camera). `solve/metric_frame.json`: X_chair = s * R @ X_colmap + t, mm; +X chair's right (as you sit), +Y forward,
  +Z up, table top = Z 0, mirror plane X = 0. Scale from the framing square's printed ticks (two legs agree to 0.085 %).
- `work/dense/chair_dense.npy` (symlink): 16.7k triangulated points on the chair (X Y Z R G B n_views rms_px ...). About 3,500
  lie on the seat top; a polynomial surface through them fits to 1.8 mm rms (tools/build_model.py, seat section). That is the
  baseline you should beat and cross-check against.
- Toolkit (all documented in each file's USAGE): `rocker/cameras.py` (project / ray, EXIF orientation handled),
  `rocker/triangulate.py`, `rocker/refine.py` (the `blob` refiner locates a contrasting dot to sub-pixel: made for this),
  `tools/crop.py`, `tools/mark.py`, `tools/propose.py` (epipolar-guided propagation of a mark to other photos),
  `tools/tri.py`, `tools/review.py`, `tools/overlay.py`, `tools/overlay_sil.py`, `tools/cloud_slice.py`.
  Run Python through `tools/py.sh [-m GB] [-t MIN] script.py ...` (capped runner + full environment).

## What does NOT exist yet and you will need
1. **Registering new photos into the existing camera model.** No tool yet. Suggested light approach: SIFT on the new photo
   (tiled, as in tools/densify.py), match against the descriptors of existing photos stored in `work/dense/feat/*.npz` or the
   COLMAP database `work/solve/db_full.db`, lift matches to 3D through the model's points, then PnP + refinement with the
   known intrinsics (let focal length float if the photo is digitally zoomed: check EXIF 35 mm-equivalent; 26 = no zoom).
   CAUTION: if the chair was moved between shoots, the shop background and the chair give two different poses. Register
   against CHAIR points only (work/dense/chair_dense.npy is chair-only) and check the reprojection error; say so if it fails.
   If the dot photos form their own good set, solving them alone at HALF resolution and aligning to the chair frame through
   chair features is the alternative.
2. **Detecting the blue dots** automatically by colour, then matching them across photos with epipolar geometry.

## Hard rules
- COMPUTE SAFETY (PLAN.md): this machine is a shared hub and was crashed by heavy jobs. No full-resolution COLMAP feature
  extraction / matching / bundle adjustment. One compute job at a time, always through `tools/py.sh` or `tools/safe_run.sh`
  (low priority, 2 threads, killed above the memory/time cap). State expected memory and runtime before any new heavy script.
  Never run jobs in the background or from parallel agents. The coordinator session also runs jobs: safe_run refuses to start
  while another safe_run job is running, so just retry a little later.
- Sessions get cut off without warning. Keep a `seat/LEDGER.md` with what is done / now / next, and commit often.
- Report numbers honestly (residuals, left/right asymmetry, what is assumed). A wrong-but-pretty surface is worse than a rough one.
- Tracing lesson from the coordinator: wide automatic searches latch onto the wrong thing; seed by eye on a zoomed gridded
  view, then let the tool refine within a few millimetres, and always look at the result drawn over the image.
- Files for Joe: there is no upload helper on this machine; the work reaches him through git (branch `seat`).
