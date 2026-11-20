# Working ledger (coordinator's resume notes)

Sessions on this machine get cut off without warning; this file says where things stand. Read PLAN.md first.

## Done
- [x] Photos synced (95 in Drive as of 12:00; IMG_1592 is new and not yet looked at). Catalogue in `catalogue/`.
- [x] Final camera model `work/solve/model` (93 photos, 1.25 px mean). Never re-solve at full res (PLAN.md, compute safety).
- [x] Scale from the square's printed 1/8" tick comb, triangulated (tools/square_scale.py): tongue 349.09, body 348.79 mm
      per model unit (differ 0.085 %), legs at 89.89 deg, coplanar to 0.44 mm. Used 348.84. `solve/metric_frame.json`
      (axes provisional: X from the two back-leg pegs, Z = table plane fitted near the chair, rms 0.76 mm).
- [x] Toolkit (rocker/, tools/): projection, triangulation, overlay, orthophoto (rocker/ortho.py), cloud views.
- [x] Dense-ish chair cloud tooling: tools/densify.py (features done for 70 photos in work/dense/feat).

## Now
- [→] `densify.py gmatch` (guided matching): resumable, skips pairs already in work/dense/pairs (180 of 309 done at
      12:12). Then `densify.py tracks --out work/dense/chair_dense.npy`.

## Next
- [ ] Symmetry plane from the cloud -> final axes in metric_frame.json.
- [ ] Per part: face planes from the cloud, orthophotos on those planes, outline tracing, thickness.
- [ ] Parametric model -> mesh (GLB/STEP), overlays on photos, residual report.
- [ ] Fold in Joe's caliper sheet (R/F/B/A/C/S/T codes), check dims K1-K6, seat depth grid, far photos, tape targets.
- [ ] Templates (1:1 PDF/DXF).

## Not done / open
- Black ruler not used as an independent scale check (its units are inferred).
- Repo still local; Joe to create private `masterminnich/essick-rocker`.
