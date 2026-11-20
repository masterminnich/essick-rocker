"""USAGE: python -I tools/carve.py --masks work/masks --out parts/hull_v1 [--voxel 2.5] [--keep 0.88]
Visual hull of the chair: a voxel is chair if it projects inside the chair mask in at least --keep of the photos that see
it. Coarse pass at 4x the voxel size first, then the fine pass only near the coarse result. Marching cubes on the
vote fraction gives a mesh in the chair frame (mm). Writes <out>.glb, <out>.npz (vote grid) and prints stats.
A visual hull cannot see concavities (the seat scoop stays filled) and is slightly fat where masks leak.
Compute: masks loaded as 70 x 3 MB; voxels processed in 1.5 M chunks; < 2 GB; a few minutes on 2 threads."""
import sys, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2, trimesh
from skimage import measure
from scipy import ndimage
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); ap.add_argument("--masks", required=True); ap.add_argument("--out", required=True); ap.add_argument("--voxel", type=float, default=2.5)
ap.add_argument("--keep", type=float, default=0.88); ap.add_argument("--min-views", type=int, default=12)
a = ap.parse_args(); cams = Cameras.load()
LO = np.array([-350.0, -520, 0]); HI = np.array([350.0, 665, 1115])
masks = {}
for p in sorted(Path(a.masks).glob("IMG_*.png")):
    m = cv2.imread(str(p), 0); masks[p.stem + ".JPG"] = m
S = next(iter(masks.values())).shape[1] / 4032.0
print(len(masks), "masks, scale", S)

def votes(P):
    seen = np.zeros(len(P), np.int16); fg = np.zeros(len(P), np.int16)
    for name, m in masks.items():
        v = cams[name]; H, W = m.shape
        for c0 in range(0, len(P), 1500000):
            uv = v.project(P[c0:c0 + 1500000]) * S
            ok = np.isfinite(uv).all(1); x = np.zeros(len(uv), int); y = np.zeros(len(uv), int)
            x[ok] = np.round(uv[ok, 0]).astype(int); y[ok] = np.round(uv[ok, 1]).astype(int)
            ok &= (x >= 2) & (y >= 2) & (x < W - 2) & (y < H - 2)
            seen[c0:c0 + 1500000] += ok; f = np.zeros(len(uv), bool); f[ok] = m[y[ok], x[ok]] > 0; fg[c0:c0 + 1500000] += f
    return seen, fg

def grid(vox):
    ax = [np.arange(LO[i] + vox / 2, HI[i], vox) for i in range(3)]
    return ax, tuple(len(x) for x in ax)

# coarse
vc = a.voxel * 4; axc, shc = grid(vc); G = np.stack(np.meshgrid(*axc, indexing="ij"), -1).reshape(-1, 3)
seen, fg = votes(G); frac = np.where(seen >= a.min_views, fg / np.maximum(seen, 1), 0).reshape(shc)
coarse = ndimage.binary_dilation(frac > a.keep - 0.25, iterations=1)
print("coarse grid", shc, "candidate voxels", int(coarse.sum()))
# fine: only inside candidate coarse cells
axf, shf = grid(a.voxel); up = np.repeat(np.repeat(np.repeat(coarse, 4, 0), 4, 1), 4, 2)[:shf[0], :shf[1], :shf[2]]
pad = [(0, shf[i] - up.shape[i]) for i in range(3)]; up = np.pad(up, pad)
idx = np.argwhere(up); P = np.stack([axf[i][idx[:, i]] for i in range(3)], 1)
print("fine grid", shf, "voxels to test", len(P))
seen, fg = votes(P)
F = np.zeros(shf, np.float32); F[idx[:, 0], idx[:, 1], idx[:, 2]] = np.where(seen >= a.min_views, fg / np.maximum(seen, 1), 0)
np.savez_compressed(a.out + ".npz", F=F, lo=LO, voxel=a.voxel)
Fs = ndimage.gaussian_filter(F, 0.7)
occ = Fs > a.keep; lab, n = ndimage.label(occ); sizes = ndimage.sum(occ, lab, range(1, n + 1)); big = 1 + int(np.argmax(sizes))
Fs[(lab != big)] = 0
verts, faces, _, _ = measure.marching_cubes(Fs, level=a.keep, spacing=(a.voxel,) * 3)
verts = verts + LO + a.voxel / 2
mesh = trimesh.Trimesh(verts, faces, process=True); trimesh.smoothing.filter_taubin(mesh, iterations=10)
mesh.export(a.out + ".glb")
print("hull: voxels", int((lab == big).sum()), "| volume litres", round(mesh.volume / 1e6, 2), "| bbox", mesh.bounds.round(0).tolist(), "| faces", len(mesh.faces), "| components dropped", n - 1)
