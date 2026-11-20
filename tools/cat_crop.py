"""USAGE:
  uv run --no-project --with pillow python -I tools/cat_crop.py crop SRC.JPG OUT.jpg x0 y0 x1 y1 [--scale S]
      Crop a full-resolution photo (EXIF orientation applied first; coords are in the
      oriented image, as fractions 0-1 if all <=1 else pixels), optionally rotate (--rot DEG, counter-clockwise) and rescale (--scale S).
  uv run --no-project --with pillow python -I tools/cat_crop.py grid OUT.jpg W IMG1 IMG2 ...
      Tile images (oriented) into a grid of 2 columns, each scaled to width W, labelled.
  uv run --no-project --with pillow python -I tools/cat_crop.py sharp IMG...
      Print a Laplacian-variance sharpness metric of the central 60% of each oriented image
      at 1/2 resolution (relative; only comparable between similar scenes).
Catalogue-agent helper; never writes into drive/."""
import sys
from PIL import Image, ImageOps, ImageDraw, ImageFilter, ImageStat

def load(p):
    return ImageOps.exif_transpose(Image.open(p))

def main(a):
    cmd = a[0]
    if cmd == "crop":
        src, out = a[1], a[2]
        x0, y0, x1, y1 = map(float, a[3:7])
        s = float(a[a.index("--scale")+1]) if "--scale" in a else 1.0
        rot = float(a[a.index("--rot")+1]) if "--rot" in a else 0.0
        im = load(src); W, H = im.size
        if max(x0, y0, x1, y1) <= 1:
            x0, x1, y0, y1 = x0*W, x1*W, y0*H, y1*H
        c = im.crop((int(x0), int(y0), int(x1), int(y1)))
        if rot:
            c = c.rotate(rot, resample=Image.BICUBIC, expand=True)
        if s != 1.0:
            c = c.resize((int(c.width*s), int(c.height*s)), Image.LANCZOS)
        c.save(out, quality=92); print(out, c.size, "from", (W, H))
    elif cmd == "grid":
        out, w = a[1], int(a[2]); ims = []
        for p in a[3:]:
            im = load(p); im = im.resize((w, int(im.height*w/im.width)), Image.LANCZOS)
            d = ImageDraw.Draw(im); lab = p.split("/")[-1].split(".")[0][-4:]
            d.rectangle((0, 0, 110, 44), fill="black"); d.text((8, 6), lab, fill="yellow", font_size=36)
            ims.append(im)
        cols = 2; rows = (len(ims)+1)//2; rh = max(i.height for i in ims)
        g = Image.new("RGB", (w*cols+10, rh*rows+10*(rows-1)), "black")
        for k, im in enumerate(ims):
            g.paste(im, ((k % 2)*(w+10), (k//2)*(rh+10)))
        g.save(out, quality=88); print(out, g.size)
    elif cmd == "sharp":
        for p in a[1:]:
            im = load(p).convert("L"); im = im.resize((im.width//2, im.height//2))
            W, H = im.size; c = im.crop((int(.2*W), int(.2*H), int(.8*W), int(.8*H)))
            e = c.filter(ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], 1, 128))
            print(p.split("/")[-1], round(ImageStat.Stat(e).var[0], 1))
main(sys.argv[1:])
