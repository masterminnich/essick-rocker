"""USAGE: uv run --no-project --with pycolmap --with numpy --with pillow python -I tools/square_diag.py \
    --model M --drive drive --sqdir work/solve/square --images IMG_1540.JPG,... --out work/solve/diag/x.jpg [--extra pts.json]

Diagnostic: crops each image (display orientation) around the framing square and draws
 - grey dots: raw edge samples (from <sqdir>/edges), green lines: the triangulated 3D outline reprojected,
 - red crosses: per-image 2D corner observations, cyan rings: triangulated corners reprojected,
 - optional --extra JSON {"points3d": {name: [x,y,z]}} drawn as orange rings (e.g. triangulated inch marks).
Tiles are combined into one JPEG.
"""
import argparse, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw, ImageOps
import rc_geom as G

VN = ["O", "Bo", "Bi", "I", "Ti", "To"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("--drive", required=True)
    ap.add_argument("--sqdir", required=True); ap.add_argument("--images", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--extra"); ap.add_argument("--tile", type=int, default=900); ap.add_argument("--zoom", default="")
    a = ap.parse_args()
    _, cams = G.load_model(a.model)
    cj = json.load(open(pathlib.Path(a.sqdir) / "corners.json"))
    V = np.array([cj["corners3d"][k] for k in VN])
    extra = json.load(open(a.extra))["points3d"] if a.extra else {}
    tiles = []
    for n in a.images.split(","):
        cam = cams[n]; o = G.exif_orientation(pathlib.Path(a.drive) / n)
        im = Image.open(pathlib.Path(a.drive) / n).convert("RGB")  # raw grid
        dr = ImageDraw.Draw(im)
        ef = pathlib.Path(a.sqdir) / "edges" / (n + ".npz")
        if ef.exists():
            for k, p in np.load(ef).items():
                for x, y in p: dr.point((x, y), fill=(200, 200, 200))
        # outline (densely projected so distortion is shown)
        for i in range(6):
            P = V[i][None] + np.linspace(0, 1, 60)[:, None] * (V[(i + 1) % 6] - V[i])[None]
            uv, z = cam.project(P)
            dr.line([tuple(q) for q in uv], fill=(0, 255, 0), width=1)
        pc = cj["per_image"].get(n, {}).get("corners", {})
        for k, (x, y) in pc.items():
            dr.line([x - 6, y, x + 6, y], fill="red", width=1); dr.line([x, y - 6, x, y + 6], fill="red", width=1)
        uv, _ = cam.project(V)
        for x, y in uv: dr.ellipse([x - 4, y - 4, x + 4, y + 4], outline="cyan", width=1)
        for k, X in extra.items():
            (x, y), = cam.project(np.array([X]))[0]
            dr.ellipse([x - 5, y - 5, x + 5, y + 5], outline="orange", width=2)
        allp = np.r_[uv, *[cam.project(np.array([X]))[0] for X in extra.values()]] if extra else uv
        allp = allp[(allp[:, 0] > 0) & (allp[:, 0] < 4032) & (allp[:, 1] > 0) & (allp[:, 1] < 3024)]
        if a.zoom:
            k = a.zoom
            c = cam.project(np.array([cj["corners3d"][k]]))[0][0]; half = 80
            box = [c[0] - half, c[1] - half, c[0] + half, c[1] + half]
        else:
            lo, hi = allp.min(0) - 60, allp.max(0) + 60
            box = [max(lo[0], 0), max(lo[1], 0), min(hi[0], 4032), min(hi[1], 3024)]
        crop = im.crop(tuple(int(b) for b in box))
        # rotate the crop into display orientation
        crop = {1: crop, 3: crop.rotate(180), 6: crop.rotate(-90, expand=True), 8: crop.rotate(90, expand=True)}[o]
        s = a.tile / max(crop.size); crop = crop.resize((max(1, int(crop.width * s)), max(1, int(crop.height * s))),
                                                         Image.NEAREST if a.zoom else Image.LANCZOS)
        d2 = ImageDraw.Draw(crop); d2.rectangle([0, 0, 120, 22], fill="black"); d2.text((4, 4), n[4:8] + f" o{o}", fill="yellow")
        tiles.append(crop)
    cols = min(3, len(tiles)); rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * a.tile, rows * a.tile), (30, 30, 30))
    for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * a.tile, (i // cols) * a.tile))
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True); sheet.save(a.out, quality=90)


if __name__ == "__main__":
    main()
