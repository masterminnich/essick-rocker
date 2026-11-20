"""USAGE: uv run --no-project --with pycolmap --with numpy --with opencv-python-headless --with pillow --with scipy \
    python -I tools/square_ticks.py --model M --corners work/solve/sq_X/corners.json --drive drive --out work/solve/ticks_X.json
    [--res_mm 0.2] [--search 0.04] [--diag work/solve/diag/ticks_X.jpg]

Scale route B: the printed inch graduations of the framing square, independent of its cut lengths.
The square plane and in-plane axes come from the triangulated outline corners (route A output), in model units.
For every image that sees a leg, the leg is rectified onto the plane (bilinear resampling of the raw image through the
solved camera incl. distortion) at ~--res_mm per sample (using a rough unit from the outline). A darkness profile is
taken along each graduated edge band (body outer/inner, tongue outer/inner), non-yellow (occluded) samples are
neutralised, and the graduation pitch P (model units per inch) is found by maximising the summed Fourier power of the
inch harmonics k = 1, 2, 4, 8 over P in +-search around the rough value (then parabolic refinement).
Per view and edge we report P, the implied scale 25.4/P mm per unit, the peak contrast, and the phase-derived position
of the inch-0 line relative to the outline corner (a cross-check of route A's heel/corner placement).
Rectified strips (for looking at) are optionally tiled into --diag.
"""
import argparse, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
import rc_geom as G

INCH = 25.4


def frame_from_corners(V):
    O = V["O"]; ea = V["Bo"] - O; La = np.linalg.norm(ea); ea /= La
    n = np.cross(ea, V["To"] - O); n /= np.linalg.norm(n)
    eb = np.cross(n, ea)
    if eb @ (V["To"] - O) < 0: eb = -eb
    return O, ea, eb, n, La


def rectify(cam, img, O, ea, eb, a_rng, b_rng, step):
    import cv2
    a = np.arange(a_rng[0], a_rng[1], step); b = np.arange(b_rng[0], b_rng[1], step)
    A, B = np.meshgrid(a, b)
    P = O[None] + A.reshape(-1, 1) * ea[None] + B.reshape(-1, 1) * eb[None]
    uv, z = cam.project(P)
    if (z <= 0).any(): return None, None, None
    x = (uv[:, 0] - 0.5).reshape(A.shape).astype(np.float32); y = (uv[:, 1] - 0.5).reshape(A.shape).astype(np.float32)
    inb = (x > 1) & (y > 1) & (x < img.shape[1] - 2) & (y < img.shape[0] - 2)
    out = np.stack([cv2.remap(img[:, :, c], x, y, cv2.INTER_LINEAR) for c in range(3)], -1)
    # image-pixel footprint of one rectified sample along a (resolution check)
    du = np.gradient(uv[:, 0].reshape(A.shape), axis=1); dv = np.gradient(uv[:, 1].reshape(A.shape), axis=1)
    px_per_sample = np.sqrt(du ** 2 + dv ** 2)
    return out, inb, px_per_sample


def pitch_fit(prof, coord, P0, search, ks=(1, 2, 4, 8)):
    Ps = P0 * np.linspace(1 - search, 1 + search, 1601)
    pw = np.zeros_like(Ps)
    for k in ks:
        E = np.exp(-2j * np.pi * k * coord[None, :] / Ps[:, None])
        pw += np.abs(E @ prof) ** 2 / len(prof) ** 2 * (1.0 if k == 1 else 1.0)
    i = int(np.argmax(pw))
    if 0 < i < len(Ps) - 1:
        den = pw[i - 1] - 2 * pw[i] + pw[i + 1]; di = 0.5 * (pw[i - 1] - pw[i + 1]) / den if den < 0 else 0
    else:
        di = 0
    P = Ps[i] + di * (Ps[1] - Ps[0])
    contrast = pw[i] / np.median(pw)
    # phase of the fundamental -> position of the inch-0 line (mod 1 inch)
    ph = np.angle(np.exp(-2j * np.pi * coord / P) @ prof)
    return float(P), float(contrast), float(ph), (Ps, pw)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True); ap.add_argument("--corners", required=True); ap.add_argument("--drive", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--res_mm", type=float, default=0.2)
    ap.add_argument("--search", type=float, default=0.04); ap.add_argument("--diag")
    ap.add_argument("--min_contrast", type=float, default=30.0)
    a = ap.parse_args()
    _, cams = G.load_model(a.model)
    cj = json.load(open(a.corners))
    V = {k: np.array(v) for k, v in cj["corners3d"].items()}
    O, ea, eb, n, La = frame_from_corners(V)
    Lb = np.linalg.norm(V["To"] - O)
    u_mm = La / 609.6  # rough model units per mm (only for band sizes and the search centre)
    P0 = INCH * u_mm
    step = a.res_mm * u_mm
    Wa = np.linalg.norm(V["Bi"] - V["Bo"]); Wb = np.linalg.norm(V["Ti"] - V["To"])
    band = lambda w0, w1: (w0 * u_mm, w1 * u_mm)
    # edge definitions: (name, along-axis, range along (units), band across (units), leg)
    edges = {
        "body_outer": ("a", (0.4 * P0, La - 0.4 * P0), band(0.4, 6.0)),
        "body_inner": ("a", (Wb + 0.4 * P0, La - 0.4 * P0), (Wa - 6.0 * u_mm, Wa - 0.4 * u_mm)),
        "tongue_outer": ("b", (0.4 * P0, Lb - 0.4 * P0), band(0.4, 6.0)),
        "tongue_inner": ("b", (Wa + 0.4 * P0, Lb - 0.4 * P0), (Wb - 6.0 * u_mm, Wb - 0.4 * u_mm)),
    }
    rows, strips = [], []
    for name in sorted(cams):
        cam = cams[name]
        uvV, z = cam.project(np.array([V[k] for k in ["O", "Bo", "To"]]))
        if (z <= 0).any(): continue
        img = None
        for en, (ax, rng, bnd) in edges.items():
            if ax == "a":
                a_rng, b_rng = rng, bnd; e1, e2 = ea, eb
            else:
                a_rng, b_rng = rng, bnd; e1, e2 = eb, ea  # along b, across a
            # quick visibility test: endpoints in frame
            ends = O[None] + np.array([a_rng[0], a_rng[1]])[:, None] * e1[None]
            uve, ze = cam.project(ends)
            if (ze <= 0).any(): continue
            inside = ((uve[:, 0] > 0) & (uve[:, 0] < G.FULL_W) & (uve[:, 1] > 0) & (uve[:, 1] < G.FULL_H))
            if not inside.all(): continue
            if img is None: img = G.load_raw(pathlib.Path(a.drive) / name)
            R, inb, pps = rectify(cam, img, O, e1, e2, a_rng, b_rng, step)
            if R is None: continue
            yel = (R[..., 0] + R[..., 1]) * 0.5 - R[..., 2]
            lum = R.mean(-1)
            # yellow reference per column: occluded columns (low yellowness over the band) are neutralised
            col_y = np.median(yel, axis=0); good = (col_y > 0.5 * np.median(col_y)) & inb.all(axis=0)
            dark = (255 - lum).mean(axis=0)
            prof = dark - np.median(dark[good]); prof[~good] = 0
            coord = np.arange(a_rng[0], a_rng[1], step)[: len(prof)]
            P, con, ph, _ = pitch_fit(prof, coord, P0, a.search)
            res_px = float(np.median(pps))  # image px per rectified sample
            inch_px = res_px * P / step
            rows.append(dict(image=name, edge=en, pitch_units=P, scale_mm_per_unit=INCH / P, contrast=con,
                             good_frac=float(good.mean()), image_px_per_inch=float(inch_px),
                             zero_offset_inch=float((ph / (2 * np.pi)) % 1.0)))
            if a.diag and con > a.min_contrast and len(strips) < 24:
                strips.append((name, en, np.clip(R, 0, 255).astype(np.uint8)))
    ok = [r for r in rows if r["contrast"] > a.min_contrast and r["good_frac"] > 0.7 and r["image_px_per_inch"] > 40]
    summ = {}
    for en in edges:
        s = np.array([r["scale_mm_per_unit"] for r in ok if r["edge"] == en])
        if len(s):
            med = np.median(s); mad = 1.4826 * np.median(np.abs(s - med))
            keep = s[np.abs(s - med) < max(4 * mad, 1e-9)]
            summ[en] = dict(n=int(len(s)), n_kept=int(len(keep)), median=float(med), mean_kept=float(keep.mean()),
                            std_kept=float(keep.std(ddof=1)) if len(keep) > 1 else None,
                            sem_kept=float(keep.std(ddof=1) / np.sqrt(len(keep))) if len(keep) > 1 else None)
    allk = np.concatenate([np.array([r["scale_mm_per_unit"] for r in ok if r["edge"] == en]) for en in summ])
    med = np.median(allk); mad = 1.4826 * np.median(np.abs(allk - med)); keep = allk[np.abs(allk - med) < 4 * mad]
    summ["all"] = dict(n=int(len(allk)), n_kept=int(len(keep)), median=float(med), mean_kept=float(keep.mean()),
                       std_kept=float(keep.std(ddof=1)), sem_kept=float(keep.std(ddof=1) / np.sqrt(len(keep))))
    summ["outline_lengths_in_inches"] = {"body_O_Bo": float(La / np.median(allk) ** -1 / INCH) if False else float(La * med / INCH),
                                         "tongue_O_To": float(Lb * med / INCH), "body_width": float(Wa * med / INCH),
                                         "tongue_width": float(Wb * med / INCH)}
    G.save_json(a.out, dict(model=a.model, corners=a.corners, rough_units_per_mm=u_mm, summary=summ, rows=rows))
    for k, v in summ.items(): print(k, v)
    if a.diag and strips:
        from PIL import Image, ImageDraw
        W = 1800; tiles = []
        for nm, en, R in strips[:12]:
            im = Image.fromarray(R[::-1] if False else R); s = W / im.width
            im = im.resize((W, max(8, int(im.height * s * 1.0))))
            d = ImageDraw.Draw(im); d.text((4, 2), f"{nm[4:8]} {en}", fill=(255, 0, 0))
            tiles.append(im)
        H = sum(t.height + 6 for t in tiles); sheet = Image.new("RGB", (W, H), (20, 20, 20)); y = 0
        for t in tiles: sheet.paste(t, (0, y)); y += t.height + 6
        pathlib.Path(a.diag).parent.mkdir(parents=True, exist_ok=True); sheet.save(a.diag, quality=90)


if __name__ == "__main__":
    main()
