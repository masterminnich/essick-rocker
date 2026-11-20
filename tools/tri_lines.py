"""USAGE: python -I tools/tri_lines.py PREFIX SEEDS.json OUTDIR [--only NAME,NAME] [--photos 1507,1508,... | --pool 1507,1508,...]
Run tools/edge_tri.py for every line in SEEDS.json: a list of {"name", "seed" ("u,v u,v ..."), "inside" ("u,v"), and optionally
"mode" (clean|far|all), "band", "ddeg", "depth_guess", "depth_fixed", "seed_photo", "photos" (use exactly these) or "pool" (candidates, still filtered by mode), "margin", "max_photos", "clip"}.
Writes OUTDIR/<name>.json per line and OUTDIR/per_photo.json (every photo's own trace, key "<name>@<photo>") for the by-eye
check on single rectified photos (tools/tri_show.py). Tiny compute, one photo in memory at a time."""
import json, sys, subprocess, argparse, os
ap = argparse.ArgumentParser(); ap.add_argument("prefix"); ap.add_argument("seeds"); ap.add_argument("outdir"); ap.add_argument("--only", default=None); ap.add_argument("--photos", default=None); ap.add_argument("--pool", default=None)
a = ap.parse_args(); here = os.path.dirname(os.path.abspath(__file__)); os.makedirs(a.outdir, exist_ok=True); dump = os.path.join(a.outdir, "per_photo.json")
only = a.only.split(",") if a.only else None
if os.path.exists(dump) and not only: os.unlink(dump)
for L in json.load(open(a.seeds)):
    if only and L["name"] not in only: continue
    cmd = [sys.executable, "-I", os.path.join(here, "edge_tri.py"), a.prefix, "--seed", L["seed"], "--inside=" + L["inside"], "--name", L["name"], "--out", os.path.join(a.outdir, L["name"] + ".json"),
           "--dump", dump, "--mode", L.get("mode", "clean"), "--band", str(L.get("band", 6)), "--ddeg", str(L.get("ddeg", 1)), "--max-photos", str(L.get("max_photos", 5)), "--clip", str(L.get("clip", 1.5))]
    ph = L.get("photos", a.photos)
    if ph: cmd += ["--photos", ph]
    elif L.get("pool", a.pool): cmd += ["--pool", L.get("pool", a.pool)]
    for k in ("depth_guess", "depth_fixed", "seed_photo", "margin"):
        if k in L: cmd += ["--" + k.replace("_", "-"), str(L[k])]
    subprocess.run(cmd, check=True)
