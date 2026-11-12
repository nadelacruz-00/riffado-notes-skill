#!/usr/bin/env python3
"""Rotate and/or zoom into a recording photo so small or sideways text becomes readable.

Works from the full-resolution original when one exists (images/<id>/orig/), so a crop
keeps every pixel the camera captured.

Usage:
  photo_tool.py images/<id>/05-09m49s.jpg --rotate 90 --out p5.jpg
  photo_tool.py images/<id>/05-09m49s.jpg --crop 0.1,0.3,0.9,0.7 --out p5-code.jpg
  photo_tool.py images/<id>/05-09m49s.jpg --grid 2x2 --out p5-tile   # writes p5-tile-r1c1.jpg ...

--rotate is clockwise degrees (90, 180, 270). --crop is left,top,right,bottom as fractions
(0-1) of the image AFTER rotation. Output is capped at --max px on the long edge.
"""
import argparse, glob, os, sys

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("PIL_MISSING: install Pillow (pip install pillow) to rotate or crop photos.")


def original_of(path):
    folder, name = os.path.split(path)
    stem = os.path.splitext(name)[0]
    hits = glob.glob(os.path.join(folder, "orig", stem + ".*"))
    return hits[0] if hits else path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=0)
    p.add_argument("--crop", help="left,top,right,bottom as fractions 0-1")
    p.add_argument("--grid", help="split into tiles, e.g. 2x2 or 3x1 (cols x rows)")
    p.add_argument("--max", type=int, default=1568)
    p.add_argument("--out", required=True, help="output file (or prefix with --grid)")
    a = p.parse_args()

    src = original_of(a.src)
    try:
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    except Exception as e:
        sys.exit(f"OPEN_FAILED: {src}: {e}")
    if a.rotate:
        im = im.rotate(-a.rotate, expand=True)
    if a.crop:
        l, t, r, b = (float(x) for x in a.crop.split(","))
        W, H = im.size
        im = im.crop((int(l * W), int(t * H), int(r * W), int(b * H)))

    def save(img, path):
        img = img.copy()
        img.thumbnail((a.max, a.max))
        img.save(path, "JPEG", quality=88)
        print(f"wrote {path} {img.size[0]}x{img.size[1]} (from {os.path.basename(src)})")

    if a.grid:
        cols, rows = (int(x) for x in a.grid.lower().split("x"))
        W, H = im.size
        for r in range(rows):
            for c in range(cols):
                tile = im.crop((c * W // cols, r * H // rows, (c + 1) * W // cols, (r + 1) * H // rows))
                save(tile, f"{a.out}-r{r + 1}c{c + 1}.jpg")
    else:
        save(im, a.out if a.out.lower().endswith((".jpg", ".jpeg")) else a.out + ".jpg")


if __name__ == "__main__":
    main()
