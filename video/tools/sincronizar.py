"""Arma el VIDEO FINAL con las voces reales del grupo.

- Re-sincroniza cada animación con su grabación: cada escena tiene puntos de anclaje
  (segundo en la animación original -> segundo en que la voz dice esa palabra) y
  los tiempos se estiran por tramos entre anclajes (ver WARPS).
- Genera las escenas sin caras (S04, S08, S12: tarjetas de capítulo).
- Corta la narración de la demo (S11) en sus 8 frases y las ubica en cada evento.
- Escribe animaciones/index.html con todas las escenas, la demo y las voces.

    python video/tools/sincronizar.py
    (luego: cd video/animaciones && npx hyperframes render . -o ../render/video_final.mp4)
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
ANIM = VIDEO / "animaciones"
BASE, COMP = ANIM / "base", ANIM / "compositions"
VOCES = VIDEO / "voces" / "limpias"
OFF = 0.4  # la voz entra 0,4 s después de empezar la escena

# (segundo en la animación original, segundo nuevo). Lo nuevo = palabra clave en la voz + OFF.
WARPS = {
    "s01": [[0, 0], [3.4, 3.9], [6.2, 7.3], [7.9, 11.2], [11.1, 13.3]],
    "s03": [[0, 0], [0.5, 3.6], [4.4, 6.8], [9.2, 11.0], [13.6, 16.2], [16.6, 22.9], [18.6, 24.4], [22.5, 27.3],
            [25.2, 29.4], [29.0, 35.6], [33.6, 39.8], [36.2, 42.6], [41, 47.4]],
    "s05": [[0, 0], [0.3, 2.0], [1.6, 3.4], [5.0, 6.9], [6.6, 7.9], [8.6, 10.7], [11.3, 13.7], [13.8, 16.4],
            [16.4, 18.3], [22, 23.9]],
    "s06": [[0, 0], [0.4, 1.3], [3.0, 5.8], [3.4, 6.2], [6.0, 8.6], [6.3, 8.9], [9.6, 11.8], [11.8, 13.8],
            [14.0, 15.4], [16.4, 18.8], [18.2, 20.6], [21.6, 24.8], [24.6, 26.9], [25.6, 28.3], [33, 34.6]],
    "s07": [[0, 0], [0.5, 1.4], [3.2, 4.0], [5.8, 6.0], [8.6, 8.8], [10.8, 11.6], [19, 19.6]],
    "s09": [[0, 0], [0.6, 1.3], [3.6, 4.3], [6.3, 7.0], [10.0, 11.6], [10.6, 12.3], [15.4, 15.6], [16.4, 17.4],
            [20.4, 20.6], [21.2, 22.9], [22.8, 24.4], [27.0, 28.0], [32, 30.0]],
    "s10": [[0, 0], [1.0, 1.4], [3.4, 4.6], [6.2, 7.4], [6.9, 8.9], [8.6, 10.6], [9.0, 11.7], [11.2, 14.0],
            [14.0, 17.2], [20, 21.6]],
    "s13": [[0, 0], [0.6, 1.8], [4.6, 7.4], [8.0, 11.4], [10.4, 14.6], [12.4, 16.4], [13.8, 18.6], [16.6, 20.8],
            [19.8, 24.6], [22.4, 28.6], [31, 32.6]],
    "s14": [[0, 0], [0.3, 1.2], [1.4, 2.8], [3.6, 4.7], [6.4, 8.0], [11.8, 14.6], [14.4, 18.4], [16.2, 20.4],
            [18.6, 23.6], [19.3, 24.6], [21.2, 25.8], [26, 30]],
    "s15": [[0, 0], [0.4, 1.0], [4.2, 6.0], [7.6, 10.0], [9.0, 11.4], [10.8, 13.5], [12.6, 15.3], [13.6, 17.3],
            [17.2, 20.6], [20.8, 23.6], [25, 27.6]],
}
ORIG_DUR = {"s01": 16, "s03": 41, "s05": 22, "s06": 33, "s07": 19, "s09": 32, "s10": 20, "s13": 31,
            "s14": 26, "s15": 25, "s17": 9, "s02": 28.5, "s16": 19.5}
# capítulos sin cara: (parte, nombre, rol, color, chips con su segundo, duración)
CAPS = {
    "s04": ("2", "Johen Gustavo Castañeda García", "El servidor por dentro", "--gb",
            [("bandeja de salida", 3.4), ("reloj de Lamport", 4.4), ("idempotencia", 5.4)], 8.4),
    "s08": ("3", "Daniel Rodriguez Anaya", "Conexión con el servidor central", "--ok",
            [("enviar", 5.6), ("reintentar", 6.4), ("detectar fallas", 8.6)], 10.8),
    "s12": ("4", "Hector Felipe Higuera Jurado", "El experimento", "--warn",
            [("18 corridas", 3.4), ("caídas de 2, 5 y 10 s", 4.2), ("fallas inyectadas", 5.0)], 7.6),
}
ORDEN = ["s01", "s02", "s03", "s04", "s05", "s06", "s07", "s08", "s09", "s10", "s11",
         "s12", "s13", "s14", "s15", "s16", "s17"]
# qué grabación va en cada escena (S06 y S07 venían intercambiadas)
AUDIO = {"s01": "S01", "s02": "S02", "s03": "S03", "s04": "S04", "s05": "S05", "s06": "S07", "s07": "S06",
         "s08": "S08", "s09": "S09", "s10": "S10", "s12": "S12", "s13": "S13", "s14": "S14", "s15": "S15",
         "s16": "S16"}
AUDIO_OFF = {"s13": 0.0, "s15": 0.0, "s12": 0.0}
# demo: inicio de cada frase en S11 (segundos, de la transcripción) y su evento
DEMO_LINES = [(0.0, "inicio"), (12.18, "conversacion"), (19.78, "kill_ga"), (24.34, "gb_escribe"),
              (31.3, "start_ga"), (40.22, "ga_al_dia"), (46.28, "stop_central"), (57.92, "start_central")]


def warp_fn(pts):
    def W(t):
        if t <= pts[0][0]:
            return t
        for (a, b), (c, d) in zip(pts, pts[1:]):
            if t <= c:
                return b + (t - a) * (d - b) / (c - a)
        a, b = pts[-1]
        return b + (t - a)
    return W


JS = """
    const WARP = %s;
    const W = (t) => { const p = WARP; if (t <= p[0][0]) return t; for (let i = 1; i < p.length; i++) { if (t <= p[i][0]) { const [a, b] = p[i - 1], [c, d] = p[i]; return b + (t - a) * (d - b) / (c - a); } } const [a, b] = p[p.length - 1]; return b + (t - a); };
    for (const m of ["to", "fromTo", "set", "from"]) { const f = tl[m].bind(tl); tl[m] = (...a) => { const i = a.length - 1; if (typeof a[i] === "number") a[i] = W(a[i]); return f(...a); }; }
"""


def warp_scene(sid):
    src = (BASE / f"{sid}.html").read_text(encoding="utf-8")
    pts = [list(x) for x in WARPS.get(sid, [])] or None
    if pts and sid in AUDIO and sid != "s01":  # s01 conserva el título al final
        # acortar la cola: la escena termina 1,5 s después de la última palabra
        words = json.loads((VIDEO / "voces" / "transcripciones" / f"{AUDIO[sid]}.json").read_text(encoding="utf-8"))["words"]
        fin_voz = AUDIO_OFF.get(sid, OFF) + max(w["end"] for w in words)
        W0 = warp_fn(pts)
        end_now = W0(ORIG_DUR[sid])
        target = max(fin_voz + 1.5, pts[-2][1] + 1.2 if pts[-1][0] >= ORIG_DUR[sid] else pts[-1][1] + 1.2)
        if target < end_now:
            if pts[-1][0] >= ORIG_DUR[sid]:
                pts[-1] = [ORIG_DUR[sid], round(target, 2)]
            else:
                pts.append([ORIG_DUR[sid], round(target, 2)])
    if not pts:
        (COMP / f"{sid}.html").write_text(src, encoding="utf-8")
        return ORIG_DUR[sid]
    W = warp_fn(pts)

    def clip(m):
        s, d = float(m.group(1)), float(m.group(2))
        ns, ne = W(s), W(s + d)
        return f'data-start="{ns:.2f}" data-duration="{ne - ns:.2f}"'
    src = re.sub(r'data-start="([\d.]+)" data-duration="([\d.]+)"', clip, src)
    src = src.replace("const tl = gsap.timeline({ paused: true });",
                      "const tl = gsap.timeline({ paused: true });" + JS % json.dumps(pts), 1)
    (COMP / f"{sid}.html").write_text(src, encoding="utf-8")
    return round(W(ORIG_DUR[sid]), 2)


def chapter(sid):
    parte, nombre, rol, color, chips, dur = CAPS[sid]
    chip_html = "".join(f'<div class="cap-chip" id="{sid}-c{i}">{c}</div>' for i, (c, _) in enumerate(chips))
    chip_js = "".join(f'    tl.fromTo("#{sid}-c{i}", {{ opacity: 0, y: 16 }}, {{ opacity: 1, y: 0, duration: 0.45, ease: "expo.out" }}, {t});\n'
                      for i, (_, t) in enumerate(chips))
    html = f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; }}
    #{sid}-scene {{ position: absolute; inset: 0; }}
    #{sid}-num {{ position: absolute; left: 200px; top: 250px; font-family: var(--font-display); font-weight: 700; font-size: 420px; line-height: 1; color: var({color}); opacity: .9; }}
    #{sid}-k {{ left: 520px; top: 330px; }}
    #{sid}-name {{ left: 520px; top: 380px; font-size: 92px; }}
    #{sid}-rol {{ left: 520px; top: 500px; font-size: 54px; color: var({color}); }}
    #{sid}-chips {{ position: absolute; left: 520px; top: 640px; display: flex; gap: 22px; }}
    #{sid}-scene .cap-chip {{ padding: 16px 28px; border-radius: 999px; background: var(--panel2); border: 2px solid var({color}); font-family: var(--font-mono); font-size: 32px; }}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="1920" data-height="1080">
    <div id="{sid}-scene" class="clip" data-start="0" data-duration="{dur}">
      <div id="{sid}-num">{parte}</div>
      <div id="{sid}-k" class="kicker">Parte {parte}</div>
      <div id="{sid}-name" class="title">{nombre}</div>
      <div id="{sid}-rol" class="title">{rol}</div>
      <div id="{sid}-chips">{chip_html}</div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#{sid}-num", {{ opacity: 0, x: -60 }}, {{ opacity: 0.9, x: 0, duration: 0.8, ease: "expo.out" }}, 0.2);
    tl.fromTo("#{sid}-k", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 0.5);
    tl.fromTo("#{sid}-name", {{ opacity: 0, filter: "blur(10px)" }}, {{ opacity: 1, filter: "blur(0px)", duration: 0.4, ease: "power4.out" }}, 0.8);
    tl.fromTo("#{sid}-rol", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: "expo.out" }}, 1.8);
{chip_js}    tl.to("#{sid}-scene", {{ opacity: 0, duration: 0.3, ease: "power2.in" }}, {dur - 0.4});
    window.__timelines["{sid}"] = tl;
  </script>
</template>
"""
    (COMP / f"{sid}.html").write_text(html, encoding="utf-8")
    return dur


def dur_of(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True, check=True).stdout)


def main():
    COMP.mkdir(exist_ok=True)
    for f in COMP.glob("*.html"):
        f.unlink()
    adir = ANIM / "assets" / "voces"
    adir.mkdir(parents=True, exist_ok=True)
    for f in adir.glob("*.wav"):
        f.unlink()
    shutil.copy(VIDEO / "render" / "demo.mp4", ANIM / "assets" / "demo.mp4")
    durs = {}
    for sid in ORDEN:
        if sid == "s11":
            durs[sid] = round(dur_of(ANIM / "assets" / "demo.mp4"), 2)
        elif sid in CAPS:
            durs[sid] = chapter(sid)
        else:
            durs[sid] = warp_scene(sid)
    # que cada escena dure al menos su voz + 0,8 s
    for sid, rec in AUDIO.items():
        words = json.loads((VIDEO / "voces" / "transcripciones" / f"{rec}.json").read_text(encoding="utf-8"))["words"]
        need = AUDIO_OFF.get(sid, OFF) + max(w["end"] for w in words) + 1.0
        if durs[sid] < need:
            print(f"  {sid}: la voz dura más que la escena ({need:.1f} > {durs[sid]:.1f}); se alarga")
            durs[sid] = round(need, 2)
    # frases de la demo
    ev = json.loads((VIDEO / "demo" / "eventos.json").read_text(encoding="utf-8"))
    s11 = VOCES / "S11.wav"
    total11 = dur_of(s11)
    demo_audio, prev_end = [], 0.0
    for i, (st, evento) in enumerate(DEMO_LINES):
        a = max(st - 0.15, 0)
        b = DEMO_LINES[i + 1][0] - 0.15 if i + 1 < len(DEMO_LINES) else total11
        out = adir / f"S11_{i + 1:02d}_{evento}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a:.2f}", "-to", f"{b:.2f}", "-i", str(s11),
                        "-af", "afade=t=out:st=%.2f:d=0.12" % (b - a - 0.12), str(out)], check=True)
        at = max(ev[evento] + 0.2, prev_end + 0.3)
        demo_audio.append((out.name, round(at, 2), round(b - a, 2)))
        prev_end = at + (b - a)
    # index.html
    t, hosts, audios = 0.0, [], []
    for sid in ORDEN:
        d = durs[sid]
        if sid == "s11":
            hosts.append(f'      <video id="demo" class="clip" src="assets/demo.mp4" data-start="{t:.2f}" data-duration="{d:.2f}" '
                         f'data-track-index="1" muted playsinline style="position:absolute;left:0;top:0;width:1920px;height:1080px;object-fit:contain;z-index:2"></video>')
            for name, at, ln in demo_audio:
                audios.append(f'      <audio id="vo-{name[:-4].lower().replace("_", "-")}" class="clip" src="assets/voces/{name}" data-start="{t + at:.2f}" data-duration="{ln:.2f}" data-track-index="2" data-volume="1"></audio>')
        else:
            hosts.append(f'      <div id="{sid}" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" data-start="{t:.2f}" '
                         f'data-duration="{d:.2f}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080" style="z-index:3"></div>')
            if sid in AUDIO:
                rec = AUDIO[sid]
                shutil.copy(VOCES / f"{rec}.wav", adir / f"{rec}.wav")
                ln = dur_of(VOCES / f"{rec}.wav")
                audios.append(f'      <audio id="vo-{sid}" class="clip" src="assets/voces/{rec}.wav" data-start="{t + AUDIO_OFF.get(sid, OFF):.2f}" data-duration="{ln:.2f}" data-track-index="2" data-volume="1"></audio>')
        t += d
    total = round(t, 2)
    base = (BASE / "index_v1.html").read_text(encoding="utf-8")
    head = base.split("<body>")[0]
    page = head + f"""<body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="1920" data-height="1080">
      <div id="bg"></div>
{chr(10).join(hosts)}
{chr(10).join(audios)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""
    (ANIM / "index.html").write_text(page, encoding="utf-8")
    plan = {"total": total, "escenas": [{"id": s.upper(), "inicio": round(sum(durs[x] for x in ORDEN[:i]), 2), "dura": durs[s]}
                                        for i, s in enumerate(ORDEN)]}
    (VIDEO / "render" / "plan_final.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
    for e in plan["escenas"]:
        print(f'{e["id"]}  {e["inicio"]:7.2f}  {e["dura"]:6.2f}')
    print(f"TOTAL {total:.1f} s = {int(total // 60)} min {total % 60:.0f} s")


if __name__ == "__main__":
    main()
