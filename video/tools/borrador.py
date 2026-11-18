"""Arma un BORRADOR del video completo con ffmpeg (sin Resolve): escenas en orden,
rótulos encima y la voz guía sintética. Sirve para ver el ritmo antes de grabar.

    python video/tools/borrador.py   ->  video/render/borrador_con_voz_guia.mp4
"""
import json
import subprocess
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
man = json.loads((VIDEO / "render" / "manifiesto.json").read_text(encoding="utf-8"))
lst = VIDEO / "render" / "concat.txt"
lst.write_text("".join(f"file '{Path(c['archivo']).as_posix()}'\n" for c in man["clips"]), encoding="utf-8")

args = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst)]
for r in man["rotulos"]:
    args += ["-itsoffset", str(r["seg"]), "-i", r["archivo"]]
for v in man["voces_guia"]:
    args += ["-i", v["archivo"]]
nr, nv = len(man["rotulos"]), len(man["voces_guia"])
f, last = [], "[0:v]"
for i in range(nr):
    f.append(f"{last}[{i + 1}:v]overlay=eof_action=pass[v{i}]")
    last = f"[v{i}]"
for j, v in enumerate(man["voces_guia"]):
    ms = int(v["seg"] * 1000)
    f.append(f"[{1 + nr + j}:a]adelay={ms}|{ms},aresample=48000[a{j}]")
f.append("".join(f"[a{j}]" for j in range(nv)) + f"amix=inputs={nv}:normalize=0:duration=longest[aout]")
args += ["-filter_complex", ";".join(f), "-map", last, "-map", "[aout]", "-t", str(man["total_segundos"]),
         "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "aac", "-b:a", "160k", str(VIDEO / "render" / "borrador_con_voz_guia.mp4")]
subprocess.run(args, check=True)
lst.unlink()
print(VIDEO / "render" / "borrador_con_voz_guia.mp4")
