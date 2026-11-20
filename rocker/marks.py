"""Marks file: R/skeleton/marks.csv with columns landmark_id,image,x_raw,y_raw,source,note.

x_raw/y_raw: raw sensor pixels of the original 4032x3024 JPEG (EXIF orientation not applied), pixel centres at
integers. source: manual | refined:<method> | ... ; a landmark may have several rows for the same image only
if they carry different landmark_ids (re-marks use ids like 'L03#2')."""
import csv
from pathlib import Path
from . import ROOT

MARKS = ROOT / "skeleton/marks.csv"
COLS = ["landmark_id", "image", "x_raw", "y_raw", "source", "note"]


def read(path=MARKS):
    p = Path(path)
    if not p.exists():
        return []
    with p.open() as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["x_raw"], r["y_raw"] = float(r["x_raw"]), float(r["y_raw"])
    return rows


def write(rows, path=MARKS):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, COLS); w.writeheader()
        for r in rows:
            w.writerow({k: (f"{r[k]:.2f}" if k in ("x_raw", "y_raw") else r.get(k, "")) for k in COLS})
    tmp.replace(p)


def upsert(landmark, image, x, y, source="manual", note="", path=MARKS):
    rows = [r for r in read(path) if not (r["landmark_id"] == landmark and r["image"] == image)]
    rows.append(dict(landmark_id=landmark, image=image, x_raw=float(x), y_raw=float(y), source=source, note=note))
    rows.sort(key=lambda r: (r["landmark_id"], r["image"]))
    write(rows, path)


def remove(landmark, image=None, path=MARKS):
    rows = [r for r in read(path) if not (r["landmark_id"] == landmark and (image is None or r["image"] == image))]
    write(rows, path)


def by_landmark(rows):
    out = {}
    for r in rows:
        out.setdefault(r["landmark_id"], []).append(r)
    return out
