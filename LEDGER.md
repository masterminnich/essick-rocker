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

## 14:35 PST (machine clock; some earlier headings ran ahead of it) slats re-traced from clean-silhouette photos (step 1 of the '15:10' NEXT) -- root cause of the L/R smear found
- CAUSE of the smeared / fat slat edges: slat thickness parallax. A camera standing to one side of an edge sees the slat's
  side face, so the outline on that side is the FRONT arris, landing t*(xc-u)/depth further out on the back-face sheet.
  Measured: off-side photos read 1.3-3.8 mm outward, square-arris prediction 1.6-5.1 mm (ratio ~0.75: eased arrises).
  Pooling photos from both sides (the old 5-photo median, and even 3 frontal ones) fattens every edge. "Frontal only" was
  not the fix; "per edge, only photos that cannot see that edge's side face" is.
- tools/slat_clean_snap.py --primary: each edge from the most on-axis clean photo (IMG_1502, camera x = -39; an on-axis
  photo is also immune to sheet-depth error), other clean photos as checks (agree to 0.3-1.6 mm), small arris bias removed
  (0.65 mm slatR_in, 0.19 slatL_in). tools/snap_multi.py = per-photo snap + median (general helper).
  Sheets re-rendered to work/parts/back/f/sc|so (same geometry as sc/so: --extend 30 20, photos 1502,1501,1503,1499,1513).
- parts/slats.json (tools/slat_fit.py): edge scatter 0.15-0.83 mm. Centre slat 77.0 mm (v80) -> 99.9 (v700);
  outer slats R 39.5 -> 51.0, L 40.6 -> 53.5. The whole slat set sits +1.8 mm to the chair's right of the centre plane (constant
  at every height: placement or centre-plane error, not shape); with that removed L/R mirror disagreement is 1.14 mm rms
  (was 3.4), max 3.3 at the top of the right outer slat (as-built: right slat ~3-4 mm narrower than left at the top).
- Tape cross-check (measurements/tape_readings.csv): IMG_1551 at the slat bases: outer 40.9, centre 77.7, gaps 27.7 / 25.7 mm
  -> trace 39.5-40.6, 77.1, gaps 29.2 / 28.6 (old trace had outer 45-47, centre 80.7). IMG_1553 centre just under the crest
  98.3 mm (rated high, +-1.2) -> trace 100.0-100.5: 1.7-2.2 mm FATTER than the tape. OPEN: over the 1/16" tolerance; a caliper
  reading of the centre slat width under the crest would settle it.
- By-eye check done on IMG_1502 zoom panels: traces sit on the wood/background boundary; bright strips at the slat tops are
  highlights on the eased arris (trace runs outside them = max width). slatR_out raw trace wanders 3-4 mm onto a background
  chair leg at v 110-170; the fair curve rejects it (92% clean) and passes through the mirrored left edge there.
- zoom_panels.sh: env IMG="--img 1502" shows a single rectified photo (use it; the median hides which photo an edge is from).

## 14:38 PST back legs re-traced by EDGE TRIANGULATION (step 2 of the '15:10' NEXT); model v3
- NEW TOOL tools/edge_tri.py (+ rocker/surface.py): trace one arris in each "clean" photo (camera inside the edge line, so the
  part's side face is hidden) and solve BOTH the edge position and how far the arris sits off the sheet, from the parallax
  between photos (u_obs = u + d*(u-xc)/(H-d)). The sheet no longer has to be exactly on the face. Give --inside U,V (a
  point inside the part; with a negative u write --inside=-225,400). Validated on the slats: agrees with the 14:35 trace to
  <= 0.7 mm, residual 0.3-0.5 mm rms between photos.
- Back legs: the old "blegs_back" sheet was wrong by +30..43 mm at v100, ~0 at v400-550, +16..21 mm at v735 (all four edges
  agreed), so the old 5-photo composite put every edge in the wrong place (old width 54.7 mm at v110 was an artefact).
  Fixed in two passes (depth baked with tools/profile_offset.py): parts/back_profile.json keys blegs_back2 -> blegs_back3 =
  the back OUTER arris of the legs (y(z) side profile, good to ~1-3 mm; L and R differ by that much as built).
  Sheet: work/parts/back/t/b3 (photos 1502,1501,1503,1499,1513). Outer edges: 3 clean photos each, position + depth solved.
  Inner edges: only 2 clean photos, both far to one side (weak baseline; free depth came out +-10 mm inconsistent), so depth is
  FIXED: inner arris 5.7 mm forward of the outer one (leg faces toed out ~8.5 deg with the side frame; supported by the
  2-3 mm side-face strips visible in IMG_1502). This is an assumption worth 0.6-0.8 mm of width.
- parts/back_legs.json (tools/bleg_fit.py): edge scatter 0.2-0.4 mm; width across (x) 37.0 mm at v110, 39.8 at v250, 38.3-38.5
  above (= 38.9 mm measured along the toed face = 1.53 in; tape IMG_1556 under the crest 1.55 in +-0.05: agrees).
  Outside-to-outside 454 mm (v110) -> 514 mm (v725). L/R mirror 0.84 mm rms, 1.5 max after a +0.6 mm pair offset.
- parts/model_v3.glb (tools/model.sh --out parts/model_v3): new slats + back legs; leg rear face moved onto the triangulated
  arris (the cloud/side-trace rear face was off by +5.7 mm median, 13 max). Overlay work/overlay_v3/sil_1502.jpg: slats and
  legs sit on the wood; crest still the old box (not arched), leg tops stick up past the crest.
- LESSON: any composite of photos from both sides of a thick part is wrong at its edges. Use edge_tri per edge. The
  side-frame traces (front legs, back-leg lower part, seat edge; ribbon_trace on an 8-photo median) have the same flaw.
- NEXT: (3) side frames with edge_tri: work/parts/sideL|R have per-photo o_<photo>.png; outer-face arrises are on the plane,
  so d should come out ~0 (check), front/rear edges of legs traced from clean photos; (4) crest: own surface + top view;
  arms: top view; (5) overlays of v3 on side and front-quarter photos; then the leg top / crest joint.

## 14:41 PST side frames: pilot only, NOT valid yet (step 3 started)
- Looked at work/parts/sideL in a single photo (IMG="--img 1507" zoom_panels): the old ribbon traces are wrong in places
  (front-leg "front edge" follows an interior ridge above v350; back-leg rear edge runs inside the wood above the seat).
  The legs are sculpted: in side view each shows two faces with a ridge between them, so "width in side view" needs the
  outline AND the ridge, each as its own triangulated line.
- edge_tri.py got --mode far (cameras outside the edge: outline = far arris, depth = minus thickness) and --mode all.
- Pilot on the left front leg (by-eye seeds from the 1507 panels; work/parts/sideL/t/flegL_front|rear.json): residuals 0.6 mm
  but edges moved up to 12 mm from the seeds and depths came out +5..+12 / -13 mm instead of ~0 / ~-33. NOT trustworthy:
  8 photos up to 56 deg off the face normal were used, a +-6 mm band cannot follow that parallax, and the seeds were rough.
- NEXT for step 3: per member and per line (front outline, rear outline, ridge): seeds by eye per photo region on 1507;
  use only 1507,1508,1509,1510,1506 (within ~20 deg); first pass band 10; check each photo's trace by eye before trusting
  the solve; right side has only 1470,1469,1474,1477,1478 on file (more oblique) - render more near-frontal right photos
  if any exist. Then (4) crest/arms, (5) overlays on side and front-quarter photos.

## 14:53 PST left side frame: front leg and lower back leg triangulated (step 3, left half done except upper back-leg front edge)
- Tools: edge_tri.py got --pool (candidate photos, mode filter still applies), --depth-guess + --seed-photo (search centred where an
  arris at that depth lands in each photo, so the band stays small for far arrises), --dump (each photo's own trace).
  tools/tri_lines.py runs every line of a seeds file (parts/side_seeds_L.json = by-eye seeds read on IMG_1507 zooms);
  tools/tri_show.py draws one photo's own traces on that photo (the by-eye check); tools/side_fit.py collects the lines into
  parts/side_frame_L.json (fair curve, scatter, depth, xyz, photos, provenance); tools/xyz_on_sheet.py draws any 3D line onto a
  rectified photo (cross-check of lines triangulated from other photos).
- Run: work/toolkit/rk.sh tools/tri_lines.py work/parts/sideL/o parts/side_seeds_L.json work/parts/sideL/t2 ; then
  work/toolkit/rk.sh tools/side_fit.py work/parts/sideL/t2 --sheet work/parts/sideL/o_plane.json --side L --out parts/side_frame_L.json
- What the legs look like in side view (checked by eye on 1507, 1508, 1510, 1506 singly): the outer face is flat; the rear is a
  rounded/bevelled face, so there are THREE lines per member: front outline (clean), rear outer-face ridge (a soft tone line;
  depth fixed to the front arris, residual 1.3-2.3 mm, +-2 mm), rear inner arris (far mode, seen as the outline by cameras behind).
  The inner rear arris sits 5-9 mm rearward of the outer ridge on both legs (about half of it is the 8 deg toe of the plane).
- Left front leg (photos 1507,1508,1509,1510,1506; residuals 0.3-0.5 mm on outlines): outer-face width 31 mm at the rocker,
  40 mm just under the seat (tape IMG_1497: 39.6 +-1.6, agrees), 38 mm above the seat tapering to 28-31 mm under the arm
  (tape IMG_1498: 29.2); overall side-view width (front to inner rear arris) 38 -> 46 mm below the seat, 41 -> 34 above.
  Thickness (depth of the inner arris) 27-30 mm below the seat, 32-36 above (ddeg 1 solve; +-3 mm).
- Left back leg below the seat (v 60-290): front outline 4 photos, residual 0.31, on the plane (+0.5..-0.3); outer-face width
  35 mm at the rocker -> 42 under the seat; overall 38 -> 48; inner arris 36 mm deep at the rocker (tape IMG_1494: 34-41) but
  27 at v290 (suspect: frontal trace says 37-40 across; the frontal number is the better one).
- CROSS-CHECK front vs side: the back OUTER arris of the left back leg triangulated from the FRONT photos (work/parts/back/t/
  blegL_out) drawn into side photos 1508 and 1509 lies 0.7-2.4 mm (along u) behind the rear outline seen there over v 480-840
  (by eye: trace on the wood edge, frontal line just outside it). Above v 940 the side outline is the crest, not the leg.
  So the back-leg side profile from the front photos is good to about 1.5 mm; it could be moved forward ~1.5 mm at v 600-840.
- NOT done: front outline of the upper back leg in side view (v 530-940). In 1510 the dust hose, far leg and slats sit behind it
  and I could not read seeds reliably (two readings at v650 differed by 20 mm); the arm joins the leg at v 480-520. Try seeds on
  1506/1505 (different background) or measure the leg's front-to-back depth from a front-quarter photo instead.
- NEXT: (3b) right side frame the same way (work/parts/sideR/o, photos 1470,1469,1474,1477,1478 are more oblique: use
  --depth-guess; write parts/side_seeds_R.json); mirror-compare with parts/side_frame_L.json; upper back-leg front outline;
  seat side edge is the seat session's. Then feed side_frame_L/R into build_model (front legs and lower back legs are still the
  old ribbon traces there). (4) crest + arms. (5) overlays on side (1507) and front-quarter (1484) photos.
