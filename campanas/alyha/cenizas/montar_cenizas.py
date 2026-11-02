"""Pieza serena del colgante para cenizas: fundidos lentos, grano suave, texto serif sin cajas. Sin voz ni música.

Uso: python3 montar_cenizas.py <dir_entrada> <dir_salida> <Fraunces.ttf> <DMSans.ttf> <variante: fuerte|suave>
dir_entrada: cama.png, foto.png, manos.png, kit.webp, caja.webp, ventana.png
"""
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

IN, OUT, SERIF, SANS, VAR = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
OUT.mkdir(parents=True, exist_ok=True)
W, H, FPS, FADE = 1080, 1920, 30, 0.8
CREAM = (251, 248, 244)

PRIMERA, SEGUNDA = {
    "fuerte": ("Te va a doler…", "…pero vas a querer uno"),
    "suave": ("Te va a doler…", "…pero te acompañará siempre"),
    "sigue": ("Para quien sigue estando…", "…aunque ya no esté"),
    "huecos": ("Hay huecos que", "nadie más puede llenar…"),
}[VAR]
SCENES = [
    ("cama.png", "foto", 4.5, [PRIMERA]),
    ("foto.png", "foto", 4.5, [SEGUNDA]),
    ("manos.png", "foto", 4.5, ["Su carita y su nombre,", "en un corazón"]),
    ("kit.webp", "producto", 4.0, ["Dentro, un pequeño hueco", "para guardar un poco de él"]),
    ("caja.webp", "producto", 4.0, ["Para llevarle", "siempre cerca"]),
    ("ventana.png", "foto", 5.0, ["Colgante para cenizas", "ojoconesedetalle.es"]),
]


def serif(size, italic=False):
    f = ImageFont.truetype(SERIF, size)
    try:
        f.set_variation_by_axes([72, 350 if italic else 420, 100, 1 if italic else 0])
    except Exception:
        pass
    return f


def fill(img, zoom):
    sc = max(W / img.width, H / img.height) * zoom
    r = img.resize((int(img.width * sc) + 1, int(img.height * sc) + 1), Image.BILINEAR)
    x, y = (r.width - W) // 2, (r.height - H) // 2
    return r.crop((x, y, x + W, y + H))


def grade(im):
    im = ImageEnhance.Color(im).enhance(0.82)
    warm = Image.new("RGB", im.size, (255, 232, 205))
    return Image.blend(im, warm, 0.08)


_vig = None


def vignette(im):
    global _vig
    if _vig is None:
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).ellipse((-260, -180, W + 260, H + 180), fill=255)
        _vig = m.filter(ImageFilter.GaussianBlur(220))
    return Image.composite(im, Image.new("RGB", (W, H), (12, 10, 14)), _vig)


_noise = [Image.effect_noise((W // 3, H // 3), 22).resize((W, H)).convert("RGB") for _ in range(6)]


def grain(im, i):
    return Image.blend(im, _noise[i % 6], 0.05)


def product_frame(img, k):
    bg = fill(img, 1.0).filter(ImageFilter.GaussianBlur(45))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (25, 22, 26)), 0.45)
    side = int(860 * (1.0 + 0.04 * k))
    ph = img.resize((side, side), Image.BILINEAR)
    m = Image.new("L", ph.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, side, side), 30, fill=255)
    bg.paste(ph, ((W - side) // 2, 430 + (860 - side) // 2), m)
    return bg


def text(im, lines, a, last):
    d = ImageDraw.Draw(im, "RGBA")
    y = 1380 if not last else 1300
    for i, line in enumerate(lines):
        f = serif(78 if not (last and i == 1) else 44, italic=(i == 0 and not last))
        if last and i == 1:
            f = ImageFont.truetype(SANS, 40)
        tw = d.textlength(line, font=f)
        x = (W - tw) / 2
        for dx, dy in ((0, 3), (2, 2)):
            d.text((x + dx, y + dy), line, font=f, fill=(0, 0, 0, int(110 * a)))
        d.text((x, y), line, font=f, fill=CREAM + (int(255 * a),))
        y += int(f.size * 1.35)


def render_scene(src, kind, dur):
    img = Image.open(IN / src).convert("RGB")
    n = int(dur * FPS)
    out = []
    for i in range(n):
        k = i / n
        fr = product_frame(img, k) if kind == "producto" else fill(img, 1.0 + 0.06 * k)
        out.append(vignette(grade(fr)))
    return out


def main():
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                          "-movflags", "+faststart", "-map_metadata", "-1", "-fflags", "+bitexact",
                          str(OUT / f"cenizas-{VAR}.mp4")], stdin=subprocess.PIPE)
    nf = int(FADE * FPS)
    prev_tail = None
    count = 0
    for si, (src, kind, dur, lines) in enumerate(SCENES):
        frames = render_scene(src, kind, dur)
        last = si == len(SCENES) - 1
        for i, fr in enumerate(frames):
            if prev_tail is not None and i < nf:
                fr = Image.blend(prev_tail, fr, (i + 1) / nf)
            t = i / FPS
            a = min(max((t - 0.5) / 0.7, 0), 1) * (1 if last else min(1, (dur - t) / 0.5))
            fr = fr.copy()
            if a > 0:
                text(fr, lines, a, last)
            if last and i > len(frames) - nf:
                fr = Image.blend(fr, Image.new("RGB", (W, H), (0, 0, 0)), (i - (len(frames) - nf)) / nf)
            p.stdin.write(grain(fr, count).tobytes())
            count += 1
        prev_tail = frames[-1]
    p.stdin.close()
    p.wait()
    print(VAR, round(count / FPS, 1), "s")


main()
