"""Genera los carruseles 1080x1350 de la campaña Mascotas Navidad/Reyes 2026.

Uso: python3 render.py <carpeta_fotos_tienda> <carpeta_fuentes>
Las fotos son las de las fichas de https://ojoconesedetalle.es (sin alterar,
solo recortadas/escaladas). Los textos salen de las fichas comprobadas el 29/10/2026.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

IMG_DIR = Path(sys.argv[1])
FONT_DIR = Path(sys.argv[2])
OUT_DIR = Path(__file__).parent / "slides"
SPEC = json.loads((Path(__file__).parent / "carruseles.json").read_text())

W, H = 1080, 1350
INK = (30, 27, 46)
CREAM = (251, 248, 244)
TERRA = (185, 83, 46)
GREEN = (31, 94, 74)
MUTED = (110, 104, 120)


def font(size, weight="Bold"):
    f = ImageFont.truetype(str(FONT_DIR / "DMSans.ttf"), size)
    f.set_variation_by_name(weight)
    return f


def wrap(draw, text, fnt, max_w):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            test = (cur + " " + word).strip()
            if draw.textlength(test, font=fnt) <= max_w:
                cur = test
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def text_block(draw, xy, text, fnt, fill, max_w, spacing=1.18, align="left"):
    x, y = xy
    for line in wrap(draw, text, fnt, max_w):
        lx = x if align == "left" else x + (max_w - draw.textlength(line, font=fnt)) / 2
        draw.text((lx, y), line, font=fnt, fill=fill)
        y += int(fnt.size * spacing)
    return y


def photo(name, size):
    im = Image.open(IMG_DIR / name).convert("RGB")
    return ImageOps.fit(im, size, Image.LANCZOS, centering=(0.5, 0.5))


def brand_tag(draw, y, color):
    draw.text((60, y), "OJO CON ESE DETALLE", font=font(24, "SemiBold"), fill=color)


def page_dots(draw, idx, total, color, y=H - 46):
    x = W - 60 - total * 22
    for i in range(total):
        r = 6
        cx = x + i * 22
        if i == idx:
            draw.ellipse((cx - r, y - r, cx + r, y + r), fill=color)
        else:
            draw.ellipse((cx - r, y - r, cx + r, y + r), outline=color, width=2)


def slide_photo(s, idx, total, cover=False):
    img = Image.new("RGB", (W, H), CREAM)
    img.paste(photo(s["img"], (1000, 1000)), ((W - 1000) // 2, H - 1000))
    d = ImageDraw.Draw(img)
    brand_tag(d, 38, TERRA)
    y = text_block(d, (60, 82), s["title"], font(74 if cover else 66), INK, W - 120, 1.1)
    if s.get("sub"):
        text_block(d, (60, y + 6), s["sub"], font(38, "Regular"), MUTED, W - 120, 1.2)
    if cover:
        tag = "Desliza  →"
        f = font(28, "SemiBold")
        tw = d.textlength(tag, font=f)
        d.rounded_rectangle((W - 60 - tw - 40, H - 100, W - 60, H - 40), 30, fill=CREAM)
        d.text((W - 60 - tw - 20, H - 88), tag, font=f, fill=INK)
    else:
        page_dots(d, idx, total, CREAM)
    return img


def slide_list(s, idx, total):
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    brand_tag(d, 38, TERRA)
    y = text_block(d, (60, 100), s["title"], font(70), INK, W - 120, 1.1) + 40
    for i, item in enumerate(s["items"], 1):
        d.ellipse((60, y, 112, y + 52), fill=GREEN)
        n = str(i)
        fn = font(28)
        d.text((86 - d.textlength(n, font=fn) / 2, y + 9), n, font=fn, fill=CREAM)
        y = text_block(d, (140, y + 4), item, font(42, "Medium"), INK, W - 200, 1.2) + 30
    if s.get("img"):
        side = min(H - y - 100, 520)
        if side > 240:
            ph = photo(s["img"], (side, side))
            mask = Image.new("L", (side, side), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, side, side), 36, fill=255)
            img.paste(ph, ((W - side) // 2, H - side - 90), mask)
    if s.get("note"):
        text_block(d, (60, H - 80), s["note"], font(30, "Regular"), MUTED, W - 300)
    page_dots(d, idx, total, INK)
    return img


def slide_cta(s, idx, total):
    calm = s.get("calm", False)
    bg, fg, accent = (CREAM, INK, GREEN) if calm else (TERRA, CREAM, CREAM)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    brand_tag(d, 38, accent if calm else CREAM)
    y = text_block(d, (60, 110), s["title"], font(70), fg, W - 120, 1.1) + 20
    d.text((60, y), s["price"], font=font(120), fill=fg)
    y += 170
    for line in s["lines"]:
        d.line((60, y + 22, 84, y + 22), fill=fg, width=4)
        y = text_block(d, (104, y), line, font(42, "Medium"), fg, W - 170, 1.2) + 22
    btn = "Enlace en la bio"
    f = font(40)
    tw = d.textlength(btn, font=f)
    by = H - 260
    d.rounded_rectangle((60, by, 60 + tw + 80, by + 92), 46, fill=fg)
    d.text((100, by + 20), btn, font=f, fill=bg)
    d.text((60, by + 120), "ojoconesedetalle.es", font=font(30, "SemiBold"), fill=fg)
    if s.get("note"):
        text_block(d, (60, H - 70), s["note"], font(26, "Regular"), fg, W - 300)
    page_dots(d, idx, total, fg)
    return img


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for key, c in SPEC.items():
        total = len(c["slides"])
        for i, s in enumerate(c["slides"]):
            kind = s["type"]
            if kind == "cover":
                im = slide_photo(s, i, total, cover=True)
            elif kind == "photo":
                im = slide_photo(s, i, total)
            elif kind == "list":
                im = slide_list(s, i, total)
            else:
                im = slide_cta(s, i, total)
            im.save(OUT_DIR / f"{key}-{i + 1:02d}.jpg", quality=90)
        print(key, total)


main()
