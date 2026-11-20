"""USAGE: python -I tools/hull_mesh.py --npz parts/hull_v1.npz --out parts/hull_v1 [--keep 0.88]
Mesh the visual-hull vote grid written by tools/carve.py (kept separate so a cut-off run loses nothing).
Crops to the occupied region first, keeps the largest connected body, marching cubes at the vote level.
Compute: grid cropped to the chair (~40 M voxels float32 = 160 MB, a few copies); < 1.5 GB, under a minute."""
import argparse, numpy as np, trimesh
from skimage import measure
from scipy import ndimage
ap = argparse.ArgumentParser(); ap.add_argument("--npz", required=True); ap.add_argument("--out", required=True); ap.add_argument("--keep", type=float, default=0.88)
a = ap.parse_args()
z = np.load(a.npz); F = z["F"]; lo = z["lo"]; vox = float(z["voxel"])
occ = F > a.keep - 0.1; idx = np.argwhere(occ); i0 = np.maximum(idx.min(0) - 3, 0); i1 = np.minimum(idx.max(0) + 4, F.shape)
F = np.ascontiguousarray(F[i0[0]:i1[0], i0[1]:i1[1], i0[2]:i1[2]]); del occ, idx
Fs = ndimage.gaussian_filter(F, 0.7); del F
lab, n = ndimage.label(Fs > a.keep); sizes = np.bincount(lab.ravel()); sizes[0] = 0; big = int(sizes.argmax())
Fs[lab != big] = 0; nvox = int(sizes[big]); del lab
verts, faces, _, _ = measure.marching_cubes(Fs, level=a.keep, spacing=(vox,) * 3)
verts = verts + lo + (i0 + 0.5) * vox
mesh = trimesh.Trimesh(verts, faces, process=True)
mesh.export(a.out + ".glb")
print("hull voxels", nvox, "| volume litres", round(abs(mesh.volume) / 1e6, 2), "| bbox", mesh.bounds.round(0).tolist(), "| faces", len(mesh.faces), "| other bodies dropped", n - 1)
