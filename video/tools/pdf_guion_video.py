"""Genera docs/Guion_video.pdf (guion del video + plan de grabación y edición).

Lee video/guion_video.json y video/render/manifiesto.json, escribe
docs/pdf-src/guion_video.html y lo imprime a PDF con Chrome.

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
man = json.loads((VIDEO / "render" / "manifiesto.json").read_text(encoding="utf-8"))
dur = {c["id"]: c for c in man["clips"]}

# la voz guía usa pronunciación ("ge a"); en el papel va como se escribe
FIX = [("ge a", "ga"), ("ge be", "gb"), ("history request", "HISTORY_REQUEST"),
       ("un recovered", "un RECOVERED"), ("con history", "con /history"), ("Ge a", "ga")]


def clean(t):
    for a, b in FIX:
        t = t.replace(a, b)
    return html.escape(t)


def mmss(s):
    return f"{int(s // 60)}:{int(round(s % 60)):02d}"


FULL = {"Camilo": "Camilo Amaya Mora", "Johen": "Johen Gustavo Castañeda García",
        "Daniel": "Daniel Rodriguez Anaya", "Héctor": "Hector Felipe Higuera Jurado"}
TIPO = {"ANIM": ("Voz en off + animación", "#2f5d8a"), "CARA": ("A cámara", "#a11a3f"),
        "DEMO": ("Demo real (pantalla) + voz en off", "#2f7d4f")}
VE = {
    "S01": "Cuatro grupos alrededor de la sala #general; un mensaje viaja y su destino se apaga. Cierra con el título.",
    "S02": "Camilo a cámara, plano medio. Aparece el rótulo con su nombre.",
    "S03": "La estrella se arma: central, grupos, un mensaje que pasa por el central. Luego ga se abre y muestra Docker, FastAPI, SQLite y el .env.",
    "S04": "Johen a cámara, con rótulo.",
    "S05": "Una transacción con 3 pasos (reloj, messages, outbox). El servidor se cae; el mensaje sigue en disco y se envía al volver.",
    "S06": "Dos relojes que no coinciden; luego el contador L al enviar y al recibir; al final las dos pantallas con el mismo orden.",
    "S07": "Un mensaje y su copia con el mismo id: la copia se descarta y se responde 200 OK.",
    "S08": "Daniel a cámara, con rótulo.",
    "S09": "La bandeja de salida: 200 = enviado, 503 = reintentar con barras 1-2-4-8-16-30 s, 400 = no se insiste.",
    "S10": "Pings cada 3 s; tres fallos = central caído; al volver: registro, /history y envío de lo pendiente.",
    "S11": "Grabación real: los chats de ga y gb lado a lado y los logs abajo. Se apaga ga, se prende, se cae el central y vuelve.",
    "S12": "Héctor a cámara, con rótulo.",
    "S13": "El montaje del experimento en un portátil, la caída de 2/5/10 s, las fallas inyectadas y las 18 corridas.",
    "S14": "Los números: 0 perdidos, 0 repetidos, 363 duplicados descartados, ≤1,2 s; luego la gráfica de % perdido sin recuperación.",
    "S15": "Los 4 grupos del ensayo; todos reciben todo; los dos hallazgos del grupo con errores.",
    "S16": "Cierre a cámara. Ideal: los cuatro en cuadro, habla Camilo.",
    "S17": "Conclusión, nombres, enlace del repositorio y referencia del libro (sin voz).",
}


def fila(e):
    c = dur[e["id"]]
    t, color = TIPO[e["tipo"]] if e["voz"] else ("Animación (sin voz)", "#5f5853")
    voz = FULL.get(e["voz"], "—") if e["voz"] else "—"
    return (f"<tr><td><b>{e['id']}</b></td><td>{mmss(c['inicio'])}</td><td>{c['segundos']:.0f} s</td>"
            f"<td><span class='tp' style='background:{color}'>{t}</span></td><td>{html.escape(voz)}</td>"
            f"<td>{html.escape(e['titulo'])}</td></tr>")


def bloque(e):
    c = dur[e["id"]]
    t, color = TIPO[e["tipo"]] if e["voz"] else ("Animación (sin voz)", "#5f5853")
    if e.get("lineas"):
        texto = "".join(f"<p class='say'><span class='ev'>{html.escape(l['evento'].replace('_', ' '))}</span>{clean(l['texto'])}</p>"
                        for l in e["lineas"])
    elif e.get("texto"):
        texto = f"<p class='say'>{clean(e['texto'])}</p>"
    else:
        texto = "<p class='muted'>Sin voz: solo música y la tarjeta final.</p>"
    return (f"<div class='block'><div class='bh'><span class='id'>{e['id']}</span><span class='tp' style='background:{color}'>{t}</span>"
            f"<span class='tt'>{html.escape(e['titulo'])}</span><span class='tm'>{mmss(c['inicio'])} · {c['segundos']:.0f} s</span></div>"
            f"<p class='ve'><b>Se ve:</b> {html.escape(VE[e['id']])}</p>{texto}</div>")


def por_persona():
    out = []
    for corto, largo in FULL.items():
        es = [e for e in guion["escenas"] if e["voz"] == corto]
        caras = [e["id"] for e in es if e["tipo"] == "CARA"]
        off = [e["id"] for e in es if e["tipo"] != "CARA"]
        total = sum(dur[e["id"]]["segundos"] for e in es)
        out.append(f"<tr><td><b>{largo}</b></td><td>{', '.join(caras) or '—'}</td><td>{', '.join(off) or '—'}</td><td>{mmss(total)}</td></tr>")
    return "".join(out)


escenas = guion["escenas"]
total = man["total_segundos"]
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
 .two {{ display:grid; grid-template-columns: 1fr 1fr; gap: 4mm; }}
 .step {{ counter-increment: s; }}
 ol.steps li {{ margin: 1.6mm 0; }}
 kbd {{ font-family: Consolas, monospace; font-size: 8.5pt; background:#eee; border:1px solid #ccc; border-radius: 1mm; padding: 0 1.2mm; }}
</style></head><body>
<div class="cover">
  <div class="kicker">Sistemas Distribuidos · UIS · Proyecto final</div>
  <h1>Guion y plan del video <span>· {mmss(total)} min</span></h1>
  <p class="lead">El video reemplaza la sustentación en vivo. Alterna pocas escenas con nuestras caras y escenas con voz en off
  sobre animaciones. Las animaciones, la demo y el proyecto de DaVinci Resolve <b>ya están hechos</b>: solo falta grabar las caras y las voces.</p>
  <div class="who">Camilo Amaya Mora · Johen Gustavo Castañeda García · Daniel Rodriguez Anaya · Hector Felipe Higuera Jurado</div>
</div>

<h2><span class="n">1</span>Cómo es el video</h2>
<table class='big'><tr><th>#</th><th>Empieza</th><th>Dura</th><th>Tipo</th><th>Voz</th><th>Escena</th></tr>
{''.join(fila(e) for e in escenas)}</table>
<div class="note"><b>Regla de ritmo:</b> 5 tomas a cámara cortas (en total ~{mmss(sum(dur[e['id']]['segundos'] for e in escenas if e['tipo']=='CARA'))}),
todo lo demás es voz en off sobre animación o demo. Cada animación ya está cronometrada para la voz; si alguien habla más lento, se alarga la escena en Resolve.</div>

<h3>Qué le toca grabar a cada uno</h3>
<table><tr><th>Integrante</th><th>A cámara</th><th>Voz en off</th><th>Tiempo hablando</th></tr>{por_persona()}</table>

<h2><span class="n">2</span>Qué ya está listo y dónde</h2>
<table class="files">
<tr><td><code>video/render/borrador_con_voz_guia.mp4</code></td><td><b>Véanlo primero:</b> el video completo armado con la voz guía. Así se ve el ritmo y cuánto dura cada parte.</td></tr>
<tr><td><code>video/render/escenas/</code></td><td>Las 11 animaciones en MP4 1080p (una por escena).</td></tr>
<tr><td><code>video/render/demo.mp4</code></td><td>La demo real grabada: caída de ga, recuperación, caída y regreso del central, con los logs reales.</td></tr>
<tr><td><code>video/render/rotulos/</code></td><td>Rótulos con nombre y parte de cada uno (video con fondo transparente).</td></tr>
<tr><td><code>video/render/caras/</code></td><td>Tarjetas de relleno donde van las tomas a cámara (dicen quién y cuánto dura).</td></tr>
<tr><td><code>video/tts/</code></td><td>Voz guía sintética de cada escena: sirve para ver el ritmo; se reemplaza por la voz real.</td></tr>
<tr><td>DaVinci Resolve</td><td>Proyecto <b>Video Chat Distribuido</b> con la línea de tiempo completa armada (ver sección 5).</td></tr>
<tr><td><code>video/animaciones/</code></td><td>El código de las animaciones (HyperFrames). Si hay que cambiar un texto o un número, se cambia ahí y se vuelve a renderizar.</td></tr>
</table>

<h2><span class="n">3</span>El guion, escena por escena</h2>
<p>Lo que está en azul se dice tal cual (se puede decir con palabras propias, pero sin pasarse del tiempo).</p>
{''.join(bloque(e) for e in escenas)}

<h2><span class="n">4</span>Cómo grabar (celular sirve perfecto)</h2>
<div class="two">
<div class="card"><h4>Tomas a cámara</h4><ul>
<li>Celular <b>horizontal</b>, 1080p a 30 fps, a la altura de los ojos (sobre libros o trípode).</li>
<li>Luz de frente (ventana o lámpara detrás del celular), nunca la ventana detrás de uno.</li>
<li>Fondo ordenado. Plano medio: de la cintura o el pecho hacia arriba, con aire sobre la cabeza.</li>
<li>Mirar al lente, no a la pantalla. Grabar <b>3 tomas</b> y quedarse con la mejor.</li>
<li>Dejar 1 segundo quieto antes y después de hablar (facilita el corte).</li>
<li>El audio de la cara se usa tal cual: grabar en un cuarto sin eco y cerca del celular (1 m máximo).</li>
<li>S16 (cierre): ideal los cuatro juntos en cuadro, habla Camilo.</li>
</ul></div>
<div class="card"><h4>Voz en off</h4><ul>
<li>Cuarto pequeño y silencioso (un clóset con ropa es excelente contra el eco).</li>
<li>Celular con la app de grabadora, a un palmo de la boca, un poco de lado para no soplar.</li>
<li>Leer con calma, como explicándole a un compañero. Si se equivoca, pausa y repite la frase completa.</li>
<li>Un archivo por escena, nombrado así: <code>S05_Johen.m4a</code>, <code>S11_Daniel.m4a</code>…</li>
<li>Para la demo (S11) leer cada línea por separado; en Resolve se ubica cada una en su marcador.</li>
<li>Subir los archivos a una carpeta compartida y copiarlos a <code>video/grabaciones/</code>.</li>
</ul></div></div>

<h2><span class="n">5</span>Cómo se edita en DaVinci Resolve</h2>
<ol class="steps">
<li>Abrir DaVinci Resolve → abrir el proyecto <b>Video Chat Distribuido</b> Si no existe: menú <b>Workspace › Scripts › Utility › Armar_video_chat_distribuido</b> y se arma solo. Plan B: menú <b>File › Import › Timeline</b> y elegir <code>video/resolve/linea_de_tiempo.fcpxml</code> (sirve también en Premiere).</li>
<li>La línea de tiempo trae: <b>V1</b> escenas (azul = animación, naranja = cara pendiente, verde azulado = demo), <b>V2</b> rótulos,
<b>A1</b> voz guía, <b>A2</b> vacía para la voz real, <b>A3</b> vacía para música. Cada escena tiene un marcador amarillo con su texto.</li>
<li><b>Caras:</b> importar las tomas a la carpeta <i>04 Tomas reales</i>. Poner el cursor sobre la tarjeta naranja, seleccionar la toma en el Media Pool y
arrastrarla encima de la tarjeta soltándola en <b>Replace</b> (o seleccionar la tarjeta y la toma y pulsar <kbd>F11</kbd>). Si la toma dura más, alargar con la herramienta
<i>Trim</i> (<kbd>T</kbd>) y Resolve corre lo de después (modo <i>ripple</i>).</li>
<li><b>Voces en off:</b> importarlas a <i>05 Voz real</i> y arrastrar cada una a <b>A2</b>, alineada con el inicio de su voz guía en A1.
Cuando todas estén, silenciar A1 (botón <b>M</b> de la pista) o borrarla.</li>
<li><b>Ajustar tiempos:</b> si una voz real dura más que su animación, extender el final del clip de la animación (el último cuadro se queda quieto) o
recortar silencios de la voz. Nunca acelerar la voz.</li>
<li><b>Música:</b> una pista instrumental suave sin derechos (por ejemplo, Biblioteca de audio de YouTube, filtro «Sin atribución») en <b>A3</b>,
a unos <b>−22 dB</b> bajo la voz, con fundido al inicio y al final. Subirla en S01 y S17, donde no hay voz.</li>
<li><b>Transiciones:</b> las animaciones ya entran y salen con fundidos; entre cara y animación basta un corte directo o un <i>Cross Dissolve</i> de 10 cuadros.</li>
<li><b>Sonido parejo:</b> en la página <i>Fairlight</i>, seleccionar los clips de voz → clic derecho → <b>Normalize Audio Levels</b> a −16 LUFS (o pico −3 dBFS).</li>
<li><b>Exportar:</b> página <b>Deliver</b> → preset <b>YouTube 1080p</b> (H.264, MP4) → <i>Add to Render Queue</i> → <i>Render All</i>.</li>
</ol>
<div class="note"><b>¿Y After Effects?</b> Las animaciones están hechas con código (HyperFrames) porque así se cronometran exactas y se pueden revisar
cuadro por cuadro; el resultado son MP4 normales que se pueden abrir en After Effects o Premiere si alguien quiere retocar algo (por ejemplo,
agregar un brillo o un logo). Para cambiar un texto o un número es más fácil editar <code>video/animaciones/compositions/sXX.html</code> y volver a
renderizar con <code>npx hyperframes render</code>.</div>

<h2><span class="n">6</span>Lista final antes de entregar</h2>
<table>
<tr><th>Revisar</th><th>OK</th></tr>
<tr><td>Dura menos de 10 minutos (hoy: {mmss(total)} con la voz guía)</td><td>☐</td></tr>
<tr><td>Salimos los cuatro a cámara y cada uno explica su parte</td><td>☐</td></tr>
<tr><td>La demo muestra una falla y su recuperación (S11)</td><td>☐</td></tr>
<tr><td>Se entiende la pregunta, el método, los resultados con unidades y la conclusión</td><td>☐</td></tr>
<tr><td>Se menciona la interoperabilidad y los hallazgos</td><td>☐</td></tr>
<tr><td>La voz se escucha más fuerte que la música en todo el video</td><td>☐</td></tr>
<tr><td>No quedó ninguna tarjeta naranja ni la voz sintética</td><td>☐</td></tr>
<tr><td>Exportado en MP4 1080p y subido donde pidió el profesor</td><td>☐</td></tr>
</table>
</body></html>"""
(SRC / "guion_video.html").write_text(page, encoding="utf-8")
pdf = ROOT / "docs" / "Guion_video.pdf"
chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                (SRC / "guion_video.html").as_uri()], check=True, capture_output=True)
print(pdf)
