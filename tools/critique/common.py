"""Shared pieces of the phase 6 critique tools (not a CLI).

Model geometry: the JOINED model `parts/model_vN.glb` (the chair as assembled; the `_shapes.glb` parts overlap at the joints,
so their outlines are not what a photo shows). Measured parts = the 13 wooden parts; the Domino bodies are only occluders.

Outline point = a point on a mesh edge that is, seen from one camera, either
  sil    a silhouette edge (one adjacent face toward the camera, the other away), or
  crease a sharp edge (dihedral > CREASE_DEG) with both faces toward the camera.
Each point carries its place on the part: face classes of its two faces in the part's own mirrored frame
(top, bottom, outer, inner, front, back; outer = away from the chair's centre plane), the side (L / R / C for x ~ 0 on
SEAT, CREST, SLAT_C), an along-coordinate (y, z or |x|, see ALONG) and a joint flag (within JOINT_MM of another part).
"""
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PARTS = ["SEAT", "ARM_L", "ARM_R", "FLEG_L", "FLEG_R", "BLEG_L", "BLEG_R", "ROCKER_L", "ROCKER_R",
         "CREST", "SLAT_L", "SLAT_C", "SLAT_R"]
CLASSES = ["top", "bottom", "outer", "inner", "front", "back"]
CREASE_DEG = 30.0
JOINT_MM = 20.0
STEP_MM = 3.0           # outline sampling step along an edge
BIN_MM = 50.0           # stretch length for regions
MIRRORED = {"ARM": 1, "FLEG": 1, "BLEG": 1, "ROCKER": 1, "SLAT_L": 1, "SLAT_R": 1}
SPLIT = ("SEAT", "CREST", "SLAT_C")   # one part, split into left / right halves by x


def base(name):
    return name.split("_")[0] if name.split("_")[0] in ("ARM", "FLEG", "BLEG", "ROCKER") else name


def along_axis(part, tangent):
    """'y', 'z' or 'ax' (|x|) for a part; SEAT picks by the edge's tangent."""
    b = base(part)
    if b in ("ARM", "ROCKER"):
        return np.full(len(tangent), "y")
    if b in ("FLEG", "BLEG") or b.startswith("SLAT"):
        return np.full(len(tangent), "z")
    if b == "CREST":
        return np.full(len(tangent), "ax")
    t = np.abs(tangent)
    return np.where(t[:, 0] > np.maximum(t[:, 1], t[:, 2]), "ax", "y")


def load_model(glb, shift=None):
    """-> dict name -> trimesh (joined model). shift: (PART, dx, dy, dz) moves one part (sanity check)."""
    import trimesh
    sc = trimesh.load(str(glb))
    out = {k: g.copy() for k, g in sc.geometry.items()}
    if shift:
        p, d = shift[0], np.array(shift[1:], float)
        out[p].apply_translation(d)
    return out


def face_classes(mesh, part):
    """Class index per face in the part's mirrored frame."""
    n = np.asarray(mesh.face_normals).copy()
    c = np.asarray(mesh.triangles_center)
    if part in SPLIT:
        sg = np.where(c[:, 0] >= 0, 1.0, -1.0)
    else:
        sg = np.full(len(n), 1.0 if mesh.vertices[:, 0].mean() >= 0 else -1.0)
    nm = np.c_[n[:, 0] * sg, n[:, 1], n[:, 2]]
    D = np.c_[nm[:, 2], -nm[:, 2], nm[:, 0], -nm[:, 0], nm[:, 1], -nm[:, 1]]
    return D.argmax(1).astype(np.int8)


def static_outline(meshes, step=STEP_MM, joint_mm=JOINT_MM):
    """Per measured part: candidate points on every mesh edge (positions, edge index, tangent), edge -> faces,
    dihedral, face classes, joint flag. Camera-independent; the camera decides which edges are outline."""
    from scipy.spatial import cKDTree
    others = {}
    allv = {k: np.asarray(m.sample(60000) if m.area > 0 else m.vertices) for k, m in meshes.items()}
    S = {}
    for p in PARTS:
        m = meshes[p]
        adj = np.asarray(m.face_adjacency)            # (E, 2) faces
        ev = np.asarray(m.face_adjacency_edges)       # (E, 2) vertices
        ang = np.degrees(np.asarray(m.face_adjacency_angles))
        V = np.asarray(m.vertices)
        a, b = V[ev[:, 0]], V[ev[:, 1]]
        L = np.linalg.norm(b - a, axis=1)
        k = np.maximum(1, np.round(L / step).astype(int))
        ei = np.repeat(np.arange(len(ev)), k)
        # midpoints of k equal pieces
        off = np.concatenate([(np.arange(n) + 0.5) / n for n in k])
        X = a[ei] + (b - a)[ei] * off[:, None]
        T = (b - a) / np.maximum(L, 1e-9)[:, None]
        tree = cKDTree(np.vstack([allv[q] for q in meshes if q != p]))
        dj, _ = tree.query(X, distance_upper_bound=joint_mm + 1)
        fc = face_classes(m, p)
        S[p] = dict(X=X.astype(np.float64), ei=ei, T=T, adj=adj, ang=ang, fc=fc,
                    fn=np.asarray(m.face_normals), fcen=np.asarray(m.triangles_center), joint=dj < joint_mm)
    return S


def render_mesh(meshes, max_edge=15.0):
    """All parts as one triangle soup for the painter's render (subdivided so a triangle's centroid depth is
    close to its pixels' depth). Returns V (N,3), F (M,3), part id per face (1-based, index into list(meshes))."""
    import trimesh
    Vs, Fs, Ps, off = [], [], [], 0
    names = list(meshes)
    for i, k in enumerate(names):
        v, f = trimesh.remesh.subdivide_to_size(meshes[k].vertices, meshes[k].faces, max_edge=max_edge, max_iter=8)
        Vs.append(v); Fs.append(f + off); Ps.append(np.full(len(f), i + 1, np.int16)); off += len(v)
    return np.vstack(Vs), np.vstack(Fs), np.concatenate(Ps), names
