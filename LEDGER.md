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

- [x] Chair cloud: work/dense/chair_dense.npy (16.7k points, >=3 views, chair frame mm). Axes final: mirror plane from the
      cloud agreed with the peg-based X axis (0.08 mm, 0.23 deg); metric_frame.json updated.
- [x] METHOD THAT WORKS for part outlines ("face orthophoto"): tools/face_ortho.py rectifies ~7 photos onto a part's face
      plane and refines the plane (offset/tilt/yaw) by photo consistency; the median composite shows the face at true shape
      (0.5 mm/px) with everything off-plane smeared. tools/ortho_view.py = gridded view to read a rough centreline;
      tools/ribbon_trace.py = dynamic-programming trace of the two long edges; tools/ortho_strip.sh = check views.
- [x] Rockers: both outer side faces traced (work/parts/rockerL|R/, plane json + trace.json), fair profile in
      parts/rocker_profile.json/.png (tools/rocker_profile.py). Edge noise 0.4 mm rms; left vs right shape 1.0 mm rms after
      rigid alignment (tail tips differ up to 8 mm); face height L vs R within 0.4 mm (26.4-28.7 mm, ~21 at tail tip);
      rocking radius ~1066 mm; rockers straight in plan, toed out ~9 deg; right rocker pitched +0.85 deg vs left.

## Now
- [→] Remaining part faces, same recipe. Seed planes from the cloud (work/dense/chair_dense.npy, tools/cloud_slice.py to
      look), then face_ortho --optimize, view, centreline, trace:
      front legs (outer side face, front face), back legs (outer side, back face), arms (top face, outer edge),
      crest (front face is curved: use top view + elevation), slats (curved in side view), seat (plan outline + cloud surface).
      Rocker width (across) still needed: inner face plane or Joe's caliper R1-R5.

## Next
- [ ] Assemble parametric model -> mesh (GLB/STEP), overlays on photos (tools/overlay.py), residual report.
- [ ] Fold in Joe's caliper sheet (R/F/B/A/C/S/T codes), check dims K1-K6, seat depth grid, far photos, tape targets.
- [ ] Templates (1:1 PDF/DXF). Rocker bending-form template comes from parts/rocker_profile.json (mean_bot / mean_top).
- [ ] IMG_1592 (new in Drive at 12:00) not yet looked at or registered.
- [ ] No way found yet to hand Joe files by link from this session (no upload helper on PATH); repo push needs his GitHub repo.

## Incidents
- 12:13 machine restart during a capped (3-4 GB, 2 threads) matching job. Panic log: launchd (pid 1) died with SIGBUS;
  26 GB free, no memory pressure at the time. Cause unknown; not a memory exhaustion. All jobs are resumable.

## Not done / open
- Black ruler not used as an independent scale check (its units are inferred).
- Repo still local; Joe to create private `masterminnich/essick-rocker`.
