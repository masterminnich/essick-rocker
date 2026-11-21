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
   DONE as far as model v11.
5b. **Known fixes and joinery** (NEW. Joe, 2026-11-20 17:24: "I want everything perfect before we make the templates";
   flaws we already know are fixed BEFORE the critique loop, so the loop is spent on what we cannot already see. Source: the
   model audit, PR #12, `reports/model_audit_v9.md`). Checklist with owners in "Sessions and who owns what" below.
6. Critique loop: project the model into every photo through the solved cameras; measure the edge gap per part; fix the worst;
   repeat, until every part is inside 1/32" at joints and hard points and 1/16" on free curves. ~15% of photos are held out
   for validation only. Joints are mostly hidden, so they are checked by the assembly audit (`tools/audit_joints.py`), not here.
6b. Tape readings in, as checks on the photo numbers: M1, M3, M4, M5, M9, M11 (below); M7/M8 if Joe takes them.
6c. Finish detail: radii of the rounded edges (the model has sharp arrises everywhere; the rocker ends of PR #23 are traced on the
   tone edge of eased arrises and extruded square across: the radius there and any rounding of tip and nose in plan view); cross-check against the shop
   templates hanging in IMG_1507 (flat photos of them, if Joe can take some).
7. Deliverables: CAD model, dimensioned drawing, accuracy report, then 1:1 tiled PDF/DXF templates with a print-scale check
   square. FINAL templates only after 5b-6c. The templates session's files before that (rocker, slats: PRs #6, #7) are drafts
   and are regenerated from the final parts files.

## Sessions and who owns what (2026-11-20 17:45; Joe: split the work, do not clash)
Several sessions work on this repo at once, each in its own git worktree and on its own branches. They cannot message each
other; **this section, PR descriptions and PR comments are the channel.** Read this section after every pull of main.

| Session | Worktree, branches | Owns (only this session edits) |
|---|---|---|
| **Hub** (cc-sessions "rocking-chair"; runs unattended, works to completion. **Joe, 2026-11-20: from model v18 on, all remaining work and the supervision are to run on Opus 5.5.** The hub session cannot start a session itself, so: the remaining items are done by Opus 5.5 workers the hub starts, one at a time, until Joe switches the hub session to Opus 5.5 or starts a new Opus 5.5 hub from `HUB_HANDOFF.md`; same worktree and rules either way) | `rocking-chair/`, main + short topic branches | `PLAN.md`, `LEDGER.md`; the model version numbers `parts/model_vN.*`; in `tools/build_model.py`: SEAT (surface, front, side edges, underside, closing the mesh), arms, rockers, crest, slats, front-leg outline; `parts/seat_*.json`, `parts/side_frame.json`, `parts/lr_skew.json`, `parts/rocker_profile.json`, `parts/rocker_ends.json`, `tools/rocker_ends/`; phase 6 onward |
| **Joinery / audit** (cc-sessions "rocking-chair-seat"; Joe attends it; it did the seat survey first) | `../rocking-chair-audit`, branch `joinery` and successors | in `tools/build_model.py`: the back-leg outline code, the placement of the legs against seat and rockers, every joint body; `tools/audit_*.py`, `tools/domino_ortho.py`; `parts/dominos.json` and any new joinery file; `reports/`; `figures/joinery/`, `figures/model_audit/`. **Hub edit, 2026-11-20 (PR #24, Joe's fix-list item 3): `parts/dominos.json` `joints.front_leg.centre_xyz` moved 1.52 mm forward along the leg face, new key `centre_provenance`; format otherwise unchanged; `tools/joinery.py` not touched. Method and data: `tools/front_domino/`.** |
| **Templates** | `../rocking-chair-templates`, branch `templates` | `templates/` (its own ledger is `templates/LEDGER.md`); reads `parts/*.json` and `parts/rocker_profile.json`. **From model v18 the rocker's outline is `rocker_profile.json` between u -330 and u 572 PLUS the two ends in `parts/rocker_ends.json` `design` (its `note` says how they join); `rocker_profile.json` alone gives the old square-cut rocker** **From model v20 (PR #26) the seat's side-edge under-bevel in `parts/seat_scoop.json` `design` is the left/right mean (lens max 23.2 mm, was 24.4; bevel 45.7 degrees, was 46.2; y 83.5-460.7); new blocks `left` and `left_vs_right`, existing keys unchanged in meaning; the seat's plan outline is unchanged.** |
| Seat survey (finished; now the joinery session) | `../rocking-chair-seat`, branch `seat` | `seat/` (frozen: `seat/surface.json`, `seat/dots.csv`). A doubt about it is written in LEDGER.md, not fixed in place |
| Crest and arms (finished) | `../rocking-chair-crest` | `parts/crest.json`, `parts/arms.json` (frozen; additions go in a separate file) |
| Viewer (finished) | `../rocking-chair-viewer` | `viewer/`; it finds the newest `parts/model_vN.glb` on main by itself |

Phase 5b checklist:
- Joinery session: [x] back leg as one continuous board (PR #14, landed with PR #16, model v12) · [x] front legs lapped on the
  outside of the seat edge with a through-Domino; back legs butted to the seat's side edge with the Domino across the joint
  (PR #17, model v14; `parts/dominos.json`: 10 mm Domino, 24 x 10 section) · [x] legs seated on the rocker tops (PR #17; the
  feet still sit about 3 mm off the rocker faces in x, open) · [x] arm into back leg, crest to back legs, slat mortises (PR #17,
  as contact faces or mortises; the hidden fasteners are not modelled) · [x] arm / front leg: the oval in IMG_1528 is not a
  tenon; hidden 10 mm Domino, assumed (PR #18, model v15, `parts/joints.json`) · [x] feet swept along the leg axis and cut
  flat to the rocker (PR #19, model v15) · [x] assembly check passing on every build (v14 on: `tools/model.sh` runs it and
  prints PASS / FAIL).
- Hub: [x] seat front face and bottom edge (PR #15, model v11) · [x] SEAT mesh closed (watertight; model v13) · [x] seat
  underside along the side edges (PR #20, model v16, `parts/seat_scoop.json`: square edge, hard line, 46 degree under-bevel
  scooped between the legs; right side measured, left assumed mirror; the close-ups IMG_1570-1576 turned out too badly
  registered to use; flat ACROSS is by reflection only) · [ ] **Joe's fix list of 19:00, next, in this order** (below) ·
  [x] the 3 mm question at the right front corner of the seat (PR #25, no model change: L/R asymmetry, not a model error;
  same photo, right corner 3.9 mm lower than the left, 10 photos, sd 1.5; model 2.6 mm proud on the right, 1.0 inside on the
  left, about 1 mm above the mean of the two sides, inside tolerance; M9 tells chair from solve tilt) · [x] left-side check of the seat scoop (PR #26, model v20: the mirror does NOT hold; the left lens is 1.6-3.8 mm shallower at y 150-300 (22.1 vs 24.4 mm at most; 12 photos vs 14, jackknife se 0.5-1.3) and its edge face 1.8-3.3 mm taller; the left bottom arris sits 2.2-2.7 mm higher, the same L/R lean as PR #25; bevel angle 45.2 vs 46.2 degrees, inside 1.5. The design is now the L/R mean: lens max 24.4 -> 23.2 mm, bevel 46.2 -> 45.7 degrees, y range 83.5-460.7; only SEAT changed, at most 1.3 mm at the side edges) ·
  [ ] arm underside and thickness (new file, not `parts/arms.json`) · [ ] rocker bottom edge traced directly (today it is the
  top edge minus a fitted face height; lead from PR #23: at u -320 the directly traced side face is 26.4 mm high on the left and
  26.0 on the right where the profile says 27.7, while at the nose old and new agree; the ends in `parts/rocker_ends.json` are
  already traced directly, so this item is the stretch u -330..572) · [ ] seat side edge behind y 400, where it meets the back leg (today extrapolated).

**Joe's fix list, 2026-11-20 19:00 (said in the hub session; "add this to the plan to fix after v16, then continue with the
rest of the plan as written"). Joe gave these to the HUB, so the hub does them, including the two that touch the joinery
session's files. Joinery session: please do not start the same items; the hub keeps its edits to `tools/joinery.py`,
`parts/dominos.json` and `parts/joints.json` small and names each one in its PR.** New photos for them: IMG_1618, 1619, 1620
(close-ups, not registered; half-resolution registration only).
1. [x] (PR #22, model v17; `parts/joints.json` `back_leg_rear`, parts `DOMINO_RS*` and `DOMINO_RA*`) **Dominos missing at the back of the chair** (IMG_1620, from behind): each back leg shows TWO Domino ends on its
   rear / outer face, one at seat height and one higher, at the arm. The model has only the seat one (`DOMINO_BR/BL`) and an
   unmodelled "contact face" at arm / back leg. Add the arm / back-leg Domino and check the seat one comes out where the photo
   shows it.
2. [x] (PR #23, model v18; `parts/rocker_ends.json`, `tools/rocker_ends/`: tail tip at u -488.2, nose top corner at u 626.6 with the end 4.1 mm proud of it; open: left rocker 6.3 mm longer than the right in the photos, design = mean) **Rocker ends are not shaped right** (IMG_1618: the tail thins to a slim rounded tip; IMG_1619: the front end is cut
   to a round nose across the laminations). The model's rocker ends do not have these shapes. Rockers are the hub's part.
3. [x] (PR #24, model v19; `parts/dominos.json` `front_leg.centre_xyz` [-284.2, 466.7, 394.8] -> [-284.4, 468.2, 394.8], +1.52 mm forward along the face; photos: 0.58 mm rearward of the arris middle, 19 photos, sd 0.73; model was 2.07, now 0.55; height and tilt not changed, right-leg photo sets disagree on height by about 7 mm) **Front-leg Domino sits off-centre on the leg** (Joe's viewer screenshot of v15: the slot is to one side of the leg's
   width). Re-measure the slot's position on the leg face against the leg's two edges and centre it if the photos agree.
4. [x] (PR #21, model v17; `parts/seat_back.json`: a bow in plan, a back face leaning 10.5 degrees, a 46 degree under-bevel lens) **The seat's back edge is not modelled right** (Joe, 19:20: "the top, front and sides are pretty accurate but not the
   back edge"; no hurry, but it is tied to item 1). Model v16: a straight back edge at y 10.8, 21 mm BEHIND the back legs'
   rear faces, with a slanted corner that wraps behind each leg. Photos from behind (IMG_1502, 1513, 1578, 1620): the back edge
   is flush with the leg's rear face where they meet (a Domino end lies flat across both) and bows backward toward the centre
   line (cloud: rearmost y about 0-10 at the centre, 25-31 at |x| 160-200). Hub's part (`tools/build_model.py` SEAT). Trace the
   top and bottom arris of the back edge from the behind and above photos; done BEFORE the rear Dominos land (the lower one
   sits in that seam).

Item 1, what the photos show (hub, 19:25; LEDGER 19:25): each back leg has THREE Domino ends, not two. (a) the one already
modelled, on the leg's OUTER face at the seat (`DOMINO_BR/BL`, confirmed in IMG_1508); (b) on the leg's REAR face at seat
height, across the seam between the leg's inner face and the seat's back edge, driven in from behind; (c) on the REAR face at
arm height, centred on the leg's width: a Domino through the leg into the arm's end. (b) and (c) are the missing ones. All
four rear ends were measured on photos that are already registered (IMG_1499-1503, 1513, 1578); IMG_1620 itself did not
register and is not needed.

**For the joinery session, from PRs #21 and #22 (hub, 20:15):**
- The seat top behind the tape dots is lower now (it falls to the measured back arris instead of climbing). The slats' feet
  (SLAT_C bottom at z 328.0, SLAT_L/R at 329.7) sit only 4 to 5 mm into the seat top; v16 had 9 to 11 mm. Slat lengths and
  mortise depths are yours.
- At the rear the real seam between back leg and seat sits 3.4 mm (left) and 2.5 mm (right) INBOARD of the model leg's inner
  face (seen across the rear Domino's end, `figures/joinery/rear_dominos_1501.jpg`). Leg placement is yours; the rear Domino
  at the seat is placed by its measured position, so it will sit right once the leg does.
- `tools/audit_joints.py`: the inside test now runs in slices of 250 points (it went over the 3 GB cap on the first rear
  Domino pair; the old pairs were close to the cap too). Four pairs added. `tools/joinery.py`: step 5c added.
- New tools of the hub's: `tools/rear_ortho.py`, `tools/rear_dominos/`, `tools/seat_back/`.

Rules:
1. **Model numbers come only from the hub, on main.** No branch commits `parts/model_v*`. After another session's PR lands
   the hub rebuilds and commits the next number, and the viewer shows it about a minute later. Build to `work/` to test.
2. **One PR per fix, squash-merged.** Start each new piece from current main: a new branch, or `git merge main` into yours
   first (all worktrees share the local ref `main`; the hub keeps it at GitHub's main). After a squash, do not stack further
   work on the old branch without merging main into it; files that were added on both sides otherwise conflict.
3. Any session may squash-merge its own PR once it is mergeable and holds no model file. The hub merges what is left open
   at its next turn, after a trial build of main + the branch (parts that should not change must be vertex-identical).
4. `PLAN.md` and `LEDGER.md` are edited only by the hub. Other sessions keep their notes in their PR bodies and a file of
   their own (`templates/LEDGER.md`, `joinery/LEDGER.md`); the hub copies a short entry into `LEDGER.md` at each merge. To
   ask for a plan change: a PR comment, or Joe says so in the hub session.
5. Before editing a block of `tools/build_model.py` that another session owns: say so first (PR comment, or LEDGER for the
   hub), keep the edit small, and name it in the PR body. Preferred instead: hand over DATA (a parts file) and let the owner
   read it. The seat / leg interface is settled (PR #17): the joinery session cuts the finished parts in its own step AFTER
   the build, `tools/joinery.py`, so neither session edits the other's block of `tools/build_model.py`.
6. Existing `parts/*.json` formats stay stable; a format change is called out in the PR body and in LEDGER.md.
7. Compute: one job at a time through `tools/safe_run.sh`; the lock is shared by every worktree. `work/` is shared scratch
   through symlinks: write only under your own subfolder (`work/audit`, ...), read the rest.
8. **The build is three steps** (model v14 on), run by the hub as `tools/model.sh --out parts/model_vN`:
   `tools/build_model.py` (the parts as traced; hub and joinery blocks) -> `parts/model_vN_shapes.glb`, `_params.json`,
   `_edges.json`; `tools/joinery.py` (joinery session's file: the joints cut in, Domino bodies added) -> `parts/model_vN.glb`,
   the chair, with `_joinery.json`; `tools/audit_joints.py` + `tools/joints_gate.py` (thresholds, hub's file) ->
   `_joints.json` and PASS / FAIL. A model number is only issued on PASS. To try one part quickly:
   `tools/model.sh --shapes-only --out work/<dir>/name`. Compare versions part by part on the `_shapes.glb` files (the joined
   meshes are re-triangulated by the cuts). New part names in `model_vN.glb`: `DOMINO_FR`, `_FL`, `_BR`, `_BL` (v14), `DOMINO_AR`, `_AL` (v15).
9. **The seat's side edge** (model v16 on): `parts/seat_scoop.json` `design` gives the section between the legs (vertical edge
   face, hard line at a tabled height above the underside, under-bevel at `bevel_angle_deg`). While that file exists,
   `parts/seat_edge.json` `design.bottom_half_width_of_y` is NOT used (format unchanged; its top outline, top height and
   bottom height still are). Templates: the plan outline of the seat is unchanged; the under-bevel is a shaping step.
   From model v20 (PR #26) `design` is the LEFT/RIGHT MEAN of the two measured sides; the file adds `left` and `left_vs_right` (format addition, existing keys keep their meaning; `design.bevel_angle_deg` adds `left` / `right`, the lens table adds `left_minus_right_mm`).

## Hand measurements (Joe, 2026-11-20: optional, small list; model work never blocks on them)
Changed 17:45: Joe wants everything checked before FINAL templates, so the checks M1, M3, M4, M5, M9 and M11 sit in phase 6b,
ahead of phase 7. Model work, the critique loop and draft templates never wait for them; only the final template sign-off does.
The original 35-item caliper sheet (R/F/B/A/C/S/T codes, K1-K6, seat depth grid, far photos) is retired: photogrammetry now
covers it. Only these remain, because no photo sees them or two sources disagree. Fold them in whenever Joe sends them.
Required:
- M1 seat edge thickness, front centre. M2 seat edge thickness, middle of one side. (Since PR #8 the side edge is triangulated:
  42.0 mm square to the seat plane, +-3 mm, parts/seat_edge.json. M2 is now a CHECK on that number. Since model v11 the front
  edge is triangulated too: top of the roll to the bottom arris 38 mm beside the pommel tip, 21 mm in the thigh hollows, 39 mm at
  the corners, +-2 mm, parts/seat_front_face.json; M1 is a CHECK on the 38. If Joe takes it: straight up the front face, 10 mm to
  one side of the pommel tip. Since model v16 the side edge is known as a section: a vertical edge face 18 mm high at
  mid-length over a 46 degree under-bevel 24 mm high, parts/seat_scoop.json; M2, if taken, is the height of that vertical face
  half way between the legs. The underside between the edges is a plane along the edge (0.24 mm rms) and flat across by
  reflection only.)
- M3 crest rail height at the centre. (Photos 74.7 mm vs tape IMG_1555 77.5: 2.8 mm conflict.)
- M4 centre slat thickness. (~10 mm from photo consistency, weak; it is the lamination stock / bending-form thickness.)
- M5 centre slat width just under the crest. (Trace 100.0-100.5 vs tape IMG_1553 98.3: 1.7-2.2 mm conflict.)
Optional:
- M6 arm thickness at the front end (assumed 25 mm; try the side photos first).
- M7 table to top of crest at the centre; M8 rocker tip to tip, straight line (from PR #23 better PER ROCKER: tail tip to the top corner of the nose; the photos say 1118.6 mm left, 1112.3 right, each about +-2; the model has 1115.7). The only independent check on the single
  framing-square scale; they make the accuracy report more than self-graded.
- M9 table to the top of the seat's side edge just behind the front leg, LEFT and RIGHT (two tape readings). The photos say
  the right side sits 3.7-5.9 mm lower there and the whole right side frame is pitched about 0.5 deg nose-down against the left
  (parts/lr_skew.json). If the tape shows the same difference, the skew is the chair and the model's left/right mean is right;
  if the tape shows none, the camera solve is warped by that much and every single-side number is suspect.
- M10 depth of the front scallop: a straightedge laid against the front of the seat, touching the pommel tip and one front
  corner; the largest gap between it and the seat's top front edge in the thigh hollow (one reading, either side). The photos
  say 21.3 mm (parts/seat_front.json), but forward depth is the weak direction of that solve: it moves by 2-3 mm when its
  assumptions change, so the front outline is +-2 mm instead of 1/16 in. One reading would pin it.
- M11 one Domino end on a leg's outer face, length x thickness, and that leg's thickness across (joinery session). The photos
  now read the visible ends as 25-26 x 11-11.5 mm on true-scale leg-face views, taken as a 10 mm Domino (24 x 10 section) plus
  glue line (`parts/dominos.json`, fitted + assumed); M11 is a CHECK on that. The Domino's length cannot be seen in any photo.
- Leg stock thickness across (now +-3 mm; part of M11), only if Joe wants rough stock sizes; side templates do not depend on it.
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
