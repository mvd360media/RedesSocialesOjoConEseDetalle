"""Piezas del 1 al 8 de noviembre: Reels (mp4 9:16), historias (9:16), posts y carruseles (4:5).

Uso: python3 render_semana.py <carpeta_fotos_tienda> <carpeta_fuentes>
Fotos de las fichas de https://ojoconesedetalle.es sin alterar (solo recorte/escala).
Datos comprobados en la web el 29/10/2026.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

IMG_DIR = Path(sys.argv[1])
FONT_DIR = Path(sys.argv[2])
BASE = Path(__file__).parent
SPEC = json.loads((BASE / "piezas.json").read_text())

INK = (30, 27, 46)
CREAM = (251, 248, 244)
TERRA = (185, 83, 46)
GREEN = (31, 94, 74)
MUTED = (110, 104, 120)
FPS = 30
FADE = 0.3


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
    return ImageOps.fit(im, size, Image.LANCZOS)


def rounded(im, radius):
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *im.size), radius, fill=255)
    return mask


def brand(draw, x, y, color):
    draw.text((x, y), "OJO CON ESE DETALLE", font=font(28, "SemiBold"), fill=color)


# ---------- Vertical 9:16 (Reels e historias) ----------
VW, VH = 1080, 1920
TOP = 250       # zona tapada por la interfaz arriba
PHOTO = 960


def v_text(d, s, y=TOP + 40):
    y = text_block(d, (60, y), s["title"], font(76), INK, VW - 120, 1.1)
    if s.get("sub"):
        y = text_block(d, (60, y + 10), s["sub"], font(40, "Regular"), MUTED, VW - 120, 1.2)
    return y


def v_photo_frame(s, zoom=1.0, img_cache={}):
    key = s["img"]
    if key not in img_cache:
        img_cache[key] = photo(key, (int(PHOTO * 1.1), int(PHOTO * 1.1)))
    src = img_cache[key]
    side = int(src.width / zoom)
    off = (src.width - side) // 2
    ph = src.crop((off, off, off + side, off + side)).resize((PHOTO, PHOTO), Image.BILINEAR)
    frame = Image.new("RGB", (VW, VH), CREAM)
    d = ImageDraw.Draw(frame)
    brand(d, 60, TOP - 40, TERRA)
    y = v_text(d, s)
    py = max(y + 40, 700)
    frame.paste(ph, ((VW - PHOTO) // 2, py), rounded(ph, 40))
    return frame


def v_cta(s):
    calm = s.get("calm", False)
    bg, fg = (CREAM, INK) if calm else (TERRA, CREAM)
    im = Image.new("RGB", (VW, VH), bg)
    d = ImageDraw.Draw(im)
    brand(d, 60, TOP - 40, GREEN if calm else CREAM)
    y = text_block(d, (60, TOP + 40), s["title"], font(80), fg, VW - 120, 1.1) + 30
    if s.get("price"):
        d.text((60, y), s["price"], font=font(150), fill=fg)
        y += 210
    for line in s.get("lines", []):
        d.line((60, y + 26, 88, y + 26), fill=fg, width=5)
        y = text_block(d, (112, y), line, font(46, "Medium"), fg, VW - 180, 1.2) + 28
    btn = s.get("button", "Enlace en la bio")
    f = font(46)
    tw = d.textlength(btn, font=f)
    by = max(y + 40, 1260)
    d.rounded_rectangle((60, by, 60 + tw + 90, by + 104), 52, fill=fg)
    d.text((105, by + 24), btn, font=f, fill=bg)
    d.text((60, by + 140), "ojoconesedetalle.es", font=font(36, "SemiBold"), fill=fg)
    if s.get("note"):
        text_block(d, (60, by + 210), s["note"], font(28, "Regular"), fg, VW - 120)
    return im


def v_list(s):
    im = Image.new("RGB", (VW, VH), CREAM)
    d = ImageDraw.Draw(im)
    brand(d, 60, TOP - 40, TERRA)
    y = text_block(d, (60, TOP + 40), s["title"], font(76), INK, VW - 120, 1.1) + 50
    for i, item in enumerate(s["items"], 1):
        d.ellipse((60, y, 124, y + 64), fill=GREEN)
        n = str(i)
        fn = font(34)
        d.text((92 - d.textlength(n, font=fn) / 2, y + 11), n, font=fn, fill=CREAM)
        y = text_block(d, (156, y + 4), item, font(48, "Medium"), INK, VW - 216, 1.2) + 40
    if s.get("note"):
        text_block(d, (60, y + 20), s["note"], font(36, "Regular"), MUTED, VW - 120, 1.25)
    return im


def v_table(s):
    im = Image.new("RGB", (VW, VH), CREAM)
    d = ImageDraw.Draw(im)
    brand(d, 60, TOP - 40, TERRA)
    y = text_block(d, (60, TOP + 40), s["title"], font(76), INK, VW - 120, 1.1) + 40
    y = table(d, s, y, VW, 40, 36)
    text_block(d, (60, y + 30), s["note"], font(30, "Regular"), MUTED, VW - 120, 1.25)
    return im


def table(d, s, y, w, fs_name, fs_date):
    cols = (60, w - 360, w - 180)
    d.text((cols[1], y), "Navidad", font=font(30, "SemiBold"), fill=MUTED)
    d.text((cols[2], y), "Reyes", font=font(30, "SemiBold"), fill=MUTED)
    y += 56
    for name, nav, rey in s["rows"]:
        d.line((60, y - 14, w - 60, y - 14), fill=(225, 218, 210), width=2)
        ny = text_block(d, (cols[0], y), name, font(fs_name, "Medium"), INK, cols[1] - 90, 1.15)
        d.text((cols[1], y), nav, font=font(fs_date), fill=TERRA)
        d.text((cols[2], y), rey, font=font(fs_date), fill=GREEN)
        y = max(ny, y + fs_date + 10) + 30
    return y


def story(s):
    kind = s["type"]
    if kind == "photo":
        return v_photo_frame(s)
    if kind == "list":
        return v_list(s)
    if kind == "table":
        return v_table(s)
    return v_cta(s)


def reel(key, r, out):
    scenes = []
    for s in r["scenes"]:
        n = int(s["dur"] * FPS)
        if s["type"] == "photo":
            frames = [v_photo_frame(s, 1.0 + 0.08 * i / n) for i in range(n)]
        else:
            still = v_cta(s) if s["type"] == "cta" else v_list(s)
            frames = [still] * n
        scenes.append(frames)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-crf", "20", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "128k",
           "-map_metadata", "-1", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(FADE * FPS)
    for si, frames in enumerate(scenes):
        for i, fr in enumerate(frames):
            if si > 0 and i < nf:
                fr = Image.blend(scenes[si - 1][-1], fr, (i + 1) / nf)
            p.stdin.write(fr.tobytes())
    p.stdin.close()
    p.wait()
    # portada = primer fotograma con texto completo
    scenes[0][0].save(out.with_suffix(".jpg"), quality=90)


# ---------- 4:5 (posts y carruseles) ----------
W, H = 1080, 1350


def dots(d, idx, total, color):
    if total < 2:
        return
    x = W - 60 - total * 22
    for i in range(total):
        cx, r = x + i * 22, 6
        box = (cx - r, H - 46 - r, cx + r, H - 46 + r)
        d.ellipse(box, fill=color) if i == idx else d.ellipse(box, outline=color, width=2)


def p_photo(s, idx, total):
    im = Image.new("RGB", (W, H), CREAM)
    im.paste(photo(s["img"], (1000, 1000)), (40, H - 1000))
    d = ImageDraw.Draw(im)
    brand(d, 60, 38, TERRA)
    y = text_block(d, (60, 82), s["title"], font(66), INK, W - 120, 1.1)
    if s.get("sub"):
        text_block(d, (60, y + 6), s["sub"], font(38, "Regular"), MUTED, W - 120, 1.2)
    if idx == 0 and total > 1:
        tag, f = "Desliza  →", font(28, "SemiBold")
        tw = d.textlength(tag, font=f)
        d.rounded_rectangle((W - 60 - tw - 40, H - 100, W - 60, H - 40), 30, fill=CREAM)
        d.text((W - 60 - tw - 20, H - 88), tag, font=f, fill=INK)
    else:
        dots(d, idx, total, CREAM)
    return im


def p_table(s, idx, total):
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    brand(d, 60, 38, TERRA)
    y = text_block(d, (60, 90), s["title"], font(66), INK, W - 120, 1.1) + 30
    y = table(d, s, y, W, 36, 34)
    text_block(d, (60, y + 10), s["note"], font(28, "Regular"), MUTED, W - 120, 1.25)
    return im


def p_steps(s, idx, total):
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    brand(d, 60, 38, TERRA)
    y = text_block(d, (60, 90), s["title"], font(66), INK, W - 120, 1.1) + 40
    for i, item in enumerate(s["items"], 1):
        d.ellipse((60, y, 124, y + 64), fill=GREEN)
        n, fn = str(i), font(34)
        d.text((92 - d.textlength(n, font=fn) / 2, y + 11), n, font=fn, fill=CREAM)
        y = text_block(d, (156, y + 4), item, font(44, "Medium"), INK, W - 216, 1.2) + 36
    if s.get("img"):
        side = min(H - y - 130, 600)
        if side > 220:
            ph = photo(s["img"], (side, side))
            im.paste(ph, ((W - side) // 2, H - side - 110), rounded(ph, 36))
    if s.get("note"):
        text_block(d, (60, H - 96), s["note"], font(28, "Regular"), MUTED, W - 300)
    dots(d, idx, total, INK)
    return im


def p_trio(s, idx, total):
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    brand(d, 60, 38, TERRA)
    y = text_block(d, (60, 90), s["title"], font(66), INK, W - 120, 1.1) + 40
    side = 300
    for it in s["items"]:
        ph = photo(it["img"], (side, side))
        im.paste(ph, (60, y), rounded(ph, 28))
        ty = text_block(d, (400, y + 70), it["name"], font(48, "SemiBold"), INK, W - 460, 1.15)
        d.text((400, ty + 10), it["price"], font=font(56), fill=TERRA)
        y += side + 36
    return im


def p_cta(s, idx, total):
    im = Image.new("RGB", (W, H), TERRA)
    d = ImageDraw.Draw(im)
    brand(d, 60, 38, CREAM)
    y = text_block(d, (60, 110), s["title"], font(70), CREAM, W - 120, 1.1) + 30
    for line in s["lines"]:
        d.line((60, y + 24, 84, y + 24), fill=CREAM, width=4)
        y = text_block(d, (104, y), line, font(42, "Medium"), CREAM, W - 170, 1.2) + 22
    btn, f = "Enlace en la bio", font(40)
    tw = d.textlength(btn, font=f)
    by = H - 260
    d.rounded_rectangle((60, by, 60 + tw + 80, by + 92), 46, fill=CREAM)
    d.text((100, by + 20), btn, font=f, fill=TERRA)
    d.text((60, by + 120), "ojoconesedetalle.es", font=font(30, "SemiBold"), fill=CREAM)
    dots(d, idx, total, CREAM)
    return im


P_KINDS = {"photo": p_photo, "table": p_table, "steps": p_steps, "trio": p_trio, "cta": p_cta}


def main():
    only = sys.argv[3:] or None
    for sub in ("reels", "historias", "posts"):
        (BASE / sub).mkdir(exist_ok=True)
    for key, r in SPEC["reels"].items():
        if only and key not in only:
            continue
        reel(key, r, BASE / "reels" / f"{key}.mp4")
        print("reel", key)
    for key, s in SPEC["historias"].items():
        if only and key not in only:
            continue
        story(s).save(BASE / "historias" / f"{key}.jpg", quality=90)
        print("historia", key)
    for key, post in SPEC["posts"].items():
        if only and key not in only:
            continue
        slides = post["slides"]
        for i, s in enumerate(slides):
            P_KINDS[s["type"]](s, i, len(slides)).save(
                BASE / "posts" / f"{key}-{i + 1:02d}.jpg", quality=90)
        print("post", key, len(slides))


main()
