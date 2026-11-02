"""Genera variantes de gancho: vuelve a montar solo la escena 1 y la concatena con el resto de escenas ya montadas.

Uso: python3 generar_ganchos.py <dir_base> <dir_escenas> <dir_salida> <DMSans.ttf>
dir_base: e1-base.mp4, e2-base.png, e4-base.mp4, e5-base.mp4
dir_escenas: E01/, E02/, E04/, E05/ con E0X-escenaN.mp4 ya montadas
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

BASE, ESC, OUT, FONT = (Path(a) for a in sys.argv[1:5])
TOOL = Path(__file__).resolve().parent.parent / "montar_episodio.py"
OUT.mkdir(parents=True, exist_ok=True)

EPISODIOS = {
    "E01": ({"type": "video", "src": "e1-base.mp4", "start": 0, "len": 6, "y": 1200}, 6, {
        "familia": (["SI TU PERRO TAMBIÉN", "ES DE LA FAMILIA…"], ["FAMILIA…"]),
        "nombre": (["ESTE AÑO EL ÁRBOL", "LLEVA SU NOMBRE"], ["NOMBRE"]),
        "etiqueta": (["ETIQUETA A QUIEN", "LE FALTA ESTO EN EL ÁRBOL"], ["ETIQUETA"]),
        "pov": (["POV: TU PERRA EXIGE", "SU SITIO EN EL ÁRBOL"], ["POV:"]),
    }),
    "E02": ({"type": "still", "src": "e2-base.png", "dur": 3.5, "zoom": [1.0, 1.45], "focus": [0.27, 0.52], "y": 1350}, 6, {
        "novio": (["IMAGINA QUE TU NOVIO", "TE REGALA ESTO…"], ["NOVIO"]),
        "escondido": (["LLEVA A SU PERRO", "ESCONDIDO EN EL COLLAR"], ["ESCONDIDO"]),
        "raro": (["¿VES ALGO RARO", "EN ESTE COLLAR?"], ["RARO"]),
        "mami": (["QUE NO LO VEA", "NINGUNA MAMI PERRUNA…"], ["MAMI", "PERRUNA…"]),
    }),
    "E04": ({"type": "video", "src": "e4-base.mp4", "start": 0, "len": 4, "y": 330}, 5, {
        "pov": (["POV: TU PERRO", "TE ACOMPAÑA A TODAS PARTES"], ["POV:"]),
        "parael": (["EL REGALO PERFECTO", "PARA ÉL (Y SU PERRO)"], ["PERFECTO"]),
        "copiloto": (["SI TU PERRO ES", "TU COPILOTO… ESTO ES PARA TI"], ["COPILOTO…"]),
        "etiqueta": (["ETIQUETA A ALGUIEN QUE", "LLEVA A SU PERRO A TODAS PARTES"], ["ETIQUETA"]),
    }),
    "E05": ({"type": "video", "src": "e5-base.mp4", "start": 0, "len": 3, "y": 330}, 7, {
        "tres": (["3 COSAS QUE HACE", "MI PERRA Y ME DERRITEN"], ["DERRITEN"]),
        "derrite": (["SI TU PERRO TE DERRITE…", "MIRA ESTO"], ["DERRITE…"]),
        "pov": (["POV: TU PERRA", "TE ROBA EL CORAZÓN"], ["POV:"]),
        "mami": (["ETIQUETA A UNA MAMI PERRUNA", "QUE NECESITA ESTO"], ["MAMI", "PERRUNA"]),
    }),
}


def main():
    for ep, (scene, n_scenes, variants) in EPISODIOS.items():
        for key, (lines, accent) in variants.items():
            s = dict(scene, text=lines, accent=accent)
            with tempfile.TemporaryDirectory() as tmp:
                spec = Path(tmp) / "spec.json"
                spec.write_text(json.dumps({"name": "H", "scenes": [s]}, ensure_ascii=False))
                subprocess.run(["python3", str(TOOL), str(spec), str(BASE), tmp, str(FONT)], check=True,
                               stdout=subprocess.DEVNULL)
                lst = Path(tmp) / "list.txt"
                parts = [Path(tmp) / "H-escena1.mp4"] + [ESC / ep / f"{ep}-escena{i}.mp4" for i in range(2, n_scenes + 1)]
                lst.write_text("".join(f"file '{p}'\n" for p in parts))
                out = OUT / f"{ep}-final-{key}.mp4"
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                                "-c", "copy", "-map_metadata", "-1", "-movflags", "+faststart", str(out)], check=True)
                print(out.name, flush=True)


main()
