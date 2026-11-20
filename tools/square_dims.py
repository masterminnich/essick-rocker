"""USAGE: uv run --no-project --with numpy python -I tools/square_dims.py work/solve/sq_X/corners.json [--scale mm_per_unit]

Prints the framing-square outline geometry from triangulated corners: edge lengths (model units, and mm at the given
scale or, by default, at the scale that makes the body outer edge 24.000 in), both heel angles, the out-of-plane
deviation of the six corners, and per-corner triangulation stats. Also prints scale candidates from each nominal
length (24 in body, 16 in tongue). JSON summary on the last line.
"""
import argparse, json
import numpy as np


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("corners"); ap.add_argument("--scale", type=float)
    a = ap.parse_args()
    d = json.load(open(a.corners)); V = {k: np.array(v) for k, v in d["corners3d"].items()}
    L = lambda p, q: float(np.linalg.norm(V[p] - V[q]))
    s = a.scale or 609.6 / L("O", "Bo")
    out = dict(lengths={}, scale_candidates={})
    for p, q, nom in [("O", "Bo", 24), ("O", "To", 16), ("Bo", "Bi", 2), ("To", "Ti", 1.5), ("I", "Bi", 22.5), ("I", "Ti", 14)]:
        out["lengths"][f"{p}-{q}"] = dict(units=L(p, q), mm=L(p, q) * s, nominal_mm=nom * 25.4)
        print(f"{p:>2}-{q:<2} {L(p, q):.5f} u  {L(p, q) * s:8.2f} mm  nominal {nom * 25.4:7.2f}")
    out["scale_candidates"] = {"body_24in": 609.6 / L("O", "Bo"), "tongue_16in": 406.4 / L("O", "To")}
    ang = lambda c, p, q: float(np.degrees(np.arccos(((V[p] - V[c]) @ (V[q] - V[c])) / np.linalg.norm(V[p] - V[c]) / np.linalg.norm(V[q] - V[c]))))
    out["angle_outer_deg"] = ang("O", "Bo", "To"); out["angle_inner_deg"] = ang("I", "Bi", "Ti")
    P = np.array(list(V.values())); c = P.mean(0); _, _, vt = np.linalg.svd(P - c)
    out["planarity_mm"] = ((P - c) @ vt[2] * s).round(3).tolist()
    print("angles outer/inner", round(out["angle_outer_deg"], 4), round(out["angle_inner_deg"], 4))
    print("planarity mm", out["planarity_mm"])
    for k, t in d.get("triangulation", {}).items():
        print(f"  corner {k}: views {len(t['views'])} rms {t['rms_px']:.2f} px rejected {t['n_rejected']}")
    print("scale candidates mm/unit", out["scale_candidates"])
    print(json.dumps(out))


if __name__ == "__main__":
    main()
