"""USAGE: python -I tools/slat_clean_snap.py --dir work/parts/back/f --seeds parts/slats.json [--band 4] [--passes 2] --out work/parts/back/f/slat_edges.json
Re-trace the six slat edges using, for each edge, ONLY the photos in which that edge is a clean silhouette of the slat's
BACK face. Why: a slat is ~10 mm thick. A camera standing to the right of an edge's line sees the slat's right side face,
so the outline it sees on that side is the FRONT arris, which lands t * (xc - u) / depth further out on the back-face sheet
(2-5 mm for the off-axis photos). Pooling photos from both sides therefore fattens and smears every edge. A photo is
"clean" for an edge when the camera is inboard of the edge line (side face hidden): (xc - u) * side <= margin.
Each edge is refined per clean photo (tools/edge_snap.py, seeds = previous fair curves), averaged across the clean photos;
pass 2 reseeds from pass 1 with a tighter band. --primary: take the edge from the most on-axis clean photo only
(an off-axis photo shifts the edge by sheet-depth error * (xc - u) / depth; the on-axis one does not), the rest are checks. Also prints what the NOT-clean photos read, as a check of the reasoning.
Sheets: DIR/sc (centre slat), DIR/so (outer slats) with per-photo rectified images. Tiny compute."""
import sys, json, argparse, subprocess, tempfile, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--seeds", required=True); ap.add_argument("--band", type=float, default=4.0)
ap.add_argument("--passes", type=int, default=2); ap.add_argument("--margin", type=float, default=60.0); ap.add_argument("--out", required=True)
ap.add_argument("--primary", action="store_true", help="take the edge from the most on-axis clean photo alone (others = check), corrected for its small arris bias")
ap.add_argument("--arris-k", type=float, default=0.75, help="observed / square-arris-predicted outward bias (eased arrises), from the not-clean readings")
ap.add_argument("--vrange", nargs=2, type=float, default=[65, 715]); ap.add_argument("--thickness", type=float, default=10.0)
a = ap.parse_args(); cams = Cameras.load(); F = json.load(open(a.seeds))["fits"]
SIDE = {"slatC_left": -1, "slatC_right": 1, "slatR_in": -1, "slatR_out": 1, "slatL_in": 1, "slatL_out": -1}     # outward direction of the edge in u


def snap(prefix, seed, img, band):
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as t: tmp = t.name
    subprocess.run([sys.executable, "-I", str(ROOT / "tools/edge_snap.py"), prefix, "--seed", seed, "--band", str(band), "--name", "e", "--out", tmp, "--img", img], check=True, stdout=subprocess.DEVNULL)
    d = json.load(open(tmp)); os.unlink(tmp); return np.array(d["e"])


out = {}; info = {}
for k, side in SIDE.items():
    prefix = f"{a.dir}/{'sc' if k.startswith('slatC') else 'so'}"; pj = json.load(open(prefix + "_plane.json"))
    vs = np.arange(a.vrange[0], a.vrange[1] + 1, 1.0); cur = np.polyval(F[k]["coef"], vs); umean = float(cur.mean())
    yb = float(np.mean([r[1] for r in pj["table"]])); rows = []
    for nm in pj["photos"]:
        c = cams.views[nm].center; depth = abs(c[1] - yb); lean = (c[0] - umean) * side
        rows.append((nm[4:8], lean <= a.margin, a.thickness * max(lean, 0) / depth, abs(c[0] - umean) / depth))
    clean = [r[0] for r in rows if r[1]]; other = [r[:3] for r in rows if not r[1]]
    prim = min(rows, key=lambda r: r[3]); pbias = a.arris_k * prim[2]      # most on-axis photo: least sensitive to sheet-depth error
    for p in range(a.passes):
        band = a.band if p == 0 else max(2.0, a.band / 2); seed = " ".join(f"{u:.2f},{v:.0f}" for u, v in zip(cur[::10], vs[::10]))
        per = {}
        for im in clean:
            e = snap(prefix, seed, im, band); per[im] = np.interp(vs, e[:, 1], e[:, 0])
        raw = per[prim[0]] - side * pbias if a.primary else np.mean(list(per.values()), 0)
        # reseed from a smooth version of this pass (running median, 41 mm)
        pad = np.r_[raw[:20][::-1], raw, raw[-20:][::-1]]; cur = np.array([np.median(pad[i:i + 41]) for i in range(len(raw))])
    out[k] = np.c_[raw, vs].tolist()
    dis = (max(per.values(), key=lambda x: x.mean()) - min(per.values(), key=lambda x: x.mean())) if len(per) > 1 else np.zeros(len(vs))
    chk = []
    for im, _, pred in other:                         # what a not-clean photo reads: expected to sit OUTWARD of the clean edge
        e = snap(prefix, " ".join(f"{u:.2f},{v:.0f}" for u, v in zip(cur[::10], vs[::10])), im, a.band + 2)
        chk.append(f"{im} {np.median((np.interp(vs, e[:, 1], e[:, 0]) - raw) * side):+.1f} (square-arris prediction {pred:+.1f})")
    info[k] = {"clean_photos": clean, "between_clean_photos_mm": float(np.sqrt(np.mean(dis ** 2))), "primary": prim[0] if a.primary else None, "primary_bias_removed_mm": pbias if a.primary else 0.0,
               "other_clean_minus_edge_outward_mm": {im: float(np.median((per[im] - raw) * side)) for im in clean if im != prim[0]}}
    print(f"{k:12s} " + (f"primary {prim[0]} (bias removed {pbias:.2f}) | other clean photos read outward by " + ", ".join(f"{im} {v:+.1f}" for im, v in info[k]["other_clean_minus_edge_outward_mm"].items()) + " | " if a.primary else "")
          + f"clean photos {','.join(clean)} | rms difference between them {info[k]['between_clean_photos_mm']:.2f} mm | moved from old fair curve "
          f"{np.median((raw - np.polyval(F[k]['coef'], vs)) * side):+.2f} mm outward | not-clean photos read outward by: {'; '.join(chk) or '-'}")
json.dump(out, open(a.out, "w")); json.dump(info, open(a.out.replace(".json", "_info.json"), "w"), indent=1)
