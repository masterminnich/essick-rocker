"""USAGE: tools/py.sh tools/seat_roll/fig_back.py PICK_BACK.json STATS.json OUT.png [--summary OUT.json]
The seat's top back edge (parts/seat_back.json design.top_arris), two panels in the house style:
  left  - the direct trace (tools/seat_roll/strip.py --line back + pick.py --wood -8 -6 --lo -5.5 --hi 4, single photos): where
          the wood's outline lies against the model's top arris, per photo and half, only in the rows between the slats
          (|x| 42-64 and 112-170; in front views the slats hide the edge elsewhere). - = the wood ends short of the arris.
  right - the critique's regions of that edge: silhouette against crease (the tone line), per 50 mm stretch, left/right mean.
--summary writes the per-photo numbers the PR quotes. Tiny compute."""
import json, math, argparse
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
ap = argparse.ArgumentParser(); ap.add_argument("pick"); ap.add_argument("stats"); ap.add_argument("out"); ap.add_argument("--summary")
a = ap.parse_args()
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE, "text.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False})
VIEW = {"1559": "front, 30° above", "1528": "front-left, above", "1549": "overhead, 71° above", "1492": "behind, below",
        "1540": "behind, above (a tracing photo)"}
gap = lambda x: 42 <= abs(x) <= 64 or 112 <= abs(x) <= 170
P = json.load(open(a.pick)); res = {}
for s in P:
    if s["photo"] not in VIEW: continue
    t = np.array([r["t"] for r in s["rows"] if gap(r["x"])])
    if len(t) >= 10: res.setdefault(s["photo"], {})[s["side"]] = dict(median=round(float(np.median(t)), 2), q25=round(float(np.percentile(t, 25)), 2),
                                                                     q75=round(float(np.percentile(t, 75)), 2), rows=int(len(t)), pxmm=round(s["pxmm"], 1))
order = ["1559", "1528", "1549", "1492", "1540"]
fig, (A, B) = plt.subplots(1, 2, figsize=(13.5, 5.0), facecolor=SURF, gridspec_kw={"width_ratios": [1.15, 1]})
for ax in (A, B): ax.set_facecolor(SURF); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
A.axvspan(-0.8, 0.8, color=GRID, alpha=0.6, lw=0, zorder=0, label="the item's tolerance, ±0.8 (joint: the slats)")
A.axvline(0, color=ORANGE, lw=1.6, label="model's top arris (v23 = v24)")
for i, p in enumerate(order):
    for s_, dy, mk in (("L", -0.13, "o"), ("R", 0.13, "s")):
        r = res.get(p, {}).get(s_)
        if not r: continue
        A.plot([r["q25"], r["q75"]], [i + dy] * 2, color=BLUE, lw=1.2); A.plot(r["median"], i + dy, mk, color=BLUE, ms=7)
A.plot([], [], "o", color=BLUE, label="left half, median and quartiles"); A.plot([], [], "s", color=BLUE, label="right half")
A.set_yticks(range(len(order))); A.set_yticklabels([f"IMG_{p}\n{VIEW[p]}, {res[p]['L']['pxmm']} px/mm" for p in order], fontsize=9); A.invert_yaxis()
A.set_xlim(-4.5, 2.5); A.set_xlabel("wood outline against the top arris, mm (- = the wood ends short: model outside)")
A.set_title("Direct trace between the slats, single photos", color=INK, loc="left"); A.legend(frameon=False, fontsize=9, loc="lower left")
R = {r["region"]: r for r in json.load(open(a.stats))["regions"]}
def lr(kind, x, k):
    r = R.get(f"SEAT|{kind}|top/back|x {x}")
    v = [r["sides"].get(s, {}).get(k) for s in "LR"] if r else [None]
    return np.mean([q["median"] for q in v]) if all(v) and not any(math.isnan(q["median"]) for q in v) else np.nan
st = [0, 50, 100, 150]; xs = np.array(st) + 25; w = 14
B.bar(xs - w / 2, [lr("crease", x, "train") for x in st], w, color=MUTE, label="crease (tone line), ranking photos")
B.bar(xs + w / 2, [lr("sil", x, "train") for x in st], w, color=BLUE, label="silhouette, ranking photos")
B.axhspan(-0.8, 0.8, color=GRID, alpha=0.6, lw=0, zorder=0, label="the item's tolerance, ±0.8 (joint: the slats)"); B.axhline(0, color=ORANGE, lw=1.6)
B.set_xticks(xs); B.set_xticklabels([f"{x}-{x + 50}" for x in st]); B.set_xlabel("|x| stretch, mm"); B.set_ylim(-1, 3)
B.set_ylabel("critique gap, left/right mean, mm (+ = model outside)")
B.set_title("Critique v24: tone line on the arris, outline beyond it", color=INK, loc="left"); B.legend(frameon=False, fontsize=9, loc="upper right")
fig.tight_layout(); fig.savefig(a.out, dpi=130, facecolor=SURF)
if a.summary: json.dump(dict(rows_used="|x| 42-64 and 112-170 (between the slats)", photos=res), open(a.summary, "w"), indent=1)
print(json.dumps(res))
