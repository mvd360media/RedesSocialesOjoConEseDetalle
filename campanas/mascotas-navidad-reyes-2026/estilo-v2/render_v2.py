"""Estilo v2: historias con escenas recreadas con IA + producto real.

Uso: python3 render_v2.py <fotos_tienda> <escenas_ia> <fuentes> [claves...]
Las escenas IA no muestran el producto; el producto siempre es la foto real de la ficha.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

SHOP = Path(sys.argv[1])
AI = Path(sys.argv[2])
FONTS = Path(sys.argv[3])
BASE = Path(__file__).parent
SPEC = json.loads((BASE / "piezas_v2.json").read_text())

INK = (30, 27, 46)
CREAM = (251, 248, 244)
TERRA = (185, 83, 46)
GREEN = (31, 94, 74)
FPS = 30
VW, VH = 1080, 1920


def font(size, weight="Bold"):
    f = ImageFont.truetype(str(FONTS / "DMSans.ttf"), size)
    f.set_variation_by_name(weight)
    return f


def src(name):
    p = AI / name if (AI / name).exists() else SHOP / name
    return Image.open(p).convert("RGB")


def wrap(draw, words, fnt, max_w):
    lines, cur = [], []
    for w in words:
        if cur and draw.textlength(" ".join(cur + [w]), font=fnt) > max_w:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    lines.append(cur)
    return lines


def caption(im, text, shown, y_center, size=78, hl=None, box=INK, fg=CREAM):
    """Texto estilo subtítulo nativo: cajas por línea, palabras que aparecen una a una."""
    d = ImageDraw.Draw(im, "RGBA")
    fnt = font(size)
    words = text.split()
    lines = wrap(d, words, fnt, VW - 200)
    lh = int(size * 1.32)
    y = y_center - len(lines) * lh // 2
    k = 0
    for line in lines:
        full = " ".join(line)
        w = d.textlength(full, font=fnt)
        x = (VW - w) / 2
        vis = [wd for wd in line if (k := k + 1) <= shown]
        if vis:
            vw = d.textlength(" ".join(vis), font=fnt)
            d.rounded_rectangle((x - 26, y - 8, x + vw + 26, y + lh - 14), 22, fill=box + (235,))
            cx = x
            for wd in vis:
                col = TERRA if hl and wd.strip("…,.¿?¡!").lower() in hl else fg
                if col == TERRA and box == TERRA:
                    col = INK
                d.text((cx, y), wd, font=fnt, fill=col)
                cx += d.textlength(wd + " ", font=fnt)
        y += lh
    return im


def fill_frame(img, zoom):
    w, h = img.size
    scale = max(VW / w, VH / h) * zoom
    r = img.resize((int(w * scale), int(h * scale)), Image.BILINEAR)
    x, y = (r.width - VW) // 2, (r.height - VH) // 2
    return r.crop((x, y, x + VW, y + VH))


def product_frame(img, t, blur_cache={}):
    key = id(img)
    if key not in blur_cache:
        bg = fill_frame(img, 1.0).filter(ImageFilter.GaussianBlur(40))
        bg = Image.blend(bg, Image.new("RGB", bg.size, INK), 0.35)
        blur_cache[key] = bg
    frame = blur_cache[key].copy()
    pop = 1.18 - 0.18 * min(t / 0.35, 1.0)  # entrada con golpe
    drift = 1.0 + 0.05 * t / 3
    side = int(940 * pop * drift)
    ph = ImageOps.fit(img, (side, side), Image.BILINEAR)
    mask = Image.new("L", ph.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, side, side), 46, fill=255)
    frame.paste(ph, ((VW - side) // 2, 420 + (940 - side) // 2), mask)
    return frame


def ai_tag(im):
    d = ImageDraw.Draw(im, "RGBA")
    f = font(26, "Medium")
    t = "Escena recreada con IA"
    w = d.textlength(t, font=f)
    d.rounded_rectangle((VW - w - 90, 260, VW - 50, 306), 22, fill=(0, 0, 0, 120))
    d.text((VW - w - 70, 268), t, font=f, fill=CREAM)


def cta_frame(s, t):
    calm = s.get("calm")
    bg, fg = (CREAM, INK) if calm else (TERRA, CREAM)
    im = Image.new("RGB", (VW, VH), bg)
    d = ImageDraw.Draw(im)
    d.text((70, 250), "OJO CON ESE DETALLE", font=font(30, "SemiBold"), fill=fg)
    y = 360
    for i, line in enumerate(s["big"]):
        a = min(max((t - i * 0.25) / 0.25, 0), 1)
        if a > 0:
            f = font(118)
            d.text((70, y + int(30 * (1 - a))), line, font=f, fill=fg)
        y += 140
    y += 40
    if t > 0.8:
        d.text((70, y), s["price"], font=font(170), fill=fg)
    y += 230
    if t > 1.1:
        for line in s["lines"]:
            d.ellipse((72, y + 20, 96, y + 44), fill=fg)
            d.text((120, y), line, font=font(48, "Medium"), fill=fg)
            y += 76
    if t > 1.4:
        btn, f = "Enlace en la bio", font(54)
        tw = d.textlength(btn, font=f)
        d.rounded_rectangle((70, 1340, 70 + tw + 100, 1460), 60, fill=fg)
        d.text((120, 1366), btn, font=f, fill=bg)
        if s.get("note"):
            d.text((70, 1490), s["note"], font=font(30, "Regular"), fill=fg)
    return im


def reel(key, r):
    out = BASE / "reels" / f"{key}.mp4"
    out.parent.mkdir(exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-shortest",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-movflags", "+faststart",
           "-c:a", "aac", "-map_metadata", "-1", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cover = None
    for s in r["scenes"]:
        n = int(s["dur"] * FPS)
        img = src(s["img"]) if s.get("img") else None
        words = len(s.get("text", "").split())
        for i in range(n):
            t = i / FPS
            if s["type"] == "ai":
                fr = fill_frame(img, 1.0 + 0.07 * i / n)
                ai_tag(fr)
            elif s["type"] == "product":
                fr = product_frame(img, t)
                if i < 2:
                    fr = Image.blend(fr, Image.new("RGB", fr.size, CREAM), 0.7 - 0.35 * i)
            else:
                fr = cta_frame(s, t)
            if s.get("text"):
                shown = min(words, 1 + int(t / 0.13))
                caption(fr, s["text"], shown, s.get("y", 1250), hl=s.get("hl"),
                        box=TERRA if s["type"] == "product" else INK)
            if cover is None and s.get("text") and shown == words:
                cover = fr.copy()
            p.stdin.write(fr.tobytes())
    p.stdin.close()
    p.wait()
    cover.save(out.with_suffix(".jpg"), quality=90)
    print("reel", key)


# ---- 4:5 portada de carrusel y diapositivas ----
W, H = 1080, 1350


def slide(s, idx, total):
    if s["type"] == "ai":
        im = src(s["img"])
        sc = max(W / im.width, H / im.height)
        im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        x, y = (im.width - W) // 2, (im.height - H) // 2
        im = im.crop((x, y, x + W, y + H))
        d = ImageDraw.Draw(im, "RGBA")
        f = font(24, "Medium")
        t = "Escena recreada con IA"
        w = d.textlength(t, font=f)
        d.rounded_rectangle((W - w - 80, 30, W - 40, 72), 20, fill=(0, 0, 0, 120))
        d.text((W - w - 60, 37), t, font=f, fill=CREAM)
    else:
        base = src(s["img"])
        im = ImageOps.fit(base, (W, H)).filter(ImageFilter.GaussianBlur(40))
        im = Image.blend(im, Image.new("RGB", im.size, INK), 0.35)
        side = 900
        ph = ImageOps.fit(base, (side, side), Image.LANCZOS)
        mask = Image.new("L", ph.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, side, side), 40, fill=255)
        im.paste(ph, ((W - side) // 2, 150), mask)
    words = s["text"].split()
    caption_45(im, s["text"], s.get("y", 1080), s.get("hl"), TERRA if s["type"] != "ai" else INK)
    d = ImageDraw.Draw(im, "RGBA")
    if idx == 0 and total > 1:
        f = font(28, "SemiBold")
        tag = "Desliza  →"
        tw = d.textlength(tag, font=f)
        d.rounded_rectangle((W - 60 - tw - 40, H - 100, W - 60, H - 40), 30, fill=CREAM)
        d.text((W - 60 - tw - 20, H - 88), tag, font=f, fill=INK)
    return im


def caption_45(im, text, yc, hl, box):
    global VW
    old, VW = VW, W
    caption(im, text, 999, yc, size=64, hl=hl, box=box)
    VW = old


def main():
    only = sys.argv[4:] or None
    for key, r in SPEC.get("reels", {}).items():
        if not only or key in only:
            reel(key, r)
    for key, c in SPEC.get("carruseles", {}).items():
        if only and key not in only:
            continue
        (BASE / "carruseles").mkdir(exist_ok=True)
        for i, s in enumerate(c["slides"]):
            slide(s, i, len(c["slides"])).save(BASE / "carruseles" / f"{key}-{i + 1:02d}.jpg", quality=90)
        print("carrusel", key)


main()
