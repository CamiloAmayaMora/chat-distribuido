"""Agrega efectos de sonido al video final (sin volver a renderizar la imagen).

Cada efecto se ubica en el instante exacto de su animación: tiempo original de la
escena -> mismo estiramiento que usó sincronizar.py -> inicio de la escena en el video.
Sonidos: biblioteca incluida en la skill media-use de HyperFrames (video/sfx/).

    python video/tools/mezclar_sfx.py   ->  video/render/video_final.mp4 (con efectos)
"""
import json
import shutil
import subprocess
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
SRC_SFX = Path.home() / ".claude" / "skills" / "media-use" / "audio" / "assets" / "sfx"
SFX = VIDEO / "sfx"
plan = json.loads((VIDEO / "render" / "plan_final.json").read_text(encoding="utf-8"))
start = {e["id"].lower(): e["inicio"] for e in plan["escenas"]}
ev = json.loads((VIDEO / "demo" / "eventos.json").read_text(encoding="utf-8"))

# volumen base de cada sonido (la voz manda; los efectos acompañan)
VOL = {"whoosh": 0.22, "whoosh-short": 0.22, "whoosh-cinematic": 0.22, "pop": 0.30, "click": 0.26, "click-soft": 0.30,
       "chime": 0.35, "error": 1.8, "glitch-1": 0.16, "glitch-3": 0.18, "impact-bass-1": 0.30, "impact-bass-2": 0.30,
       "ping": 0.28, "notification": 0.22, "sparkle": 0.20, "typing": 0.3, "key-press": 0.25}
CUES = {
    "s01": [(0.3, "pop"), (3.3, "pop"), (4.3, "click-soft"), (5.1, "click-soft"), (6.9, "whoosh-short"), (7.9, "error"),
            (8.6, "pop"), (11.35, "impact-bass-1")],
    "s02": [(1.7, "pop"), (2.7, "pop"), (3.2, "pop"), (3.9, "pop"), (8.0, "pop"), (11.8, "whoosh-short"), (12.5, "pop"),
            (17.7, "notification"), (25.5, "impact-bass-1"), (26.2, "chime")],
    "s03": [(0.5, "pop"), (4.4, "pop"), (4.75, "pop"), (5.1, "pop"), (5.45, "pop"), (10.1, "error"), (14.6, "whoosh-short"),
            (16.1, "ping"), (17.3, "pop"), (18.6, "whoosh-short"), (22.5, "whoosh-cinematic"), (25.2, "pop"), (29.0, "pop"),
            (33.6, "pop"), (34.1, "click-soft"), (34.35, "click-soft"), (34.6, "click-soft"), (36.2, "chime")],
    "s05": [(0.3, "pop"), (4.0, "whoosh-short"), (5.3, "click"), (6.9, "click"), (8.9, "click"), (10.0, "chime"),
            (11.3, "glitch-1"), (13.8, "ping"), (17.6, "whoosh-short"), (18.6, "chime")],
    "s06": [(0.4, "pop"), (0.6, "pop"), (3.0, "error"), (9.6, "pop"), (11.8, "whoosh-short"), (13.2, "pop"), (14.0, "click"),
            (16.4, "ping"), (18.8, "pop"), (21.6, "ping"), (24.6, "whoosh-short"), (25.6, "chime")],
    "s07": [(0.5, "pop"), (2.2, "whoosh-short"), (2.9, "pop"), (4.1, "whoosh-short"), (4.9, "error"), (5.8, "click"),
            (8.8, "impact-bass-1"), (12.6, "pop"), (12.95, "pop"), (13.3, "pop"), (14.0, "chime")],
    "s09": [(0.6, "pop"), (3.6, "whoosh-short"), (4.6, "chime"), (6.3, "whoosh-short"), (7.1, "error"), (10.6, "click-soft"),
            (11.4, "click-soft"), (12.2, "click-soft"), (13.0, "click-soft"), (14.2, "click-soft"), (15.4, "click-soft"),
            (20.4, "whoosh-short"), (21.2, "error"), (22.8, "glitch-3"), (27.0, "pop")],
    "s10": [(1.0, "click-soft"), (2.2, "click-soft"), (3.7, "click-soft"), (4.6, "click-soft"), (5.5, "click-soft"),
            (6.2, "error"), (6.9, "pop"), (7.4, "pop"), (7.9, "pop"), (8.6, "chime"), (9.0, "pop"), (11.2, "pop"),
            (14.0, "pop"), (15.2, "ping")],
    "s13": [(0.6, "pop"), (0.95, "pop"), (1.3, "pop"), (8.0, "error"), (10.4, "click"), (11.4, "click"), (12.4, "click"),
            (13.8, "ping"), (16.6, "ping"), (20.6, "sparkle")],
    "s14": [(1.4, "pop"), (3.6, "pop"), (6.4, "pop"), (8.1, "ping"), (11.8, "pop"), (14.4, "whoosh-short"), (16.2, "pop"),
            (17.2, "pop"), (18.6, "impact-bass-1"), (21.2, "ping")],
    "s15": [(0.4, "pop"), (4.2, "pop"), (5.0, "pop"), (7.6, "pop"), (9.0, "pop"), (10.8, "chime"), (12.7, "whoosh-short"),
            (13.6, "error"), (17.2, "error"), (20.8, "pop")],
    "s16": [(2.3, "pop"), (4.3, "pop"), (6.8, "impact-bass-1"), (10.8, "pop"), (12.6, "pop"), (16.6, "chime")],
    "s17": [(0.2, "sparkle")],
}
for sid, chips in {"s04": [3.4, 4.4, 5.4], "s08": [5.6, 6.4, 8.6], "s12": [3.4, 4.2, 5.0]}.items():
    CUES[sid] = [(0.2, "whoosh"), (0.8, "pop")] + [(t, "click-soft") for t in chips]
CUES["s11"] = [(ev["conversacion"] + 0.3, "typing"), (ev["conversacion"] + 3.6, "typing"), (ev["kill_ga"] + 0.9, "glitch-1"),
               (ev["gb_escribe"] + 0.2, "typing"), (ev["gb_escribe"] + 3.6, "typing"), (ev["start_ga"] + 0.9, "whoosh-short"),
               (ev["ga_al_dia"] + 0.1, "chime"), (ev["stop_central"] + 0.9, "error"), (ev["stop_central"] + 8.4, "typing"),
               (ev["start_central"] + 0.9, "whoosh-short"), (ev["start_central"] + 10.0, "chime")]


def warp(sid, t):
    pts = plan["warps"].get(sid)
    if not pts or t <= pts[0][0]:
        return t
    for (a, b), (c, d) in zip(pts, pts[1:]):
        if t <= c:
            return b + (t - a) * (d - b) / (c - a)
    a, b = pts[-1]
    return b + (t - a)


def main():
    SFX.mkdir(exist_ok=True)
    cues = []
    for sid, lst in CUES.items():
        for t, name in lst:
            cues.append((round(start[sid] + warp(sid, t), 3), name))
    order = [e["id"].lower() for e in plan["escenas"]]
    seams = ["whoosh-short", "whoosh", "whoosh-short", "whoosh-cinematic"]
    for i, sid in enumerate(order[1:]):  # transición entre escenas
        if sid not in ("s04", "s08", "s12"):
            cues.append((round(start[sid] - 0.12, 3), seams[i % len(seams)]))
    cues.sort()
    names = sorted({n for _, n in cues})
    for n in names:
        shutil.copy(SRC_SFX / f"{n}.mp3", SFX / f"{n}.mp3")
    src = VIDEO / "render" / "video_final.mp4"
    sinfx = VIDEO / "render" / "video_final_sin_efectos.mp4"
    if not sinfx.exists():
        shutil.copy(src, sinfx)
    args = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(sinfx)]
    for n in names:
        args += ["-i", str(SFX / f"{n}.mp3")]
    idx = {n: i + 1 for i, n in enumerate(names)}
    f, labels = [], []
    use = {n: [c for c in cues if c[1] == n] for n in names}
    for n in names:
        k = len(use[n])
        f.append(f"[{idx[n]}:a]aresample=48000,aformat=channel_layouts=stereo,volume={VOL[n]},asplit={k}" +
                 "".join(f"[s{idx[n]}x{j}]" for j in range(k)))
        for j, (t, _) in enumerate(use[n]):
            ms = int(t * 1000)
            f.append(f"[s{idx[n]}x{j}]adelay={ms}|{ms}[d{idx[n]}x{j}]")
            labels.append(f"[d{idx[n]}x{j}]")
    f.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest[fx]")
    f.append("[0:a]aresample=48000,aformat=channel_layouts=stereo[vo]")
    f.append("[vo][fx]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
    args += ["-filter_complex", ";".join(f),
             "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(src)]
    subprocess.run(args, check=True)
    (VIDEO / "sfx" / "cues.json").write_text(json.dumps(cues, indent=0), encoding="utf-8")
    print(f"{len(cues)} efectos ({', '.join(names)}) -> {src}")


if __name__ == "__main__":
    main()
