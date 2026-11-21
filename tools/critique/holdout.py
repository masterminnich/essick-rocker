"""USAGE: work/toolkit/rk.sh tools/critique/holdout.py [OUT.json]   (default tools/critique/holdout.json)
The fixed held-out photo list of the phase 6 critique (about 15%): photos whose numbers are reported but never used to rank
or to decide a fix, so a later fix can be judged on photos it was not tuned on.
Rule (deterministic, chosen to span the views): camera azimuth about the seat centre (0 = in front, +90 = the chair's right)
in 12 sectors of 30 degrees, elevation -15..45; from every sector holding at least 3 solved photos, the photo whose
elevation is the sector's median (ties: lower number); plus the median-elevation photo of the overhead group (elevation > 45
degrees) and of the low group (elevation < -15), each on the chair's right half and left half. Run once and committed; do not regenerate it to suit a result."""
import sys, json
sys.path.insert(0, ".")
import numpy as np
from rocker.cameras import Cameras
c = Cameras.load()
rows = []
for n in c.names():
    C = c[n].center; r = np.hypot(C[0], C[1] - 270)
    rows.append((n, np.degrees(np.arctan2(C[0], C[1] - 270)), np.degrees(np.arctan2(C[2] - 500, r))))


def pick(group):
    group = sorted(group, key=lambda t: t[2]); return group[(len(group) - 1) // 2][0]


H = {}
mid = [t for t in rows if -15 <= t[2] <= 45]
for k in range(12):
    lo = -180 + 30 * k
    g = [t for t in mid if lo <= t[1] < lo + 30]
    if len(g) >= 3: H[pick(g)] = f"azimuth {lo}..{lo + 30}, {len(g)} photos"
for nm, f in (("overhead (elevation > 45)", lambda e: e > 45), ("low (elevation < -15)", lambda e: e < -15)):
    for sd, fs in (("right", lambda az: az >= 0), ("left", lambda az: az < 0)):
        g = [t for t in rows if f(t[2]) and fs(t[1])]
        if g: H[pick(g)] = f"{nm}, {sd} half, {len(g)} photos"
out = sys.argv[1] if len(sys.argv) > 1 else "tools/critique/holdout.json"
info = {n: dict(why=w, azimuth=round(next(t[1] for t in rows if t[0] == n), 1), elevation=round(next(t[2] for t in rows if t[0] == n), 1)) for n, w in sorted(H.items())}
json.dump({"rule": __doc__.split("Rule")[1].strip(), "n_solved": len(rows), "held_out": info}, open(out, "w"), indent=1)
print(f"{len(H)} of {len(rows)} held out ({100 * len(H) / len(rows):.0f}%):"); [print(" ", n, v) for n, v in info.items()]
