"""rocker: projection / triangulation / overlay toolkit for the walnut rocking-chair reconstruction.

Pixel convention used everywhere in this package unless a name says otherwise:
  "raw"  = raw sensor pixels of the ORIGINAL 4032x3024 JPEG, EXIF orientation NOT applied,
           array-index convention: the centre of the top-left pixel is (0, 0); x to the right, y down.
  "disp" = the same image after applying its EXIF orientation (what a viewer shows), same index convention.
COLMAP's own coordinates (pixel corner at 0, model resolution) are only used inside cameras.py.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
