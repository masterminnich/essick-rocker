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
   **Pass 3 (model v24, after PR #34): `reports/critique_v24.md` / `.json`, 36 items (the item count can move by one between runs on
   the same mesh: `joint_frac` is sampled).** **Pass 1 done (PR #31, model v22, no model change):** `tools/critique/` (rerun: its README), `reports/critique_v22.md` / `.json`,
   `figures/critique/`; 15 of 93 photos held out (`tools/critique/holdout.json`, fixed); sign + = model outside the wood;
   shift test recovers a 2 mm move at 0.98-1.0. Ranked fix list from it (symmetric gap; held-out value in brackets):
   - Hub, in order of size:
     - [x] rocker inner face 2-3 mm inside the wood, top and bottom edges (bottom -3.1 [-3.2], top -2.0 [-2.0]). DONE, PR #32,
       model v23: the thickness across VARIES along the rocker. Both arrises of the top face traced in single outboard photos
       (pose-free), every 20 mm, 12-30 photos per station and side, spread 0.2-1.0 mm: 29.7 mm at the tail tip (tape IMG_1493
       30.5 +-1.6 there), 33-34 at the back leg, 36.2 between the legs, 34 at the front leg; L/R differ up to 1.5 mm; easing bias
       -0.8 +-1.6, not resolved. Outer face moved by the measured L+R mean (0 in the tail, up to 1.2 inward at the rear, up to
       2.25 outward at u 200-400). New `parts/rocker_section.json` (`tools/rocker_thickness/`). Critique: rocker items 9 (score
       16.07) -> 7 (9.29), held-out rocker mean |gap| 1.64 -> 1.52; top/inner -2.0 gone; bottom/inner -3.15 -> -2.74 (#18),
       what is left is the RIGHT rocker's placement (request to joinery below). `reports/critique_v23.md` / `.json`.
     - [ ] seat front corner in front of the front leg (PR #30's `ends.open`; outer side y 500-550 -3.3 right only, 7 photos [-1.3];
       corner top -1.2, within tolerance): not settled by the photos; a tape / profile-gauge reading at y 500-530 decides it.
     - [x] side slats' inner front edge +1.7..+2.9 (z 450-1000, worst at the top [+1.3..+3.0]): MEASURED, PR #33, NO model
       change. Cause: the side slats are TURNED about their length, outer edge forward (face the sitter), L 4.4-6.1 deg, R 1.4-7.3
       (pose-free silhouette widths in single photos, 8-27 photos per 100 mm band, native 1.7-2.4 px/mm; centre slat control
       +0.6); width within ~1 mm of the model, thickness not resolved (M4). Design = L/R mean, straight line 7.2 deg (z 375) ->
       3.6 (z 1000), `parts/slat_turn.json` with `apply_in_build` FALSE. Trial with it applied (PASS): ranking photos better
       (slat median |gap| 0.72 -> 0.54, out of tolerance 6 -> 3, item z 900/950 +2.90/+3.23 -> +2.45/+2.54), pose-free held-out
       widths better, but the critique's held-out edge medians mixed (0.83 -> 0.90): measurement only. OPEN for the hub: apply
       it (set the flag, rebuild) or first read the slats' position near the crest (forward shift 0..+2, R ~1.8 inboard).
     - [x] seat roll underside edge -2.2..-2.5 (x 0-50, 200-250 [-3.8]). DONE, PR #34, model v24: a bookkeeping slip. PR #15
       traced the edge as a tube of r 1 mm and stored the tube's SPINE as the arris; the arris is now the tube's outline (spine +
       r k, k measured from PR #15's r 4 variant): 0.90-1.00 mm lower, 0.40-0.50 forward along |x| 8-262; corner point unchanged.
       Direct single-photo trace (`tools/seat_roll/`, 14 photos, 2.0-6.4 px/mm): the two 6 px/mm photos read +1.14 / +1.30
       against v23 where the slip predicts 1.17 / 1.31; median +1.49, all 14 positive. Only SEAT changes (at most 1.0 mm,
       y 461-537; slat ends untouched). Critique: bottom/front silhouette mean |gap| 1.85 / 2.18 -> 1.50 / 1.96, held-out better
       in 9 of 9 like-for-like stretches; item x 0-50 gone; x 200-250 -2.54 -> -2.01 (#27, right half only: the right front is
       2.6 mm lower, the design is the L/R mean). `reports/critique_v24.md` / `.json`.
     - [x] seat top back edge at the slats +1.8 [+1.4] (v24 #10). MEASURED, PR #35, NO model change: cannot be told. Between the
       slats, 4 photos from the front, overhead and behind-below see the outline 1.8-3.4 mm inside the model's top arris (2.0-3.0
       px/mm, both halves); the tracing direction (behind-above, IMG_1540) and the critique's tone line from behind read 0..+0.5.
       A round of r 4-5 mm or more, or a top that rolls off before the edge, fits; reading M13 decides (then a 6c radius or a
       seat_back.json change).
     - [x] rocker top at the nose (v24 #20: top/outer y 300-650 -2.27 [-3.1..+0.1]) and tail (y -500..-450 +2.0 [+2.1]).
       MEASURED, PR #36, NO model change: asymmetry and pose, not shape. In single photos (PR #29 ribbons, 17 L / 14 R, 1.4-3.9
       px/mm, up to 6.1 at one end) each side's top keeps its own traced shape within 1.2 mm (rms 0.5-0.6) once the photo's own
       shift and tilt are removed; what is left in the critique is the rocker's tilt in 3D: per photo, left -3.8 mm/m (ranking
       -4.4, held -2.2), right -0.6, scatter 3-4 mm/m (IMG_1492: top AND bottom edges 3.5 mm high together). Reading M14 settles it
       (placement: the joinery side's call).
     - [x] arm underside inner edge (v24 #17: bottom/inner y 50-100 +1.43 [+1.67]; y 400-450 +1.08). MEASURED, PR #36, NO change
       to `h_inner`: within spread, L/R asymmetric. Pose-free per photo against the same photo's outer top arris
       (`tools/arm_underside/critique_inner.py`, 1.6-2.3 px/mm, best 7.2): left -0.59 (20 photos), right +0.81 (18 photos),
       spread 1-2.5 mm per stretch; right +3.4 at y 50-100 (3 photos) and +2.4 at y 400-450 (6); left held-out disagrees with
       its ranking photos; all within `tolerance_inner`. PR #27's inner-face caliper reading settles it (M15).
     - NEXT hub fix: 6c edge radii. Ranked list: v24 (`reports/critique_v24.md`); every hub item of it is now measured; the seat
       front corner waits for a reading; the slat turn waits for Joe's yes/no.
   - Requests to the joinery session (its files; not fixed by the hub):
     - [ ] back-leg foot (z 0-100) +2.1..+4.1 on every edge [+2.3..+3.5]: the real foot is about 3 mm narrower than the model
       (`figures/critique/top_back_leg_foot_IMG_1503.jpg`).
     - [ ] front leg sits about 2 mm forward of the wood at z 150-600 (back edge -2.7 [-3.5], front edge +1.6..+2.6): leg
       placement or tilt; if the placement is right, the hub's front-leg outline is next.
     - [ ] front-leg top at the arm +3.4 (right only) / +1.5; back leg z 150-400 +1.9..+2.1. (The front-leg foot lip, -2.9, is
       gone in v23: the foot re-cut on the new rocker section.)
     - [ ] RIGHT rocker placement (PR #32): its outer face reads 5-7.5 mm inward at the tail and rear and 4-5 mm outward at the
       front, the left about the opposite and smaller: the right rocker looks turned about 0.6 deg about z against its model. It
       is what remains of the rocker inner-face items (R bottom/inner front -3.3, rear +1.9; L within 0.8). Also stale: the
       assembly note "leg feet sit about 3 mm off the rocker faces in x (rocker width is a tape value, 31 mm)"; v23 feet: front
       98.3 % of the bottom on the rocker, back 86.7 % (the 38 mm leg overhangs the ~33.5 mm rocker's inner face by 6.7 mm).
   - Doubts on frozen files (fix, if ever, through a new hub file):
     - [ ] crest bottom edges +2.4..+2.9 [+1.0..+1.1] (`parts/crest.json`; lower edge low, or a larger round on its arrises).
     - [ ] arm top outer edge at the back leg -2.5 [-2.6] (`parts/arms.json`).
   - IMG_1588-1593: closed, NOT registered (pass 1). 1588-1592 are far, zoomed shots (~1 px/mm against 2-4 for the orbit),
     taken from directions the solved orbit already covers, so they add no view of any part; 1593 is a tape close-up across the
     seat front, a reading rather than a view.
6b. Tape readings in, as checks on the photo numbers: M1, M3, M4, M5, M9, M11 (below); M7/M8 if Joe takes them.
6c. Finish detail: radii of the rounded edges (the model has sharp arrises everywhere; candidates from the critique: the seat's top back edge (PR #35, M13) and the seat front's bottom arris (PR #34, low-view crease); the rocker ends of PR #23 are traced on the
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
| **Hub** (cc-sessions "rocking-chair"; runs unattended, works to completion. **Joe, 2026-11-20: from model v18 on, all remaining work and the supervision are to run on Opus 5.5.** The hub session cannot start a session itself, so: the remaining items are done by Opus 5.5 workers the hub starts, one at a time, until Joe switches the hub session to Opus 5.5 or starts a new Opus 5.5 hub from `HUB_HANDOFF.md`; same worktree and rules either way) | `rocking-chair/`, main + short topic branches | `PLAN.md`, `LEDGER.md`; the model version numbers `parts/model_vN.*`; in `tools/build_model.py`: SEAT (surface, front, side edges, underside, closing the mesh), arms, rockers, crest, slats, front-leg outline; `parts/seat_*.json`, `parts/arm_underside.json`, `tools/arm_underside/`, `parts/side_frame.json`, `parts/lr_skew.json`, `parts/rocker_profile.json`, `parts/rocker_ends.json`, `tools/rocker_ends/`, `parts/rocker_bottom.json` (new, PR #29: the bottom-edge correction the build reads, see the Templates row), `tools/rocker_bottom/`; `tools/seat_side_ends/` (PR #30); `tools/critique/` (PR #31); `parts/rocker_section.json` and `tools/rocker_thickness/` (PR #32, the rocker's thickness across, see the Templates row); `parts/slat_turn.json` (new, PR #33: the side slats' turn, measured, `apply_in_build` false), `tools/slat_width/`, `measurements/slat_width*`; `tools/seat_roll/` (PRs #34, #35: single-photo strips of the seat's front and back edges; PR #34 adds `design.bottom_arris.from_tube` to `parts/seat_front_face.json`, see the Templates row); phase 6 onward |
| **Joinery / audit** (cc-sessions "rocking-chair-seat"; Joe attends it; it did the seat survey first) | `../rocking-chair-audit`, branch `joinery` and successors | in `tools/build_model.py`: the back-leg outline code, the placement of the legs against seat and rockers, every joint body; `tools/audit_*.py`, `tools/domino_ortho.py`; `parts/dominos.json` and any new joinery file; `reports/`; `figures/joinery/`, `figures/model_audit/`. **Hub edit, 2026-11-20 (PR #24, Joe's fix-list item 3): `parts/dominos.json` `joints.front_leg.centre_xyz` moved 1.52 mm forward along the leg face, new key `centre_provenance`; format otherwise unchanged; `tools/joinery.py` not touched. Method and data: `tools/front_domino/`.** |
| **Templates** | `../rocking-chair-templates`, branch `templates` | `templates/` (its own ledger is `templates/LEDGER.md`); reads `parts/*.json` and `parts/rocker_profile.json`. **From model v18 the rocker's outline is `rocker_profile.json` between u -330 and u 572 PLUS the two ends in `parts/rocker_ends.json` `design` (its `note` says how they join); `rocker_profile.json` alone gives the old square-cut rocker. From model v22 (PR #29) the BOTTOM edge also takes `parts/rocker_bottom.json` `correction` (`u`, `dv_mm`): bottom v = `mean_bot` + dv(u), and the same dv is added to `rocker_ends.json` `design.tail.bot` (dv runs from u -400 to 572 and is 0 outside it, so the nose is untouched); linear between stations, in the left-plane frame before `to_mean`; the top edge is unchanged; `rocker_profile.json` and `rocker_ends.json` themselves are unchanged** **From model v20 (PR #26) the seat's side-edge under-bevel in `parts/seat_scoop.json` `design` is the left/right mean (lens max 23.2 mm, was 24.4; bevel 45.7 degrees, was 46.2; y 83.5-460.7); new blocks `left` and `left_vs_right`, existing keys unchanged in meaning; the seat's plan outline is unchanged.** **PR #30: `parts/seat_edge.json` adds `ends` (a check: the seat's plan outline at both legs agrees with the model within 0.5 mm; nothing to do for templates).** **NEW (PR #27): the arms' thickness and underside are in `parts/arm_underside.json` `design` (`h_outer_mm` / `h_inner_mm` = vertical drop of the outer / inner bottom arris below the arm's OUTER top arris, straight across between them, stations `y`; `parts/arms.json` `thickness` (25, assumed) is superseded; `arms.json` itself unchanged). From model v21 (PR #28) this is what the build uses: `tools/build_model.py` reads `parts/arm_underside.json` by default (`--arm-slab` builds the old 25 mm slab), so the arms in `parts/model_v21*.glb` are the measured ones and the front-leg tops are cut at z 625.8 (was 621.9).** **NEW (PR #32, model v23): the rocker's THICKNESS ACROSS is no longer the constant 31 mm: `parts/rocker_section.json` `design` (`u` in the rocker's side-plane frame, as in `rocker_profile.json`; `T_mm` thickness, `d_outer_mm` depth of the outer face INWARD from the old outer face; linear between stations): the rocker is solid from depth d_outer(u) to d_outer(u) + T(u), 29.7 mm at the tail tip to 36.2 between the legs; `tolerance_mm` +-1.6. Plan-view stock and lamination thickness change with it; the side outline (rocker_profile + ends + bottom correction) is unchanged.** **NEW (PR #33, NOT in the model yet): `parts/slat_turn.json` `design` (`z_mm`, `turn_deg`): the side slats are turned about their own centre line, + = outer edge forward, 3.6-7.2 deg (SLAT_L the mirror; centre slat not turned); `left` / `right` blocks hold each side; `apply_in_build` false = the model and `parts/slats.json` are unchanged, so templates are unchanged until the hub applies it. If applied, the side slats' bending form needs the face turned by design(z); outline and width unchanged.** **NEW (PR #34, model v24): the seat front's BOTTOM arris in `parts/seat_front_face.json` moved 0.90-1.00 mm down and 0.40-0.50 forward (`bottom_arris_z_of_abs_x`, `bottom_arris_y_of_abs_x`, same keys and meaning; front face 1 mm taller, min 21.6); format addition `design.bottom_arris.from_tube` (note, `k_yz_right`, `k_yz_left`: provenance only, nothing to read). The seat's plan outline and top are unchanged; for templates only the front roll's shaping depth changes.** |
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
  [x] arm underside and thickness (PR #27 measured, `parts/arm_underside.json`, `tools/arm_underside/`; LANDED in model v21 by PR #28, the build's default; built arm within 0.12 / 0.14 mm of the file (outer / inner) from y 55 forward: the arm is 36.7 mm deep (vertical, outer face) at the back leg, thinning to 26.2 at y 200, 22.1 at y 300 and about 21 from y 350 to the front (20.5 square to the top), where the model assumed 25 square to the top (27.4-25.8 vertical); one smooth concave underside, lowest at y 380-420; outer face vertical; L/R within 0.3 mm at y 60-100 and 300-400, left 1.0-1.4 thinner at y 150-250 and 2.5 thinner at y 480; 10 + 14 photos, jackknife se 0.1-0.5; across: right inner arris 0.8-2.9 mm lower than the outer (3 photos), left 2.9-9.3 (1 photo); design = L/R mean; ends y 40-60 and > 490 extrapolated; M6 reads about 21 vertical) · [x] rocker bottom edge traced directly for u -330..572 (PR #29,
  `tools/rocker_bottom/`, `parts/rocker_bottom.json`; LANDED in model v22: face height square to the top edge read in single photos,
  13 (left) / 10 (right) photos per station (median), spread typically 0.2-0.6 mm, each station read at a square view (the photos'
  heights run with camera height, the face being a few degrees off square to its plane); the tail third is shallower than the old
  fitted face, -2.1 at u -330 and -2.4 at -300 (beyond the 1.6 tolerance; PR #23's end trace: -1.5 at -320), about -1 from -270 back
  to -60; from u -30 forward it agrees within 1.3 mm (worst +1.3 at u 155, the right face against its own shadow), so there the
  bottom stays the fitted one; L/R mostly within 0.6, right deeper by up to 1.5 at u 390-540; unseen by one side only: left u -220,
  -145..-135, 290-295; right -250, -190, 25; rocking radius of the trace 1045 mm rms 0.32 over u -75..405 vs 1066 (0.5 mm of sagitta;
  kept); the build moves the bottom up by up to 2.2 mm at u -330..-60, fading into the tail end by -400; top edge, feet, contact and
  z unchanged) · [x] seat side edge at both legs (PR #30, NO model change; `parts/seat_edge.json` `ends`, `tools/seat_side_ends/`): the top arris traced from the back leg's face to y 110 (y 81-110) and from y 400 to the front leg (400-435), where the build extrapolates; R 13 / L 9 photos, jackknife se 0.2-0.6 / 0.5-1.3, every trace checked by eye at 10-12 px/mm; L/R mean minus v22 -0.26..+0.49 mm, each side's shape within 0.6: provenance now "traced, agrees within 0.5 mm"; y 45-78 and ~446-500 are inside the leg joints (assumed); open: the left front corner in front of the front leg reads 3 mm narrower and 3-10 mm higher than the model's rounded-down horn (right side not solved), left to the front edge.

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

**For the joinery session, from PR #28 (hub, 23:20; model v21): the hub changed ONE line in your `tools/joinery.py` step 5c.** The back leg's rear mortises are now cut with `raw` (the untrimmed Domino) instead of `dom`: `cut(BL, raw, ...)`; the cut into the seat / arm still uses `dom`; nothing else in the file changed. Why: inside the leg the two bodies are identical (`leg ∩ raw` = `leg ∩ dom`, same bounds to 0.1 mm, volumes within 0.07 cm3), so the mortise is the same wood, but cutting with the trimmed body shared faces with the Domino: with the measured arm it left a coplanar sliver (gate FAIL `DOMINO_RAR~BLEG_R` 0.22 cm3), and in v20 it had left zero-thickness films inside the rear mortises (gone now; `figures/arm_underside/v21_joint_section.png`). Step 5c was the hub's own addition (PR #22) and your worktree was idle with nothing open, so the hub made the edit; please keep it. Also: 5b's hidden arm / front-leg Dominos moved up 3.4 mm with the leg tops; their centre is the sampled contact-face centroid, which puts DOMINO_AL 1.9 mm inboard of v20 and DOMINO_AR 0.2, so they now differ by about 1.7 mm in |x| (ASSUMED joint; centre the left on the mirrored right if you want them exact).

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
   From PR #30 (no model change) `parts/seat_edge.json` adds the block `ends`: the plan outline's two extrapolated ends (y 81-110, 400-435) checked against the photos, agrees within 0.5 mm; format addition, existing keys unchanged; `tools/seat_edge_fit.py` keeps it.

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
- M12 rocker thickness across, between the legs (about 300 mm forward of the back leg's front edge), one caliper reading on
  either rocker. The photos say 36 mm there and 29.7 at the tail tip (PR #32, `parts/rocker_section.json`); the only tape
  (IMG_1493, tail) cannot tell an easing bias of -0.8 +-1.6 from zero. One reading pins both.
- M13 seat top back edge between the slats (PR #35): the shape of the edge where the seat top meets the back face, at |x|
  about 50 (between the centre and a side slat) or 140 (between a side slat and the leg). A radius gauge, or a coin held in the
  corner (a US cent is 19 mm across, r 9.5; a dime 18 mm, r 9), says whether it is rounded and how much; and a straightedge laid
  front to back on the seat top says whether the top rolls off over the last 10-20 mm before the edge. The photos see the
  outline 2-3 mm inside the model's top arris from the front, from overhead and from behind-below, but on it from behind-above,
  where the arris was traced; a round of r 4-5 mm or more, or a roll-off of the top, would each do that, and the photos cannot
  tell which. Decides the critique item seat top/back (+1.8 [+1.4]) and that edge's 6c radius.
- M14 rocker tilt (PR #36): with the chair on the flat bench, table to the rocker's TOP edge at the nose top corner and about
  50 mm in from the tail tip, on both rockers (4 tape readings). Each rocker's top shape matches the photos within 1.2 mm; the
  photos cannot pin its tilt in 3D better than 3-4 mm/m, which is the critique's -2 at the nose / +2 at the tail (left mostly).
- M15 arm thickness on the INSIDE face (PR #27 open, PR #36): vertical, at y about 150 and about 400, both arms. The photos read
  the right arm's inner bottom arris 1-3 mm higher than the design (the mean) and the left 0-3 lower; settles `h_inner`.
- Leg stock thickness across (now +-3 mm; part of M11), only if Joe wants rough stock sizes; side templates do not depend on it.
Dropped as covered by photos: R1-R5, F1-F3, B1-B4, A1-A3 widths, C2-C4, S2/S3 (except M5), K2, K4-K6, the seat depth grid
(replaced by the tape-dot survey, leave-one-out 1.18 mm), the far photos (IMG_1588-1592: taken, not registered; see phase 6 pass 1). Every dimension that stays
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
