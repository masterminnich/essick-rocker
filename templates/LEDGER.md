# Templates workstream ledger (phase 7)

Branch `templates`, worktree ../rocking-chair-templates. The coordinator owns main, seat, legs and tools/build_model.py;
this workstream only adds files under templates/ and figures/templates/ and reads parts/*.json. Read PLAN.md first.

Rebuild everything: `templates/build.sh`. Kit: templates/tplkit.py (spec in mm -> tiled Letter PDF with assembly map,
0.5 in overlaps, 1 in registration crosses on a global grid and a 2 in check square on every page; single-sheet 1:1 PDF;
R12 DXF in mm with layers CUT/REF/MARK/DIM/TEXT; preview PNG).

`work/` in this worktree holds symlinks into the coordinator's work/ (solve, sheets, parts, dense, masks, toolkit, frame):
read only. NOTE work/toolkit/rk.sh cds into the COORDINATOR's tree; use it only with absolute paths and never to write.

## State
- [x] 1. Rocker template + two-part bending form (this PR)
- [ ] 2. Slats (parts/slats.json), bending form if laminated
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
