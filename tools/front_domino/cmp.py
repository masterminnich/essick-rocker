"""Compare two GLBs part by part. Usage: tools/py.sh work/fdom/cmp.py A.glb B.glb"""
import sys, trimesh, numpy as np
a, b = (trimesh.load(p) for p in sys.argv[1:3]); same, diff = [], []
for k in sorted(set(a.geometry) | set(b.geometry)):
    if k not in a.geometry or k not in b.geometry: diff.append(f"{k}: only in {'B' if k not in a.geometry else 'A'}"); continue
    A, B = a.geometry[k], b.geometry[k]
    if A.vertices.shape == B.vertices.shape and np.array_equal(A.vertices, B.vertices) and np.array_equal(A.faces, B.faces): same.append(k)
    else: diff.append(f"{k}: verts {len(A.vertices)}->{len(B.vertices)}, volume {A.volume/1000:.3f}->{B.volume/1000:.3f} cm3, centroid shift {np.round(B.centroid-A.centroid,2).tolist()}")
print("identical:", len(same), " ".join(same)); print("changed:", len(diff)); [print("  " + d) for d in diff]
