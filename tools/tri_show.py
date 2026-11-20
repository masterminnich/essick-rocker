"""USAGE: python -I tools/tri_show.py PREFIX OUTDIR PHOTO OUT.jpg SCALE GRID "U0 U1 V0 V1" ["U0 U1 V0 V1" ...] [--final]
By-eye check of triangulated lines: draws, on ONE rectified photo, that photo's own traces from OUTDIR/per_photo.json
(written by tools/tri_lines.py) in zoomed gridded panels side by side. --final draws the solved lines (OUTDIR/<name>.json,
on the sheet, parallax removed) instead. Tiny compute."""
import json, sys, subprocess, os, glob, tempfile, cv2, numpy as np
args = [x for x in sys.argv[1:] if x != "--final"]; final = "--final" in sys.argv; prefix, outdir, photo, out, scale, grid = args[:6]; here = os.path.dirname(os.path.abspath(__file__))
if final:
    cur = {}
    for f in sorted(glob.glob(os.path.join(outdir, "*.json"))):
        if os.path.basename(f) == "per_photo.json": continue
        d = json.load(open(f)); cur.update({k: v for k, v in d.items() if not k.endswith(("_depth_mm", "_xyz", "_info"))})
else:
    cur = {k.split("@")[0]: v for k, v in json.load(open(os.path.join(outdir, "per_photo.json"))).items() if k.endswith("@" + photo)}
t = tempfile.mkdtemp(); cj = os.path.join(t, "c.json"); json.dump(cur, open(cj, "w")); ims = []
for i, w in enumerate(args[6:]):
    f = os.path.join(t, f"{i}.jpg"); subprocess.run([sys.executable, "-I", os.path.join(here, "ortho_view.py"), prefix, "--img", photo, "--scale", scale, "--grid", grid, "--window", *w.split(), "--curves", cj, "--out", f], check=True, stdout=subprocess.DEVNULL)
    ims.append(cv2.imread(f))
H = max(i.shape[0] for i in ims); cv2.imwrite(out, np.hstack([cv2.copyMakeBorder(i, 0, H - i.shape[0], 0, 8, cv2.BORDER_CONSTANT, value=(0, 0, 255)) for i in ims])); print(out, photo, sorted(cur))
