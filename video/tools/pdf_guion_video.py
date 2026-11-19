"""Genera docs/Guion_video.pdf: guion del video final (voz en off + animaciones + demo).

Lee video/guion_video.json y video/render/plan_final.json (que escribe sincronizar.py),
escribe docs/pdf-src/guion_video.html y lo imprime a PDF con Chrome.

    python video/tools/pdf_guion_video.py
"""
import html
import json
import subprocess
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
ROOT = VIDEO.parent
SRC = ROOT / "docs" / "pdf-src"
guion = json.loads((VIDEO / "guion_video.json").read_text(encoding="utf-8"))
plan = json.loads((VIDEO / "render" / "plan_final.json").read_text(encoding="utf-8"))
dur = {e["id"]: e for e in plan["escenas"]}
total = plan["total"]

FIX = [("ge a", "ga"), ("ge be", "gb"), ("history request", "HISTORY_REQUEST"),
       ("un recovered", "un RECOVERED"), ("con history", "con /history")]
FULL = {"Camilo": "Camilo Amaya Mora", "Johen": "Johen Gustavo Castañeda García",
        "Daniel": "Daniel Rodriguez Anaya", "Héctor": "Hector Felipe Higuera Jurado"}
ARCHIVO = {"S06": "S07.mp4 (venía intercambiado)", "S07": "S06.mp4 (venía intercambiado)",
           "S12": "S12.mp4 (era video: se usa solo el audio)", "S11": "S11.mp4 (cortado en 8 frases)"}
VE = {
    "S01": "Cuatro grupos alrededor de la sala #general; un mensaje viaja y su destino se apaga. Cierra con el título.",
    "S02": "Aparecen los cuatro nombres; nuestro servidor se conecta al central del profesor; luego la pregunta y la hipótesis: «Ninguno».",
    "S03": "La estrella se arma: central, grupos, un mensaje que pasa por el central. Luego ga se abre y muestra Docker, FastAPI, SQLite y el .env.",
    "S04": "Tarjeta de capítulo: «2 · Johen Gustavo Castañeda García · El servidor por dentro».",
    "S05": "Una transacción con 3 pasos (reloj, messages, outbox). El servidor se cae; el mensaje sigue en disco y se envía al volver.",
    "S06": "Dos relojes que no coinciden; el contador L al enviar y al recibir; al final las dos pantallas con el mismo orden.",
    "S07": "Un mensaje y su copia con el mismo id: la copia se descarta y se responde 200 OK.",
    "S08": "Tarjeta de capítulo: «3 · Daniel Rodriguez Anaya · Conexión con el servidor central».",
    "S09": "La bandeja de salida: 200 = enviado, 503 = reintentar con barras 1-2-4-8-16-30 s, 400 = no se insiste.",
    "S10": "Pings cada 3 s; tres fallos = central caído; al volver: registro, /history y envío de lo pendiente.",
    "S11": "Grabación real: los chats de ga y gb lado a lado y los logs abajo. Se apaga ga, se prende, se cae el central y vuelve.",
    "S12": "Tarjeta de capítulo: «4 · Hector Felipe Higuera Jurado · El experimento».",
    "S13": "El montaje del experimento en un portátil, la caída de 2/5/10 s, las fallas inyectadas y las 18 corridas.",
    "S14": "Los números: 0 perdidos, 0 repetidos, 363 duplicados descartados, ≤1,2 s; luego la gráfica de % perdido sin recuperación.",
    "S15": "Los 4 grupos del ensayo; todos reciben todo; los dos hallazgos del grupo con errores.",
    "S16": "Resumen: reintentar + descartar repetidos = exactamente una vez; Lamport = mismo orden. «Gracias».",
    "S17": "Créditos: título, nombres, enlace del repositorio y referencia del libro (sin voz).",
}


def clean(t):
    for a, b in FIX:
        t = t.replace(a, b)
    return html.escape(t)


def mmss(s):
    return f"{int(s // 60)}:{int(round(s % 60)):02d}"


def tipo(e):
    if e["tipo"] == "DEMO":
        return "Demo real + voz", "#2f7d4f"
    if not e["voz"]:
        return "Animación (sin voz)", "#5f5853"
    return "Voz en off + animación", "#2f5d8a"


def fila(e):
    d = dur[e["id"]]
    t, color = tipo(e)
    return (f"<tr><td><b>{e['id']}</b></td><td>{mmss(d['inicio'])}</td><td>{d['dura']:.0f} s</td>"
            f"<td><span class='tp' style='background:{color}'>{t}</span></td>"
            f"<td>{html.escape(FULL.get(e['voz'], '—'))}</td><td>{html.escape(e['titulo'])}</td></tr>")


def bloque(e):
    d = dur[e["id"]]
    t, color = tipo(e)
    if e.get("lineas"):
        texto = "".join(f"<p class='say'><span class='ev'>{html.escape(l['evento'].replace('_', ' '))}</span>{clean(l['texto'])}</p>"
                        for l in e["lineas"])
    elif e.get("texto"):
        texto = f"<p class='say'>{clean(e['texto'])}</p>"
    else:
        texto = "<p class='muted'>Sin voz.</p>"
    arch = ARCHIVO.get(e["id"], f"{e['id']}.mp4") if e["voz"] else "—"
    return (f"<div class='block'><div class='bh'><span class='id'>{e['id']}</span><span class='tp' style='background:{color}'>{t}</span>"
            f"<span class='tt'>{html.escape(e['titulo'])}</span><span class='tm'>{mmss(d['inicio'])} · {d['dura']:.0f} s</span></div>"
            f"<p class='ve'><b>Se ve:</b> {html.escape(VE[e['id']])}<br><b>Voz:</b> {html.escape(FULL.get(e['voz'], '—'))} · "
            f"<b>Grabación:</b> {html.escape(arch)}</p>{texto}</div>")


def por_persona():
    out = []
    for corto, largo in FULL.items():
        es = [e for e in guion["escenas"] if e["voz"] == corto]
        t = sum(dur[e["id"]]["dura"] for e in es)
        out.append(f"<tr><td><b>{largo}</b></td><td>{', '.join(e['id'] for e in es)}</td><td>{mmss(t)}</td></tr>")
    return "".join(out)


escenas = guion["escenas"]
page = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Guion del video</title>
<link rel="stylesheet" href="estilo.css">
<style>
 .cover {{ min-height: auto; page-break-after: auto; padding: 10mm 12mm; }}
 .cover h1 {{ font-size: 26pt; margin: 4mm 0 3mm; }}
 .tp {{ color:#fff; border-radius: 1.5mm; padding: .3mm 2mm; font-size: 8pt; font-weight: 700; white-space: nowrap; }}
 .block {{ padding: 3mm 4mm; margin: 3mm 0; }}
 .bh {{ display:flex; align-items:center; gap: 2.5mm; margin-bottom: 1.5mm; }}
 .bh .id {{ font-weight: 800; color: var(--wine); font-size: 12pt; }}
 .bh .tt {{ font-weight: 700; font-size: 11pt; flex: 1; }}
 .bh .tm {{ font-family: Consolas, monospace; font-size: 9pt; color: var(--muted); }}
 .ve {{ font-size: 9pt; color: var(--muted); margin: 1mm 0 2mm; }}
 .say .ev {{ display:inline-block; font-style: normal; font-family: Consolas, monospace; font-size: 8pt; background:#e7eef6; color: var(--blue);
             border-radius: 1mm; padding: 0 1.5mm; margin-right: 2mm; text-transform: uppercase; }}
 table.big {{ page-break-inside: auto; }}
 .muted {{ color: var(--muted); }}
 ol.steps li {{ margin: 1.6mm 0; }}
 kbd {{ font-family: Consolas, monospace; font-size: 8.5pt; background:#eee; border:1px solid #ccc; border-radius: 1mm; padding: 0 1.2mm; }}
</style></head><body>
<div class="cover">
  <div class="kicker">Sistemas Distribuidos · UIS · Proyecto final</div>
  <h1>Guion del video <span>· {mmss(total)} min</span></h1>
  <p class="lead">El video reemplaza la sustentación en vivo. No salen caras: todo es <b>voz en off con nuestras grabaciones</b> sobre animaciones,
  más una demo real del sistema. El video final <b>ya está armado</b> en <code style="color:#fff;background:rgba(255,255,255,.15)">video/render/video_final.mp4</code>.</p>
  <div class="who">Camilo Amaya Mora · Johen Gustavo Castañeda García · Daniel Rodriguez Anaya · Hector Felipe Higuera Jurado</div>
</div>

<h2><span class="n">1</span>Cómo es el video</h2>
<table class="big"><tr><th>#</th><th>Empieza</th><th>Dura</th><th>Tipo</th><th>Voz</th><th>Escena</th></tr>
{''.join(fila(e) for e in escenas)}</table>
<h3>Quién narra qué</h3>
<table><tr><th>Integrante</th><th>Escenas</th><th>Tiempo</th></tr>{por_persona()}</table>

<h2><span class="n">2</span>Cómo se armó con nuestras grabaciones</h2>
<ul>
<li>Las grabaciones están en <code>Audios y Videos Video/</code> (una por escena). Se extrajo solo el audio; la mayoría traía la imagen en negro.</li>
<li><b>S12</b> era el único video con cara: se le quitó la imagen y se dejó solo el audio, como se pidió.</li>
<li><b>S06 y S07 venían intercambiados</b> (el archivo S06 dice lo de idempotencia y el S07 lo del reloj de Lamport). Se pusieron en su escena correcta.</li>
<li><b>S15</b> la narra Héctor.</li>
<li>Todas las voces se limpiaron igual: filtro de graves (80 Hz), reducción suave de ruido y volumen nivelado a −16 LUFS, para que nadie suene más bajo que otro.</li>
<li>Cada grabación se transcribió automáticamente para saber en qué segundo se dice cada palabra, y <b>cada animación se re-sincronizó</b> para que cada cosa aparezca justo cuando se nombra.</li>
<li>La narración de la demo (S11) se cortó en sus 8 frases y cada una se ubicó en el momento de la demo que describe.</li>
</ul>

<h2><span class="n">3</span>Qué hay y dónde</h2>
<table class="files">
<tr><td><code>video/render/video_final.mp4</code></td><td><b>El video para entregar</b> (1080p, 30 fps, con voz).</td></tr>
<tr><td><code>video/voces/limpias/</code></td><td>Las voces ya limpias y niveladas.</td></tr>
<tr><td><code>video/voces/transcripciones/</code></td><td>Lo que dice cada grabación, palabra por palabra con su segundo.</td></tr>
<tr><td><code>video/animaciones/</code></td><td>El código de las animaciones (HyperFrames). <code>base/</code> son las escenas originales; <code>compositions/</code> las sincronizadas.</td></tr>
<tr><td><code>video/tools/sincronizar.py</code></td><td>Rehace la sincronización y el montaje si se cambia una grabación.</td></tr>
<tr><td><code>video/render/demo.mp4</code></td><td>La demo real grabada (sin voz).</td></tr>
<tr><td>DaVinci Resolve</td><td>Script que crea el proyecto con el video final y un marcador por escena, listo para agregar música (sección 5).</td></tr>
</table>

<h2><span class="n">4</span>El guion, escena por escena</h2>
<p>Texto del guion; en la grabación cada uno lo dijo con sus palabras.</p>
{''.join(bloque(e) for e in escenas)}

<h2><span class="n">5</span>Si quieren retocarlo en DaVinci Resolve (opcional)</h2>
<ol class="steps">
<li>Abrir DaVinci Resolve → menú <b>Workspace › Scripts › Utility › Armar_video_chat_distribuido</b>. Crea el proyecto <b>Video Chat Distribuido</b>
con el video final en V1/A1 y un marcador amarillo por escena. (Plan B: <b>File › Import › Timeline</b> → <code>video/resolve/linea_de_tiempo.fcpxml</code>.)</li>
<li><b>Música (recomendado):</b> una pista instrumental suave sin derechos (Biblioteca de audio de YouTube, filtro «Sin atribución») en <b>A2</b>,
a unos <b>−22 dB</b> bajo la voz, con fundido al inicio y al final.</li>
<li><b>Exportar:</b> página <b>Deliver</b> → preset <b>YouTube 1080p</b> → <i>Add to Render Queue</i> → <i>Render All</i>.</li>
</ol>
<div class="note"><b>¿Cambiar una voz?</b> Reemplazar el archivo en <code>Audios y Videos Video/</code> con el mismo nombre y correr, en orden:
<code>python video/tools/transcribir.py SXX</code>, ajustar los anclajes de esa escena en <code>sincronizar.py</code> si cambió mucho el ritmo,
<code>python video/tools/sincronizar.py</code> y <code>npx hyperframes render</code> dentro de <code>video/animaciones</code>.</div>

<h2><span class="n">6</span>Lista final antes de entregar</h2>
<table>
<tr><th>Revisar</th><th>OK</th></tr>
<tr><td>Dura menos de 10 minutos (dura {mmss(total)})</td><td>☐</td></tr>
<tr><td>Cada integrante narra su parte</td><td>☐</td></tr>
<tr><td>La demo muestra una falla y su recuperación (S11)</td><td>☐</td></tr>
<tr><td>Se entiende la pregunta, el método, los resultados con unidades y la conclusión</td><td>☐</td></tr>
<tr><td>Verlo completo con audífonos: ninguna voz se corta ni se pisa con otra</td><td>☐</td></tr>
<tr><td>Subido donde pidió el profesor (Moodle, «Trabajo Final»)</td><td>☐</td></tr>
</table>
</body></html>"""
(SRC / "guion_video.html").write_text(page, encoding="utf-8")
pdf = ROOT / "docs" / "Guion_video.pdf"
chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                (SRC / "guion_video.html").as_uri()], check=True, capture_output=True)
print(pdf)
