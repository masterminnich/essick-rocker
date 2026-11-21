"""USAGE: python -I tools/audit_sections.py parts/model_v9.glb
Horizontal sections (raw cut lines) through the leg-to-seat joints, to see in plan how the leg and seat solids sit against each other.
Writes figures/model_audit/seat_leg_sections.png and prints how far each leg section reaches inside the seat's outline. Tiny compute."""
import sys, json
import numpy as np, trimesh, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sc = trimesh.load(sys.argv[1]); G = sc.geometry
cut = lambda m, z: trimesh.intersections.mesh_plane(m, [0, 0, 1], [0, 0, z])[:, :, :2]
fig, axs = plt.subplots(1, 2, figsize=(15, 7.5)); rep = {}
for ax, leg, zs, win in ((axs[0], "FLEG_R", (350, 372, 390), (200, 330, 380, 560)), (axs[1], "BLEG_R", (320, 340, 360), (120, 300, -60, 130))):
    for z, ls in zip(zs, ("-", "--", ":")):
        S, Lg = cut(G["SEAT"], z), cut(G[leg], z)
        for segs, c in ((S, "#c9a227"), (Lg, "#b5452a" if leg == "BLEG_R" else "#1f6fb2")):
            for a, b in segs: ax.plot([a[0], b[0]], [a[1], b[1]], ls, color=c, lw=1.4)
        # seat outline half-width at the leg's y range: max x of seat cut points within the leg's y band
        if len(Lg) and len(S):
            ly = Lg[:, :, 1].ravel(); sx = S[:, :, 0].ravel(); sy = S[:, :, 1].ravel(); band = (sy > ly.min() - 3) & (sy < ly.max() + 3)
            seat_x = float(sx[band].max()) if band.any() else None; leg_in = float(Lg[:, :, 0].min()); leg_out = float(Lg[:, :, 0].max())
            rep[f"{leg}_z{z}"] = {"leg_x": [round(leg_in, 1), round(leg_out, 1)], "leg_y": [round(float(ly.min()), 1), round(float(ly.max()), 1)],
                                 "seat_edge_x_in_leg_band": None if seat_x is None else round(seat_x, 1),
                                 "leg_inside_seat_mm": None if seat_x is None else round(seat_x - leg_in, 1)}
    ax.set_xlim(win[0], win[1]); ax.set_ylim(win[2], win[3]); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_xlabel("x (mm, + = chair's right)"); ax.set_ylabel("y (mm, + = forward)")
    ax.set_title(f"{leg} (red/blue) vs SEAT (gold): plan cuts at z {zs}\n(solid, dashed, dotted)")
fig.tight_layout(); fig.savefig("figures/model_audit/seat_leg_sections.png", dpi=110); print(json.dumps(rep, indent=1))
