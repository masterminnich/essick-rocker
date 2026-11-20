"""USAGE:
  python -I tools/mark.py add LANDMARK IMAGE X_RAW Y_RAW [--source manual] [--note TEXT]
  python -I tools/mark.py rm LANDMARK [IMAGE]
  python -I tools/mark.py list [LANDMARK]
  python -I tools/mark.py convert IMAGE X Y --space disp|mid      (print the raw coordinates of a point)
  python -I tools/mark.py nudge LANDMARK IMAGE DX DY   move a mark by DX right / DY down AS SEEN in the upright crop
                                                       (raw-pixel units; orientation handled here)
'batch' reads sub-commands (one per line, e.g. 'nudge CRS_L 1528 -3 2') from stdin.
'add' also takes --space mid|disp to enter a rough seed read off a work/mid viewing copy.
Edit skeleton/marks.csv (landmark_id,image,x_raw,y_raw,source,note). Coordinates are raw sensor pixels.
Example: python -I tools/mark.py add L01 1470 1203.5 2210 --note "R front leg plug"
"""
import argparse
import sys
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # noqa: E702
from tools._common import img_name


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=None, help="marks csv (default skeleton/marks.csv)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("add"); p.add_argument("landmark"); p.add_argument("image"); p.add_argument("x", type=float); p.add_argument("y", type=float)
    p.add_argument("--source", default="manual"); p.add_argument("--note", default="")
    p.add_argument("--space", default="raw", choices=["raw", "disp", "mid"])
    p = sp.add_parser("nudge"); p.add_argument("landmark"); p.add_argument("image"); p.add_argument("dx", type=float); p.add_argument("dy", type=float)
    p = sp.add_parser("rm"); p.add_argument("landmark"); p.add_argument("image", nargs="?")
    p = sp.add_parser("list"); p.add_argument("landmark", nargs="?")
    p = sp.add_parser("convert"); p.add_argument("image"); p.add_argument("x", type=float); p.add_argument("y", type=float)
    p.add_argument("--space", required=True, choices=["disp", "mid", "raw"])
    p = sp.add_parser("batch", help="read one sub-command per line from stdin")
    a = ap.parse_args(argv)
    if a.cmd == "batch":
        import shlex
        for line in sys.stdin:
            line = line.split("#")[0].strip()
            if line:
                main((["--file", a.file] if a.file else []) + shlex.split(line))
        return
    from rocker import marks as mk
    kw = {"path": a.file} if a.file else {}
    if a.cmd == "add":
        from rocker.images import to_raw
        x, y = to_raw(img_name(a.image), (a.x, a.y), a.space)
        mk.upsert(a.landmark, img_name(a.image), x, y, a.source if a.space == "raw" else "seed", a.note, **kw)
        print(f"{a.landmark} {img_name(a.image)} raw=({x:.2f},{y:.2f})")
    elif a.cmd == "nudge":
        from rocker.images import orient_of
        from rocker.orientation import disp_dir_to_raw
        name = img_name(a.image)
        r = [m for m in mk.read(**kw) if m["landmark_id"] == a.landmark and m["image"] == name][0]
        d = disp_dir_to_raw([a.dx, a.dy], orient_of(name))
        mk.upsert(a.landmark, name, r["x_raw"] + d[0], r["y_raw"] + d[1], "manual", r["note"], **kw)
        print(f"{a.landmark} {name} raw=({r['x_raw'] + d[0]:.2f},{r['y_raw'] + d[1]:.2f})")
    elif a.cmd == "rm":
        mk.remove(a.landmark, img_name(a.image) if a.image else None, **kw)
    elif a.cmd == "list":
        for r in mk.read(**kw):
            if a.landmark in (None, r["landmark_id"]):
                print(r["landmark_id"], r["image"], f"{r['x_raw']:.2f}", f"{r['y_raw']:.2f}", r["source"], r["note"])
    elif a.cmd == "convert":
        from rocker.images import to_raw
        x, y = to_raw(img_name(a.image), (a.x, a.y), a.space)
        print(f"{x:.2f} {y:.2f}")


if __name__ == "__main__":
    main()
