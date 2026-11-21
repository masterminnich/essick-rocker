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

## Now (rewritten 19:05 PST, model v16)
- Phase 5b, known fixes and joinery, split between two sessions: PLAN.md, "Sessions and who owns what". Read it after every
  pull of main; it is the only channel between the sessions.
- Model v16 (main). `tools/model.sh` builds the parts, cuts the joints (`tools/joinery.py`) and runs the assembly check; a
  number is issued only on PASS (PLAN rule 8). v15 = joinery PRs #18, #19; v16 = seat side-edge section (PR #20).
- NEXT, in this order: **Joe's fix list of 19:00** (PLAN.md: 1 Dominos missing at the back, IMG_1620; 2 rocker ends, IMG_1618
  and 1619; 3 front-leg Domino off-centre), then the hub's remaining 5b items: [ ] 3 mm question at the right front corner of
  the seat · [ ] left-side check of the seat scoop · [ ] arm underside and thickness (new file) · [ ] rocker bottom edge traced
  directly · [ ] seat side edge behind y 400. Done: seat front face (v11), seat mesh closed (v13), seat side-edge section (v16).
- Joe gave items 1 and 3 of his list to the hub although they touch the joinery session's files; said so in PLAN.md and in a
  comment on PR #20.

## Next
- [ ] Phase 6 critique loop (per-part photo error, ~15% of photos held out) once 5b is done.
- [ ] Phase 6b tape readings M1, M3, M4, M5, M9, M11 as checks, whenever Joe sends them. Model work never waits for them;
      the FINAL templates do (PLAN.md, 'Hand measurements').
- [ ] Phase 6c: edge-rounding radii; the shop templates in IMG_1507.
- [ ] Phase 7 final templates (templates session; its PR #6, #7 files are drafts until then).
- [ ] IMG_1588-1593 not registered (half resolution only, one job).

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

## 15:05 PST right side frame, mirror comparison, model v4 (front legs lofted from triangulated lines)
- Right sheet: work/parts/sideR/p (NOT the old .../o), plane point [202.513,0,0], normal [0.98719,-0.15629,-0.03196], u -260..660,
  v -10..1150, photos 1472,1471,1470,1473,1469 (the near-frontal ones on this side). Render command is in tools/face_ortho.py usage
  form: --point ... --normal ... --urange -260 660 --vrange -10 1150 --res 0.5 --photos 1472,1471,1470,1473,1469 (946 MB, 4 s).
- Seeds: parts/side_seeds_R.json = the solved LEFT lines mirrored onto the right sheet (drawn on 1472 first and checked by eye:
  they sit on the right leg edges; my own reading of the small full view was 40 mm off, so mirrored solved lines are the better seed).
  Run: work/toolkit/rk.sh tools/tri_lines.py work/parts/sideR/p parts/side_seeds_R.json work/parts/sideR/t2 ; side_fit.py --side R
  -> parts/side_frame_R.json. Outline residuals 0.23-0.52 mm; far-arris depths 30-36 mm.
- Widths agree left/right within ~1 mm: front leg outer face R 30.4/32.6/35.7/38.6/40.4 vs L 31.0/32.8/35.0/37.5/40.3 (rocker ->
  under the seat); overall side-view width R 38.7/41.9/45.0/46.5 vs L 38.7/41.2/44.0/45.9; lower back leg outer face
  R 37.4/38.9/40.7 vs L 36.4/38.3/40.3.
- tools/side_mirror.py (left reflected, compared with right at the same height, averaged) -> parts/side_frame.json (symmetric lines:
  z, y, x_abs per line). Right minus mirrored left, fore-aft mean: front leg below the seat -0.1 (front), -0.4 (ridge), +0.2 (inner
  rear); front leg above the seat +4.8 / +2.3 / +4.1; lower back leg +2.7 / +1.9 / +1.4 mm. So the chair as built is a few mm
  out of mirror above the seat (the right front leg top sits ~4-5 mm forward of the left); the symmetric model takes the mean.
- FINDING: the old model legs were 13-27 mm too wide in side view (old ribbon traces on the multi-photo median included the side
  face; the old upper front-leg front edge followed an interior ridge 16-20 mm back). Old trace width 55.5 at v150, 58.6 at v300;
  triangulated overall width 37.9 and 44.6.
- tools/build_model.py: if parts/side_frame.json exists, the FRONT LEG is a loft through 4-cornered sections (front arris, rear
  outer-face ridge, inner rear arris, front at inner depth) from the three lines; foot cut on the rocker top; the seat joint
  (v 370-470, hidden by the seat) is bridged linearly. LOWER BACK LEG: front and inner-rear lines replace the old trace; the rear
  edge through the seat joint is a cubic between the lower inner-rear line (last 90 mm) and the frontal back outer arris
  (parts/back_legs.json, traced range only), fit 0.6 mm rms. Report keys: front_leg.*, back_leg.lower.
- parts/model_v4.* (tools/model.sh --out parts/model_v4). Front leg outer-face width 31.9 (v150), 38.1 (v300), 40.1 (v360),
  39.5 (v500), 30.3 (v600); overall 37.9/44.6/45.8/40.7/33.6; thickness across 28-31. Back leg side-view width 41.4 (z100),
  48.7 (z300), 47.6 (z450), 48.3 (z600), 39.5 (z800-1000); across 37-40.
- Overlays (tools/overlay_sil.py --glb parts/model_v4.glb --images 1507,1484,1472 --max-side 3000 --out-dir work/overlay_v4): front
  legs sit on the wood in 1507 and 1484. Back leg: rear outline on the wood; a 20-30 mm kink remains where the upper (cloud
  extents) and lower (triangulated) parts meet at the seat joint, and the lower leg's rear outline is ~5 mm outside the wood in 1484.
- STILL OPEN: front outline of the upper back leg in side view (v 530-940; model uses cloud extents there). Second attempt on 1510
  with the frontal arris projected (tools/xyz_on_sheet.py) located the leg but not a clean front edge. Front-leg seat joint bridge.
- Crest rail + arms: now a separate session (worktree ../rocking-chair-crest, branch crest-arms). Do not edit those parts here;
  merge parts/crest.json and parts/arms.json when it reports. Seat session reported (seat/REPORT.md, PR #1): merged below.
- NEXT: (a) feed the measured seat (seat/surface.json thin-plate spline, valid |x|<=251, y 64-530) into build_model; (b) upper
  back-leg front outline (try right-side photos 1471/1470 where the background differs, or the leg's fore-aft depth from a
  front-quarter photo); (c) seat-joint region of both legs; (d) merge crest-arms when ready; (e) overlays on the 5 spread views
  1485,1472,1527,1502,1545 as before/after for Joe.

## 15:10 PST seat merged and fed into the model (v5); pull-request workflow from now on
- WORKFLOW (Joe, 15:08): big changes go through a pull request that is SQUASH-merged, so each PR is a readable record of the
  progress (figures, plots, roadblocks) for a later write-up. Small ledger fixes may still go straight to main.
  How: branch off main; commit figures under figures/<topic>/; `tools/push.sh BRANCH`; `gh pr create` with Joe's sign-in
  (GH_CONFIG_DIR=/Users/sean/.cc-sessions/code2-fresh-home/.cc-sessions/users/726d315d-a06f-409b-b996-e0d36778bd9c/gh, absolute path:
  HOME here is already .../code2-fresh-home, so `~/.cc-sessions/code2-fresh-home/...` points nowhere); images in the PR body as
  https://github.com/masterminnich/essick-rocker/blob/<commit>/<path>?raw=true; `gh pr merge --squash --delete-branch`;
  `tools/push.sh --pull-main`. The seat PR (#1) is the pattern.
- Seat branch merged into main (b2ca0c2): seat/REPORT.md, seat/surface.json (thin-plate spline through 103 mirrored tape dots,
  leave-one-out 1.18 mm rms interior), figures in seat/figures.
- tools/build_model.py now uses seat/surface.json for the seat top inside the dotted region (|x| <= 251, y 64-530); outside it the
  old cloud polynomial is kept but shifted to meet the spline at the region's edge. Measured minus old polynomial inside the
  region: median -1.8, rms 4.5, range -16.7..+6.1 mm (the old polynomial was fitted to cloud points above a guide plane that sat
  ~13 mm too high at the back, so it probably never saw the back hollow: inferred, not checked).
- ROADBLOCK: first try also took the seat's edge height and underside from the measured rim line (extended behind the dots).
  In IMG_1507 the underside then sat ~35 px (about 40 mm at the rear) too low. The rim line is the highest point INSIDE the dotted
  region, not the seat's edge, and it is extrapolated behind y 64. Reverted: underside = the old assumed plane, which matches the
  seat's lower edge in 1507 by eye. Resulting edge thickness 30 mm (y100), 36 (y300), 43 (y500): NOT measured.
- parts/model_v5.* ; overlays v3 vs v5 on 1507,1484,1472,1485,1527,1502,1545 in figures/side_frames/ (tools/before_after.py pairs two
  overlay_sil outputs); figures/side_frames/side_lines.png (tools/side_plot.py: elevation of the triangulated lines and widths against
  height with the tape readings); traces_L_1507.jpg / traces_R_1472.jpg (tools/tri_show.py panels).
- STILL OPEN: upper back-leg front outline in side view; seat plan outline, edge thickness and underside (no data: needs an edge
  trace or two tape readings); seat-joint regions of the legs; arm/crest come from the crest-arms session.
- NEXT: (a) upper back-leg front outline (right-side photos 1471/1470, or fore-aft depth from a front-quarter photo); (b) seat edge:
  trace the side edge face on the side sheets with edge_tri (top and bottom lines), front edge from IMG_1599; (c) merge crest-arms
  when it reports; (d) K1-K6 check dimensions and Joe's caliper sheet when they arrive.

## 15:27 PST crest rail and arms from the photos taken from above (step 4, branch crest-arms; Joe's section)
Method: each arris (edge) traced only in photos that cannot see that part's side face, and solved on its own. No photo
blending across a thick part. No COLMAP re-solve; every job ran through tools/py.sh / safe_run, one at a time, peak < 0.5 GB.
- New tools: tools/curve_tri.py (one arris as a 3D curve from traces on DIFFERENT sheets: overhead z = const + rear
  y = const, so both y and z are solved), tools/crest_fit.py, tools/arm_fit.py, tools/cam_table.py.
- **Crest (parts/crest.json)**: four arrises.
  - Top-rear (the back face's top edge): triangulated from 1545/1547/1548/1549 overhead + 1502/1501/1503 rear.
    Residuals 0.4-1.7 mm; sigma < 0.9 mm.
  - Top-front and bottom-front: triangulated in plan; z assumed square to the lean (+4.4 mm).
  - Bottom-rear: z triangulated from the rear photos; y carried down the back legs' lean (9.9 deg, assumed; flush backs per IMG_1540).
  - Shape: the back face bows 18.0 mm in plan (arc R 1231). The top arches in elevation: 1078.5 at the centre,
    1063.8 at the leg outer face, so the rise is 14.7 mm.
  - The rail tapers: 28.4 thick at the top, 40.6 at the bottom (the front face leans 18.8 deg at the centre).
  - Leg tops end flush with the crest top, so the arch runs over them. Visible span between the legs' inner faces: 436.7 mm (+-0.8).
  - Left/right mirror rms 0.6-1.8 mm.
  - OPEN: the tape height check is off by 2.8 mm (74.7 here vs IMG_1555's 77.5).
- **Arms (parts/arms.json)**: left and right solved separately, then a symmetric design version.
  - Outer top arris: depth solved (1544/1545/1547-1549 for the right arm; 1544/1545/1537-1539 for the left). Residual 0.36 / 0.56 mm.
  - Inner top arris: its clean photos all stand on one side (1537-1539 R, 1547-1549 L). So its depth is taken from the
    outer arris at the same station, which assumes the top is flat across the width. Sensitivity is 0.4-0.6 mm per mm of depth.
  - Front ends: a second sheet with its axes swapped, since edge_tri only follows edges running along v. All photos
    stand behind the front edge, so all are clean. The free depth solve put the arris 7-13 mm deeper than the side
    arrises do. The point cloud sides with the side arrises, so their depth is used. Front position along the arm: +-2.5 mm.
  - Heights checked independently against the dense cloud at every 30 mm station: within 1-3 mm.
  - Design: a tapered plank. Width 41 / 53 / 63 / 72 / 76 mm at y = 100 / 200 / 300 / 400 / 480. Top z 531 -> 659.
    Slope 23 deg at the back easing to 14 deg at the front. The inner edge curves; the outer is nearly straight.
    Front corners (design, right arm) (239.0, 490.1) and (315.6, 503.8): the front end is cut on a slant.
  - Left vs right: forward of y 340, both arms sit ~3.6 mm toward +x and the left is ~5 mm higher. That is a real
    asymmetry or a slight roll of the frame; the design averages it out.
  - The left inner trace behind y 180 follows a shading line ~4-5 mm inside the edge, so the design uses the right arm there.
  - Lesson: on long tapered parts, the outer trace jumped onto background where the arm narrows (behind y ~ 230).
    Re-seeding by eye on 10 mm grids fixed it. Always overlay the per-photo traces before trusting a solve.
- **build_model.py**: reads both files (`--legacy` gives back v3's cloud crest and arms).
  - The crest is lofted between its four design arrises, 2 mm into each leg.
  - The back-leg tops are cut to the arch: they were 1088.5 high, now flush with the crest top at the leg (1064.5).
  - The arms are a grid solid from the design curves, carried back to y 40 into the back leg.
  - The front-leg tops ran 10.7 mm up through the arm; now cut at the arm underside.
  - Output: parts/model_v3_crest.glb.
- Overlays (v3 left, new right): figures/crest-arms/sbs_{1545,1485,1472,1527,1502}.jpg.
- OPEN:
  - Arm thickness is still assumed (25 mm).
  - Where each arm meets its back leg isn't seen from above.
  - Neither the arms' inner edges nor their front ends meet 1/32"; both are within 1/16".
  - R2 delivery: no uploader on CB. The figures are on GitHub (private repo).

## 15:35 PST upper back leg traced in side view on its own face sheets; model v6 (branch back-leg-upper, PR #3)
- WHY IT FAILED BEFORE: (1) tools/zoom_panels.sh wrote its panels to /tmp/_zp_N.jpg, shared with the seat and crest sessions, so the
  panels I read were sometimes another session's (fixed: own mktemp folder). (2) The upper back leg splays outward: its outer face is
  8 mm outside the side sheet at v 450 and 43 mm at v 1000, so every photo showed it displaced by a different parallax.
- SHEETS on the leg's own outer face (plane through the back outer arris from the back views, rms 1.2 mm): work/parts/sideL/ub and
  work/parts/sideR/ub (u -230..130, v 420..1080, 0.5 mm/px):
    tools/py.sh tools/face_ortho.py --point -250.972 -6.651 698.892 --normal -0.986062 -0.139517 -0.090645 --urange -230 130 --vrange 420 1080 --res 0.5 --photos 1510,1506,1507,1508,1509,1505,1504,1511 --max-angle 75 --out work/parts/sideL/ub
    tools/py.sh tools/face_ortho.py --point 253.65 -8.096 698.702 --normal 0.983159 -0.155652 -0.095768 --urange -230 130 --vrange 420 1080 --res 0.5 --photos 1470,1477,1469,1478,1471,1472,1473,1555 --max-angle 75 --out work/parts/sideR/ub
  then tools/tri_lines.py SHEET parts/side_seeds_ub_?.json work/parts/side?/tub and tools/side_fit.py (--sheet ..._plane.json). On these sheets the FAR leg appears displaced (it is ~483 mm behind the sheet): behind the near leg's rear edge for a
  camera near u 0 (IMG_1507), in front of its front edge for a camera well forward (1508). So each edge needs its own cameras.
- FRONT OUTLINE (bleg?_front_hi, v 610-1040): cameras standing BEHIND the leg see the front edge against the shop. Left 1510, 1506,
  1505, 1511: residual 0.61 mm rms, arris 3.7-6.1 mm inside the sheet (rounded corner). Right 1470, 1477, 1478, 1469: 0.46 mm rms.
  First try with two cameras and depth fixed at 0 gave 1.18 mm with the two photos pulling opposite ways: depth has to be solved.
- REAR EDGE (bleg?_rear_hi, v 600-940): cameras standing IN FRONT of the leg; depth held at 0 (sheet is on that arris; 1 mm of depth
  moves the line 0.2 mm). Left 1508, 1509: 0.45 mm rms. Right 1472, 1473: 0.70 mm rms. IMG_1471 was dropped: the far leg and the
  slats are behind the edge there and the trace locked onto a highlight (residual 1.9 mm with it).
- All eight photos checked by eye on single rectified photos (figures/back_leg_upper/trace_*.jpg): traces on the wood's edge.
- LEFT vs RIGHT (tools/side_mirror.py): rear edge R minus mirrored L +0.31 mm mean, 0.36 rms, 0.73 max. Front outline +0.83 mean,
  1.17 rms, 3.2 max: the difference is 3.0 mm at z 620 just above the arm joint and falls to 0 by z 900 (hand-blended joint, or a
  trace effect: not settled; the design line is the mean, so +-1.5 mm there, inside the 1.6 mm curve tolerance but only just).
  The rear arris from the BACK views disagrees L/R in fore-aft (their weak direction) by 2.8 mm at z 700, 2.2 at z 925, 4.7 at
  z 1000; the side traces settle it inside their range (z 925: side L -150.8, R -151.3; back views L -149.2, R -151.4).
- parts/side_frame_ub_L.json, _R.json (per side, on the ub sheets), merged into parts/side_frame.json as bleg_front_hi, bleg_rear_hi
  (tools/side_mirror.py --out parts/side_frame.json --update). Seeds: parts/side_seeds_ub_L.json, _R.json.
- MODEL v6 (parts/model_v6.*): tools/build_model.py takes the upper back leg's fore-aft outline from these lines (z 608-1028 front,
  608-928 rear; above 928 the rear follows the back-view arris shifted to meet the side trace; z 450-608, the arm joint, is a linear
  ramp from the lower leg). v5's front outline was 10-21 mm too far forward and the rear 0.4-3.6 mm; width square to the leg is now
  34.9 (z620), 31.9 (z700), 30.0 (z800), 27.8 (z900), 23.7 (z1000) against v5's 48 (z600), 39.5 (z800), 39.4 (z1000).
  Across-width unchanged (back view). Overlays v5 vs v6 in figures/back_leg_upper/ (1508, 1473, 1510 zooms; 1507, 1472 full).
- STILL OPEN on the back leg: z 928-1085 rear and the leg top (crest joint; wait for the crest merge); the arm-joint ramp z 450-608
  is not traced (only ~70 mm of front edge is exposed between seat and arm); depth of the front arris is weak (L/R differ 5.9 mm in x)
  and is not used: across-width comes from the back view.
- crest-arms worktree now has parts/crest.json AND parts/arms.json committed (7d2edbd, based on old main 89564b3; it also edits
  tools/build_model.py, so the merge will conflict there).
- NEXT: (a) merge crest-arms (rebase or merge onto main, keep both sets of build_model changes, rebuild the model, PR);
  (b) seat edge: top and bottom lines of the side edge face on the side sheets with edge_tri, front edge from IMG_1599;
  (c) K1-K6 and Joe's caliper sheet when they arrive; (d) register IMG_1588-1593 at half resolution only.

## 15:39 PST crest-arms merged; model v7 = v6 legs + measured crest and arms (branch crest-arms-merge, PR #4)
- Merged branch crest-arms (7d2edbd: parts/crest.json, parts/arms.json, tools/curve_tri.py, crest_fit.py, arm_fit.py, cam_table.py,
  figures/crest-arms/) into main's line. tools/build_model.py merged without conflict (my upper-back-leg block sits before the leg
  sweep, the crest/arm block after it); only this ledger conflicted (both entries kept, in time order). crest.json and arms.json are
  untouched: they belong to the crest session.
- MODEL v7 (parts/model_v7.*, `tools/model.sh --out parts/model_v7`): crest lofted between its four measured arrises, arms from
  the arms design, on top of v6's legs. Numbers from the build report:
  - back-leg tops cut from z 1087.0 to the crest arch: top now 1064.5 at the leg centre (1068.3 at the highest corner);
    crest top 1078.5 at the centre; visible crest span between the legs' inner faces 436.7 mm.
  - arms y 40.0-503.8, 25 mm thick (assumed); front-leg top was 628.7, now cut at the arm underside 621.9 (it ran 6.8 mm into the arm).
  - upper back-leg widths unchanged from v6. Overall box 42.62 in high, 24.86 in wide, 43.01 in long.
- CHECKED BY EYE, v6 vs v7 on single photos (figures/crest_arms_merge/):
  - IMG_1545 from above, both crest ends zoomed: the crest outline now stops on the visible joint line with the leg and the leg
    outline sits on the leg's end grain; v6's crest was a straight box that missed the bowed rail and overshot both ends.
  - IMG_1508 leg top zoomed: leg outline ends on the top of the wood; v6's leg and crest stood about 20 mm above it.
  - IMG_1502 from behind: crest outline follows the arch. IMG_1485 and IMG_1527 arm zooms: arm outlines follow both arms' top and
    outer edges; v6's arm outlines (from the point cloud) missed the front ends and undersides, and the front legs ran up into the arms.
  - Arm underside in 1485: the model's flat 25 mm plank is thicker than the wood at mid length (the real underside is hollowed
    between leg and back): thickness and underside shape are still assumed.
- NEW OPEN ITEM found by the merge: the crest and the back leg do not meet flush in the model. At the leg's inner face (x 220) the
  crest's back face is at y -179.3 (top) and -166.9 (bottom) while the leg's rear is at -175.1 and -164.5: a 4.2 / 2.4 mm step. At
  the leg's outer face the crest's top-rear arris (y -176.2 at x 252) is only 1.1 mm behind the leg. The crest arris is the better
  measurement there (solved in y, sigma < 0.5 mm); the leg's rear above z 928 is the back-view arris, weak fore-aft. So the leg's
  rear face twists near the top to carry the crest's bow, and the model's constant section does not. Fix: pin the leg's rear line
  above z 928 to the crest's top-rear and bottom-rear arrises at the joint (a build_model change, no new tracing).
- Still open from the crest session: tape height check 2.8 mm off (74.7 vs 77.5 in IMG_1555, tape hooked over a rounded edge);
  arm thickness assumed 25 mm; arm-to-back-leg joint not seen; arm inner edges and front ends within 1/16" but not 1/32".
- NEXT: (a) pin the back-leg rear to the crest arrises at the joint (above); (b) seat edge: top and bottom lines of the side edge
  face on the side sheets with edge_tri, front edge from IMG_1599; (c) arm underside/thickness from the side sheets (the arm's side
  face is seen square-on in 1507/1472); (d) K1-K6 and Joe's caliper sheet when they arrive; (e) register IMG_1588-1593 at half
  resolution only.

## 15:43 PST back-leg rear pinned to the crest's edge at the leg top; model v8 (branch leg-crest-joint, PR #5)
- Problem (found by the crest merge): above z 928 the leg's rear line only had the back-view arris (weak fore-aft). At z 1060 the
  leg's rear was at y -173.9; the crest's top-rear arris, which runs on over the leg top and was solved in y and z, puts the leg's
  top rear corner at y -176.7, z 1064.5 at the leg centre x 237.6 (raw points: L -177.3, R -176.0).
- Fix in tools/build_model.py (needs parts/crest.json; skipped with --legacy): the rear line is ramped from the end of the side
  trace (z 927.5, no change) onto that point (-1.95 mm at z 1064.5). No new tracing; crest.json only read.
- Result, v8 vs the crest's back face at the leg centre x 237.6 (crest value = line between its bottom-rear and top-rear arrises):
  z 1000: leg -164.7, crest -164.8; z 1020: -168.5 / -168.5; z 1040: -172.0 / -172.2; z 1060: -175.8 / -175.9. v7 was 1.2-2.0 mm
  in front. The agreement at z 1000-1040 is an independent check: the crest's bottom-rear depth was ASSUMED (carried down a
  9.9 deg lean), and the leg line gets there from the side trace and the top pin alone.
- Leg fore-aft width at z 1000: 25.2 mm (v7 24.1); at z 1060: 26.4 (v7 24.5). Everything below z 928 unchanged.
- By eye, v7 vs v8 (figures/leg_crest_joint/): IMG_1508 the leg outline's rear edge now runs on the boundary between the leg and
  the lit crest back face behind it, and reaches the top rear corner (v7 ran inside the wood); IMG_1473 small move, on the edge.
- STILL OPEN at this joint: the crest's back face is bowed, so at the leg's INNER face (x 220) it is 2.5-2.8 mm behind the leg's
  rear face in the model (z 1000-1060), and at the outer face (x 252, top) within 0.5 mm. On the chair the leg's rear face is
  blended into the bow by hand; the model's leg has a constant section. Front faces: leg -149.4 vs crest -150.8 at x 220, z 1060
  (leg 1.4 mm proud). A side template of the leg is not affected (it is the outer-face profile); the blend is shaping after glue-up.
- NEXT: (b) seat edge lines on the side sheets; (c) arm underside/thickness from the side sheets; (d) K1-K6 and the caliper
  sheet when they arrive; (e) register IMG_1588-1593 at half resolution only.

## 16:18 PST seat side edge measured on both sides; model v9 (branch seat-edge)
- NEW FILE parts/seat_edge.json (tools/seat_edge_fit.py). No existing parts JSON changed format. For the templates session:
  the seat blank's side outline, edge height and edge lean are in `design` (polynomials in (y-250), valid y 110-400, plus a
  `stations` table); `parts/model_v9_params.json` parts.seat gained `underside` and `side_edge`, and its `outline` text changed.
- METHOD. Bottom arris: side sheets (u = height), outline against the background, tools/edge_tri.py. Top arris: the side sheet
  alone was not good enough (no camera sees the top line "clean" from the side; depth = x came out 10 mm different at the ends
  with ddeg 1 vs 2). So a second sheet was laid in the seat's rim plane (normal 0, -0.186, 0.9825; u = x). On it the top arris is
  the seat's horizon against the floor from the overhead cameras on the far side (1537-1539 for the left edge, 1547-1549 for the
  right) and the face/top tone boundary from the near-side cameras: about 100 deg between the two groups, so the plan
  half-width is the strong direction. Seeds: parts/seat_plan_seeds_{L,R}.json, parts/seat_edge_seeds_{L,R}.json.
- SOLVES (residual rms; photos): left plan 0.66 mm (9), right plan 0.62 (13), left bottom 0.53 (8), right bottom 0.65 (11),
  left top on the side sheet 0.54 (8), right 0.66 (11).
- DESIGN (mean of right and mirrored left), y / top half-width / top z / bottom half-width / bottom z / edge height / lean under:
  110 / 233.0 / 349.5 / 224.0 / 306.9 / 42.5 / 9.0;  200 / 249.5 / 364.9 / 232.6 / 323.0 / 41.9 / 16.9;
  260 / 258.0 / 375.9 / 238.4 / 333.8 / 42.1 / 19.7;  320 / 264.2 / 387.5 / 244.1 / 344.5 / 43.0 / 20.1;
  400 / 268.6 / 403.8 / 251.8 / 358.8 / 45.0 / 16.8.
  Edge thickness square to the seat plane: mean 42.0 mm (41.2-44.3), triangulated, +-3 mm. Bottom plane tilt 10.13 deg.
  Tolerances: top half-width +-1.5, top z +-2.5, bottom half-width +-3.0 (depth-limited, a straight line by construction),
  bottom z +-2.5. The top arris solved twice (plan sheet vs side sheet): z differs 0.8 mm (left) / 0.7 (right) on average;
  half-width 0.4 / 1.2 mean but sd 2.2 / 2.5 (the side-sheet depth is the weak one).
- LEFT vs RIGHT (right minus mirrored left): top half-width +3.8 mm (1.3..6.0), top z -2.3 (plan) / -3.8 (side), bottom z -4.6
  (-7.1..-2.7), bottom half-width 0.0 (sd 2.2). Same sense as the arms (parts/arms.json: both arms 3.6 mm to +x, left 5 mm
  higher). As a rigid roll that would be 0.3-0.5 deg, but solve/metric_frame.json found only -0.09 deg of mirror-plane roll for
  the whole cloud, so it is NOT settled whether the frame is rolled or the seat and arms really sit skew. The design is the
  mean, so on any one side the model is 1-2.5 mm (up to 3.5 at the front of the bottom arris) off the wood. OPEN.
- MODEL v9 (tools/build_model.py, reads parts/seat_edge.json; --legacy skips it):
  - side outline y 110-400 = measured top arris: +1.7 mm mean vs the cloud outline (-0.6..+4.7); beyond the range the cloud
    outline is kept, shifted +0.0 (back) / +4.6 (front) and faded over 60 mm. Half-width at mid 258.9 (v8 257.0).
  - underside = plane through the two bottom arrises: 12.3 / 7.6 / 2.9 mm lower than v8 at y 100 / 300 / 500. Thickness near
    the edge 42.3 / 43.9 / 45.6 (v8 30.1 / 36.3 / 43.2). Least wood under the scoop 20.5 mm (flat underside ASSUMED).
  - side face leans under by the measured amount; in front of y 400 the bottom line is carried straight on for 60 mm.
  - top surface between the dotted region (|x| 251) and the outline tilted to reach the measured top-arris height (the shifted
    cloud polynomial fell up to 5.7 mm short): model top at the outline minus measured arris +0.3 mean (-0.2..+1.9).
  - mesh bug fixed (also in v8): the front wall's top edge was ONE straight line from corner to corner, bridging over the
    thigh hollows of the measured surface. Front and back edges now have a point every 10 mm. This is what made the seat
    outline look wrong from low viewpoints (Joe asked about it during this step); the measured surface itself was never changed.
  - overall box unchanged: 42.62 in high, 24.86 wide, 43.01 long.
- CHECKED BY EYE on single photos (figures/seat_edge/):
  - plan traces on the rectified plan sheet: left on 1538, 1518, 1522, 1509; right on 1548, 1480, 1475, 1472: on the edge
    (1472 wobbles slightly at v 370-410).
  - side traces: left 1507, 1505, 1510 good except 1505 bottom at v > 300 (dark on dark); right 1491 and 1475 good; 1472 / 1470
    bottom line partly wood on wood where the far rocker passes behind (v 150-400), cannot be judged there.
  - raw lines and design lines projected into the ORIGINAL photos: IMG_1491 (right) and IMG_1507 (left): the raw lines sit on
    both arrises; the design lines sit a few mm off, above on the right and below on the left at the bottom arris, in the
    sense the left/right numbers give (half of 2.7..7.1 mm).
  - v8 vs v9 outlines: 1507, 1491: bottom line was through the middle of the edge band, now on its lower edge; 1491, 1472,
    1538, 1548: the outline now follows the front hollows and the horizon of the seat.
- STILL WRONG / OPEN on the seat: the front corners are square in the model and stick out past the front legs (the real corners
  are rounded); the front and back edges are straight in plan (cloud); the section of the edge face
  between the arrises is taken straight (its lower 12-17 mm reads darker in low photos, 4 mm in the high photo 1510: a reflection
  that moves with the camera, so the face curves under; not a third arris); underside between the bottom arrises unmeasured.
- CORRECTION to PLAN.md: "no photo sees the underside" is wrong. IMG_1570, 1572, 1573, 1576 look up at it from close range
  (figures/seat_edge/underside_photos.jpg). Not used yet. M1 and M2 (edge thickness by hand) are now a check on 42.0 +-3, no
  longer a missing number.
- manifest.json: Drive sync picked up 3 new seat-dot photos (IMG_1594, 1596, 1607); not registered, not used here.
- NEXT: (a) seat front corners and front edge in plan from the plan sheet / overhead photos 1545, 1544 (same method);
  (b) arm underside and thickness from the side sheets (parts/arms.json is the crest session's: write a separate file);
  (c) left/right skew: compare rocker and leg heights L vs R to decide roll vs real; (d) underside from 1570-1576;
  (e) register IMG_1588-1593 at half resolution only; (f) M1-M8 if Joe sends them (never block). Templates: the templates
  session (branch `templates`), not here.

## 16:24 PST left/right skew: it is the chair's side frames, not a roll of the frame (main)
- tools/lr_skew.py -> parts/lr_skew.json (NEW file; reads rocker_profile.json, seat_edge.json, arms.json; changes nothing).
- Both rockers' lowest points are on the table: left 0.1 mm at y 183, right 0.4 mm at y 198 (bottom edge there is the top edge
  minus the fitted face height, not a direct trace). A roll of the frame of 0.3-0.5 deg would lift one of them 2.5-4 mm. So
  the frame's vertical is right, and the question "roll of the frame?" from 16:18 is answered: no.
- Right minus mirrored left HEIGHT, line fit in y (y110 / y250 / y400, pitch):
  rocker top +1.5 / -0.1 / -1.8, -0.65 deg;  seat top arris (plan) -0.9 / -2.3 / -3.7, -0.55 deg;  seat top (side sheet)
  -1.7 / -3.7 / -5.9, -0.82 deg;  seat bottom arris -3.6 / -4.6 / -5.6, -0.39 deg;  arm top -0.5 / -2.9 / -5.5, -0.99 deg.
  Three parts, three methods, same sign: the right side is nose-down against the left by 0.4-1.0 deg.
- After taking off the rocker's own difference at the same y, the right seat edge is still 2.0-2.8 mm (top, plan) or 4.3-5.5 mm
  (bottom) lower than the left, and the right arm 2.4-4.4 mm lower: the right seat edge and arm sit lower on their rocker.
- Behind the seat the rockers differ more: right minus left +7.3 at y -200, +8.8 at y -400 (the tails; noted at the start as
  "tail tips differ up to 8 mm").
- READING: the chair as built is slightly racked (or the camera solve is warped by the same amount, which the photos alone cannot
  rule out). The design stays the left/right mean. On any single side the model then sits 1-3 mm off the wood at seat and arm
  height; that is expected, not a tracing error.
- PLAN.md: optional M9 added (table to top of the seat edge behind the front leg, left and right: predicted 3.7-5.9 mm lower on
  the right). It is the one cheap reading that tells the chair from the solve. Not blocking.
- NEXT unchanged: (a) seat front corners and front edge in plan; (b) arm underside and thickness (separate file);
  (d) underside from 1570-1576; (e) register IMG_1588-1593 at half resolution only.

## 16:55 PST seat front edge in plan: scalloped, measured from above (branch seat-front, model v10)
- RESULT (parts/seat_front.json, NEW file; tools/seat_front_fit.py): the seat's front edge is not a straight line. In plan the
  pommel tip is at y 537.0 (x 0), the thigh hollows are deepest at |x| 128, y 514.4, and the front corners are at
  (|x| 268, y 534.2). Scallop depth 22.5 mm from the tip, 19.7 mm from the corners. Model v9 had one straight line at y 513.6.
  Provenance triangulated, tolerance +-2 mm (NOT 1/16 in, see below); pommel tip = seat session dot 108 (measured, +-1.5);
  corners = outline carried 6 mm straight on to the side line (fitted, +-2).
- METHOD (new: tools/tube_tri.py, seeds parts/seat_front_seeds.json; viewer tools/tube_show.py; plot tools/seat_front_plot.py).
  The front edge is rolled over, no arris, so each camera outlines a different line on it. tools/edge_tri.py (one fixed line,
  parallax along one normal) cannot do that. The edge is modelled as a tube (circle of radius r swept along a spine); for each
  camera the outline is where its rays touch the tube; the spine is solved so those outlines match the outline traced in each
  photo on the rectified front sheet (work/parts/seatF/fp, sheet through the front rim). 8 overhead photos: 1545, 1544 (behind),
  1549, 1548, 1547 (left), 1539, 1538, 1537 (right). Seeds by eye on 1545, snap within a 7 mm band shrinking to 2.3 mm.
  Residual rms right 0.39 mm, left 0.50 mm (per photo 0.13-0.75).
- WHAT THE PHOTOS CANNOT TELL:
  - the roll radius: solved free it went negative; fixed at 4, 8, 12 or 16 mm the residual is the same and the plan outline moves
    by under 1 mm (mean -0.25 / 0 / +0.23 / +0.58). Fixed at 8 mm, ASSUMED.
  - height and forward depth: the cameras look at the edge from 0-34 deg round the roll, so the solved top of the roll wanders
    against the seat session's surface (right -3.6..+4.6 mm, left -5.3..+10.7). The plan outline is what is used; heights at the
    front edge in the model still come from seat/surface.json.
  - sensitivity of the plan outline (design, |x| 8-262): roll height tied to the measured seat surface instead of solved:
    moves +0.39 mean, -0.5..+2.0; without the two steepest photos 1539, 1538: +1.13 mean, 0.0..+2.7; without 1545, 1544:
    +2.06 mean, up to +7.4 (the right half beyond x 126 then has one camera group left and is no longer triangulated).
    Hence +-2 mm.
- CHECKS: right minus mirrored left 0.81 mean, sd 1.4, -1.8..+2.4. Five of the seat session's tape dots on the front face
  (91, 94, 96, 100, 109; 11-23 mm below the top; not used in the solve): design outline minus dot +0.03 mean, rms 1.11,
  -1.9..+1.4, so the face is vertical within about 1 mm there. Dot 107 (on the horn, 35 mm below the top) is 4.1 mm behind
  the outline; not counted. Every tape dot on the seat top is inside the outline (smallest margin 1.6 mm, dot 103).
- TRACES CHECKED BY EYE on single rectified photos, both halves, all 8 photos (figures/seat_front/traces_*.jpg): on the edge.
  Two things had to be cut out: 1537 right half beyond u 36 (the steel ruler lies behind the edge and the snap took its marks)
  and 1549 right half u 96-150 (white blob and ruler).
- MODEL v10 (tools/build_model.py reads parts/seat_front.json; --legacy skips it):
  - front outline = the design outline, a point every 8 mm; side from y 400 to the corner straight (hidden in the leg joint).
  - front wall vertical (the side face's lean-under fades out over the last 40 mm).
  - seat depth in y 10.8 .. 537.0 (was 513.6). Top along the front edge: 427.5 at the pommel tip (dot 88, 7 mm behind the tip,
    426.4), 399.7 at x 130, 423.1 at x 260. Front wall height top to underside: 44.3 / 20.5 / 40.6 mm at x 0 / 130 / 260.
    Least wood under the scoop 20.0 mm (was 20.5). Overall box unchanged: 42.62 in high, 24.86 wide, 43.01 long.
- CHECKED BY EYE, v9 vs v10 outlines (figures/seat_front/v9_v10_IMG_*.jpg): 1545 (above), 1549 (left), 1539 (right): the
  outline now runs along the scalloped edge, pommel tip and both corners on the wood.
- STILL WRONG, visible in the figures:
  - IMG_1485 (low, from the front): the model's front wall reaches visibly below the wood. The underside is still one plane
    carried to the front and the front face's bottom edge is not measured (M1). The real seat thins toward the front edge.
  - IMG_1539 / 1538: a dark band outside the outline on the right flank of the pommel (about 5 mm wide at u 20-50 on the sheet's 5 mm grid,
    gone by u 125) and a thinner one at the far horn: the lower part of the front face stands further forward than the top
    edge. Not measured (figures/seat_front/dark_band_IMG_1539_1538.jpg).
- FORMATS: no existing parts file changed. NEW: parts/seat_front.json (design.front_y_of_abs_x = [[|x|, y], ...] every 2 mm,
  0..268; x -> -x for the left), parts/seat_front_seeds.json, parts/model_v10.*. Templates session: the seat blank's front
  outline should now come from parts/seat_front.json instead of a straight line.
- PLAN.md: optional M10 added (straightedge from pommel tip to a front corner, largest gap to the edge in the hollow:
  predicted 21.3 mm). Not blocking.
- NEXT: (a2) front face of the seat: bottom edge and section from the low front photos (1485, 1496, 1484) and the dark band
  in 1539; (b) arm underside and thickness from the side sheets (separate file, not parts/arms.json); (d) underside from
  1570-1576; (e) register IMG_1588-1593 at half resolution only; M1-M10 if Joe sends them (never block).

## 17:33 PST seat front face: rim height and bottom arris measured; CORRECTION of the 16:55 "front wall" claim (branch seat-front-face, model v11)
- CORRECTION. The 16:55 entry, PR #11 and the report to Joe said "the model's front wall reaches visibly below the wood
  (IMG_1485) ... the real seat thins toward the front edge". That was wrong. It came from judging a small preview. Measured
  now: the bottom arris of the front face is at z 381.6 in the hollows and 385.4 beside the pommel tip (design); v10's wall
  bottom was at 379.2-383.2, so v10 was 2-3 mm too LOW at the bottom, not hanging far below, and the front edge heights
  (38 / 21 / 39 mm at pommel flank / hollow / corner) are close to v10's 44 / 20.5 / 41. What v10 really had wrong at the front:
  the rim 2-2.5 mm too low in the hollows, the bottom 2-3 mm too low, a square box at the corners where the wood is rounded.
  RULE kept from this: judge an outline on a zoomed view with the measured LINES drawn (tools/seat_front_lines.py), never on
  a preview; and a silhouette cannot show the bottom arris at all (next point).
- WHAT THE LEVEL PHOTO SHOWS (figures/seat_front_face/underside_mirror_1558.jpg): the underside is glossy and pitched 10 deg,
  so the level camera of IMG_1558 sees it as a bright mirror band (it reflects the slats and the shop) under the dark front
  face. The seat's silhouette therefore runs along the underside further back, well below the arris; the arris is the crease
  between the dark face and the mirror band in 1558 and 1562, and a silhouette against the floor in the higher photos.
- RESULT (parts/seat_front_face.json, NEW file; tools/seat_front_face_fit.py; seeds parts/seat_front_face_seeds.json):
  - top of the rolled edge, height (design = left/right mean): 423.7 at |x| 8, 413.2 at 40, 405.6 at 72, 402.5 at 104,
    402.3 at 136, 404.9 at 168, 412.2 at 200, 422.1 at 232. Triangulated, +-1.5 mm for |x| 70-250, +-3 on the pommel flanks
    and at the corner ends.
  - bottom arris: z 385.4 / 383.5 / 382.3 / 381.6 / 381.7 / 382.3 / 383.3 / 385.6 at the same stations; y 535.8 / 525.5 /
    518.4 / 513.5 / 513.0 / 515.0 / 520.0 / 528.1. Triangulated, z +-1.5, y +-2. Beyond |x| 240 it rounds up into the horn's
    end: 398 at |x| 268, read on the 5 mm grid of rectified IMG_1558 (397-400), fitted, +-3.
  - front edge height (top of roll to bottom arris): 38.4 at |x| 8, least 20.6 at |x| 128, 39.5 at 262; +-2.
  - lean: bottom arris y minus top outline y, |x| < 240: mean 0.0, sd 1.3, -1.7..+2.6. Inside the tolerance of the two
    lines: the face stays VERTICAL in the model. Beyond 240 the bottom reads 2-4 mm forward (rounded corner, both lines weak).
  - plan outline of the top edge from the combined solve minus parts/seat_front.json: mean -0.25, -0.9..+0.7. Inside its
    +-2, so parts/seat_front.json is unchanged (only two notes in it were rewritten).
  - the bottom arris stands 2.2-4.1 mm (mean 2.7, |x| < 240) ABOVE the plane through the two side bottom arrises carried forward.
- METHOD. tools/tube_tri.py can now take photos on several rectified sheets in one solve ("sheets" per photo), with new keys
  y_guess, outward, init, init_top_z, r_bounds (docstring). Regression on the PR #11 seeds: same outline within 0.12 mm.
  - TOP: the 8 overhead photos on the plan sheet plus 6 front photos on a vertical sheet through y 525 (1558 at +4 deg, 1562
    at -7 deg square on; 1531, 1530, 1523, 1524 from the left at -2..-13 deg). The front photos see the top of the roll as a
    horizon, which is exactly the height the overhead-only solve could not fix. Radius 8 given. Rms right 0.80, left 0.82
    (per photo 0.17-1.48).
  - BOTTOM: a line (tube of radius 1) in 9 front photos between -7 and +34 deg: 1558, 1559, 1496, 1562 square on, 1533, 1534,
    1525 from the left, 1485, 1484 from the right. Rms right 0.44, left 0.33 (per photo 0.09-0.86).
  - all traces checked by eye on single rectified photos, both halves (figures/seat_front_face/trace_*.jpg).
- DEAD ENDS AND CUTS:
  - first bottom solve landed on the TOP edge (spine z 400 instead of 383): the start put the spine r0 = 12 mm behind the seed
    while the radius was fixed at 1, and a 7 mm band on a face only 21 mm high reached the roll. Fixed with r0 = 1, band 5.
  - 1526, 1527 (bottom): traces on the wood, but 1.2-2.0 mm below the line the other nine photos agree on, same sign on both
    halves, while 1525 from the same direction fits: camera pose. Left out (variant with them: z moves -0.3..+0.1).
  - 1486, 1487 (top): 2-2.5 mm systematic misfit; they look at the roll from 40 deg below and 55 deg to the side, where a
    circular section is the wrong model. Left out (variant with them: top z moves 0..+0.3, rms 1.0).
  - radius solved freely: wanders 2-12 mm on the right, 3-21 on the left, rms 0.76 / 0.81 against 0.80 / 0.82. Not observable;
    stays 8, ASSUMED. Radius 4 / 12: top z moves by under 1.3 mm, plan outline -1.3 / +1.4 at most.
  - left corner top traced 4-6 mm above the wood on 1558 at first: the start (overhead-only solve) was 8 mm too high there and
    the snap followed the background. Fixed by starting the height from grid readings on 1558 (init_top_z) and band 5.
  - my own overlay crops showed a zigzag "silhouette": cv2.fillPoly on a list of triangles fills by the even-odd rule;
    tools/overlay_sil.py is not hurt (it only draws the outer contour), tools/seat_front_lines.py fills one by one.
- VARIANTS (design lines, |x| 8-262): top z: without 1558 -0.7..+1.7 (|x| > 70: -0.4..+1.7), front photos 1558+1562 only
  -2.2..+0.9, side cameras only -0.6..+2.4, without overhead 1545/1544 -0.5..+0.2. Bottom z: -0.5..+0.6 in every variant
  with radius 1; bottom y: -1.1..+2.6. Hence the tolerances above.
- LEFT/RIGHT: right minus mirrored left: top z -5.4..+2.1 (the outer left is 3-5 mm higher from |x| 200 out), bottom z
  0.0 at the pommel falling to -2.9 from |x| 100 out. Same sense and size as parts/lr_skew.json. Design = mean, so on each
  side alone the design lines sit 1-3 mm off the wood toward the corners; the figures draw both (yellow design, cyan as
  triangulated).
- CHECKS against the seat session's tape dots (not used): the six dots on the right front face all lie between the bottom
  arris and the top (2.9-20.0 mm above the arris); dot y against the right top outline -1.1..+1.8 (107 on the horn: 5.1).
  Thirteen dots on the roll itself: up to x 218 they sit 1.1 mm below the radius-8 tube on average (-2.0..+0.9; a softer
  roll would do that), from x 228 to the corner 2.1-4.0 mm ABOVE the right-hand tube. See OPEN.
- MODEL v11 (tools/build_model.py reads parts/seat_front_face.json; --legacy skips it):
  - the front edge is rolled: three rows of points (top of the roll one radius behind the outline, 45 deg, the plan outline =
    top of the vertical face). Top of the roll at the measured height: 425.6 / 413.2 / 404.5 / 402.2 / 407.1 / 421.5 / 428.9 at
    x 0 / 40 / 80 / 130 / 180 / 230 / 260 (the surface the model had on that line: 426.2 / 411.8 / 402.6 / 400.3 / 405.6 /
    421.8 / 423.5; moved by +1.4 mean, -0.7..+5.3, the +5.3 at the corner). The correction fades out over 30 mm behind.
  - bottom of the front face at the measured arris: 385.4 / 383.5 / 382.1 / 381.6 / 382.5 / 385.4 / 389.4; the underside is
    raised by 2.1-4.7 mm at the front, fading out over 60 mm (ASSUMED shape); bottom corners rounded up beyond |x| 240
    (11.7 mm at the corner, fading over 25 mm, ASSUMED). Front edge height 40.2 / 29.7 / 22.4 / 20.6 / 24.6 / 36.1 / 39.5.
  - least wood under the scoop 17.0 mm (was 20.0: the raised underside near the front). Overall box unchanged.
- CHECKED BY EYE on zoomed crops with the lines drawn (figures/seat_front_face/lines_*.jpg, v10_v11_*.jpg): 1558, 1562:
  bottom line on the crease, top line on the rim in the hollows, both halves; toward the corners the design sits above the
  wood on the right and below it on the left by 2-3 mm (the skew). Side view 1507 and 1491: the front end is now rounded like
  the wood instead of a box.
- OPEN, visible in the figures:
  - in 1558 the MODEL silhouette (white) stands 2-3 mm above the wood at x 180-230 on the chair's right. It is not the rim:
    it is the model's seat surface 30-50 mm behind the edge (vertices near (210, 481) and (180, 491)), i.e. seat/surface.json,
    and v10 shows the same. Together with the dots at x 228-245 sitting 2-4 mm above the right-hand rim: either the dots'
    heights or the right-hand rim are off by about 3 mm near the right front corner. Not resolved (the seat surface is the
    seat session's file). A tape reading table-to-rim at one front corner would settle it; not asked for yet.
  - the dark band in IMG_1539 outside the top edge on the right pommel flank (16:55) is NOT explained: the bottom arris is only
    0-2.5 mm forward there and that camera looks along the face (2 deg behind edge-on).
  - roll radius assumed; pommel tip |x| < 8 and corner ends |x| > 262 not traced; underside itself unmeasured.
- FORMATS: no existing parts file changed format. parts/seat_front.json: two note strings only. NEW: parts/seat_front_face.json
  (design.top_of_roll_z_of_abs_x, design.bottom_arris_y_of_abs_x, design.bottom_arris_z_of_abs_x: [[|x|, value], ...] every
  2 mm, |x| 8-262; design.bottom_arris_z_of_abs_x_with_corner adds |x| 268), parts/seat_front_face_seeds.json,
  parts/model_v11.*. Templates session: the seat blank's front outline is still parts/seat_front.json; the blank must be at
  least 40 mm thick at the front (38.4 measured beside the tip, 40.2 in the model at the tip); the bottom arris is under the
  top edge within 2 mm, so one outline serves both faces. The first top solve's start file (work/parts/seatF/tube/front*.json)
  is the gitignored output of the PR #11 solve: run that first to reproduce.
- TOOLS: tools/seat_front_lines.py (measured lines on an original photo), tools/seat_front_face_plot.py,
  tools/before_after.py --stack (one above the other, nothing shrunk).
- NEXT: (b) arm underside and thickness from the side sheets (separate file, not parts/arms.json); (c) the 3 mm question at
  the right front corner: seat surface near (180-230, 480-500) against the level photos 1558 / 1562 / 1559 (horizon check),
  report to the seat session; (d) underside from 1570-1576; (e) register IMG_1588-1593 at half resolution only; M1-M10 if
  Joe sends them (never block).

## 17:45 PST plan change (phase 5b) and two-session split; audit PRs #12 and #14 landed; model v12 (branch joinery-merge)
- JOE (in the joinery / audit session, 17:20-17:26, his words): "I want everything perfect before we make the templates";
  known flaws are fixed before the critique loop; the hub (this session) "remains the central hub that works until completion",
  the other session fixes the things he pointed out in the audit. To the hub, 17:36: that session is subdividing the work,
  "ensure we don't clash and we can collaborate effectively".
- The audit session's hand-over message never arrived (sessions cannot message each other here); read from its transcript and
  ACCEPTED as written. PLAN.md now has phase 5b (known fixes and joinery), 6b (tape checks), 6c (finish detail) ahead of
  templates, and a section "Sessions and who owns what" with the owner table, the 5b checklist and seven rules (model numbers
  only from the hub; one PR per fix from current main; PLAN / LEDGER edited only by the hub; say so before editing the other
  session's block of build_model.py, or hand over data; formats stable; one compute job at a time).
- HAND MEASUREMENTS wording changed: model work, the critique loop and draft templates never wait for them; the FINAL template
  sign-off waits for M1, M3, M4, M5, M9, M11 (phase 6b). M11 is new (one Domino end and the leg thickness across); the joinery
  session has since read the Domino ends off true-scale leg-face views (25-26 x 11-11.5 mm, taken as a 10 mm Domino 24 x 10,
  parts/dominos.json), so M11 is a check. To confirm with Joe: his earlier instruction to the hub was "never block on them".
- MERGED: PR #15 (seat front face, v11, 9eb0cd0). PR #12 (audit report, squash b048fbc). PR #14 (back leg as one board +
  Domino ends) could not be merged as it stood: after #12's squash it conflicted in tools/audit_bleg.py (added on both sides,
  edited later on joinery). Landed instead through branch joinery-merge = main + joinery 3f913f1, that one file taken from
  joinery, plus model v12 and this entry; #14 closed with a pointer. Lesson, now rule 2: after a squash, merge main into the
  branch before stacking more work on it.
- TRIAL BUILD before merging (rule 3): main + joinery against v11: BLEG_L / BLEG_R changed (267 of 480 vertices moved, largest
  16.9 mm to the nearest old vertex), the other 11 parts vertex-identical; overall box unchanged.
- MODEL v12 = v11 + back leg as one board (joinery session's code, tools/build_model.py, "one_board" in the report): one
  smoothing spline per outline through the measured stretches only (front z <= 270.1 and >= 607.8, rear z <= 261.1 and >= 607.8);
  fit to the measured lines rms 0.08 / 0.05 mm, largest 0.40 / 0.21 (front / rear). Fore-aft width in side view at z 300 / 450 /
  600: 48.5 / 46.6 / 36.7 (v11 48.7 / 47.5 / 36.2). Between z 265 and 608 the leg is NOT measured: a smooth guess, tagged so.
- CHECKED BY EYE (figures/joinery/v11_v12_back_leg_1507.jpg, _1527.jpg, zoomed crops of 4032 px overlays): v11's steps in
  the outline at seat height are gone; in 1527 the outline follows the near leg past the arm joint on both edges. In the level
  side view 1507 the two legs overlap in the picture, so the fit inside the unmeasured band cannot be read there.
- ASSEMBLY CHECK baseline on v12 (tools/audit_joints.py, the joinery session's tool; nothing fixed yet): legs float above the
  rockers by 0.8 mm (front) and 1.8 mm (back); SEAT not watertight (every seat pair unmeasurable by boolean); arm into back
  leg 4.1 mm / 2.26 cm3; back leg into crest 3.6 mm / 4.28 cm3; slats into crest 14.8-15.0 mm (20.5 / 11.6 cm3).
- FORMATS: no parts file changed format. NEW: parts/dominos.json (joinery session's file), parts/model_v12.*.
- OPEN INTERFACE (PLAN rule 5): the cut of the seat's side edge at the back leg sits in the SEAT outline (hub's block). Waiting
  for the joinery session's choice: the cut line as data for the hub to apply, or its own marked block after the seat is built.
- NEXT (hub): (b) arm underside and thickness from the side sheets (new file); (c) the 3 mm question at the right front corner
  of the seat; (d) seat underside from 1570-1576, then close the SEAT mesh (the joinery checks need a watertight seat: do this
  early); (e) rocker bottom edge traced directly; (f) seat side edge behind y 400; (g) register IMG_1588-1593 at half
  resolution. At the start of every turn: pull main, read open PRs and their comments, trial-build and merge what the joinery
  session left open, issue the next model number.

## 17:52 PST seat mesh closed; model v13 (main, small fix)
- The SEAT mesh had 28 open and 76 three-faced edges, all along the scalloped front top edge (audit PR #12: "not watertight").
  Cause: tools/build_model.py kept a Delaunay triangle when its centroid was within 0.5 mm of the outline polygon; in the
  hollows of the front edge Delaunay puts a thin fan of triangles OUTSIDE the outline, and part of that fan passed the test.
  Fix: centroid strictly inside the polygon, zero-area triangles dropped.
- Model v13: all 13 parts vertex-identical to v12; the seat has 48 fewer faces, is watertight with consistent winding, volume
  8507 cm3. New in the report: parts.seat.mesh_closed, parts.seat.mesh_volume_cm3. --legacy still builds.
- For the joinery session: the seat is a solid now, so tools/joinery.py's repair step has nothing to do and booleans on SEAT
  work directly. `git merge main` to get it.
- PLAN 5b: [x] SEAT mesh closed.
- NEXT (hub): seat underside from IMG_1570/1572/1573/1576; arm underside and thickness; then the rest of the 17:45 list.

## 18:00 PST joinery PR #17 landed; the build is now three steps; model v14 (main)
- PR #17 (joinery session, squash 78dee09): `tools/joinery.py`, a step AFTER the build that cuts the joints into the finished
  parts: front legs lapped on the seat edge with a through-Domino, back legs butted with the Domino across the joint, feet
  carried 5 mm down and cut to the rocker tops, arm and crest coped to the legs, slat mortises in seat and crest. It also made
  `tools/audit_joints.py` lighter (KD-tree distances; 1.5 GB peak, 25 s on v14).
- Trial before merging (main 463eee1 + its branch 276ddcf): joinery on v13 ran in 1 s; ROCKER_L/R and the three slats came out
  vertex-identical, every other part changed only at its joints; all 17 parts closed solids; overlay on IMG_1519 checked by eye.
- Hub's integration: `tools/model.sh --out parts/model_vN` now runs build -> joinery -> assembly check and prints PASS / FAIL
  through the new `tools/joints_gate.py` (every part a closed solid; each joint pair touching with at least 3 cm2 of contact
  face and under 0.05 cm3 of overlap; arm / seat, slat / back leg, slat / slat clear by at least 5 mm).
- FILES (new convention, PLAN rule 8): `parts/model_vN.glb` is the joined chair (what the viewer shows; 17 parts, four of them
  new: DOMINO_FR, _FL, _BR, _BL). `parts/model_vN_shapes.glb` is the parts as traced, before the joints; compare versions on
  that file. `_params.json` and `_edges.json` describe the shapes; `_joinery.json` lists every cut with the volume removed;
  `_joints.json` is the assembly check. No `parts/*.json` format changed.
- v14: shapes identical to v13 (byte-identical file). Assembly check PASS: 17 joint pairs in contact (contact faces 6.2 to
  60.6 cm2, largest overlap 0.01 cm3 at the Dominos), 3 clearance pairs clear (28 to 134 mm). Seat loses 14.3 cm3 at each
  front-leg lap and 56 cm3 at each back-leg butt.
- Viewer: a 'Dominos' chip and labels added (viewer/app.js, viewer/cloud.js; two lines).
- One oddity, not chased: the first run of the new model.sh reported 'assembly check failed to run' although the same command
  passed by hand and on the rerun; the step logs now go to work/logs/ so the next occurrence can be read.
- Told to the joinery session in a PR #17 comment: its report line 'seat mesh closed with pymeshfix' is now printed although
  nothing is repaired (the seat is a solid since v13); and the four open points of its PR stay on its list.
- NEXT (hub): seat underside from IMG_1570/1572/1573/1576; then arm underside and thickness; then the rest of the Now list.

## 19:05 PST joinery PRs #18, #19 -> model v15; seat side edge is a square edge over a scooped 46 degree bevel -> model v16 (PR #20)
- FOUND ON MAIN at 18:47: the joinery session had merged #18 (arm / front leg: the oval on the left arm is not a tenon; hidden
  10 mm Domino, assumed; `parts/joints.json`, new parts `DOMINO_AR/AL`) and #19 (feet swept along the leg axis and cut flat to
  the rocker; Joe had spotted the step at the feet in v14) without a model file, as rule 3 allows.
- v15 (5f81628): shapes vertex-identical to v14; assembly check PASS, 19 pairs touching, 3 clear. The first build DIED in the
  check: `safe_run: KILLED, memory 3379 MB over 3 GB cap`. Cause: #19's exact-gap step ran `closest_point` on the three pairs
  that stand well clear (28 to 134 mm), which pulls in much of the other part's triangles per sample. Hub's edit in the joinery
  session's file `tools/audit_joints.py` (told in a comment on #19): refine only when the KD-tree gap is under 3 mm. Peak is
  still 2.7 GB of the 3 GB cap. This is probably also the 'assembly check failed to run' oddity of the 18:00 entry.
- Contact areas in the check are 3000 random samples times the part's area: they move by several cm2 between builds without
  the joint changing (FLEG_R~SEAT 36.0, 28.8, 33.8 in v14, v15, v16). Not a measure of change; told to the joinery session.
- SEAT SIDE EDGE (hub item d; PR #20, squash 3c904d8; all numbers RIGHT side, chair frame, mm):
  - Section between the legs: top arris (eased) -> vertical edge face -> hard line -> flat under-bevel -> bottom arris ->
    underside. v15 had one straight wall from top arris to bottom arris: 10.4 mm inside the wood at the hard line at y 250,
    up to 11.3 mm along the edge.
  - Under-bevel angle 46.2 deg below horizontal (sd 0.44; 45.75 to 47.3 over y 150-410; the two edges solved separately).
  - Hard line height above the underside: 0 at the tips (back y 89.7, front y 456.4: straight continuation, fitted), 24.4 at
    y 255 (bevel 23.4 wide there). Table every 5 mm in `parts/seat_scoop.json`.
  - Edge face vertical: hard line x minus plan-sheet top arris x = +0.39 mean, sd 0.78, -1.38 to +1.16 (y 110-400). Face
    height 17.8 at mid-length to 37.9 near the legs (soft: eased arris).
  - Underside along the edge: straight, tilt 10.6 deg, rms 0.24, worst 0.97 (bottom arris y 140-440).
  - Hard line: 14 photos, camera elevation -30 to +72 deg; rms per photo 0.23-1.69 for 13 photos, IMG_1490 2.83;
    leave-one-photo-out 0.78 away from the ends, 3.52 at the back end (leans on IMG_1492). Bottom arris: 8 photos, rms
    0.12-0.85 for 7, IMG_1490 1.50; leave-one-out 1.23 inner, 2.31 at the ends. IMG_1490 is off both the same way: its pose.
  - New bottom arris against the old one in `parts/seat_edge.json` (right): -1.27 to +1.44 in x over y 150-300; toward the
    front the old one is up to 15 mm too far in (side photos only; the real arris swings out to close the lens).
- METHOD (tools/seat_scoop/, four steps): `strip.py` unrolls the edge per photo (column = station y, row = across the edge;
  `ALT="dx0 dz0 dx1 dz1"` unrolls across a line through the top arris, needed for steep photos that look along the edge
  face); `snap.py` snaps by-eye seeds to the tone edge; `solve.py` fits x(y), z(y) (Legendre degree 6) to all photos at once;
  `fit.py` writes `parts/seat_scoop.json`. Check figure: `overlay_edge.py` (model feature edges + measured dots on a photo
  crop). Inputs (seeds, traces, trusted stretches per photo) in `tools/seat_scoop/inputs/`.
- LESSONS: (1) low photos alone cannot place an edge in depth (leave-one-out 6-34 mm); the three photos from 31-38 deg above
  and six steep silhouettes fixed it. (2) The residual's px-per-mm must be taken square to the line of sight; taken along
  the old wall it made the steep photos look 3-9 mm off when they fit to 0.2-1.7. (3) The close-ups IMG_1570-1576 are
  registered too badly to measure with; none is used. (4) The 'dark band in IMG_1539 = reflection, not a third arris' note
  in `parts/seat_edge.json` was a misreading: it is the vertical edge face seen from above. (5) A wall ring that jumps in
  height between two stations makes a sliver on a tilted plane and a stray edge in the overlays; run it out into the next
  arris instead.
- FORMAT NOTE (PLAN rule 9): new file `parts/seat_scoop.json`; `parts/seat_edge.json` unchanged, but its
  `design.bottom_half_width_of_y` is not used while the new file exists. Outside the lens the seat's side edge is now
  vertical for the full thickness (it leaned under before), also where it meets the legs.
- v16 (main): only SEAT differs from v15 in the shapes. Assembly check PASS; every part watertight. SEAT after the joints
  8342.0 -> 8513.4 cm3. Seat / leg pairs still gap 0, overlap 0 (contact 33.8 and 59.1 cm2).
- VISIBLE MISFIT, explained, not fixed: on right-side photos the model's seat edge lines sit inboard of the measured dots:
  hard line within 0.7 mm in x at y 113-155, 2.1 to 3.4 mm inboard at y 195-400, 4.2 at y 438; 1.9 mm high at the back to
  0.8 low at the front. v15 has the same offset on its lines. The model is the left/right mean; the right side measures
  wider (half-width 258.9 against 255.2 at y 250) and lower (`parts/lr_skew.json`). Either the seat is 3.7 mm lopsided or it
  sits off the frame's centre line: that is the '3 mm question', which now has this lead.
- OPEN on the seat edge: left side assumed mirror (no trace from below); tips of the lens fitted, not traced; top arris
  radius; underside flat ACROSS by the undistorted reflection in IMG_1492 only; V-shaped creases on the seat top at y 205-230
  where the taped surface's edge (x 250) runs into the outline (cosmetic, in v15 too).
- JOE, 19:00: three new photos in Drive (IMG_1618, 1619, 1620; manifest updated, 123 files listed) and a fix list for after
  v16, copied into PLAN.md: Dominos missing at the back of the chair (IMG_1620 shows two Domino ends on each back leg, at the
  seat and at the arm); rocker ends not shaped right (IMG_1618 slim rounded tail tip, IMG_1619 round nose at the front);
  front-leg Domino off-centre on the leg (viewer screenshot). Then the rest of the plan as written.
- NEXT (hub): Joe's list item 1 (back Dominos: register IMG_1620 at half resolution, read both Domino ends on each back leg
  on true-scale leg-face views, add the arm / back-leg Domino in `parts/joints.json` + `tools/joinery.py`, small named edit),
  then 2 (rocker ends from the existing rocker face sheets plus IMG_1618/1619 for the shape), then 3 (front-leg Domino
  position against the leg's two edges). Then the 3 mm question, the left-side scoop check, arm underside, rocker bottom
  edge, seat edge behind y 400.

## 19:25 PST back Dominos measured (three ends per back leg); the seat's back edge is wrong; IMG_1618-1620 did not register (branch back-dominos, nothing built yet)
- JOE, 19:20: "it looks like the back of the seat isn't modeled correctly. The top, front, and sides are pretty accurate but
  not the back edge (just noting something that you should handle at SOME point)". Added to PLAN.md as item 4 of Joe's list.
- REGISTRATION: `tools/seat_register.py` (SIFT against the descriptor bank, PnP; no COLMAP) on IMG_1620, 1619, 1618: 0 inliers
  each, all three FAILED (close-ups against a bank made from whole-chair photos). Not needed for item 1: the registered
  photos from behind show every Domino end. Item 2 (rocker ends) needs another route.
- NEW TOOL `tools/rear_ortho.py`: orthophotos of each back leg's REAR face in two windows (seat joint, arm joint), on the
  plane fitted to the model leg's rear face there (fit 0.34-0.35 mm rms), 10 mm grid; writes the planes. Peak 588 MB, 4 s.
- WHAT IS THERE (item 1): each back leg shows THREE Domino ends. (a) outer face at the seat: the one modelled (`DOMINO_B*`),
  confirmed in IMG_1508. (b) REAR face at seat height, across the seam between the leg's inner face and the seat's back
  edge. (c) REAR face at arm height, centred across the leg: through the leg into the arm's end.
- (b) rear, at the seat. Visible end 24.5 x 10.5 mm on the left (IMG_1578 close-up and IMG_1501: tips at plane u +7.6/+31.3
  and +7.5/+31.4, height 10.3-10.5), 24.8-26.8 x 9.9-10.0 on the right (its seat-side tip is dark on dark: soft). Level
  within about 3 degrees. Leg-side tip, triangulated from 4 photos (left) and 3 (right), ray misses 0.16-0.71 mm:
  L [-199.6, 33.7, 313.6], R [199.5, 32.9, 313.5]; 1.3 and 0.6 mm in front of the model leg's rear face. Seam (leg's inner
  face / seat) read at u +22.2 on the left and -21.2 on the right, i.e. 14.5 mm (L) and 13.9 mm (R) of the Domino end is in
  the leg, about 10 mm in the seat. With a 24 mm Domino: centre |x| 187.55, z 313.55, on the rear face.
- (c) rear, at the arm. Visible end 23.5 mm (L) and 23.1 mm (R) tip to tip, 9.9-10.4 high: a 10 mm Domino. Tips triangulated
  from 5-6 photos each (ray misses 0.27-1.17 mm, one 2.18): centres L [-210.6, -1.4, 476.9], R [212.0, 0.2, 476.7]. The model
  leg's rear face is centred on x 211.2 there: the Domino is centred on the leg's width. Points sit -0.7..+1.7 mm off the
  model's rear face. A Domino driven in square to that face (17.5 degrees up from level) comes out of the leg's front face at
  z 492, the middle of the model arm's end (z 480-508 there): consistent with the arm as modelled.
- LEG NOTE for the joinery session (their part, not changed): at seat height the seam leg / seat sits 3.4 mm (L) and 2.5 mm (R)
  inboard of the model leg's inner face at the rear.
- SEAT BACK EDGE (hub's part, WRONG in v16): model back edge straight at y 10.8 (cloud, 1st percentile), 21 mm behind the
  leg's rear face (y 31.8 at z 322), with a slanted corner (-202.3, 10.8) -> (-210, 31.8) that wraps behind the leg. Photos:
  the seat's back edge is flush with the leg's rear face at the joint (Domino (b) lies flat across both); cloud: rearmost y
  about 0-10 near the centre line, 25-31 at |x| 160-200, so the edge bows backward in plan. To be traced (top and bottom
  arris) before the rear Dominos are cut in.
- NEXT: (1) seat back edge: rear sheet + plan sheet, tools/curve_tri.py, into `tools/build_model.py` SEAT (own PR);
  (2) rear Dominos (b) and (c) in `parts/joints.json` + `tools/joinery.py` + the audit's pair list (small named edits; PR);
  model v17; then items 2 and 3.


## 20:15 PST seat back edge (PR #21) and rear Dominos (PR #22) merged; MODEL v17 on main
- SEAT BACK EDGE (Joe's item 4; PR #21, `parts/seat_back.json`, `tools/seat_back/`): three edges triangulated from 12 photos
  from behind (rear sheet, plane y 30): top arris (11 photos, rms 0.21-1.11 mm, leave-one-out <= 0.61 mm y / 0.15 z), hard
  line (7 photos, 0.71-1.13, <= 0.58 y / 0.49 z), bottom arris (10 photos, 0.16-1.23, <= 1.68 y at the ends, 0.74 inside).
  Section: sharp top arris, back face leaning forward going down by 10.5 deg (sd 0.6), hard line, under-bevel 45.8 deg
  (sd 0.6; sides: 46.2), bottom arris on the same underside plane as the sides (-0.44..+0.09 mm). Plan: a bow, top arris
  y -3.7 on the centre line, 28.5 at |x| 180 (32.2 mm), meeting the leg flush (y 31.5 at |x| 188; leg's rear face 30.2).
  Lens 16.6 mm on centre, 9.6 at |x| 120, 1.5 at 165, tip 173.5 (fitted).
- v16 was wrong there: straight edge at y 10.8 (14.5 mm too far forward on centre, 17.7 too far back at |x| 180, running on
  behind the legs), vertical, and the top climbed to 351.1 at (0, 14) (cloud polynomial pulled up by the slats' feet;
  measured arris 324.8, new top there 327.4). Sparse cloud on the strip behind the dots (189 points): cloud minus model
  median -2.52 / rms 7.56 in v16, +0.94 / 2.85 now.
- In `tools/build_model.py` SEAT: back outline = the bow (x -192..192); side outline starts at y 45 inside the leg; top
  behind the dots (y < 64) = ruled strip from the arris to the measured surface (fitted); underside's back edge moved to the
  bottom arris; one wall ring on the hard line inside the lens. Only SEAT changed against v16 (648 vertices, max 18.0 mm).
- DEAD ENDS: tilting the old cloud polynomial to the arris (it was 35 mm high on the new edge line: gave a hollow); a
  re-entrant corner in the outline (12 open edges; the corner is inside the leg, closed with one straight line).
- OPEN (seat back): bottom arris depth L/R differ up to 4.8 mm at the ends (weak direction); hard line's left half 1.1 mm
  lower on average (to 1.6): design = mean, visible on IMG_1502; lens tips and the last stretch to the legs are straight
  continuations; top arris drawn sharp; IMG_1542's outline sits 1.9 mm off the hard line on the right half.
- REAR DOMINOS (Joe's item 1; PR #22, `parts/joints.json` `back_leg_rear`, `tools/joinery.py` step 5c, `tools/rear_ortho.py`,
  `tools/rear_dominos/`): `DOMINO_RS*` at the seat seam (centre |x| 186.8, z 313.55 on the rear face, 24 x 10, 25 deep,
  level) and `DOMINO_RA*` at the arm (centre |x| 211.3, z 476.8, through the leg 45.5 mm + 25 into the arm's end). Direction
  (square to the rear face) and depths ASSUMED. Centre of the seat one: first tip minus 12 (187.55), then centred on the
  visible end (24.6 in the close-up IMG_1578, to 26.5 in distant photos): 186.5-187.3, 186.8 taken.
- Checked on IMG_1502 and IMG_1501: the arm ends sit on the ovals; at the seat the photo's end runs 1-2 mm further into the
  seat than the model's (soft rim on the seat side), and the model leg's inner face is 2.5-3.4 mm outboard of the real seam
  (leg placement, joinery session), so 10.8 mm of the model Domino's end is in the leg against about 14 in the photos.
- AUDIT: `tools/audit_joints.py` inside test in slices of 250 points (the first new pair was killed at the 3 GB cap: 3000
  rays x 800-1900 candidate triangles in one call); whole check now peaks at 1.4 GB. JOINERY: the rear face must be fitted on
  the leg AS TRACED (after the side Domino's mortise is cut its back wall also looks backward: 5.6 mm rms).
- MODEL v17 = main after #21 and #22: `tools/model.sh --out parts/model_v17`, every part closed, assembly check PASS (26
  pairs; new: DOMINO_RSR~BLEG_R 9.9 cm2, ~SEAT 11.2, DOMINO_RAR~BLEG_R 32.5, ~ARM_R 21.1).
- NEXT: Joe's item 2 (rocker ends: IMG_1618 tail tip, IMG_1619 front nose; both unregistered close-ups, so start from the
  registered photos that show the rocker ends and the rocker face sheets; a manual PnP of 1618/1619 at half resolution only
  if those are not enough), then item 3 (front-leg Domino centring on the leg face, `tools/domino_ortho.py`), then the 3 mm
  question at the seat's right front corner, left-side scoop check, arm underside (new file), rocker bottom edge, seat side
  edge behind y 400.

## 21:19 PST rocker ends (PR #23) merged; MODEL v18 on main
- ROCKER ENDS (Joe's item 2; PR #23, `parts/rocker_ends.json`, `tools/rocker_ends/`: ortho -> trace -> fit -> trace with the
  first fit -> fit). v17 cut both ends square (u -480, face 19.9 mm high; u 620). Measured, design = left and right averaged:
  tail tip at u -488.17 (face 22.8 mm high 80 mm from the tip, 19.7 at 40, 14.2 at 20, 9.6 at 10, 6.6 at 5); nose top corner
  at u 626.65, the end 4.05 mm proud of it (u 630.70), one large rounded lower corner. Tip to nose top corner 1115.7 mm,
  overall 1118.4. Only ROCKER_L / ROCKER_R changed against v17 (945.5 cm3 each, closed); assembly check PASS.
- PER END (photos used; slide between photos sd along / across, largest; rms per photo after its slide; spread between photos
  median, p90): left tail 12 of 12; 5.44 / 2.46, 10.07; 0.18-0.55; 0.30, 0.66. Right tail 11 of 11; 2.66 / 1.05, 4.83;
  0.19-0.52; 0.30, 0.59. Left nose 18 of 18; 3.59 / 2.38, 7.79; 0.19-0.58; 0.34, 0.61. Right nose 12 of 14; 1.52 / 1.49,
  3.51; 0.15-0.59; 0.20, 0.42 (32 mm of its outline bridged by hand over a white scuff and a worn arris). A further round
  moves the outlines, after a common slide <= 0.6 mm, by 0.06-0.10 median, 0.12-0.22 p90, 0.26-1.04 max (left tail tip).
- METHOD THAT HELD: coarse slide of the seed onto each photo (photos sit up to 10 mm apart at the chair's ends: pose error,
  not parallax), seed for the final round from the all-photo median of "unlike the face" cut at level 5 of 8, points
  dropped where a camera looks onto the neighbouring surface, weights that make a tail say where it is ALONG the rocker.
- DEAD ENDS: iterating the fit's own outline as the next seed (tip wears away, or bumps grow to 4 mm loops); snapping
  without the colour-gradient step (0.2-0.6 mm inward); median level 3.5 (wanders through the pale eased arris under the
  right tail); two-number registration of an end to the old profile (ill-conditioned; one number square to the top edge).
- DESIGN: each side's end slid square to its top edge onto `mean_top` (left tail -0.06 / -0.27, right tail 0.38 / 1.73,
  left nose -0.28 / 0.63, right nose 1.06 / -2.35 mm), averaged, faired over 12 mm (<= 0.18 mm), blended into the old profile
  over u -330..-400 and 572..590. Nose meets the old profile within 0.4 mm.
- OPEN: (1) left rocker 1118.6 mm tip to nose top corner, right 1112.3 (each about +-2): tail tips differ 5.89 mm along u
  in the right_vs_left frame, nose corners 0.82; design = mean, so 2.9 mm off either tail tip. Tape check M8 per rocker
  would settle it. (2) Tail face height at u -320: traced 26.4 left / 26.0 right, old profile 27.7 (fitted height); traced
  bottom 0.8-1.5 mm above the old one across the blend zone. Belongs to "rocker bottom edge traced directly". (3) Shape gap
  left / right away from the tips: tail top 0.89 mean / 2.76 max, bottom 0.83 / 1.74; nose top 0.25 / 1.10, bottom
  0.69 / 2.53. (4) Eased arrises (tone edge traced; radius not measured), ends square across, photos slid not turned.
- TEMPLATES SESSION: `parts/rocker_profile.json` alone is now the OLD square-cut rocker; add `parts/rocker_ends.json`
  `design` (PLAN ownership table).
- MODEL v18 = main after #23: `tools/model.sh --out parts/model_v18`, identical to the trial build of the branch.
- HUB HAND-OVER (Joe, this evening: "after it lands continue working unsupervised but do all the remaining work including
  supervision in opus 5.5"): the hub could not start a new session itself (only Sean's sessions can). `HUB_HANDOFF.md` is the complete brief; until
  Joe switches the hub session to Opus 5.5 or starts a new one from that file, the hub gives each remaining item to an
  Opus 5.5 worker, one at a time (PLAN "Sessions and who owns what").
- NEXT: Joe's item 3 (front-leg Domino centring on the leg face, `tools/domino_ortho.py`; `parts/dominos.json` is the
  joinery session's: small named edit), then the 3 mm question at the seat's right front corner, left-side scoop check, arm
  underside and thickness (new file), rocker bottom edge u -330..572, seat side edge behind y 400.

## 21:49 PST front-leg Domino centred on the leg face (PR #24); MODEL v19 on main
- FRONT-LEG DOMINO (Joe's item 3; PR #24, `tools/front_domino/`, figures `figures/front_domino/`). Run on Opus 5.5. Straightened
  orthophotos of each front leg's outer face (0.1 mm/px, sheared by the leg's lean 0.185 so the edges stand vertical); Domino
  end by a matched filter from eye seeds; arrises by the strongest tone step within 4 mm of a seed, in a band below and one
  above the Domino; each reading checked on single photos at 10 px/mm. Used if view <= 50 deg, fit score >= 6, the two bands
  agree within 1.5 mm.
- RESULT (Domino centre minus the middle of the two arrises, + = toward the leg's front): left -0.29 (n 7, sd 0.88), right
  -0.74 (n 12, sd 0.61), both -0.58 (n 19, sd 0.73, se 0.17). All 27 photos: left +0.61 (n 13, sd 1.25), right -0.69 (n 14).
  Arris to arris: left 41.26, right 38.13 (40.26 on the 5 square-on right photos); model flat face 40.39.
- CAUSE: the v12 centre sat at u -6.22 on the face plane = the middle of the leg's whole section (-28.57..+16.08, middle -6.24,
  including the slanted rear face), not of the flat outer face (-24.40..+15.99, middle -4.20). Most likely cause; the
  original reading figure does not say which edges were used.
- CHANGE: `parts/dominos.json` front_leg centre_xyz [-284.2, 466.7, 394.8] -> [-284.4, 468.2, 394.8] (+1.52 mm along the
  face, design = mean of the legs, -0.515). Joined end vs the flat face's middle: v18 -2.07, v19 -0.55 (both legs).
- MODEL v19 = main after #24: `tools/model.sh --out parts/model_v19`, assembly check PASS, identical to the branch trial build
  (all 23 joined parts). vs v18: `_shapes.glb` all 13 parts vertex-identical; joined: DOMINO_FL/FR (+1.5 mm y), FLEG_L/R and
  SEAT (mortises; SEAT -0.011 cm3), ARM_L/R and DOMINO_AL/AR (the hidden arm/front-leg Domino moved 0.2-0.4 mm: joinery.py
  5b places it at the centroid of an even surface sampling of the leg, which shifts when the leg mesh changes; sampling noise).
- OPEN: (1) height not changed: right-leg photo sets disagree by about 7 mm (1469-1477 fit v 11.8-14.8, 1488-1490 v 19.1-24.6,
  model 19.2); left photos v 15.6-20.4. (2) tilt not changed (15 deg): fits 12-18 deg, 8 deg on 1488-1490. (3) for the joinery
  session: the arm/front-leg Domino's position depends on mesh sampling (5b), 0.2-0.4 mm jitter per rebuild of the leg.
- NEXT: the 3 mm question at the seat's right front corner (LEDGER 17:33 and 19:05), then left-side scoop check, arm underside
  and thickness (new file), rocker bottom edge u -330..572, seat side edge behind y 400.
