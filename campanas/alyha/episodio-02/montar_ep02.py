"""Monta el episodio 02 de Alyha (collar con foto dentro) sin coste.

Uso: python3 montar_ep02.py <dir_entrada> <dir_salida> <fuente_DMSans.ttf>
dir_entrada: L1.png, L2.png, pov.jpg, linterna.jpg, producto.jpg, real_trote.mp4
Salida: escenas sueltas + E02-final.mp4 (con linterna) + E02-final-sin-linterna.mp4. Sin voz, sin metadatos.
"""
import math
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

IN, OUT, FONT = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
OUT.mkdir(parents=True, exist_ok=True)
W, H, FPS = 1080, 1920, 30
INK, CREAM, TERRA = (30, 27, 46), (251, 248, 244), (185, 83, 46)


if os.environ.get("NOTEXT"):
    ImageDraw.ImageDraw.text = lambda self, *a, **k: None


def font(size, weight="Bold"):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(weight)
    return f


def fill(img, zoom=1.0, fx=0.5, fy=0.5):
    """Recorte 9:16 con zoom hacia el punto (fx, fy) de la imagen."""
    sc = max(W / img.width, H / img.height) * zoom
    r = img.resize((int(img.width * sc) + 1, int(img.height * sc) + 1), Image.BILINEAR)
    x = min(max(int(fx * r.width - W / 2), 0), r.width - W)
    y = min(max(int(fy * r.height - H / 2), 0), r.height - H)
    return r.crop((x, y, x + W, y + H))


def caption(im, lines, t, y, size=76, box=INK, accent=()):
    if os.environ.get("NOTEXT"):
        return
    k = min(t / 0.25, 1.0)
    fnt = font(int(size * (0.85 + 0.15 * k + 0.04 * math.sin(k * math.pi))))
    d = ImageDraw.Draw(im, "RGBA")
    lh = int(fnt.size * 1.3)
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=fnt)
        x, yy = (W - tw) / 2, y + i * lh
        d.rounded_rectangle((x - 26, yy - 8, x + tw + 26, yy + lh - 12), 22, fill=box + (int(235 * k),))
        cx = x
        for word in line.split(" "):
            hit = word.strip("…,.¡!¿?").upper() in accent
            col = (INK if box == TERRA else TERRA) if hit else CREAM
            d.text((cx, yy), word, font=fnt, fill=col + (int(255 * k),))
            cx += d.textlength(word + " ", font=fnt)


def video_frames(path, start, dur, speed=1.0):
    vf = f"setpts={1 / speed}*PTS,fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(start), "-t", str(dur), "-i", str(path),
                          "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    while (b := p.stdout.read(W * H * 3)) and len(b) == W * H * 3:
        yield Image.frombytes("RGB", (W, H), b)


def writer(path):
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "19",
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-map_metadata", "-1",
                             "-fflags", "+bitexact", str(path)], stdin=subprocess.PIPE)


def still(src, dur, z0, z1, fx=0.5, fy=0.5):
    img = Image.open(IN / src).convert("RGB")
    n = int(dur * FPS)
    return [fill(img, z0 + (z1 - z0) * i / n, fx, fy) for i in range(n)]


def pov(dur):
    img = Image.open(IN / "pov.jpg").convert("RGB")
    n = int(dur * FPS)
    out = []
    for i in range(n):
        t = i / FPS
        fr = fill(img, 1.0 + 0.05 * i / n)
        blur = max(0.0, 18 * (1 - t / 1.0))
        out.append(fr.filter(ImageFilter.GaussianBlur(blur)) if blur > 0.3 else fr)
    return out


def product(dur):
    img = Image.open(IN / "producto.jpg").convert("RGB")
    bg = Image.new("RGB", (W, H), (246, 246, 246))
    n = int(dur * FPS)
    out = []
    for i in range(n):
        t = i / FPS
        side = int(1080 * (1.12 - 0.12 * min(t / 0.35, 1.0)) * (1 + 0.04 * t / dur))
        fr = bg.copy()
        ph = img.resize((side, side), Image.BILINEAR)
        fr.paste(ph, ((W - side) // 2, 520 + (1080 - side) // 2))
        out.append(fr)
    return out


SCENES = [
    ("escena1", lambda: still("L1.png", 3.5, 1.0, 1.45, 0.27, 0.52),
     ["NADIE SABE LO QUE", "LLEVA DENTRO…"], {"DENTRO…"}, 1350, INK),
    ("escena2", lambda: still("L2.png", 3.5, 1.0, 1.10, 0.45, 0.55),
     ["Acércalo al ojo…"], {"OJO…"}, 330, INK),
    ("escena3", lambda: pov(3.5), ["¡PERO SI SOY YO!"], {"YO!"}, 1500, INK),
    ("escena4", lambda: still("linterna.jpg", 3.5, 1.0, 1.12, 0.6, 0.3),
     ["Y CON LA LINTERNA…", "¡EN LA PARED!"], {"PARED!"}, 1250, INK),
    ("escena5", lambda: list(video_frames(IN / "real_trote.mp4", 0, 6, 1.0))[: int(5 * FPS)],
     ["ME LLEVA EN EL CORAZÓN.", "LITERAL."], {"LITERAL."}, 330, INK),
    ("escena6", lambda: product(4.0), ["Tu foto, escondida dentro", "21 modelos"], {"DENTRO"}, 300, TERRA),
    ("escena7", lambda: list(video_frames(IN / "real_trote.mp4", 12, 3.5, 0.85)),
     ["34,90 €", "Para Navidad,", "antes del 24 nov*"], {"34,90"}, 1300, TERRA),
]


def main():
    con = writer(OUT / "E02-final.mp4")
    sin = writer(OUT / "E02-final-sin-linterna.mp4")
    for name, make, lines, accent, y, box in SCENES:
        out = writer(OUT / f"E02-{name}.mp4")
        frames = make()
        for i, fr in enumerate(frames):
            fr = fr.copy()
            caption(fr, lines, i / FPS, y, box=box, accent=accent)
            if name == "escena7":
                ImageDraw.Draw(fr).text((70, 1690), "*Fecha recomendada, no garantiza la entrega.",
                                        font=font(30, "Regular"), fill=CREAM, stroke_width=2, stroke_fill=INK)
            b = fr.tobytes()
            out.stdin.write(b)
            con.stdin.write(b)
            if name != "escena4":
                sin.stdin.write(b)
        out.stdin.close()
        out.wait()
        print(name, round(len(frames) / FPS, 1), "s")
    for p in (con, sin):
        p.stdin.close()
        p.wait()


main()
