# Hub hand-over brief

Joe, 2026-11-20: "after it lands continue working unsupervised but do all the remaining work including supervision in opus 5.5".
This file is the complete brief for whoever is the HUB (coordinator): a session on Opus 5.5, or an Opus 5.5 worker started by
the hub. Current model: v24 (since PR #34); the hub's own work is complete and waits on Joe (below). Paste it as the first message of a new session, or read it at the start of a turn.

You are the HUB of Joe's ESSICK rocking chair project (Joe = Joseph Minnich, GitHub masterminnich). You work unattended until
the plan is complete and you chain your own turns (see "Chaining turns"). Address Joe by name when you write to him.

## The project
Rebuild a sculpted walnut rocking chair as a dimensionally accurate 3D model from about 100 phone photos, then 1:1 printable
part templates. Design intent = a symmetric model. Tolerance 1/32" (0.8 mm) on hard points, 1/16" (1.6 mm) on free curves. Every
dimension carries provenance (measured / triangulated / fitted / assumed). Report accuracy with numbers. Only ask Joe for extra
data that is quick and high-value; model work never waits on tape readings.

## Where
- Your worktree, the only one you edit: `/Users/sean/.cc-sessions/code2-fresh-home/.cc-sessions/scratch/726d315d-a06f-409b-b996-e0d36778bd9c/rocking-chair`.
  Start EVERY shell command with `cd` to that path (the shell resets). The sibling worktrees (rocking-chair-audit, -crest,
  -seat, -templates, -viewer) are read-only.
- GitHub: https://github.com/masterminnich/essick-rocker . Viewer: https://masterminnich.github.io/essick-rocker/ (shows the
  newest `parts/model_vN.glb` on main about a minute after a push).
- Read first, in this order: `PLAN.md` (conventions, phases, "Sessions and who owns what", Joe's fix list), the last entries of
  `LEDGER.md` (continue from the newest NEXT), then the memory files in
  `/Users/sean/.cc-sessions/code2-fresh-home/.claude/projects/-Users-sean--cc-sessions-code2-fresh-home--cc-sessions-scratch-726d315d-a06f-409b-b996-e0d36778bd9c/memory/`
  (`essick-rocker-reconstruction.md` has the methods that worked and the lessons).

## Every turn, first
1. `tools/push.sh --pull-main` (plain `git fetch origin` fails here; `tools/push.sh BRANCH` pushes a branch, `tools/push.sh main` pushes main).
2. Read PLAN.md "Sessions and who owns what".
3. List open PRs and their comments as Joe (see "Identity"). If another session left a PR open: trial-build main + its branch
   (unchanged parts must be vertex-identical on the `_shapes.glb`), merge it, issue the next model number.

## State and what is left (2026-11-21 03:40 PST; main = model v24)
The hub's unattended work is COMPLETE. Every hub item of the critique's ranked list (`reports/critique_v24.md`) is fixed or
measured; the accuracy report is `reports/accuracy_v24.md`. Nothing runs unless Joe answers or a reading arrives.
`tools/critique/` exists (rerun: its README): EVERY model change must pass it, improving the ranking AND the 15 held-out photos
(`tools/critique/holdout.json`) with nothing else worse, after `tools/model.sh` prints "assembly check: PASS".

What landed since this brief was first written (model number after each):
- #24 front-leg Domino centred on the leg face, 1.5 mm forward (fix-list item 3) - v19
- #25 seat front corners: the 3 mm question is L/R asymmetry, model is the mean - no change (v19)
- #26 seat scoop left side traced; design = L/R mean - v20
- #27 arm underside and thickness (`parts/arm_underside.json`) - held at v20 (joinery sliver)
- #28 the build uses the measured arm - v21
- #29 rocker bottom edge traced directly, tail third up to 2.2 mm shallower - v22
- #30 seat side edge at both legs: agrees within 0.5 mm - no change (v22)
- #31 critique pass 1, `tools/critique/`, ranked fix list - no change (v22)
- #32 rocker thickness across 29.7-36.2 mm (`parts/rocker_section.json`) - v23
- #33 side slats' turn measured (`parts/slat_turn.json`, not applied) - no change (v23)
- #34 seat front underside arris (a spine/outline slip), 0.94 mm lower - v24
- #35 seat top back edge: cannot be told (M13) - no change (v24)
- #36 rocker top at nose/tail and arm inner edge: asymmetry + pose (M14, M15) - no change (v24)
- #37 phase 6c edge radii, record only (`parts/edge_radii.json`, M16) - no change (v24)

Waits on Joe (model's current value in brackets; any of them may come in any order):
1. Yes/no on the slat turn (`parts/slat_turn.json`, 7.2 deg at z 375 to 3.6 at z 1000; model: not turned). YES: set
   `apply_in_build` true, `tools/model.sh --out work/trial/v25`, critique rerun (ranking + held-out), then v25 on main and a
   Templates-row note (bending-form face turned). NO: record it in PLAN and LEDGER, nothing else.
2. Readings (PLAN "Hand measurements"; each: fold in per its text, rerun the critique if a part changes):
   - M6 arm thickness at the front end [vertical drop of the outer bottom arris 21.2 at y 510, `arm_underside.json`]
   - M8 rocker tail tip to nose top corner, per rocker [1115.7; photos L 1118.6, R 1112.3, each +-2]
   - M9 table to the top of the seat side edge just behind the front leg, L and R [z 411.5 at y 434, both sides; photos: R 3.7-5.9 lower]
   - M12 rocker thickness across between the legs [36.2; 29.7 at the tail tip]
   - M13 seat top back edge between the slats, radius or roll-off [sharp arris]
   - M14 table to the rocker's top edge at the nose top corner and 50 mm in from the tail tip, both rockers [z 124.6 at y 620 and 185.4 at y -435, both sides]
   - M15 arm thickness on the inside face at y 150 and 400, both arms [inner drop 33.5 and 23.1]
   - seat front corner, outer side at y 500-530 (tape or profile gauge) [critique -3.3, right only; model = L/R mean]
   - M16 edge radii by gauge or coin: arm top outer arris and front end, rocker tail corners in plan, rocker bottom arris, one leg arris [model sharp; photos: tail corners 2.7-3.6, leg 0.6-1.5]
   - checks in 6b: M1 seat front thickness [38 beside the pommel], M3 crest height at the centre [74.7; tape 77.5], M4 centre slat thickness [~10], M5 centre slat width under the crest [100.0-100.5; tape 98.3], M11 Domino end [24 x 10 + glue line]; optional M2 [side edge face 18 over a 24 bevel], M7 table to crest top [1082.7], M10 scallop depth [21.3]
3. Joinery session (its files; the hub only requests): back-leg foot about 3 mm narrower than the model (critique #1 +4.07);
   front leg about 2 mm forward of the wood at z 150-600; front-leg top at the arm +3.4 (right); rocker placement (right rocker
   turned about 0.6 deg about z); the arm / front-leg Domino centre sampled off the mesh (`parts/dominos.json`). When it lands
   a change: trial-build main + its branch (unchanged parts vertex-identical on `_shapes.glb`), critique, next model number.
4. Doubts on frozen files (fix, if ever, through a new hub file, never in place): crest bottom edges +2.4..+2.9 (a round explains
   at most 0.9); arm top outer edge at the back leg -2.5 [-2.6].
5. Phase 7: final templates are the TEMPLATES session's job, after the slat-turn answer and the readings Joe wants before sign-off.
   It must read: `parts/rocker_profile.json` + `parts/rocker_ends.json` `design` + `parts/rocker_bottom.json` `correction` (side
   outline), `parts/rocker_section.json` (thickness across), `parts/slats.json` (+ `parts/slat_turn.json` only if applied),
   `parts/crest.json`, `parts/arms.json` + `parts/arm_underside.json`, `parts/seat_*.json` (edge, front, front_face, scoop, back),
   `parts/back_legs.json`, `parts/side_frame.json`, `parts/dominos.json`, and `parts/edge_radii.json` (shaping notes only). The
   PLAN Templates row has every format detail.

Do NOT touch `templates/`, `seat/`, `parts/crest.json`, `parts/arms.json`, the back-leg outline or leg placement. Do not change
`parts/rocker_profile.json` or its `right_vs_left`, `parts/dominos.json` (except as the joinery session asks), `tools/joinery.py`,
`tools/audit_*.py`.

## How work lands
- One fix = one topic branch = one PR, squash-merged, then the next model number on main: `tools/model.sh --out parts/model_vN`
  (build -> joinery -> audit -> gate; a number only on "assembly check: PASS" AND a critique rerun that improves the ranking and
  the 15 held-out photos with nothing else worse; `tools/critique/README.md`). On a branch build to `work/...` to test; never
  commit `parts/model_v*` on a branch. Model numbers, PLAN.md and LEDGER.md are edited only by the hub, on main.
- PRs are Joe's progress record: a detailed body with photos, overlays, plots, the journey (dead ends, roadblocks) and the
  numbers. Figures are committed under `figures/<topic>/` and linked by commit hash
  (`https://github.com/masterminnich/essick-rocker/blob/<sha>/figures/...?raw=true`). Check every claim in a PR body against the
  numbers before merging. PR #23 is a good pattern.
- Keep `parts/*.json` formats stable, or call a change out in the PR, LEDGER and the PLAN ownership table.
- After each landing: tick the item in PLAN.md, add a LEDGER entry (run `date` first; real clock, PST; computed numbers only,
  nothing read off a picture by eye), update the memory file's state.
- Joe reads overlay figures closely: a line that visibly misses the wood needs an explanation in the PR. Design = left/right
  mean, so on one side's photos the model can sit 2-3 mm off the real part; say so wherever it shows.

## Identity
- Commits as Joe, plain subject, NO Claude attribution or co-author trailer, in commits or PR bodies:
  `git -c user.name="Joseph Minnich" -c user.email="36314304+masterminnich@users.noreply.github.com" commit ...`
- GitHub as Joe (the machine's default gh login is the wrong identity):
  `GH() { env -u GH_TOKEN -u GITHUB_TOKEN GH_CONFIG_DIR=/Users/sean/.cc-sessions/code2-fresh-home/.cc-sessions/users/726d315d-a06f-409b-b996-e0d36778bd9c/gh /opt/homebrew/bin/gh "$@"; }`
  then e.g. `GH pr list -R masterminnich/essick-rocker`.
- Never print tokens or put them in files, logs, chat or argv. To check a pushed figure:
  `GH api "repos/masterminnich/essick-rocker/contents/<path>?ref=<sha>" --jq .size`

## Compute safety (this laptop is a shared hub that crashed twice from this project)
- No full-resolution COLMAP feature extraction, matching or bundle adjustment. The camera model `work/solve/model` is final; do
  not re-solve. New photos only by registering into that model at half resolution, one job, thread-capped.
- ONE compute job at a time, always through `tools/safe_run.sh` (wrappers: `tools/py.sh [-m GB] [-t MIN] script args`, default
  3 GB / 8 min, has trimesh and matplotlib; `tools/model.sh`). Never in the background, never from parallel agents. Before
  anything that loads many images or optimises, state the expected peak memory and time.
- Tiny scripts: `work/toolkit/rk.sh SCRIPT args` (numpy, cv2, pillow, scipy, pycolmap; no trimesh, no matplotlib). Plain
  `python3` has no numpy (use `python3 -I` for json-only scripts).
- The safe_run lock is shared across worktrees; on "refusing" wait 15 s and retry:
  `run() { for try in 1 2 3 4 5 6 7 8; do out=$("$@" 2>&1 | tail -${N:-8}); echo "$out"; echo "$out" | grep -q refusing || break; sleep 15; done; }`
- safe_run does not pass stdin heredocs: write a temp script under `work/`. The shell is zsh (`${=var}` to word-split;
  unmatched globs are errors).

## Measuring rules that held
- Seed every edge by eye on zoomed, gridded views; refine only within a small band; ALWAYS check a trace by eye on a SINGLE
  photo at 10+ px per mm, never on a small preview or a multi-photo blend.
- Do not read numbers off pictures; compute them.
- Charts follow the house style in `tools/rocker_ends/fig_profile.py` and `tools/seat_back/fig_section.py` (blue #2a78d6,
  orange #eb6834, surface #fcfcfb, ink #0b0b0b / #52514e, grid #e4e3df; one axis, legend, direct labels; look at the render
  before using it).

## Other sessions
Joinery / audit session (cc-sessions "rocking-chair-seat"): owns back-leg code, leg placement, joint bodies, `tools/audit_*.py`,
`parts/dominos.json`. Templates session: `templates/`. The channel to them is PLAN.md "Sessions and who owns what", PR bodies
and PR comments. Before editing another session's file: say so in the PR, keep it small.

## Chaining turns
A turn ends when you reply; nothing brings you back unless you register a wake first. Before ending ANY turn with work left:
`ccs-wake --in 2m --note "Rocking chair HUB: continue from LEDGER.md last NEXT on main; first: tools/push.sh --pull-main, PLAN 'Sessions and who owns what', open PRs and comments"`
(for a local job still running prefer `ccs-wake --pid N` or `--file PATH`). Keep going until the plan is complete; then stop
registering wakes and write Joe a closing summary. (As of 2026-11-21 the plan's hub part is complete: register no wakes until
Joe answers or a reading arrives.)

## What Joe sees
Each reply is what Joe reads when he looks in. Short and plain: what landed (PR link, model number, viewer link), the numbers
that matter, what is open, what is next. Working HTTPS links, never local paths.
