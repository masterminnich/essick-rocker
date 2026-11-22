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
