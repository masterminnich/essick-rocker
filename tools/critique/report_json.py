"""USAGE: python3 -I tools/critique/report_json.py STATS.json ITEMS.json OUT.json [SHIFT_CHECK.json ...]
Phase 6 critique, step 4: the committed summary (reports/critique_vN.json) from stats.py's full output (kept in work/): per
region (member | kind | edge | stretch) and side, the non-held-out n photos, n points, median, spread, se and the held-out
median; per region the symmetric and antisymmetric parts, tolerance, score and rank; plus the fix items (items.py), the run's
photo counts and the shift-test results."""
import sys, json
from pathlib import Path
S = json.load(open(sys.argv[1])); items = json.load(open(sys.argv[2])); out = sys.argv[3]
run = json.load(open(Path(S["run"]) / "run.json"))


def side(v):
    t, h = v["train"], v["held"]
    r = dict(n_photos=t["n_photos"] if t else 0, n_points=t["n_points"] if t else 0)
    if t: r.update(median=t["median"], spread=t["spread"], se=t["se"], ease_k=t["ease_k"])
    r.update(held_out_median=h["median"] if h else None, held_out_photos=h["n_photos"] if h else 0,
             outline_points=v["outline_points"], searched=v["searched"], measured=v["measured"])
    return r


regs = []
for e in S["regions"]:
    r = {k: e[k] for k in ("region", "member", "kind", "edge", "stretch", "tol_mm")}
    for k in ("symmetric", "antisymmetric", "sym_se", "held_symmetric", "paired", "one_side", "score", "rank"):
        if k in e: r[k] = e[k]
    r["sides"] = {s: side(v) for s, v in e["sides"].items()}
    regs.append(r)
shift = [json.load(open(f)) for f in sys.argv[4:]]
res = dict(model=run["glb"], sign=S["sign"], gap_definition="signed distance from the model's outline to the wood edge found along the outline's outward normal, in mm at the part",
           photos_solved=len(run["photos"]), photos_ranked=S["photos_used"], photos_held_out=S["photos_held"], held_out=S["holdout"],
           tolerance_mm={"joint (most points within 20 mm of another part)": 0.8, "free curve": 1.6},
           ranking="silhouettes only, non-held-out photos only, by |symmetric| / tolerance", items=items, shift_tests=shift,
           regions=sorted(regs, key=lambda r: (r.get("rank", 10 ** 6), r["region"])))
Path(out).write_text(json.dumps(res, indent=0)); print("wrote", out, len(regs), "regions", len(items), "items")
