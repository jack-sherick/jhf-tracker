import icnsutil
import math
import os
import sys
import tempfile
from PIL import Image, ImageDraw


def make_circular_cover(img: Image.Image, size: int) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    scale = max(size / w, size / h)
    new_w, new_h = math.ceil(w * scale), math.ceil(h * scale)
    scaled = img.resize((new_w, new_h), Image.LANCZOS)

    # background-position: left bottom
    x, y = 0, new_h - size
    cropped = scaled.crop((x, y, x + size, y + size))

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(cropped, mask=mask)
    return result


def build_ico(img: Image.Image, out: str):
    sizes = [16, 32, 48, 256]
    frames = [make_circular_cover(img, s) for s in sizes]
    frames[0].save(out, format="ICO", append_images=frames[1:], sizes=[(s, s) for s in sizes])
    print(f"Saved {out}")


_ICNS_KEYS = {16: 'icp4', 32: 'icp5', 64: 'icp6', 128: 'ic07', 256: 'ic08', 512: 'ic09', 1024: 'ic10'}

def build_icns(img: Image.Image, out: str):
    ic = icnsutil.IcnsFile()
    with tempfile.TemporaryDirectory() as tmp:
        for size, key in _ICNS_KEYS.items():
            frame = make_circular_cover(img, size)
            path = os.path.join(tmp, f"{size}.png")
            frame.save(path, format="PNG")
            ic.add_media(key=key, file=path)
    ic.write(out)
    print(f"Saved {out}")


if __name__ == "__main__":
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    src = positional[0] if positional else "assets/stoke.png"
    img = Image.open(src)

    if "--icns" in sys.argv:
        build_icns(img, "assets/stoke.icns")
    else:
        build_ico(img, "assets/stoke.ico")
