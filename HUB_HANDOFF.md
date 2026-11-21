# Hub hand-over brief

Joe, 2026-11-20: "after it lands continue working unsupervised but do all the remaining work including supervision in opus 5.5".
This file is the complete brief for whoever is the HUB (coordinator) from model v18 on: a session on Opus 5.5, or an Opus 5.5
worker started by the hub. Paste it as the first message of a new session, or read it at the start of a turn.

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

## What is left, in order (PLAN.md has the detail)
1. Joe's fix-list item 3: the front-leg Domino sits off-centre on the leg (his viewer screenshot of v15). Re-measure the slot's
   position on the leg face against the leg's two edges (`tools/domino_ortho.py`; orthophotos of the face with a mm grid, as
   `tools/rear_ortho.py` did for the rear Dominos) and centre it if the photos agree. `parts/dominos.json` and
   `tools/joinery.py` belong to the joinery session: Joe gave this item to the hub, so make a small edit and name it in the PR.
2. The 3 mm question at the seat's right front corner (LEDGER 17:33 and 19:05).
3. Left-side check of the seat scoop (right side measured, left assumed mirror).
4. Arm underside and thickness: a NEW file, not `parts/arms.json`.
5. Rocker bottom edge traced directly for u -330..572 (lead: at u -320 the traced side face is 26.4 / 26.0 mm high, the profile
   says 27.7; the ends in `parts/rocker_ends.json` are already traced directly; `tools/rocker_ends/` is a working
   ortho -> trace -> fit pipeline to adapt).
6. Seat side edge behind y 400, where it meets the back leg.
7. Register IMG_1588-1593 (half resolution only; see compute rules).
8. Phase 6 critique loop, 6b tape checks as they arrive, 6c edge radii, then phase 7: final templates are the TEMPLATES
   session's job (branch `templates`); tell it through PLAN.md what changed.

Do NOT touch `templates/`, `seat/`, `parts/crest.json`, `parts/arms.json`, the back-leg outline or leg placement. Do not change
`parts/rocker_profile.json` or its `right_vs_left`.

## How work lands
- One fix = one topic branch = one PR, squash-merged, then the next model number on main: `tools/model.sh --out parts/model_vN`
  (build -> joinery -> audit -> gate; a number only on "assembly check: PASS"). On a branch build to `work/...` to test; never
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
registering wakes and write Joe a closing summary.

## What Joe sees
Each reply is what Joe reads when he looks in. Short and plain: what landed (PR link, model number, viewer link), the numbers
that matter, what is open, what is next. Working HTTPS links, never local paths.
