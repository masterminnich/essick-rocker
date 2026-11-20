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

- [x] Side frames: work/parts/sideL|R/ = whole side rectified on the rocker's outer plane (front leg, back leg lower part and
      seat side edge share it). tools/trace_side.sh traces them; rocker/sideframe.py = symmetric side planes.
- [x] FIRST MODEL: tools/model.sh --out parts/model_v1 -> parts/model_v1.glb, _params.json (provenance per number), _edges.json.
      Check views: tools/overlay_sil.py (part outlines on photos) -> work/overlay_v1/sil_*.jpg.

## Now
- [→] Critique loop on model v1. Known faults seen in the overlays (1507 side, 1502 back, 1484 front-quarter):
      * crest rail: too long (sticks out past the back legs), drawn as a straight vertical extrusion; needs its arch and tilt
      * arms: cloud-extent plank, back end pinches to 10 mm wide, front too wide (88 mm); needs a traced top-view outline
      * back legs upper: cloud centreline only; no traced edges above the arm joint
      * slats: OK in back view to a few mm; widths biased narrow
      * seat: outline has no front scallops / leg notches; scoop surface fit 1.8 mm rms
      * rocker width across (31 mm), leg thicknesses across (33 / 38 mm), arm thickness (25 mm) are tape/assumed values
      * no numeric model-vs-photo residual yet: build one (distance from projected outline to image edges per part)
      Next traces to make: back view plane (crest front face, back legs, slats) from 1501/1502/1513; top view (arms, seat
      outline, crest plan) from 1544/1545/1538/1539.

## Next
- [ ] Fold in Joe's caliper sheet (R/F/B/A/C/S/T codes), check dims K1-K6, seat depth grid, far photos, tape targets.
- [ ] Templates (1:1 PDF/DXF). Rocker bending-form template comes from parts/rocker_profile.json (mean_bot / mean_top).
- [ ] IMG_1592 (new in Drive at 12:00) not yet looked at or registered.
- [ ] File delivery by link: no working uploader on this machine (the atrium repo's upload-r2.py depends on a path that is
      not on CB). Repo push needs Joe's GitHub repo `masterminnich/essick-rocker`.

## Incidents
- 12:13 machine restart during a capped (3-4 GB, 2 threads) matching job. Panic log: launchd (pid 1) died with SIGBUS;
  26 GB free, no memory pressure at the time. Cause unknown; not a memory exhaustion. All jobs are resumable.

## Not done / open
- Black ruler not used as an independent scale check (its units are inferred).
- Repo still local; Joe to create private `masterminnich/essick-rocker`.

## 13:30 note
- tools/residual.py + tools/resid.sh exist but the metric does NOT discriminate yet: every part reads ~3 mm median, including
  the rockers known to be ~1 mm. Background clutter and neighbouring arrises dominate. Needs: restrict to photos where the
  part is seen against a plain background / use the multi-photo consistency (spread) image instead of single-photo edges.
- Joe (13:30) was surprised model v1 looks rough and asked whether rectified images were the problem. Answer given: no; the
  rough parts never came from rectified traces, they came from sparse cloud extents drawn as boxes. Plan: fit part
  silhouettes directly in the photos (model-driven), keep rectified traces for flat faces only.

## 13:50 carved hull (new shape source for the sculpted parts)
- tools/chair_mask.py: chair masks for 70 photos (work/masks/, GrabCut seeded by projected cloud points + model v1 band).
  Masks leak onto similar-coloured background in places (back views, under the seat).
- tools/carve.py -> parts/hull_v1.npz (vote grid, 2.5 mm voxels); tools/hull_mesh.py --keep 0.97 -> parts/hull_v1.glb.
  keep 0.88 fills the gaps between slats; 0.97 opens them. Run carve and mesh as SEPARATE steps (a combined run was cut off).
- tools/hull_views.py (ortho thickness views), tools/shade.py (shaded render from a photo's camera beside the photo).
- Result: recognisable chair with real part shapes. Faults: lump behind the centre slat / seat back, seat scoop filled
  (a hull cannot see hollows), stepped surface, accuracy not yet measured against anything.
- NEXT: (1) measure hull vs the traced rocker profile (known good) to get a real accuracy number for the hull;
  (2) tighten masks using the hull itself as the prior and re-carve; (3) take part cross-sections from the hull to give
  model parts real section shapes instead of boxes; (4) seat scoop from the cloud surface, cut into the hull.

## 13:55 hull accuracy measured: NOT usable for dimensions
- tools/hull_vs_rocker.py: hull vs traced left rocker profile. keep 0.97: top edge +11.4 mm fat (8.5..16.5), bottom -3.0 mm,
  face height +13.6 mm on a 27 mm part. keep 0.88: +26 mm. Cause: masks leak onto table/background consistently.
- Joe (13:55) spotted the generous masks himself. Conclusion told to Joe: the hull improved looks, not accuracy; do not take
  any dimension or cross-section from it. The NEXT list under '13:50' is superseded.
- NEXT (replaces the above): keep to the method with proven numbers (face orthophotos + traces):
  back-view plane (crest front face, upper back legs, slats) from 1501/1502/1513; top view (arm outlines, seat outline,
  crest plan) from 1544/1545/1538/1539; then rebuild model v2 with those. Hull only as a visual reference.
  A tighter segmenter (a learned model such as SAM) would be the way to make carving accurate; needs Joe's OK (compute).

## 14:10 unrolled back view + tracing method changed (Joe: "tracing could be better from the jump")
- tools/sheet_ortho.py: "unrolled" orthophoto along a side profile y(z) (parts/back_profile.json from the cloud). Slats from the
  back: work/parts/back/s_* ; photo-consistency minimum at offset +10 mm = slat back face -> slat thickness ~10 mm.
  Image is sharp for slats; crest and back legs visible but slightly off-sheet (do their own sheets: key "blegs").
- WIDE-BAND AUTO TRACING IS WRONG HERE: ribbon_trace on the median image jumped to background (centre slat 98 mm at the
  bottom); on a likelihood image it ran inside the wood (58 mm). By eye on a zoomed 10 mm grid: 76-82 mm.
- NEW TRACING RULE: seed every edge BY EYE on zoomed gridded views (ortho_view.py --scale 2.6 --grid 10, read u,v off the
  grid), then tools/edge_snap.py refines within +-3 mm only. Centre slat: 81.8 mm (v60) -> 100.0 mm (v665); tape close-up
  IMG_1553 read 98.3 mm just under the crest. Remaining ambiguity 2-3 mm low on the slat (light strip = side face showing).
- NEXT: redo with this rule: outer slats; back legs + crest (own sheets); then REDO front legs / back legs lower / seat edge
  in work/parts/sideL|R (old traces only 54-61 % clean) and re-check the rockers; then model v2.

## 14:30 slats done with the new rule; back-leg sheet ready
- Slats: by-eye seeds + edge_snap for all six edges (work/parts/back/slat_edges.json), fair 4th-order edges with a raw-trace
  guard -> parts/slats.json (tools/slat_fit.py). Edge scatter 0.4-0.8 mm; left/right mirror disagreement 2.1 mm rms, 4.8 max.
  Centre slat 80.7 mm (v60) -> 99.6 mm (v660) [tape 98.3 under the crest]; outer slats ~45-47 mm -> 53-57 mm.
  LESSON: a quadratic was too stiff (7 mm error at the ends); always check the fair curve against the raw trace.
- Back legs from behind: tools/sheet_ortho.py now has --score-absu/--score-v. Back-face offset from the cloud profile by
  height band: 24, 22, 10, 4 mm (top band unreliable). parts/back_profile.json key "blegs_back" (5th-order refit residual
  3.7 mm: improve with a spline). Unrolled view: work/parts/back/b_* (legs + crest visible, v 0..850).
- tools/zoom_panels.sh PREFIX OUT SCALE GRID "U0 U1 V0 V1"... [-- curves.json] = close-up panels for by-eye seeding/checking.
- NEXT: by-eye seeds on work/parts/back/b for back-leg inner/outer edges (|u| ~195-275) and crest top/bottom edges; then redo
  side-frame traces (work/parts/sideL|R) with edge_snap; then model v2 (slats from parts/slats.json on the slat sheet).

## 14:50 back legs traced from behind
- parts/back_legs.json: inner/outer edges of both back legs in the unrolled back view (work/parts/back/b, sheet "blegs_back"),
  by-eye seeds + edge_snap (band 3). Width across ~54 mm at v110 -> ~40 mm from v400 up. L/R mirror figures printed by the fit.
  By-eye tip: read seeds from a MEDIUM zoom with existing traces drawn (zoom_panels.sh ... 1.5 50), not the 10 mm-grid close-up;
  the close-up of a dark leg against clutter was misread by >10 mm.
- Crest in this view is distorted (crest bows back ~14 mm in plan, sheet is straight across; camera looks up at it): bottom edge
  v~768 at the ends, ~783 at the centre, top edge near the sheet end. Needs its own surface (plan curve) or a top view.
  sheet_ortho should get linear extension beyond the profile's z range.
- NEXT: model v2 now (rockers as v1; slats from parts/slats.json on the slat sheet, 10 mm thick; back legs = side profile from
  the cloud/side trace x back-view edges from parts/back_legs.json; crest clipped between the legs; arms/seat as v1), overlay
  check; then redo side-frame traces with edge_snap; crest and arms from a top view.

## 15:10 model v2 + first real critique-loop catch
- parts/model_v2.glb (tools/model.sh --out parts/model_v2): slats from parts/slats.json, back legs across-width from
  parts/back_legs.json, crest clipped to the legs; rockers/front legs/arms/seat as v1.
- Overlay on 1502 (tools/overlay_sil.py --max-side 3000 --crop 600 420 1640 1900) showed slat outlines ~7 mm off low down.
  Cause: the cloud side profile of the slats was wrong near the seat. Banded photo-consistency search (sheet_ortho --score-absu
  --score-v) gave back-face offsets centre 0,5,9,11,11,10,11 / outer -7,-1,5,8,8,9,8 mm for v bands 30-90 ... 550-690.
  tools/profile_offset.py bakes these into tabulated profiles "slats_back_c" / "slats_back_o" (parts/back_profile.json);
  sheet_ortho now takes tabulated profiles and --extend LO HI. Views: work/parts/back/sc (centre), work/parts/back/so (outer).
  NOTE v coordinates on sc/so are ~30 mm larger than on the old s view (extension below the seat).
- After the fix the outlines sit on the slats in 1502 to ~1-3 mm. BUT L/R mirror disagreement of the slat edges rose to
  3.4 mm rms (6.7 max): the 5-photo composite (max-angle 40) smears edges more; slatR_out is the worst trace (76% clean).
- NEXT: (1) re-render sc/so with --max-angle 25 (3 frontal photos) and re-snap, esp. slatR_out; (2) same banded-offset fix for
  the back legs sheet (tabulated, replaces the 5th-order refit); (3) side-frame retraces with edge_snap; (4) crest + arms from
  a top view / own surface; (5) overlays of v2 on side and front-quarter photos.

## 14:35 pushed to GitHub; seat split out
- GitHub: https://github.com/masterminnich/essick-rocker (private). `tools/push.sh` pushes main + seat (fast-forward) through the
  sandbox clone at ~/.cc-sessions/sandboxes/essick-rocker-joe/repo, which holds Joe's own GitHub sign-in. Push after commits.
  The sandbox's PREVIEW setup failed (hub tried to write a service file into a folder that does not exist); not needed here.
- Seat work is split to another session: worktree ../rocking-chair-seat, branch `seat`, brief in SEAT_HANDOFF.md. The coordinator
  (this ledger) does NOT touch the seat any more; merge `seat` into main when that session reports.
- Drive had 100 photos at 14:25. New since the first 94: IMG_1588-1592 (far views, square stood upright, digitally zoomed,
  chair possibly moved) and IMG_1593 (tape across the seat front). No blue-dot photos uploaded yet. None of the six are
  registered in the camera model.
