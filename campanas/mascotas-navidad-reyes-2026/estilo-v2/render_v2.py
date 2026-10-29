"""Estilo v2: historias con escenas generadas con IA + producto real + voz en off.

Uso: python3 render_v2.py <fotos_tienda> <escenas_ia> <fuentes> <carpeta_tts> [claves...]
Variables: VOZ (por defecto coral). Necesita OPENAI_API_KEY para generar la voz.
Las escenas IA nunca muestran el producto: el producto es siempre la foto real de la ficha.
Todos los archivos se exportan sin metadatos.
"""
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

SHOP, AI, FONTS, TTS = (Path(a) for a in sys.argv[1:5])
BASE = Path(__file__).parent
SPEC = json.loads((BASE / "piezas_v2.json").read_text())
VOZ = os.environ.get("VOZ", "coral")

INK = (30, 27, 46)
CREAM = (251, 248, 244)
TERRA = (185, 83, 46)
GREEN = (31, 94, 74)
FPS = 30
RATE = 24000
VW, VH = 1080, 1920
W, H = 1080, 1350

INSTR = ("Habla como una mujer nacida en Madrid: español de España, acento peninsular suave y natural. "
         "Pronuncia la z y la c ante e/i como en España (corazón, cenizas, Navidad, hacer). "
         "Nada de seseo ni entonación latinoamericana. Tono cálido, cercano, tranquilo, como hablando "
         "con una amiga; nada publicitario.")


def font(size, weight="Bold"):
    f = ImageFont.truetype(str(FONTS / "DMSans.ttf"), size)
    f.set_variation_by_name(weight)
    return f


def src(name):
    p = AI / name if (AI / name).exists() else SHOP / name
    return Image.open(p).convert("RGB")


def save_jpg(im, path):
    im.convert("RGB").save(path, quality=90, exif=b"")


# ---------- voz ----------
def voice_pcm(text, calm=False):
    TTS.mkdir(exist_ok=True)
    key = f"{VOZ}-{'c' if calm else 'n'}-{hashlib.md5(text.encode()).hexdigest()[:12]}"
    wav, raw = TTS / f"{key}.wav", TTS / f"{key}.pcm"
    if not raw.exists():
        instr = INSTR + (" Muy pausado, sereno y respetuoso." if calm else "")
        body = json.dumps({"model": "gpt-4o-mini-tts", "voice": VOZ, "input": text,
                           "instructions": instr, "response_format": "wav"}).encode()
        req = urllib.request.Request("https://api.openai.com/v1/audio/speech", body,
                                     {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                                      "Content-Type": "application/json"})
        wav.write_bytes(urllib.request.urlopen(req, timeout=120).read())
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-f", "s16le", "-ac", "1",
                        "-ar", str(RATE), str(raw)], check=True)
    return raw.read_bytes()


# ---------- texto ----------
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


def caption(im, text, shown, y_center, size=78, hl=(), box=INK, fg=CREAM):
    """Subtítulo nativo: cajas por línea y palabras que aparecen una a una."""
    width = im.width
    d = ImageDraw.Draw(im, "RGBA")
    fnt = font(size)
    lines = wrap(d, text.split(), fnt, width - 200)
    lh = int(size * 1.32)
    y = y_center - len(lines) * lh // 2
    k = 0
    for line in lines:
        x = (width - d.textlength(" ".join(line), font=fnt)) / 2
        vis = []
        for wd in line:
            k += 1
            if k <= shown:
                vis.append(wd)
        if vis:
            vw = d.textlength(" ".join(vis), font=fnt)
            d.rounded_rectangle((x - 26, y - 8, x + vw + 26, y + lh - 14), 22, fill=box + (235,))
            cx = x
            for wd in vis:
                accent = wd.strip("…,.¿?¡!:").lower() in hl
                col = (CREAM if box == TERRA else TERRA) if accent else fg
                if accent and box == TERRA:
                    col = INK
                d.text((cx, y), wd, font=fnt, fill=col)
                cx += d.textlength(wd + " ", font=fnt)
        y += lh


def fill(img, size, zoom=1.0):
    w, h = img.size
    sc = max(size[0] / w, size[1] / h) * zoom
    r = img.resize((int(w * sc) + 1, int(h * sc) + 1), Image.BILINEAR)
    x, y = (r.width - size[0]) // 2, (r.height - size[1]) // 2
    return r.crop((x, y, x + size[0], y + size[1]))


def rounded_paste(base, ph, xy, radius=44, border=0):
    if border:
        b = Image.new("RGB", (ph.width + 2 * border, ph.height + 2 * border), CREAM)
        m = Image.new("L", b.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, *b.size), radius + border, fill=255)
        base.paste(b, (xy[0] - border, xy[1] - border), m)
    m = Image.new("L", ph.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, *ph.size), radius, fill=255)
    base.paste(ph, xy, m)


_blur = {}


def blurred_bg(img, size):
    k = (id(img), size)
    if k not in _blur:
        bg = fill(img, size).filter(ImageFilter.GaussianBlur(40))
        _blur[k] = Image.blend(bg, Image.new("RGB", size, INK), 0.4)
    return _blur[k].copy()


# ---------- Reels ----------
def product_frame(img, t, top=420):
    frame = blurred_bg(img, (VW, VH))
    pop = 1.18 - 0.18 * min(t / 0.35, 1.0)
    side = int(940 * pop * (1.0 + 0.05 * t / 3))
    ph = ImageOps.fit(img, (side, side), Image.BILINEAR)
    rounded_paste(frame, ph, ((VW - side) // 2, top + (940 - side) // 2), 46)
    return frame


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
            d.text((70, y + int(30 * (1 - a))), line, font=font(118), fill=fg)
        y += 140
    y += 40
    if t > 0.7:
        d.text((70, y), s["price"], font=font(170), fill=fg)
    y += 230
    if t > 1.0:
        for line in s["lines"]:
            d.ellipse((72, y + 20, 96, y + 44), fill=fg)
            d.text((120, y), line, font=font(48, "Medium"), fill=fg)
            y += 76
    if t > 1.3:
        btn, f = s.get("button", "Enlace en la bio"), font(54)
        tw = d.textlength(btn, font=f)
        d.rounded_rectangle((70, 1340, 70 + tw + 100, 1460), 60, fill=fg)
        d.text((120, 1366), btn, font=f, fill=bg)
        if s.get("note"):
            d.text((70, 1490), s["note"], font=font(30, "Regular"), fill=fg)
    return im


def reel(key, r):
    out = BASE / "reels" / f"{key}.mp4"
    out.parent.mkdir(exist_ok=True)
    calm = r.get("calm", False)
    audio = bytearray()
    plan = []
    for s in r["scenes"]:
        pcm = voice_pcm(s["vo"], calm) if s.get("vo") else b""
        vo_dur = len(pcm) / 2 / RATE
        dur = max(s.get("min", 1.6), vo_dur + (0.5 if calm else 0.3))
        audio += pcm + b"\x00\x00" * int((dur - vo_dur) * RATE)
        plan.append((s, dur, vo_dur))
    apath = TTS / f"{key}-{VOZ}.pcm"
    apath.write_bytes(bytes(audio))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
           "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", str(apath),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-shortest",
           "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cover = None
    for s, dur, vo_dur in plan:
        n = int(dur * FPS)
        img = src(s["img"]) if s.get("img") else None
        text = s.get("text", s.get("vo", ""))
        words = len(text.split())
        per_word = max(vo_dur, 0.8) / max(words, 1)
        for i in range(n):
            t = i / FPS
            if s["type"] == "ai":
                fr = fill(img, (VW, VH), 1.0 + 0.07 * i / n)
            elif s["type"] == "product":
                fr = product_frame(img, t)
                if i < 2:
                    fr = Image.blend(fr, Image.new("RGB", fr.size, CREAM), 0.7 - 0.35 * i)
            else:
                fr = cta_frame(s, t)
            shown = words
            if s["type"] != "cta" and text:
                shown = min(words, 1 + int(t / per_word))
                caption(fr, text, shown, s.get("y", 1250 if s["type"] == "ai" else 1500),
                        hl=s.get("hl", ()), box=TERRA if s["type"] == "product" else INK)
            if cover is None and shown == words and s["type"] != "cta":
                cover = fr.copy()
            p.stdin.write(fr.tobytes())
    p.stdin.close()
    p.wait()
    save_jpg(cover, out.with_suffix(".jpg"))
    print("reel", key, round(len(audio) / 2 / RATE, 1), "s")


# ---------- historias 9:16 ----------
def story(key, s):
    if s["type"] == "poster":
        im = poster((VW, VH), s, 300)
    else:
        im = fill(src(s["img"]), (VW, VH))
        if s.get("product"):
            side = 460
            ph = ImageOps.fit(src(s["product"]), (side, side), Image.LANCZOS)
            rounded_paste(im, ph, (80, 330), 36, border=12)
        caption(im, s["text"], 999, s.get("y", 1250), hl=s.get("hl", ()))
        if s.get("sub"):
            caption(im, s["sub"], 999, s.get("y", 1250) + 230, size=50, box=TERRA)
    out = BASE / "historias"
    out.mkdir(exist_ok=True)
    save_jpg(im, out / f"{key}.jpg")
    print("historia", key)


def poster(size, s, top):
    w, h = size
    im = Image.new("RGB", size, INK)
    d = ImageDraw.Draw(im)
    d.text((70, top - 70), "OJO CON ESE DETALLE", font=font(28, "SemiBold"), fill=TERRA)
    y = top
    for line in s["big"]:
        d.text((70, y), line, font=font(s.get("bigsize", 110)), fill=CREAM)
        y += int(s.get("bigsize", 110) * 1.08)
    y += 40
    d.text((70, y), "NAVIDAD", font=font(28, "SemiBold"), fill=TERRA)
    d.text((w - 250, y), "REYES", font=font(28, "SemiBold"), fill=(150, 190, 170))
    y += 56
    for name, nav, rey in s["rows"]:
        d.line((70, y - 16, w - 70, y - 16), fill=(70, 66, 90), width=2)
        d.text((70, y), nav, font=font(64), fill=TERRA)
        d.text((330, y + 12), name, font=font(40, "Medium"), fill=CREAM)
        d.text((w - 250, y + 12), rey, font=font(40), fill=(150, 190, 170))
        y += 104
    d.text((70, y + 10), s["note"], font=font(28, "Regular"), fill=(190, 186, 200))
    return im


# ---------- posts y carruseles 4:5 ----------
def slide(s, idx, total):
    kind = s["type"]
    if kind == "poster":
        im = poster((W, H), s, 170)
    elif kind == "ai":
        im = fill(src(s["img"]), (W, H))
        caption(im, s["text"], 999, s.get("y", 1060), size=64, hl=s.get("hl", ()))
    elif kind == "product":
        img = src(s["img"])
        im = blurred_bg(img, (W, H))
        side = 900
        rounded_paste(im, ImageOps.fit(img, (side, side), Image.LANCZOS), ((W - side) // 2, 110), 40)
        caption(im, s["text"], 999, s.get("y", 1170), size=58, hl=s.get("hl", ()), box=TERRA)
    elif kind == "trio":
        im = Image.new("RGB", (W, H), INK)
        d = ImageDraw.Draw(im)
        d.text((60, 50), "OJO CON ESE DETALLE", font=font(26, "SemiBold"), fill=TERRA)
        y = 100
        for line in s["big"]:
            d.text((60, y), line, font=font(76), fill=CREAM)
            y += 84
        y += 30
        for it in s["items"]:
            ph = ImageOps.fit(src(it["img"]), (300, 300), Image.LANCZOS)
            rounded_paste(im, ph, (60, y), 28)
            d.text((400, y + 70), it["name"], font=font(46, "SemiBold"), fill=CREAM)
            d.text((400, y + 140), it["price"], font=font(58), fill=TERRA)
            y += 330
    else:  # cta
        im = Image.new("RGB", (W, H), TERRA)
        d = ImageDraw.Draw(im)
        d.text((60, 50), "OJO CON ESE DETALLE", font=font(26, "SemiBold"), fill=CREAM)
        y = 140
        for line in s["big"]:
            d.text((60, y), line, font=font(92), fill=CREAM)
            y += 100
        y += 40
        for line in s["lines"]:
            d.ellipse((62, y + 18, 84, y + 40), fill=CREAM)
            d.text((104, y), line, font=font(44, "Medium"), fill=CREAM)
            y += 70
        btn, f = s.get("button", "Enlace en la bio"), font(44)
        tw = d.textlength(btn, font=f)
        d.rounded_rectangle((60, H - 250, 60 + tw + 90, H - 150), 50, fill=CREAM)
        d.text((105, H - 228), btn, font=f, fill=TERRA)
    if idx == 0 and total > 1:
        d = ImageDraw.Draw(im)
        f, tag = font(28, "SemiBold"), "Desliza  →"
        tw = d.textlength(tag, font=f)
        d.rounded_rectangle((W - 60 - tw - 40, H - 100, W - 60, H - 40), 30, fill=CREAM)
        d.text((W - 60 - tw - 20, H - 88), tag, font=f, fill=INK)
    return im


def main():
    only = sys.argv[5:] or None
    for key, r in SPEC.get("reels", {}).items():
        if not only or key in only:
            reel(key, r)
    for key, s in SPEC.get("historias", {}).items():
        if not only or key in only:
            story(key, s)
    for key, c in SPEC.get("posts", {}).items():
        if only and key not in only:
            continue
        (BASE / "posts").mkdir(exist_ok=True)
        for i, s in enumerate(c["slides"]):
            save_jpg(slide(s, i, len(c["slides"])), BASE / "posts" / f"{key}-{i + 1:02d}.jpg")
        print("post", key, len(c["slides"]))


main()
