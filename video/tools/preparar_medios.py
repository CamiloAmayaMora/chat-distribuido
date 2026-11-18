"""Prepara todos los medios del video y el script de DaVinci Resolve.

1. Corta el render de animaciones en un archivo por escena (render/escenas/).
2. Crea los "marcadores de posición" de las tomas a cámara (render/caras/):
   tarjetas que dicen quién habla y cuánto dura; se reemplazan por la toma real.
3. Escribe render/manifiesto.json con el orden y la duración de todo.
4. Genera resolve/Armar_video_chat_distribuido.lua (el script que arma la
   línea de tiempo dentro de Resolve) y lo copia a la carpeta de scripts de Resolve.

    python video/tools/preparar_medios.py
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
RENDER = VIDEO / "render"
FPS = 30
guion = json.loads((VIDEO / "guion_video.json").read_text(encoding="utf-8"))
escenas = {e["id"]: e for e in guion["escenas"]}

# inicio y duración de cada escena dentro de animaciones/index.html
ANIM = {"S01": (0, 16), "S03": (16, 41), "S05": (57, 22), "S06": (79, 33), "S07": (112, 19),
        "S09": (131, 32), "S10": (163, 20), "S13": (183, 31), "S14": (214, 26), "S15": (240, 25),
        "S17": (265, 9)}
# duración de las tomas a cámara: voz guía x 1.25 + 1.5 s de aire
TTS = {}
_raw = (VIDEO / "tts" / "duraciones.tsv").read_bytes()
_txt = _raw.decode("utf-16") if _raw[:2] in (bytes([255, 254]), bytes([254, 255])) else _raw.decode("utf-8-sig")
for line in _txt.splitlines():
    name, dur = line.split("\t")
    TTS[name] = float(dur.replace(",", "."))
CARAS = {sid: round(TTS[sid] * 1.25 + 1.5, 1) for sid in ("S02", "S04", "S08", "S12", "S16")}
ORDEN = ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10", "S11",
         "S12", "S13", "S14", "S15", "S16", "S17"]
ROTULOS = {"S02": "Camilo", "S04": "Johen", "S08": "Daniel", "S12": "Hector"}
FONT = "C\\:/Windows/Fonts/segoeui.ttf"
FONTB = "C\\:/Windows/Fonts/segoeuib.ttf"


def slug(s):
    rep = str.maketrans("áéíóúñÁÉÍÓÚÑ :", "aeiounAEIOUN__")
    return "".join(c for c in s.translate(rep) if c.isalnum() or c == "_")


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def main():
    (RENDER / "escenas").mkdir(parents=True, exist_ok=True)
    (RENDER / "caras").mkdir(parents=True, exist_ok=True)
    src = RENDER / "animaciones_completas.mp4"
    items = []
    for sid in ORDEN:
        e = escenas[sid]
        if e["tipo"] == "ANIM":
            start, length = ANIM[sid]
            out = RENDER / "escenas" / f"{sid}_{slug(e['titulo'])}.mp4"
            if not out.exists():
                ff("-ss", str(start), "-i", str(src), "-t", str(length), "-c:v", "libx264", "-crf", "15",
                   "-preset", "slow", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an", str(out))
        elif e["tipo"] == "CARA":
            length = CARAS[sid]
            out = RENDER / "caras" / f"{sid}_CARA_{slug(e['voz'])}.mp4"
            l1 = f"{sid} · TOMA A CÁMARA · {e['voz'].upper()}"
            l2 = f"Graba aquí tu toma ({length:.0f} s aprox.) y reemplaza este clip"
            l3 = e["titulo"]
            vf = (f"drawbox=x=0:y=0:w=iw:h=ih:color=0x0c1016:t=fill,"
                  f"drawbox=x=160:y=330:w=1600:h=420:color=0xf5b748@0.9:t=4,"
                  f"drawtext=fontfile='{FONTB}':text='{l1}':fontcolor=0xf5b748:fontsize=64:x=(w-tw)/2:y=400,"
                  f"drawtext=fontfile='{FONT}':text='{l3}':fontcolor=white:fontsize=56:x=(w-tw)/2:y=510,"
                  f"drawtext=fontfile='{FONT}':text='{l2}':fontcolor=0x8b97a8:fontsize=40:x=(w-tw)/2:y=620")
            ff("-f", "lavfi", "-i", f"color=c=black:s=1920x1080:r={FPS}:d={length}", "-vf", vf,
               "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(out))
        else:  # DEMO
            out = RENDER / "demo.mp4"
            length = dur(out)
        items.append({"id": sid, "tipo": e["tipo"], "titulo": e["titulo"], "voz": e["voz"],
                      "archivo": str(out), "segundos": round(length, 3)})

    # voces guía y marcadores
    eventos = json.loads((VIDEO / "demo" / "eventos.json").read_text(encoding="utf-8"))
    t = 0.0
    voces, marcas = [], []
    for it in items:
        it["inicio"] = round(t, 3)
        e = escenas[it["id"]]
        nota = e.get("texto") or " / ".join(l["texto"] for l in e.get("lineas", []))
        marcas.append({"seg": t, "nombre": f"{it['id']} {it['titulo']}", "nota": f"{it['tipo']} · {it['voz']}: {nota}"[:900]})
        if e.get("lineas"):
            for i, ln in enumerate(e["lineas"], 1):
                wav = VIDEO / "tts" / f"{it['id']}_{i:02d}_{ln['evento']}.wav"
                voces.append({"archivo": str(wav), "seg": round(t + eventos[ln["evento"]] + 0.3, 3)})
        elif e.get("texto"):
            voces.append({"archivo": str(VIDEO / "tts" / f"{it['id']}.wav"), "seg": round(t + 0.6, 3)})
        t += it["segundos"]
    rotulos = []
    for it in items:
        if it["id"] in ROTULOS:
            mov = VIDEO / "render" / "rotulos" / f"rotulo_{ROTULOS[it['id']]}.mov"
            rotulos.append({"archivo": str(mov), "seg": round(it["inicio"] + 0.8, 3)})
    man = {"fps": FPS, "total_segundos": round(t, 2), "clips": items, "voces_guia": voces,
           "rotulos": rotulos, "marcadores": marcas}
    (RENDER / "manifiesto.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Duración total: {t / 60:.0f} min {t % 60:.0f} s · {len(items)} clips · {len(voces)} voces guía")
    escribir_lua(man)
    escribir_fcpxml(man)


def lua_str(s):
    return '"' + s.replace("\\", "/").replace('"', '\\"').replace("\n", " ") + '"'


def escribir_lua(man):
    clips = ",\n".join(f'  {{id={lua_str(c["id"])}, tipo={lua_str(c["tipo"])}, file={lua_str(c["archivo"])}, '
                       f'frames={round(c["segundos"] * FPS)}}}' for c in man["clips"])
    voces = ",\n".join(f'  {{file={lua_str(v["archivo"])}, at={round(v["seg"] * FPS)}}}' for v in man["voces_guia"])
    rots = ",\n".join(f'  {{file={lua_str(r["archivo"])}, at={round(r["seg"] * FPS)}}}' for r in man["rotulos"])
    marks = ",\n".join(f'  {{at={round(m["seg"] * FPS)}, name={lua_str(m["nombre"])}, note={lua_str(m["nota"])}}}'
                       for m in man["marcadores"])
    plantilla = (VIDEO / "resolve" / "plantilla_armar.lua").read_text(encoding="utf-8")
    lua = (plantilla.replace("--@@CLIPS@@", clips).replace("--@@VOCES@@", voces)
           .replace("--@@ROTULOS@@", rots).replace("--@@MARCAS@@", marks))
    out = VIDEO / "resolve" / "Armar_video_chat_distribuido.lua"
    out.write_text(lua, encoding="utf-8")
    dest = Path(os.environ["APPDATA"]) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Utility"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(out, dest / out.name)
    print(f"Script de Resolve: {out}\nCopiado a: {dest / out.name}")


def escribir_fcpxml(man):
    """Línea de tiempo en FCPXML 1.10: File > Import > Timeline en Resolve (o Premiere/Final Cut)."""
    from urllib.parse import quote
    from xml.sax.saxutils import quoteattr
    fr = lambda sec: f"{round(sec * FPS)}/{FPS}s"
    assets, ids = [], {}
    def asset(path, video, secs):
        if path in ids:
            return ids[path]
        aid = f"a{len(ids) + 1}"
        ids[path] = aid
        url = "file:///" + quote(Path(path).as_posix(), safe="/:")
        if video:
            assets.append(f'<asset id="{aid}" name={quoteattr(Path(path).stem)} start="0s" duration="{fr(secs)}" hasVideo="1" hasAudio="0" format="r1" videoSources="1"><media-rep kind="original-media" src={quoteattr(url)}/></asset>')
        else:
            assets.append(f'<asset id="{aid}" name={quoteattr(Path(path).stem)} start="0s" duration="{fr(secs)}" hasVideo="0" hasAudio="1" audioSources="1" audioChannels="1" audioRate="48000"><media-rep kind="original-media" src={quoteattr(url)}/></asset>')
        return aid
    spine = []
    clips = man["clips"]
    def parent_of(t):
        for i, c in enumerate(clips):
            if c["inicio"] <= t < c["inicio"] + c["segundos"]:
                return i
        return len(clips) - 1
    children = {i: [] for i in range(len(clips))}
    for r in man["rotulos"]:
        i = parent_of(r["seg"]); d = 6.0
        children[i].append(f'<asset-clip ref="{asset(r["archivo"], True, d)}" lane="1" offset="{fr(r["seg"] - clips[i]["inicio"])}" duration="{fr(d)}" start="0s" name="rotulo"/>')
    for v in man["voces_guia"]:
        i = parent_of(v["seg"]); d = dur(v["archivo"])
        children[i].append(f'<asset-clip ref="{asset(v["archivo"], False, d)}" lane="-1" offset="{fr(v["seg"] - clips[i]["inicio"])}" duration="{fr(d)}" start="0s" name="voz guia"/>')
    for m in man["marcadores"]:
        i = parent_of(m["seg"])
        children[i].insert(0, f'<marker start="{fr(m["seg"] - clips[i]["inicio"])}" duration="1/{FPS}s" value={quoteattr(m["nombre"])} note={quoteattr(m["nota"])}/>')
    for i, c in enumerate(clips):
        aid = asset(c["archivo"], True, c["segundos"])
        spine.append(f'<asset-clip ref="{aid}" offset="{fr(c["inicio"])}" duration="{fr(c["segundos"])}" start="0s" name={quoteattr(c["id"] + " " + c["titulo"])}>' + "".join(children[i]) + "</asset-clip>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.10"><resources>'
           f'<format id="r1" name="FFVideoFormat1080p30" frameDuration="1/{FPS}s" width="1920" height="1080"/>' + "".join(assets) +
           '</resources><library><event name="Video Chat Distribuido"><project name="Video sustentacion (FCPXML)">'
           f'<sequence format="r1" duration="{fr(man["total_segundos"])}" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k"><spine>'
           + "".join(spine) + "</spine></sequence></project></event></library></fcpxml>\n")
    out = VIDEO / "resolve" / "linea_de_tiempo.fcpxml"
    out.write_text(xml, encoding="utf-8")
    print(f"FCPXML: {out}")


if __name__ == "__main__":
    main()
