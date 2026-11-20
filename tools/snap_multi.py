"""USAGE: python -I tools/snap_multi.py PREFIX --seed "u,v u,v ..." --imgs 1502,1501,1503 [--band 3] --name NAME --out FILE.json
Refine ONE by-eye-seeded edge in each rectified photo separately (tools/edge_snap.py per photo), then take the per-station
median across photos. Background clutter behind an edge differs from photo to photo while the edge itself stays put on the
sheet, so the median rejects a photo whose trace latched onto clutter. Prints the per-station spread between photos
(the honest noise figure for the edge) and each photo's bias from the median.
Output JSON {"<name>": [[u, v], ...], "<name>_spread_mm": [...], "<name>_per_photo": {photo: [moved...]}}. Tiny compute."""
import json, argparse, subprocess, sys, tempfile, os, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("prefix"); ap.add_argument("--seed", required=True); ap.add_argument("--imgs", required=True)
ap.add_argument("--band", type=float, default=3.0); ap.add_argument("--name", default="edge"); ap.add_argument("--out", required=True); ap.add_argument("--lam", type=float, default=1.5)
a = ap.parse_args(); here = os.path.dirname(os.path.abspath(__file__)); res = {}
for im in a.imgs.split(","):
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as t: tmp = t.name
    subprocess.run([sys.executable, "-I", os.path.join(here, "edge_snap.py"), a.prefix, "--seed", a.seed, "--band", str(a.band), "--name", "e", "--out", tmp, "--img", im, "--lam", str(a.lam)],
                   check=True, stdout=subprocess.DEVNULL)
    d = json.load(open(tmp)); os.unlink(tmp); res[im] = (np.array(d["e"]), np.array(d["e_seed"]), np.array(d["e_moved_mm"]))
ims = list(res); M = np.stack([res[i][2] for i in ims]); P = res[ims[0]][1]
T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True); N = np.c_[-T[:, 1], T[:, 0]]
med = np.median(M, 0); E = P + med[:, None] * N; spread = M.max(0) - M.min(0)
json.dump({a.name: E.tolist(), a.name + "_seed": P.tolist(), a.name + "_spread_mm": spread.tolist(), a.name + "_per_photo": {i: res[i][2].tolist() for i in ims}}, open(a.out, "w"))
bias = " ".join(f"{i}:{np.median(M[k] - med):+.2f}" for k, i in enumerate(ims))
print(f"{a.name}: {len(med)} stations | moved from seed median {np.median(med):+.2f} (5..95 pct {np.percentile(med, 5):+.2f} .. {np.percentile(med, 95):+.2f}) | "
      f"photo spread median {np.median(spread):.2f}, 90th pct {np.percentile(spread, 90):.2f} mm | photo bias {bias}")
