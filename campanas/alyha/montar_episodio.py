"""Montador genérico de episodios de Alyha a partir de un JSON de escenas (sin coste, sin voz, sin metadatos).

Uso: python3 montar_episodio.py <spec.json> <dir_entrada> <dir_salida> <fuente_DMSans.ttf>
Tipos de escena: still, video, reveal (tapado -> destapado), product (foto de ficha sobre fondo).
"""
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SPEC, IN, OUT, FONT = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
OUT.mkdir(parents=True, exist_ok=True)
W, H, FPS = 1080, 1920, 30
INK, CREAM, TERRA = (30, 27, 46), (251, 248, 244), (185, 83, 46)


def font(size, weight="Bold"):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(weight)
    return f


def fill(img, zoom=1.0, fx=0.5, fy=0.5):
    sc = max(W / img.width, H / img.height) * zoom
    r = img.resize((int(img.width * sc) + 1, int(img.height * sc) + 1), Image.BILINEAR)
    x = min(max(int(fx * r.width - W / 2), 0), r.width - W)
    y = min(max(int(fy * r.height - H / 2), 0), r.height - H)
    return r.crop((x, y, x + W, y + H))


def caption(im, lines, t, y, box, accent):
    k = min(t / 0.25, 1.0)
    fnt = font(int(76 * (0.85 + 0.15 * k + 0.04 * math.sin(k * math.pi))))
    d = ImageDraw.Draw(im, "RGBA")
    lh = int(fnt.size * 1.3)
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=fnt)
        x, yy = (W - tw) / 2, y + i * lh
        d.rounded_rectangle((x - 26, yy - 8, x + tw + 26, yy + lh - 12), 22, fill=box + (int(235 * k),))
        cx = x
        for word in line.split(" "):
            hit = word.strip("…,.¡!¿?«»").upper() in accent
            col = (INK if box == TERRA else TERRA) if hit else CREAM
            d.text((cx, yy), word, font=fnt, fill=col + (int(255 * k),))
            cx += d.textlength(word + " ", font=fnt)


def video_frames(path, start, dur, speed):
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


def frames_for(s):
    kind, dur = s["type"], s.get("dur", 3.5)
    n = int(dur * FPS)
    if kind == "video":
        return list(video_frames(IN / s["src"], s.get("start", 0), s.get("len", dur), s.get("speed", 1.0)))
    if kind == "still":
        img = Image.open(IN / s["src"]).convert("RGB")
        z0, z1 = s.get("zoom", [1.0, 1.1])
        return [fill(img, z0 + (z1 - z0) * i / n, *s.get("focus", [0.5, 0.5])) for i in range(n)]
    if kind == "reveal":
        a = Image.open(IN / s["cover"]).convert("RGB")
        b_img = Image.open(IN / s["src"]).convert("RGB")
        a_f = fill(a, 1.04)
        out = []
        for i in range(n):
            t = i / FPS
            b = fill(b_img, 1.0 + 0.06 * i / n)
            k = min(max((t - s.get("hold", 1.0)) / 0.5, 0.0), 1.0)
            k = k * k * (3 - 2 * k)
            if k <= 0:
                fr = a_f
            elif k < 1:
                off = int(H * k)
                fr = b.copy()
                fr.paste(a_f.crop((0, off, W, H)), (0, 0))
                ImageDraw.Draw(fr).rectangle((0, H - off - 6, W, H - off), fill=(255, 255, 255))
            else:
                fr = b
            out.append(fr)
        return out
    if kind == "product":
        img = Image.open(IN / s["src"]).convert("RGB")
        out = []
        for i in range(n):
            t = i / FPS
            side = int(1080 * (1.12 - 0.12 * min(t / 0.35, 1.0)) * (1 + 0.04 * t / dur))
            fr = Image.new("RGB", (W, H), (246, 246, 246))
            fr.paste(img.resize((side, side), Image.BILINEAR), ((W - side) // 2, 520 + (1080 - side) // 2))
            out.append(fr)
        return out
    raise ValueError(kind)


def main():
    name = SPEC["name"]
    final = writer(OUT / f"{name}-final.mp4")
    for idx, s in enumerate(SPEC["scenes"], 1):
        out = writer(OUT / f"{name}-escena{idx}.mp4")
        box = TERRA if s.get("box") == "terra" else INK
        frames = frames_for(s)
        for i, fr in enumerate(frames):
            fr = fr.copy()
            t = i / FPS
            if s.get("text_after"):
                t -= s["text_after"]
            if t >= 0 and s.get("text"):
                caption(fr, s["text"], t, s.get("y", 330), box, set(s.get("accent", [])))
            if s.get("note"):
                ImageDraw.Draw(fr).text((70, 1690), s["note"], font=font(30, "Regular"),
                                        fill=CREAM, stroke_width=2, stroke_fill=INK)
            b = fr.tobytes()
            out.stdin.write(b)
            final.stdin.write(b)
        out.stdin.close()
        out.wait()
        print(name, idx, round(len(frames) / FPS, 1), "s")
    final.stdin.close()
    final.wait()


main()
