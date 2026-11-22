# Templates workstream ledger (phase 7)

Branch `templates`, worktree ../rocking-chair-templates. The coordinator owns main, seat, legs and tools/build_model.py;
this workstream only adds files under templates/ and figures/templates/ and reads parts/*.json. Read PLAN.md first.

Rebuild everything: `templates/build.sh`. Kit: templates/tplkit.py (spec in mm -> tiled Letter PDF with assembly map,
0.5 in overlaps, 1 in registration crosses on a global grid and a 2 in check square on every page; single-sheet 1:1 PDF;
R12 DXF in mm with layers CUT/REF/MARK/DIM/TEXT; preview PNG).

`work/` in this worktree holds symlinks into the coordinator's work/ (solve, sheets, parts, dense, masks, toolkit, frame):
read only. NOTE work/toolkit/rk.sh cds into the COORDINATOR's tree; use it only with absolute paths and never to write.

## State
- [x] 1. Rocker template + two-part bending form: PR #6, squash-merged ddca1fe (16:45). Local main NOT touched (coordinator's ref).
- [x] 2. Slats: flat outlines (centre x1, outer x2) + one two-part bending form for all three (PR, this entry)
- [ ] 3. Leg side profiles (parts/side_frame*.json), crest, arms, seat outline when the coordinator has one

## 2026-11-20 16:00-16:40 rocker
- Profile = parts/rocker_profile.json mean_top / mean_bot (u -480..620). Ends were never traced: fitted by eye on 5 mm
  gridded zooms of rectified single photos (templates/rocker_ends.json). Rear nose tip (-484.5, 170.0); front end plumb at
  u 630 with a 15 mm lower round.
- ROADBLOCK: first fit had the front end at 628 with r 10. The overlay showed wood 2-3 mm past the end on all four photos
  (L 1507/1506, R 1472/1471) and a bigger lower round; read the corner at 629.5-630 (L) and 630-632 (R moved into the L frame
  with right_vs_left). Fixed to 630 / r 15. Nose tip moved in 1 mm (R 1472 showed it proud).
- Leg landings: the four lower leg lines of parts/side_frame.json, line fit over their lowest 80 mm, extrapolated 10-31 mm
  down to the rocker top: back leg 32.5..66.8 (34.3 wide), front leg 539.1..565.9 (26.8 wide) along u. On the photos the marks
  run on the leg faces (figures/templates/rocker_overlay.jpg).
- Numbers: overall 1114.5 mm (43 7/8"); face height 28.5 max, 19.9 at the tail tip; rocking radius 1066; bottom curve
  reverses 432 mm behind the rest point (an S), so the form is two-part (lower form = rocker bottom, caul = bottom offset by the
  stack). Tightest bend 344 mm (tail, convex). Lamination plan 10 x 1/8" = 31.75 mm stack is a suggestion (`--stack-mm`).
- Checks: overlay on 4 rectified single photos, by eye: both edges, nose, front end and leg marks on the wood. Every check
  square in both tiled PDFs measures 144.0 x 144.0 pt (pymupdf); DXF reads in ezdxf, CUT outline length 1114.5 mm.
- Delivery: no R2 uploader on CB; PDFs committed under templates/out and linked from GitHub (private repo, Joe's login).
- OPEN: leg seats on the rocker top (flats/notches) are not modelled; scribe to the leg. Rocker width across (31 mm, tape) not
  on the template. Spring-back not allowed for.

## 2026-11-20 17:00-17:45 slats
- templates/slats.py -> slat_template_* (flat outlines of the BACK face, unrolled along the bend) and slat_bending_form_*.
  The slats bend one way only (front-back), so the flat outline wraps onto the bent blank exactly; stations S0-S7 every 100 mm of
  back-face arc length from the seat line tie the paper template to the form.
- Edges: parts/slats.json symmetric fits (v 70-715). Outside: below v 70 held constant (on IMG_1502 the edges run plumb from v 70
  to the seat; tangent extrapolation of the 4th-order fit put the outer inner edge 1.5 mm off), above v 715 on the end tangent (9 mm).
- Ends (templates/slat_ends.json): seat ends by eye on 3-4x zooms of IMG_1502 (centre v 16.5, outer 16 inner / 18 outer, +-2);
  crest ends = slat back face meets the crest bottom strip between the triangulated arrises (centre v 724.1, outer 722.3, +-3; the
  slat highlights end in the crest's shadowed bottom face at v 718-727, consistent). 3/4 in joinery allowance each end, assumed.
- Numbers: centre 707.6 mm seat-crest, 77.0 -> 101.8 wide; outer 705.3 mm, 39.6 -> 53.0. Gap at the back face 29.5 / 33.7
  (tape at the bases 27.7 / 25.7 as built, set sits 1.8 mm right). Centre width under the crest: fit 100-102 vs tape 98.3 (M5 OPEN).
- Form: centre and outer back-face profiles differ by 2.1 mm max / 1.1 rms after rigid alignment (inside the +-2 mm profile
  uncertainty), so ONE form from their average (smoothed 1.1 mm). Gentle S: turn 16 deg, reverses at S0+44, +352, +592; tightest
  R 317 / 503 mm. Stack 10 mm (4 x 2.5 mm suggestion; thickness weak, M4). S0 is 336 mm above the floor.
- Checks: overlay on rectified single photos 1502 / 1501 / 1503 (figures/templates/slat_overlay.jpg): all six edges, seat ends and
  crest ends on the wood. Check squares 144.0 pt on every tile (8 + 10); DXFs read in ezdxf, mm.
- OPEN: outer slats' twist in plan not modelled (their sheet is a pure extrusion along x); joinery not seen.

## 2026-11-21 16:30-17:00 slats (regenerated against model v24)
- Inputs, as tools/build_model.py builds SLAT_C/R/L in v24: parts/slats.json (edges, back-face profiles, thickness_mm 10;
  unchanged since PR #7), the v24 SEAT and CREST solids (parts/model_v24_shapes.glb) for the visible ends; parts/slat_turn.json
  (PR #33) for a note only (apply_in_build false in v24). templates/slat_ends.json now feeds only the 3/4 in joinery allowance
  and the PR #7 by-eye seat ends as a comparison line on the overlay.
- CHANGES in templates/slats.py: (1) ends = where each slat's back face crosses the model SEAT top / CREST bottom, on plane
  sections at 11 points across the width (end lines are now polylines, no longer square); (2) edges held constant above
  v_range like the build (PR #7 carried them on the end tangent for the last 9 mm); (3) stack defaults to thickness_mm.
- Why the seat ends moved: v24's seat top behind the dotted region is a ruled strip from the measured top arris
  (parts/seat_back.json); the older cloud polynomial climbed 16 mm toward the back edge where the slats' feet stand.
- NUMBERS (old PR #7 -> new): centre seat to crest 707.6 -> 711.8 mm (28"), outer 705.3 -> 708.8 mm (27 29/32");
  centre width 77.0 -> 77.0 at the seat, 101.8 -> 101.2 under the crest (3 1/32" -> 3 31/32"); outer 39.6 -> 39.6 (1 9/16"),
  53.0 -> 52.8 (2 3/32"). Seat ends v 16.5 (centre) / 16-18 (outer) -> 11.2-12.3 / 11.7 (inner edge) - 15.0 (outer edge);
  crest ends 724.1 / 722.3 -> 723.8-724.1 / 721.2-723.2 (centre lines identical to the crest.json computation). Outlines: edges
  over v 30-700 identical (max 0.01 mm); max point difference 5.3 / 4.3 mm, all at the seat end; area 601.0 -> 604.5 /
  320.0 -> 321.4 cm2. Gaps 29.5 / 33.8. Form: back-face profile identical (new vs old working face inside the run-out max
  0.05, rms 0.04 mm; 4.5 mm only in the extended run-out); C vs O profile dev 2.05 max / 1.15 rms; inflections S0+50, +356,
  +596 (same places, S0 moved 4.2 mm down); tightest R 315 / 503; S0 331.9 mm above the floor (was 336).
- OUTER SLATS' TURN (#33): NO separate form. Turn is a rotation about the slat's own centre line, so its back-face side profile
  (= the bend) is unchanged; 7.15 deg at the seat (held at the z 375 table value) -> 3.44 deg under the crest, i.e. a 3.7 deg
  twist = 1.7 mm at an edge over 700 mm, small enough to spring in at glue-up into turned mortises. Width-true outline stays
  valid (PR #33 width fit vs model within 1 mm). A note on the template says so; the model (v24) has it unapplied.
- Checks: overlay figures/templates/slat_overlay.jpg on rectified 1502 / 1501 / 1503: all six edges and the crest ends on the
  wood; stations S0-S7 yellow; PR #7 by-eye seat line cyan. Seat end, numeric read (strongest wood -> seat brightness step,
  13 px wide strips): centre 13.0-14.0, outer 13.0-15.5 across the three photos; model 11.2-12.3 / 11.7-15.0, so the v24
  seat end is 1-2 mm low on the centre slat (inside the +-2 tolerance; the by-eye 16.5 read the top of the transition).
  Every check square 144.0 x 144.0 pt (pymupdf; 8 + 10 tiles); DXFs R12 (AC1009), units mm, layers CUT/REF/MARK/DIM/TEXT.
- OPEN: seat end 1-2 mm below the photo transition on the centre slat (seat top at the slats, M13 / #35 doubt); joinery not
  seen (the model's in-run is 4 mm at the seat and 18 mm at the crest, both "NOT measured"); thickness M4; centre width M5;
  if the hub applies the turn (Joe's yes/no), the template and form stay, only the mortise angles change.

## 2026-11-21 16:15-17:10 rocker (regenerated against model v24)
- Inputs: the rocker outline of model v24 exactly as tools/build_model.py builds it (rocker_profile mean_top; mean_bot + the directly
  traced bottom correction parts/rocker_bottom.json (#29); tail and nose from parts/rocker_ends.json (#23, triangulated, L+R); all carried
  to the build's half-way design frame, to_mean). Check: every outline vertex sits on a ROCKER_R vertex of parts/model_v24.glb (0.000 mm;
  rocker.py asserts < 0.05 so a later model change cannot pass silently). Thickness across T(u) from parts/rocker_section.json (#32) is now
  printed at each station. Rocker top at nose/tail (#36) measured, no model change, so nothing extra. Leg landings: sections of the v24
  FLEG_R / BLEG_R meshes across the rocker's thickness (every 1 mm of depth), where they sit on the rocker top; rake from
  model_v24_joinery leg_axis. templates/rocker_ends.json (the by-eye ends) is no longer read (marked superseded).
- Numbers: overall 1118.4 mm (44 1/32") tail tip to nose, along the floor; tail tip 175.8 above the floor (6 15/16"), nose top corner 123.3
  (4 27/32"); the nose is now the measured round end (no plumb end / r 15). Face height 28.1 max, 10.3 at u -480 (the tail thins to a slim
  tip). T 29.7 (tail) - 36.2 mm. Floor = tangent at the rest point u 193 (v 0.31 in the design frame). Back leg on the rocker: rear edge on the
  outer face 28.3, front face 67.2 (38.9 wide; the foot's rear on the inner face reaches 23.4, dashed); front leg 539.1..567.6 (28.5; inner
  rear 533.7). Clear span 471.9. Form: bottom from u -471 to 605 (where the end rounds start, bottom R < 150) + 60 mm each end; the
  bottom reverses at u -257 (450 mm behind the rest point; convex from the form end to u -265, concave forward) so the form stays TWO-PART. Tightest bend
  over 80 mm: R 477 convex (tail, u -324), 511 concave (a local bend at u -49); old 344 / 825. Stack suggestion unchanged (10 x 1/8").
- Differences vs the PR #6 template (templates/rocker_vs_old.py; new outline carried to the left sheet; distances both ways):
  as drawn max 6.35 mm, rms 0.99; after the best rigid fit on the middle (0.05 deg, 0.2 mm) max 5.63, rms 0.82. By region (as drawn):
  tail end u < -400 max 6.35 / rms 2.95 (triangulated slim tip, bottom raised up to 8.5 mm at u -480); middle -400..560 max 2.10 / rms 0.55
  (top edge identical: rms 0.06, max 0.21; bottom +0.45 mean, max 2.17 at u -330: the traced bottom); nose u > 560 max 4.03 / rms 0.88
  (round end instead of plumb end + r 15). Length 1114.5 -> 1118.4 (+3.9: tail tip 3.7 mm further back, nose 0.7 further forward).
  Leg marks moved -2.0 / +2.6 (back leg rear / front), +1.8 / +3.4 (front leg), mostly the half-way frame (2.5 mm shift) plus the
  model's feet (the template marks the side-view foot; the old marks were the outer-face leg lines extrapolated).
- ROADBLOCKs: (1) the design frame is the half-way frame, not the left sheet the photos are in: check_overlay.py now carries the outline
  through the geom's to_left first (backward compatible). (2) Raw curvature of the traced bottom flips sign several times in the tail (2 mm
  sampling, noise); bend radii and the S are read over 80 mm, near-straight (|R| > 3 m) samples ignored and blips < 40 mm dropped: one
  reversal left. (3) The back leg's side-view foot (23.4..67.2) is wider than what shows on the outer face (rear ridge 28.3; the rear face is
  bevelled): both marked, the inner rear dashed. (4) The shared safe_run lock was busy (other template jobs): waited and retried.
- Checks: outline = v24 mesh (0.000 mm). Overlay on 4 rectified photos (L 1507/1506, R 1472/1471, figures/templates/rocker_overlay.jpg),
  by eye on the zooms: tail tip, both edges, the round nose and the leg marks on the wood (the front-face marks on the leg fronts, the rear
  marks on the visible rear edges; the dashed inner-rear marks a few mm behind, as expected). Check squares 144.0 x 144.0 pt on every tile
  (template 7, form 14; pymupdf). DXFs read in ezdxf, $INSUNITS 4 (mm), layers CUT/REF/MARK/DIM/TEXT; template CUT 1118.4 long.
- OPEN: leg seats on the rocker (flats / notches) still not modelled: scribe to the leg. The outer face bows -2.3..+1.2 mm (rocker_section)
  and the left/right rockers differ by ~1 mm rms: the template is the design mean. Spring-back not allowed for. The concave R 511 at u -49
  is a 1-2 mm bump in the traced bottom (inside its tolerance); fair the form there if the glue-up shows a flat.
## 2026-11-21 16:47-17:05 seat
- templates/seat.py -> seat_plan_* (plan outline, true size on the flat underside) and seat_sections_* (cross-section gauges S1-S5
  + centre line); templates/check_seat_overlay.py -> figures/templates/seat_overlay.jpg. Inputs: the model v24 SEAT mesh itself
  (parts/model_v24.glb after joinery, parts/model_v24_shapes.glb before), so the template is exactly what tools/build_model.py
  makes from seat_edge.json (PR #8, #30 ends), seat_front.json (#11 scallops), seat_front_face.json (#34), seat_back.json (#21,
  #35), seat_scoop.json (#20, #26) and seat/surface.json; joinery = parts/model_v24_joinery.json.
- Frame: the underside is one plane in the model: z = 332.05 + 0.1800 (y - 250), tilt 10.2 deg, fitted to the mesh's downward
  faces (rms 0.30, across x 0.00 mm/m). Outline = silhouette of the mesh projected square onto that plane (largest extent: top
  arris at the sides and back, front roll at the front). Y = along the plane from the back edge on the centre line (chair y 3.0).
- Numbers: width 537.1 mm (21 1/8") across the front horns; depth on the underside plane 548.6 mm (21 19/32") back bow to pommel
  (chair-plan depth -3.7..537.0 = 540.7); horns 3.2 behind the pommel; scallop hollow at |X| 130, 23.2 behind the horn line.
  Top 20.4..47.3 above the underside (blank >= 48 mm, 1 7/8"; edges 42-44); dish lowest 23.3 at X +-40, Y 184. Front face is
  vertical in the chair = 10.2 deg off square to the underside (top forward); back face 0.6 deg off square (square to the board).
  Stations S1-S5 at Y 50/150/250/350/450: CL 36.1/23.9/28.7/39.8/41.5, low 35.0/23.9/24.4/26.4/27.1, widths 376.9/
  481.2/512.2/532.1/536.8 (DXF CUT extents).
- MARK: leg faces at 15 mm up (back legs X 187.8-225.2, Y 33-82; front legs X 253-288, Y 457-501), Domino mortises (side front
  X +-259 Y 477 23 up; side back X +-217 Y 81 22.5 up; back edge X +-186.7 Y 43.6 L / 40.7 R 20 up: the model's rear pair is not
  mirror-placed), slat mortises (C X 0 Y 57, outer X +-87.7 Y 64; bottoms 32 above the underside, depth NOT measured).
- L/R DECISION: one symmetric template. Measured (not drawn): side top arris R - mirrored L +3.8 half-width (sd 1.2), bottom arris
  -0.03 (sd 2.2), front outline +0.8 (sd 1.4). The +3.8 is a 1.9 mm sideways shift on the chair centre plane with the same total
  width (the bottom arrises agree), so there is no plan-shape asymmetry to cut; the R front corner is 3.6-3.9 mm LOWER (PR #25),
  which is height (sections), not plan.
- ROADBLOCKS: (1) the joined mesh's up-facing Domino mortise floors entered the top-surface interpolation (dish low read 14 mm
  at a back leg): top surface now from the before-joinery mesh. (2) contours were drawn 251 mm forward (Y offset applied twice);
  fixed. (3) no photos in the worktree: the overlay reads the coordinator's drive/ read-only (--drive). (4) safe_run lock held by
  other sessions: retried.
- Checks: overlay on 1545 (behind), 1548 (left), 1538 (right) rectified 38 mm above the underside, each outline point carried
  along its own camera ray: front edge, both hollows, pommel and both horns on the wood edge in all three by eye (1 mm/px zooms);
  sides mostly hidden by the arms, back corners hidden by slats/legs except on 1545 (on the wood). Every tile carries one check
  square, 144.0 x 144.0 pt (pymupdf; plan 12 tiles 3x4, sections 9 tiles 3x3; full 1:1 sheets too). DXFs read in ezdxf, units mm;
  plan CUT 537.1 x 548.6, perimeter 2082.5; sections CUT x6.
- OPEN: underside flatness across X is ASSUMED in the model (raised 1-4 mm at the front); slat mortise depth and all Domino depths
  ASSUMED; the leg cuts are the model's leg shapes, scribe to the real legs; left front corner M9 / seat front corner reading
  (PR #30 lead) could move the horn top 3 mm (height only); glue-up board layout not seen in the photos (blank size only).
## 2026-11-21 16:47-17:10 crest
- templates/crest.py -> crest_plan_*, crest_back_*, crest_sections_* (+ crest_geom.json); templates/check_crest_overlay.py ->
  figures/templates/crest_overlay.jpg. Inputs: parts/crest.json (four arrises, design even polys, lean, joints; PR #4),
  parts/model_v24_shapes.glb (BLEG_R inner face beside the crest = shoulder line, PR #5 pinned the leg rear to the crest;
  SLAT_C/L/R faces where they meet the crest bottom = mortises), parts/edge_radii.json (arris note).
- HOW IT IS MADE: SAWN FROM SOLID and shaped; NO bending form. Basis: crest.json's design is a solid rail tapering 28 -> 41 mm
  top to bottom with a twisted front face (front lean 12-19 deg vs back 9.9); no lamination lines were reported on the top face
  (overhead traces at 0.3 mm/px); bow 16.5 mm over 437 mm (plan R 1231) saws easily from 2 in stock. Not checked by eye here.
- VIEWS (why): all drawn in a RAIL FRAME tipped by the back legs' 9.9 deg lean: crest.json carried the bottom-rear arris down
  that lean from the top-rear one, so the back face is a ruled cylinder (bottom-rear vs top-rear differ <= 0.34 mm in w):
  a square bandsaw cut, developable, and the blank shrinks to 49 mm thick (59 in the chair frame). (1) plan square onto the top
  face: saw line = back face + bottom-front arris (outermost), top-front arris to shape the front face to, shoulders, mortise
  footprints, leg tops, stations X100/X200; (2) back face UNROLLED (exact): both arches, shoulders, arch over the leg tops,
  mortises; (3) section gauges X0 / X100 / X200 / shoulder (cards; slat mortise drawn at X0 and X100; plumb line shown).
  Order for the maker: blank -> plan (back face square, front square to the bottom-front line) -> wrap crest_back, saw arches
  square to the back face (top/bottom faces are square to it in crest.json) -> spokeshave the front to the top-front line, gauges.
- Numbers: shoulder to shoulder 436.6 (17 3/16") at the top, 432.6 at the bottom (model leg inner face leans out 2 mm over the
  crest height: 216.3 at z 998 -> 218.3 at z >= 1038); 438.2 along the bowed back face. Height 76.0 centre / 70.0 shoulder;
  thickness 28.4 / 40.7 at X0, 26.8 / 28.6 at the shoulder (= crest.json per_station within 0.2). Bow of the back face 16.5 at
  the shoulders in the rail frame (crest.json 18.0 is measured to the line between the joints at the top-rear arris). Blank
  526 x 49 x 89 mm (20 23/32 x 1 29/32 x 3 1/2") incl. 3/4" allowance + 25 mm waste per end. Mortises (v24 slats at the bottom
  face): C 100.0 wide x 10.2 (at X0), outer 53.0 wide (x 83.8-136.8); slats run 10.7 deg further back than the back face;
  v24 slats reach 20.8 / 23.4 mm in.
- Checks: overlay by projecting the 3D template geometry with the solved cameras into raw photos (no plane parallax) 1545,
  1548, 1502, 1501: top/bottom arrises on the wood edges, shoulders on the leg seams (1502 both ends), slat lines over the slats,
  arch over the leg tops (right end on 1502 runs ~1-2 mm past the lit leg corner: glare/round). Check squares 144.0 pt on every
  tile (3 + 3 + 2). DXFs read in ezdxf, mm; back-face CUT perimeter 1020.4 (= 2 x 438.2 + 76 + 70 - rounding).
- ROADBLOCKS: overhead/rear sheets for the crest live only in ../rocking-chair-crest (not read); projecting into raw photos
  instead. First slat-face fits picked up the slat edges' end faces (front line flat, a 47.9 mm footprint); fixed by per-band
  outline extremes. A leg section outlier (x 256.8 at z 1058) from undersampled outline; fixed by densifying.
- OPEN: crest/leg joint hidden (3/4" tenon allowance ASSUMED); mortise depth ASSUMED 3/4" to match slat_template; M3 (height
  74.7 vs tape 77.5) and M7 open; critique bottom/front +2.9 at x 0..100 (frozen-file doubt) would move the bottom-front line;
  fits extrapolated 6 mm past |x| 212 to the shoulder; arris rounds are a note only; lamination question not checked on a photo.
## 2026-11-21 16:46-17:05 arms
- templates/arms.py -> arms_plan_* (plan from straight above, chair X-Y, front to the right, outside edge down) and arms_side_*
  (side profile from outside the right arm, chair Y-Z, front to the right). ONE template for both arms, flipped for the left.
- Inputs: parts/arms.json design (top arrises, plan, front line), parts/arm_underside.json design (h_outer / h_inner below the
  outer top arris, straight across), parts/model_v24.glb: ARM_R silhouettes (= the build, carried back to y 40 and coped to
  BLEG_R), FLEG_R (section 10 mm below its top = front-leg footprint; faces at its centre x in side view), BLEG_R (front face at
  the arm's end, plan section at mid-end height, side sections at the arm's outer / inner face), DOMINO_AR (ASSUMED vertical
  10 mm Domino arm/front leg, 24 x 10, 15 into the arm), DOMINO_RAR (through the back leg into the arm's end; position measured,
  depth ASSUMED). The oval on the left arm top is not a tenon (parts/joints.json): not drawn. Stations S0-S9 at chair y 50..500
  are the same vertical planes on both drawings; the side one also gives mm along the top from the end.
- Numbers: plan length (chair fore-aft) 463.9 mm (18 1/4"), y 40.0..503.9; along the outer top arris 491.2 (19 11/32");
  overall plan width 125.0 (4 15/16", the arm sweeps outboard); arm width 41.0 / 63.3 / 76.4 at y 100 / 300 / 500; front end
  77.8 straight. Thickness, outer face, vertical: 38.1 (1 1/2") at the cope (y 45; 36.7 at y 60) -> 21.2 (27/32") at the front;
  inner face 44.2 -> 23.5 (the underside slopes down inward: CUT = inner bottom arris, REF = outer bottom arris). Top rises
  ~160 mm, slope 24 deg at the back, 13 at the front. Front leg under the arm y 423.5..456.2 (383.5..416.2 from the end).
  Profile fits a board 43.7 x 503 at 21 deg to level; blank 46 x 136 x 510 with its jointed edge = the plan's REF baseline
  (x 323.7, 8 mm outboard of the front outer corner); side template goes on that edge, plan set out by station offsets.
- Sides are VERTICAL in the chair (arm_underside.json); cutting them square to the sloping top instead moves the bottom edge
  up to 5.5 mm (outer) / 4.2 (inner) at the back: stated on both templates (saw outside both lines, plane to them).
- L/R: model arms are exact mirrors. Measured (arms.json): width L-R 3.9 mm rms, 6.4 max from y 180 (6.8 rms overall: the left
  inner trace behind y 180 follows a shading line); outer-edge shape 2.2 rms / 4.0 max after the common +x shift; tops up to 5.1
  apart at the front; underside h_outer L-R <= 3.1. Within the design tolerance (half the L/R difference) -> one flipped template.
- ROADBLOCK: first plan overlay projected the outline square onto the overhead sheet plane: the left arm's front end sat ~10-15 mm
  off on IMG_1538 because aL's plane runs ~15 mm above the arm top at the front (tilt 3.4 deg). Fixed: each point goes where the
  photo's camera ray through it meets the sheet plane (rocker.cameras); then on the wood. Strongest-gradient edge reading on the
  median sheets was tried as a numeric check and dropped (grain lines and the side faces beat the arris).
- Checks: silhouette vs parts curves (y 80-470) max 0.05 mm inner / 0.04 outer / 0.04 top / 0.04 inner bottom. Overlay
  (figures/templates/arms_overlay.jpg): plan on the overhead sheets R 1544/1549, L 1544/1538 (each arm moved rigidly by its
  own offset from the design, R dx +2.7 dz -1.2, L dx +2.2 dz +1.2): both edges, the front end and corners on the wood at the
  back, middle and front zooms. Side on the unrolled outer-face strips R 1469/1477, L 1504/1516 (tools/arm_underside/strip.py):
  top and outer bottom arris on the wood end to end, front end on the end. Check squares 144.0 x 144.0 pt on every tile (3 + 3)
  and on both 1:1 sheets (pymupdf); DXFs read in ezdxf (R12, $INSUNITS 4), CUT bbox 463.9 x 125.0 (plan), 463.9 x 198.4 (side).
- OPEN: back end / cope not seen from above (traces stop at y 66-68): scribe the end to the real leg. Front leg placement +-3 mm
  (joinery); front-leg y range on the side strips is not checkable (the leg face is ~30 mm inboard: parallax). Both Dominos'
  depths ASSUMED. M6 (front-end thickness), M15 (inner face), M16 (edge radii; drawn sharp). The arm's top is assumed flat across
  (arms.json). A narrower blank (plan min rectangle 79 mm, angled in plan) needs a different set-out: not drawn.
