"""EXIF orientation <-> raw sensor pixel mapping. The ONE place this mapping lives.

Raw image: width W, height H (4032 x 3024 here), array-index pixel convention (pixel centres at integers).
Displayed image = PIL.ImageOps.exif_transpose(raw). Tested against PIL in tests/test_orientation.py.

  orient  display size  disp (u, v) from raw (x, y)
  1       W x H         (x, y)
  2       W x H         (W-1-x, y)            mirror horizontal
  3       W x H         (W-1-x, H-1-y)        rotate 180
  4       W x H         (x, H-1-y)            mirror vertical
  5       H x W         (y, x)                transpose
  6       H x W         (H-1-y, x)            rotate 90 CW to display (iPhone portrait)
  7       H x W         (H-1-y, W-1-x)        transverse
  8       H x W         (y, W-1-x)            rotate 90 CCW to display
"""
from functools import lru_cache
import numpy as np

RAW_W, RAW_H = 4032, 3024


def disp_size(orient, W=RAW_W, H=RAW_H):
    return (H, W) if orient in (5, 6, 7, 8) else (W, H)


def raw_to_disp(xy, orient, W=RAW_W, H=RAW_H):
    xy = np.asarray(xy, float)
    x, y = xy[..., 0], xy[..., 1]
    m = {1: (x, y), 2: (W - 1 - x, y), 3: (W - 1 - x, H - 1 - y), 4: (x, H - 1 - y),
         5: (y, x), 6: (H - 1 - y, x), 7: (H - 1 - y, W - 1 - x), 8: (y, W - 1 - x)}[int(orient)]
    return np.stack(m, axis=-1)


def disp_to_raw(uv, orient, W=RAW_W, H=RAW_H):
    uv = np.asarray(uv, float)
    u, v = uv[..., 0], uv[..., 1]
    m = {1: (u, v), 2: (W - 1 - u, v), 3: (W - 1 - u, H - 1 - v), 4: (u, H - 1 - v),
         5: (v, u), 6: (v, H - 1 - u), 7: (W - 1 - v, H - 1 - u), 8: (W - 1 - v, u)}[int(orient)]
    return np.stack(m, axis=-1)


def disp_dir_to_raw(duv, orient):
    """Map a direction vector (no offset) from display to raw."""
    return disp_to_raw(duv, orient, W=1, H=1) - disp_to_raw(np.zeros(2), orient, W=1, H=1)


def to_display_array(arr, orient):
    """Apply EXIF orientation to a raw numpy image (H x W [x C]) -> displayed array."""
    o = int(orient)
    if o == 1: return arr
    if o == 2: return arr[:, ::-1]
    if o == 3: return arr[::-1, ::-1]
    if o == 4: return arr[::-1]
    if o == 5: return np.swapaxes(arr, 0, 1)
    if o == 6: return np.swapaxes(arr, 0, 1)[:, ::-1]
    if o == 7: return np.swapaxes(arr, 0, 1)[::-1, ::-1]
    if o == 8: return np.swapaxes(arr, 0, 1)[::-1]
    raise ValueError(o)


@lru_cache(maxsize=None)
def exif_orientation(path):
    from PIL import Image
    with Image.open(path) as im:
        return int(im.getexif().get(0x0112, 1) or 1)
