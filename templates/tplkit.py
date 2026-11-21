"""Template rendering kit: one drawing spec (mm) -> tiled Letter PDF, single full-size PDF, DXF (R12, mm) and a preview PNG.

Spec (dict):
  name, title, rev, part_note        strings
  items: list of
    {"kind": "cut",  "pts": Nx2 mm, "closed": bool}          cut line (heavy, black)
    {"kind": "line", "pts": Nx2, "style": "ref"|"hidden"|"centre"|"mark", "label": optional}
    {"kind": "dim",  "p1": (x,y), "p2": (x,y), "off": mm, "label": str (optional; default = length)}
    {"kind": "text", "xy": (x,y), "s": str, "size": pt, "rot": deg, "ha": "center"}
  title_block: list of lines (provenance/accuracy), key_dims: list of (name, mm or str, note)
Units on the drawing: inches to 1/32 with mm alongside (fmt()).
The tiled PDF prints at 100 % ("Actual size") on Letter; every page carries a 2 in check square and a 50 mm bar, the tile
label, the overlap band (0.5 in, shaded) and 1 in registration crosses on a global grid, so crosses in the overlap of two
neighbouring pages land on each other. Page 1 is the assembly map.
"""
import math, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Polygon

IN = 25.4
PAGE = (8.5, 11.0)
MARGIN = 0.35          # in, unprintable margin assumed on every side
OVERLAP = 0.5          # in
INK = "#111111"; REF = "#6b7b8c"; MARK = "#c0392b"; DIMC = "#1f4e79"


def frac32(mm, sign=True):
    x = mm / IN; s = "-" if x < 0 else ""; x = abs(x)
    n = int(round(x * 32)); w, r = divmod(n, 32)
    if r == 0: t = f"{w}"
    else:
        d = 32
        while r % 2 == 0: r //= 2; d //= 2
        t = f"{w} {r}/{d}" if w else f"{r}/{d}"
    return s + t + '"'


def fmt(mm, dec=1):
    return f"{frac32(mm)} ({mm:.{dec}f} mm)"


def _bbox(spec, pad=0.0):
    P = []
    for it in spec["items"]:
        if it["kind"] in ("cut", "line"): P.append(np.asarray(it["pts"], float))
        elif it["kind"] == "dim":
            p1, p2 = np.asarray(it["p1"], float), np.asarray(it["p2"], float); d = p2 - p1; n = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-9)
            P.append(np.array([p1, p2, p1 + n * it["off"], p2 + n * it["off"]]))
        elif it["kind"] == "text":
            x, y = it["xy"]; lines = it["s"].split("\n"); sz = it.get("size", 7) * 0.3528 * 1.25      # line height mm
            w = 0.55 * it.get("size", 7) * 0.3528 * max(len(l) for l in lines); h = sz * len(lines)
            xa = {"left": (x, x + w), "right": (x - w, x)}.get(it.get("ha", "center"), (x - w / 2, x + w / 2))
            ya = {"bottom": (y, y + h), "top": (y - h, y)}.get(it.get("va", "center"), (y - h / 2, y + h / 2))
            P.append(np.array([[xa[0], ya[0]], [xa[1], ya[1]]]))
    P = np.vstack(P); lo, hi = P.min(0) - pad, P.max(0) + pad
    return lo, hi


def _draw(ax, spec, scale_pt=1.0, labels=True):
    """Draw all items on an axes whose data units are mm at 1:1 (or scaled for the map: scale_pt shrinks line widths)."""
    for it in spec["items"]:
        k = it["kind"]
        if k == "cut":
            p = np.asarray(it["pts"], float)
            if it.get("closed"): p = np.vstack([p, p[:1]])
            ax.plot(p[:, 0], p[:, 1], "-", color=INK, lw=0.9 * scale_pt, solid_joinstyle="round", zorder=5)
        elif k == "line":
            p = np.asarray(it["pts"], float); st = it.get("style", "ref")
            ls = {"ref": "-", "hidden": (0, (4, 2)), "centre": (0, (8, 2, 2, 2)), "mark": "-"}[st]
            col = MARK if st == "mark" else REF
            ax.plot(p[:, 0], p[:, 1], linestyle=ls, color=col, lw=(0.6 if st == "mark" else 0.45) * scale_pt, zorder=4)
            if labels and it.get("label"):
                i = len(p) // 2 if it.get("label_at") is None else it["label_at"]
                ax.text(p[i, 0], p[i, 1], it["label"], fontsize=it.get("size", 6.5), color=col, ha="center", va="bottom",
                        rotation=it.get("rot", 0), zorder=6, clip_on=True, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))
        elif k == "dim":
            p1, p2 = np.asarray(it["p1"], float), np.asarray(it["p2"], float); d = p2 - p1; L = np.linalg.norm(d)
            t = d / L; n = np.array([-t[1], t[0]]); o = it["off"]; a, b = p1 + n * o, p2 + n * o
            ext = 2.0 * np.sign(o) if o else 0
            ax.plot([p1[0], a[0] + n[0] * ext], [p1[1], a[1] + n[1] * ext], color=DIMC, lw=0.3 * scale_pt, zorder=4)
            ax.plot([p2[0], b[0] + n[0] * ext], [p2[1], b[1] + n[1] * ext], color=DIMC, lw=0.3 * scale_pt, zorder=4)
            ax.plot([a[0], b[0]], [a[1], b[1]], color=DIMC, lw=0.4 * scale_pt, zorder=4)
            ah = 2.2 if L > 8 else 1.0                                    # arrowheads as filled triangles (mm)
            for tip_, dirn in ((a, t), (b, -t)):
                tri = np.array([tip_, tip_ + dirn * ah * 1.8 + n * ah * 0.45, tip_ + dirn * ah * 1.8 - n * ah * 0.45])
                ax.add_patch(Polygon(tri, closed=True, fc=DIMC, ec="none", zorder=4))
            if labels:
                ang = math.degrees(math.atan2(t[1], t[0]))
                if ang > 90: ang -= 180
                if ang < -90: ang += 180
                m = (a + b) / 2
                ax.text(m[0], m[1], it.get("label") or fmt(L), fontsize=it.get("size", 6.5), color=DIMC, ha="center",
                        va="center", rotation=ang, rotation_mode="anchor", zorder=6, clip_on=True, bbox=dict(fc="white", ec="none", pad=0.8))
        elif k == "text" and labels:
            ax.text(it["xy"][0], it["xy"][1], it["s"], fontsize=it.get("size", 7), color=it.get("color", INK),
                    ha=it.get("ha", "center"), va=it.get("va", "center"), rotation=it.get("rot", 0), zorder=6,
                    family=it.get("family", "sans-serif"), linespacing=1.25, clip_on=True,
                    bbox=dict(fc="white", ec="none", pad=0.8, alpha=0.9) if it.get("box", True) else None)


def _layout(lo, hi):
    """Pick portrait or landscape Letter, whichever needs fewer pages. Returns (pw, ph, cols, rows, origin)."""
    best = None
    for pw, ph in (PAGE, PAGE[::-1]):
        cw, ch = (pw - 2 * MARGIN) * IN, (ph - 2 * MARGIN) * IN; sx, sy = cw - OVERLAP * IN, ch - OVERLAP * IN
        W, H = hi - lo
        cols = max(1, math.ceil((W - OVERLAP * IN) / sx)); rows = max(1, math.ceil((H - OVERLAP * IN) / sy))
        n = cols * rows
        if best is None or n < best[0]: best = (n, pw, ph, cols, rows, cw, ch, sx, sy)
    n, pw, ph, cols, rows, cw, ch, sx, sy = best
    # centre the drawing in the tiled area
    totw, toth = cols * sx + OVERLAP * IN, rows * sy + OVERLAP * IN
    org = np.array([lo[0] - (totw - (hi[0] - lo[0])) / 2, hi[1] + (toth - (hi[1] - lo[1])) / 2])   # top-left of tile grid
    return dict(pw=pw, ph=ph, cols=cols, rows=rows, cw=cw, ch=ch, sx=sx, sy=sy, org=org)


def _segments(spec):
    S = []
    for it in spec["items"]:
        if it["kind"] in ("cut", "line"):
            p = np.asarray(it["pts"], float)
            if it.get("closed"): p = np.vstack([p, p[:1]])
            S.append(p)
        elif it["kind"] == "dim":
            p1, p2 = np.asarray(it["p1"], float), np.asarray(it["p2"], float); d = p2 - p1; n = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-9)
            t = np.linspace(0, 1, 60)[:, None]; S.append(p1 + n * it["off"] + t * d); S.append(np.array([p1, p2]))
        elif it["kind"] == "text":
            x, y = it["xy"]; nl = it["s"].count("\n") + 1; w = 1.0 * it.get("size", 7) * max(len(l) for l in it["s"].split("\n")) / 2
            gx, gy = np.meshgrid(np.linspace(-w, w, 15), np.linspace(-nl * 3, nl * 3, 5))
            if it.get("ha") == "left": gx = gx + w
            S.append(np.stack([x + gx.ravel(), y + gy.ravel()], 1))
    return S


def _box_hits(S, x0, y0, x1, y1):
    n = 0
    for p in S:
        n += int(np.sum((p[:, 0] > x0) & (p[:, 0] < x1) & (p[:, 1] > y0) & (p[:, 1] < y1)))
    return n


def _check_square(ax, x, y):
    """2 in check square + 50 mm bar, lower-left corner at (x, y) mm; 62 x 64 mm box."""
    ax.add_patch(Rectangle((x - 3, y - 3), 62, 66, fc="white", ec="none", zorder=7))
    ax.add_patch(Rectangle((x, y + 9), 2 * IN, 2 * IN, fc="none", ec=INK, lw=0.5, zorder=8))
    ax.text(x + IN, y + 9 + IN, "CHECK\n2.000 in\n= 50.8 mm\nboth ways", fontsize=5.5, ha="center", va="center", zorder=8, linespacing=1.2)
    ax.plot([x, x + 50], [y + 3, y + 3], color=INK, lw=0.5, zorder=8)
    for k in range(0, 51, 10): ax.plot([x + k, x + k], [y + 3, y + (6 if k % 50 == 0 else 5)], color=INK, lw=0.4, zorder=8)
    ax.text(x + 25, y + 0.2, "50 mm", fontsize=5, ha="center", va="bottom", zorder=8)


def _cross(ax, x, y, s=3.0):
    ax.plot([x - s, x + s], [y, y], color="#888", lw=0.3, zorder=3); ax.plot([x, x], [y - s, y + s], color="#888", lw=0.3, zorder=3)


def tile_name(r, c): return f"{chr(65 + r)}{c + 1}"


def write_tiled(spec, path):
    lo, hi = _bbox(spec, pad=6); L = _layout(lo, hi); S = _segments(spec)
    with PdfPages(path) as pdf:
        # ---- page 1: assembly map + title block
        fig = plt.figure(figsize=PAGE[::-1]); ax = fig.add_axes([0.04, 0.56, 0.92, 0.34])
        _draw(ax, spec, scale_pt=0.5, labels=False)
        for r in range(L["rows"]):
            for c in range(L["cols"]):
                x0 = L["org"][0] + c * L["sx"]; y1 = L["org"][1] - r * L["sy"]
                ax.add_patch(Rectangle((x0, y1 - L["ch"]), L["cw"], L["ch"], fc="none", ec=DIMC, lw=0.5, ls="--"))
                ax.text(x0 + L["cw"] / 2, y1 - L["ch"] / 2, tile_name(r, c), fontsize=11, color=DIMC, ha="center", va="center", alpha=0.7)
        ax.set_aspect("equal"); ax.axis("off")
        fig.text(0.04, 0.95, spec["title"], fontsize=15, weight="bold")
        fig.text(0.04, 0.925, f"{spec['name']}  rev {spec['rev']}   |   {L['rows'] * L['cols']} tiles "
                 f"({L['rows']} rows A-{chr(64 + L['rows'])} x {L['cols']} cols), Letter {'landscape' if L['pw'] > L['ph'] else 'portrait'}, 1:1",
                 fontsize=8.5, color="#333")
        _title_block(fig, spec, 0.04, 0.53)
        pdf.savefig(fig); plt.close(fig)
        # ---- tiles
        for r in range(L["rows"]):
            for c in range(L["cols"]):
                fig = plt.figure(figsize=(L["pw"], L["ph"]))
                ax = fig.add_axes([MARGIN / L["pw"], MARGIN / L["ph"], 1 - 2 * MARGIN / L["pw"], 1 - 2 * MARGIN / L["ph"]])
                x0 = L["org"][0] + c * L["sx"]; y1 = L["org"][1] - r * L["sy"]; x1 = x0 + L["cw"]; y0 = y1 - L["ch"]
                ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.axis("off")
                _draw(ax, spec)
                ov = OVERLAP * IN
                # overlap bands (where the neighbour's page also prints): right and bottom edges are glued UNDER the next page
                if c < L["cols"] - 1: ax.add_patch(Rectangle((x1 - ov, y0), ov, L["ch"], fc="#dfe8f1", ec="none", alpha=0.55, zorder=1))
                if r < L["rows"] - 1: ax.add_patch(Rectangle((x0, y0), L["cw"], ov, fc="#dfe8f1", ec="none", alpha=0.55, zorder=1))
                if c > 0: ax.plot([x0 + ov, x0 + ov], [y0, y1], color=DIMC, lw=0.4, ls=(0, (2, 2)), zorder=2)
                if r > 0: ax.plot([x0, x1], [y1 - ov, y1 - ov], color=DIMC, lw=0.4, ls=(0, (2, 2)), zorder=2)
                # registration crosses on the global 1 in grid
                gx = np.arange(math.ceil(x0 / IN), math.floor(x1 / IN) + 1) * IN; gy = np.arange(math.ceil(y0 / IN), math.floor(y1 / IN) + 1) * IN
                for X in gx:
                    for Y in gy: _cross(ax, X, Y, 1.5)
                # frame
                ax.add_patch(Rectangle((x0, y0), L["cw"], L["ch"], fc="none", ec="#999", lw=0.4, zorder=2))
                # page label, edge notes
                lab = f"{spec['name']} rev {spec['rev']}  |  tile {tile_name(r, c)}  ({r * L['cols'] + c + 1}/{L['rows'] * L['cols']})"
                fig.text(0.5, 1 - MARGIN / L["ph"] / 2.2, lab, fontsize=7, ha="center", va="center", color="#333")
                fig.text(0.5, MARGIN / L["ph"] / 2.2, "Print at 100% / Actual size. Trim the left and top edges along the dashed line where shown, lay over the "
                         "neighbour's shaded band, match the + crosses, tape.", fontsize=5.5, ha="center", va="center", color="#555")
                if c < L["cols"] - 1: fig.text(1 - MARGIN / L["pw"] / 2, 0.5, f"{tile_name(r, c + 1)} goes here >", rotation=-90, fontsize=6, ha="center", va="center", color=DIMC)
                if r < L["rows"] - 1: fig.text(0.85, MARGIN / L["ph"] * 0.85, f"v {tile_name(r + 1, c)} below", fontsize=6, ha="center", va="center", color=DIMC)
                # check square in the emptiest corner of the non-overlap area
                bw, bh = 62, 66; cands = [(x0 + 4 + (ov if c > 0 else 0), y0 + 4 + (ov if r < L["rows"] - 1 else 0)),
                                          (x1 - bw - 4 - (ov if c < L["cols"] - 1 else 0), y0 + 4 + (ov if r < L["rows"] - 1 else 0)),
                                          (x0 + 4 + (ov if c > 0 else 0), y1 - bh - 4 - (ov if r > 0 else 0)),
                                          (x1 - bw - 4 - (ov if c < L["cols"] - 1 else 0), y1 - bh - 4 - (ov if r > 0 else 0))]
                hits = [_box_hits(S, x - 3, y - 3, x + bw, y + bh) for x, y in cands]
                bx, by = cands[int(np.argmin(hits))]
                _check_square(ax, bx + 3, by + 3)
                pdf.savefig(fig); plt.close(fig)
    return L


def _title_block(fig, spec, x, ytop):
    y = ytop
    fig.text(x, y, "Key dimensions", fontsize=9, weight="bold"); y -= 0.028
    for row in spec.get("key_dims", []):
        name, val, note = row
        v = fmt(val) if isinstance(val, (int, float)) else val
        fig.text(x, y, name, fontsize=7.2); fig.text(x + 0.21, y, v, fontsize=7.2, family="monospace"); fig.text(x + 0.42, y, note, fontsize=6.4, color="#444")
        y -= 0.021
    y -= 0.008
    fig.text(x, y, "Provenance and accuracy", fontsize=9, weight="bold"); y -= 0.026
    for line in spec.get("title_block", []):
        fig.text(x, y, line, fontsize=6.6, color="#222"); y -= 0.019


def write_full(spec, path, png=None, dpi=110):
    """One page, exact 1:1, sized to the drawing plus a title strip (for a plotter / print shop). Optional preview PNG."""
    lo, hi = _bbox(spec, pad=12); lo = lo - [0, 75]; W, H = (hi - lo) / IN      # 75 mm strip below for the check square
    nlines = len(spec.get("key_dims", [])) + len(spec.get("title_block", [])) + 5
    strip = 0.2 * nlines + 0.6
    fig = plt.figure(figsize=(max(W, 11.0), H + strip))
    FW, FH = fig.get_size_inches()
    ax = fig.add_axes([0, strip / FH, W / FW, H / FH]); ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.axis("off")
    _draw(ax, spec); _check_square(ax, lo[0] + 6, lo[1] + 4)
    fig.text(0.2 / FW, (strip - 0.25) / FH, f"{spec['title']}  -  {spec['name']} rev {spec['rev']}  -  1:1, print at 100%", fontsize=11, weight="bold")
    y = (strip - 0.5) / FH; x = 0.2 / FW
    for name, val, note in spec.get("key_dims", []):
        v = fmt(val) if isinstance(val, (int, float)) else val
        fig.text(x, y, f"{name}:  {v}   {note}", fontsize=7.2); y -= 0.2 / FH
    y -= 0.05 / FH
    for line in spec.get("title_block", []): fig.text(x, y, line, fontsize=6.6, color="#222"); y -= 0.2 / FH
    fig.savefig(path)
    if png: fig.savefig(png, dpi=dpi)
    plt.close(fig)


def write_dxf(spec, path):
    """AutoCAD R12 ASCII DXF, millimetres. Layers: CUT, REF, MARK, DIM, TEXT."""
    out = []
    def g(c, v): out.append(f"{c}\n{v}")
    g(0, "SECTION"); g(2, "HEADER"); g(9, "$ACADVER"); g(1, "AC1009"); g(9, "$INSUNITS"); g(70, 4); g(9, "$MEASUREMENT"); g(70, 1); g(0, "ENDSEC")
    g(0, "SECTION"); g(2, "TABLES"); g(0, "TABLE"); g(2, "LAYER"); g(70, 5)
    for nm, col in (("CUT", 7), ("REF", 8), ("MARK", 1), ("DIM", 5), ("TEXT", 7)):
        g(0, "LAYER"); g(2, nm); g(70, 0); g(62, col); g(6, "CONTINUOUS")
    g(0, "ENDTAB"); g(0, "ENDSEC"); g(0, "SECTION"); g(2, "ENTITIES")
    def poly(p, layer, closed=False):
        g(0, "POLYLINE"); g(8, layer); g(66, 1); g(70, 1 if closed else 0)
        for x, y in p: g(0, "VERTEX"); g(8, layer); g(10, f"{x:.4f}"); g(20, f"{y:.4f}")
        g(0, "SEQEND"); g(8, layer)
    def text(x, y, s, h=3.0, layer="TEXT", rot=0):
        for i, line in enumerate(str(s).split("\n")):
            g(0, "TEXT"); g(8, layer); g(10, f"{x:.3f}"); g(20, f"{y - i * h * 1.5:.3f}"); g(40, h); g(1, line.replace('"', " in")); g(50, rot)
    for it in spec["items"]:
        k = it["kind"]
        if k == "cut": poly(np.asarray(it["pts"]), "CUT", it.get("closed", False))
        elif k == "line":
            poly(np.asarray(it["pts"]), "MARK" if it.get("style") == "mark" else "REF")
            if it.get("label"): p = np.asarray(it["pts"]); i = len(p) // 2; text(p[i, 0], p[i, 1] + 1, it["label"], 2.5, "MARK" if it.get("style") == "mark" else "REF")
        elif k == "dim":
            p1, p2 = np.asarray(it["p1"], float), np.asarray(it["p2"], float); d = p2 - p1; t = d / np.linalg.norm(d); n = np.array([-t[1], t[0]])
            a, b = p1 + n * it["off"], p2 + n * it["off"]; poly([p1, a, b, p2], "DIM"); m = (a + b) / 2
            text(m[0], m[1] + 1, it.get("label") or fmt(np.linalg.norm(d)), 2.5, "DIM", math.degrees(math.atan2(t[1], t[0])))
        elif k == "text": text(it["xy"][0], it["xy"][1], it["s"], 3.0)
    g(0, "ENDSEC"); g(0, "EOF")
    open(path, "w").write("\n".join(out) + "\n")


def write_all(spec, outdir):
    import os; os.makedirs(outdir, exist_ok=True); b = f"{outdir}/{spec['name']}"
    L = write_tiled(spec, b + "_tiled_letter.pdf"); write_full(spec, b + "_full_1to1.pdf", png=b + "_preview.png"); write_dxf(spec, b + ".dxf")
    return L
