"""Monta el episodio 01 de Alyha sin coste: vídeo real + clip Higgsfield + fotogramas IA animados.

Uso: python3 montar_ep01.py <dir_entrada> <dir_salida> <fuente_DMSans.ttf> <foto_producto>
dir_entrada: escena1.mp4, escena3.mp4, escena6.mp4, F2-rincon.png, F4-arbol.png
Salida: una pieza por escena + E01-final.mp4 (sin voz, sin metadatos).
"""
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

IN, OUT, FONT, PRODUCT = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
OUT.mkdir(parents=True, exist_ok=True)
W, H, FPS = 1080, 1920, 30
INK, CREAM, TERRA = (30, 27, 46), (251, 248, 244), (185, 83, 46)


def font(size, weight="Bold"):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(weight)
    return f


def fill(img, zoom=1.0, dx=0.0):
    sc = max(W / img.width, H / img.height) * zoom
    r = img.resize((int(img.width * sc) + 1, int(img.height * sc) + 1), Image.BILINEAR)
    x = (r.width - W) // 2 + int(dx * (r.width - W) / 2)
    y = (r.height - H) // 2
    return r.crop((x, y, x + W, y + H))


def caption(im, lines, t, y=360, size=74, box=INK, accent=()):
    """Bloque de texto con cajas por línea; entra con un pequeño rebote."""
    k = min(t / 0.25, 1.0)
    scale = 0.85 + 0.15 * k + 0.04 * math.sin(k * math.pi)
    fnt = font(int(size * scale))
    d = ImageDraw.Draw(im, "RGBA")
    lh = int(fnt.size * 1.3)
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=fnt)
        x = (W - tw) / 2
        yy = y + i * lh
        d.rounded_rectangle((x - 26, yy - 8, x + tw + 26, yy + lh - 12), 22, fill=box + (int(235 * k),))
        cx = x
        for word in line.split(" "):
            col = (TERRA if box != TERRA else INK) if word.strip("…,.¡!¿?").upper() in accent else CREAM
            d.text((cx, yy), word, font=fnt, fill=col + (int(255 * k),))
            cx += d.textlength(word + " ", font=fnt)


def sparkles(im, pts, t):
    d = ImageDraw.Draw(im, "RGBA")
    for (x, y, ph, sp) in pts:
        a = max(0.0, math.sin(t * sp + ph))
        r = 3 + 9 * a
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 236, 190, int(150 * a)))
        d.line((x - 2.2 * r, y, x + 2.2 * r, y), fill=(255, 245, 220, int(170 * a)), width=2)
        d.line((x, y - 2.2 * r, x, y + 2.2 * r), fill=(255, 245, 220, int(170 * a)), width=2)


def bright_points(img, n=26, seed=3):
    g = fill(img).convert("L").filter(ImageFilter.GaussianBlur(2))
    px = g.load()
    cand = [(x, y) for x in range(20, W - 20, 6) for y in range(200, H - 300, 6) if px[x, y] > 225]
    random.seed(seed)
    pick = random.sample(cand, min(n, len(cand))) if cand else []
    return [(x, y, random.uniform(0, 6.28), random.uniform(2.5, 5)) for x, y in pick]


def writer(path):
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "19",
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-map_metadata", "-1",
                             "-fflags", "+bitexact", str(path)], stdin=subprocess.PIPE)


def video_frames(path, speed=1.0):
    vf = f"setpts={1 / speed}*PTS,fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", str(path), "-vf", vf, "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        yield Image.frombytes("RGB", (W, H), b)


def product_frame(img, t):
    bg = fill(img).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), INK), 0.4)
    pop = 1.18 - 0.18 * min(t / 0.35, 1.0)
    side = int(920 * pop * (1 + 0.04 * t / 4))
    ph = ImageOps.fit(img, (side, side), Image.BILINEAR)
    m = Image.new("L", ph.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, side, side), 46, fill=255)
    bg.paste(ph, ((W - side) // 2, 640 + (920 - side) // 2), m)
    return bg


SCENES = [
    ("escena1", "video", "escena1.mp4", 1.0, ["YO YA VOY DE RENO…", "Y EN ESTA CASA", "NI ÁRBOL"], {"RENO…", "ÁRBOL"}),
    ("escena2", "still", "F2-rincon.png", 4.5, ["«Ya lo pondré», dice.", "Ya, ya…"], {"YA,", "YA…"}),
    ("escena3", "video", "escena3.mp4", 1.0, ["Pues me pongo", "las pilas yo solita"], {"PILAS"}),
    ("escena4", "tree", "F4-arbol.png", 4.5, ["Pero aquí", "falta algo…"], {"ALGO…"}),
    ("escena5", "product", PRODUCT, 4.0, ["Su nombre,", "en el árbol"], {"ÁRBOL"}),
    ("escena6", "video", "escena6.mp4", 0.8, ["24,90 €", "Pídelo antes del 29 nov*"], {"24,90"}),
]


def main():
    final = writer(OUT / "E01-final.mp4")
    for name, kind, src, arg, lines, accent in SCENES:
        out = writer(OUT / f"E01-{name}.mp4")
        frames = []
        if kind == "video":
            frames = list(video_frames(IN / src, speed=arg))
        else:
            img = Image.open(src if kind == "product" else IN / src).convert("RGB")
            n = int(arg * FPS)
            pts = bright_points(img) if kind == "tree" else []
            for i in range(n):
                t = i / FPS
                if kind == "product":
                    fr = product_frame(img, t)
                else:
                    fr = fill(img, 1.0 + 0.10 * i / n, dx=0.15 * (i / n - 0.5))
                    if pts:
                        sparkles(fr, pts, t)
                frames.append(fr)
        for i, fr in enumerate(frames):
            fr = fr.copy()
            t = i / FPS
            box = TERRA if name in ("escena5", "escena6") else INK
            if name == "escena6":
                caption(fr, lines, t, y=1180, size=80, box=box, accent=accent)
                d = ImageDraw.Draw(fr)
                d.text((70, 1460), "*Fecha recomendada para Navidad, no garantiza la entrega.",
                       font=font(28, "Regular"), fill=CREAM, stroke_width=2, stroke_fill=INK)
            else:
                caption(fr, lines, t, y={"escena1": 1200, "escena5": 360}.get(name, 330), box=box, accent=accent)
            b = fr.tobytes()
            out.stdin.write(b)
            final.stdin.write(b)
        out.stdin.close()
        out.wait()
        print(name, round(len(frames) / FPS, 1), "s")
    final.stdin.close()
    final.wait()


main()
