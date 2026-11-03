"""Monta el episodio 03 de Alyha (colgante con foto, 3 colores) sin coste.

Uso: python3 montar_ep02.py <dir_entrada> <dir_salida> <fuente_DMSans.ttf>
dir_entrada: cubierto.png, mano.png, tres.png, cuello.png, cara.jpg, cierre.mp4
Salida: escenas sueltas + E03-final.mp4. Sin voz, sin metadatos.
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


def reveal(dur):
    """Destape: la caja cerrada se desliza hacia arriba como un telón y aparece el colgante."""
    a = fill(Image.open(IN / "cubierto.png").convert("RGB"), 1.12, 0.3, 0.6)
    img = Image.open(IN / "mano.png").convert("RGB")
    n = int(dur * FPS)
    out = []
    for i in range(n):
        t = i / FPS
        b = fill(img, 1.0 + 0.06 * i / n)
        k = min(max((t - 0.15) / 0.55, 0.0), 1.0)
        k = k * k * (3 - 2 * k)
        if k < 1:
            off = int(H * k)
            fr = b.copy()
            fr.paste(a.crop((0, off, W, H)), (0, 0))
            if 0 < k:
                ImageDraw.Draw(fr).rectangle((0, H - off - 6, W, H - off), fill=(255, 255, 255))
            if t > 0.15 and k < 0.35:
                fr = Image.blend(fr, Image.new("RGB", (W, H), (255, 255, 255)), 0.25 * (1 - k / 0.35))
        else:
            fr = b
        out.append(fr)
    return out


def compare(dur):
    """Pantalla partida: Alyha real arriba, su retrato grabado abajo."""
    face = Image.open(IN / "cara.jpg").convert("RGB")
    pend = Image.open(IN / "mano.png").convert("RGB")
    pw, ph = pend.size
    pend = pend.crop((int(pw * 0.21), int(ph * 0.47), int(pw * 0.76), int(ph * 0.78)))
    n = int(dur * FPS)
    out = []
    for i in range(n):
        z = 1.0 + 0.05 * i / n
        top = fill_box(face, W, H // 2, z)
        bot = fill_box(pend, W, H // 2, z)
        fr = Image.new("RGB", (W, H))
        fr.paste(top, (0, 0))
        fr.paste(bot, (0, H // 2))
        ImageDraw.Draw(fr).rectangle((0, H // 2 - 4, W, H // 2 + 4), fill=CREAM)
        out.append(fr)
    return out


def fill_box(img, w, h, zoom):
    sc = max(w / img.width, h / img.height) * zoom
    r = img.resize((int(img.width * sc) + 1, int(img.height * sc) + 1), Image.BILINEAR)
    x, y = (r.width - w) // 2, (r.height - h) // 2
    return r.crop((x, y, x + w, y + h))


VARIANTES = {
    "fuerte": (["ESTO ES MUY FUERTE…", "Y VAS A QUERER UNO"], {"FUERTE…", "UNO"},
               ["34,90 €", "Para Navidad,", "antes del 24 nov*"]),
    "mami": (["QUE NO LO VEA", "NINGUNA MAMI PERRUNA…"], {"MAMI", "PERRUNA…"},
             ["34,90 €", "Para Navidad,", "antes del 24 nov*"]),
    "novio": (["IMAGINA QUE TU NOVIO", "TE REGALA ESTO…"], {"NOVIO"},
              ["Comenta «QUIERO»", "si lo necesitas", "34,90 € · antes del 24 nov*"]),
    "etiqueta": (["ETIQUETA A QUIEN TE", "TIENE QUE REGALAR ESTO"], {"ETIQUETA"},
                 ["34,90 €", "Para Navidad,", "antes del 24 nov*"]),
    "hijo": (["SI TU PERRO ES TU HIJO…", "ESTO ES PARA TI"], {"HIJO…"},
             ["34,90 €", "Para Navidad,", "antes del 24 nov*"]),
    "minovio": (["MI NOVIO NO SABE QUE", "VA A REGALARME ESTO"], {"NOVIO"},
                ["34,90 €", "Para Navidad,", "antes del 24 nov*"]),
}
HOOK, HOOK_ACCENT, CTA = VARIANTES[os.environ.get("VARIANTE", "fuerte")]

SCENES = [
    ("escena1", lambda: still("cubierto.png", 3.5, 1.0, 1.12, 0.3, 0.6),
     HOOK, HOOK_ACCENT, 330, INK),
    ("escena2", lambda: reveal(4.0), ["SU CARITA.", "GRABADA PARA SIEMPRE."], {"SIEMPRE."}, 330, INK),
    ("escena3", lambda: compare(3.5), ["¿SE PARECE O NO?"], {"NO?"}, H // 2 - 70, INK),
    ("escena4", lambda: still("tres.png", 3.5, 1.0, 1.10, 0.5, 0.45), ["Rosado, dorado o plateado"], {"ROSADO,", "DORADO", "PLATEADO"}, 300, INK),
    ("escena5", lambda: still("cuello.png", 3.5, 1.0, 1.15, 0.55, 0.55), ["Y contigo,", "a todas partes"], {"PARTES"}, 330, INK),
    ("escena6", lambda: list(video_frames(IN / "cierre.mp4", 0, 2.8, 0.65)),
     CTA, {"34,90", "«QUIERO»"}, 1250, TERRA),
]


def main():
    final = writer(OUT / f"E03-final-{os.environ.get('VARIANTE', 'fuerte')}.mp4")
    for name, make, lines, accent, y, box in SCENES:
        out = writer(OUT / f"E03-{name}.mp4")
        frames = make()
        for i, fr in enumerate(frames):
            fr = fr.copy()
            caption(fr, lines, i / FPS, y, box=box, accent=accent)
            if name == "escena6":
                ImageDraw.Draw(fr).text((70, 1660), "*Fecha recomendada, no garantiza la entrega.",
                                        font=font(30, "Regular"), fill=CREAM, stroke_width=2, stroke_fill=INK)
            b = fr.tobytes()
            out.stdin.write(b)
            final.stdin.write(b)
        out.stdin.close()
        out.wait()
        print(name, round(len(frames) / FPS, 1), "s")
    final.stdin.close()
    final.wait()


main()
