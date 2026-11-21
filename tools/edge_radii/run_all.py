"""USAGE: tools/py.sh tools/edge_radii/run_all.py [OUT work/edge_radii/results.json]
Phase 6c: reruns every single-photo measurement listed in tools/edge_radii/edges.json with its tape scale:
  bands   - prof.py (tone profile across the edge) then band.py (B10/B50 tone-band widths, blur, r bracket)
  corners - cornerfit.py at each listed arm length (radius of a corner seen square-on)
One photo at a time, sequential; about 1 GB and under a minute."""
import sys, json, subprocess, os
import numpy as np

out = sys.argv[1] if len(sys.argv) > 1 else "work/edge_radii/results.json"
E = json.load(open("tools/edge_radii/edges.json"))
os.makedirs("work/edge_radii/run", exist_ok=True)


def py(*args):
    r = subprocess.run([sys.executable, "-I", *map(str, args)], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr)
    return r.stdout.strip().splitlines()[-1]


res = dict(scales=E["scales"], bands=[], corners=[])
for b in E["bands"]:
    pre = f"work/edge_radii/run/{b['id']}"
    py("tools/edge_radii/prof.py", b["img"], *b["line"], b["half"], pre)
    pxmm = E["scales"][b["img"]]["pxmm"]
    r = json.loads(py("tools/edge_radii/band.py", pre + ".json", pxmm, *b["wood"], *b["sil"]))
    r.update(id=b["id"], family=b["family"], img=b["img"], what=b["what"], line=b["line"], by_eye=b["by_eye"])
    res["bands"].append(r)
    print(b["id"], "B10", r["B10_mm"], "B50", r["B50_mm"], "blur", r["step_fwhm_mm"], r["kind"])
for c in E["corners"]:
    pxmm = E["scales"][c["scale"]]["pxmm"]; runs = []
    for arm in c["arms"]:
        runs.append(json.loads(py("tools/edge_radii/cornerfit.py", c["img"], *c["box"], *c["seed"], arm, pxmm,
                                  f"work/edge_radii/run/{c['id']}_arm{arm}.jpg")))
    R = [q["R_mm"] for q in runs]
    res["corners"].append(dict(id=c["id"], family=c["family"], img=c["img"], what=c["what"], pxmm=pxmm, seed=c["seed"], box=c["box"],
                               R_mm_by_arm=dict(zip(map(str, c["arms"]), R)), turn_deg=[q["turn_deg"] for q in runs],
                               R_mm_median=round(float(np.median(R)), 2), R_mm_range=[min(R), max(R)]))
    print(c["id"], "R", R, "turn", [q["turn_deg"] for q in runs])
json.dump(res, open(out, "w"), indent=1)
