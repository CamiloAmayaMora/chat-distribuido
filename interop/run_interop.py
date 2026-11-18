#!/usr/bin/env python3
"""Ensayo de la sesión de interoperabilidad (sección 7 del enunciado).

Hace las dos pruebas mínimas de la sesión y deja el resultado en
interop/results/interop_report.md:
  1. Conversación global: cada grupo escribe y todos deben ver todo, en el mismo orden.
  2. Caída y recuperación por turnos: un grupo se apaga, los demás escriben,
     al volver debe tener lo perdido y sin duplicados.
Además prueba la robustez de NUESTRO servidor frente a mensajes "raros"
que podría reenviar el central desde otros grupos.

    docker compose -f interop/docker-compose.interop.yml up -d --build
    python interop/run_interop.py
"""
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPOSE = ["docker", "compose", "-f", str(HERE / "docker-compose.interop.yml")]
CENTRAL = "http://localhost:9100"
GROUPS = {   # nombre -> (url, tipo)
    "amaya": ("http://localhost:8101", "nuestro"),
    "amaya2": ("http://localhost:8102", "nuestro (copia)"),
    "ext1": ("http://localhost:8103", "ajeno correcto"),
    "ext2": ("http://localhost:8104", "ajeno con errores"),
}
report = []


def http(method, url, body=None, timeout=4):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def say(line=""):
    print(line, flush=True)
    report.append(line)


def write(group, user, body):
    url, kind = GROUPS[group]
    if kind.startswith("nuestro"):
        http("POST", f"{url}/api/users", {"name": user})
    st, m = http("POST", f"{url}/api/messages", {"user": user, "body": body})
    return m["id"] if st in (200, 201) else None


def listing(group, tag):
    st, msgs = http("GET", f"{GROUPS[group][0]}/api/messages?limit=5000")
    return [m for m in msgs if tag in m["body"]] if st == 200 else None


def wait_up(group, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if http("GET", f"{GROUPS[group][0]}/fed/health", timeout=1)[0] == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def central_order(tag):
    msgs = http("GET", f"{CENTRAL}/history?since=0")[1]
    return [m["id"] for m in msgs if tag in m["body"]]


def main():
    say(f"# Ensayo de interoperabilidad — {datetime.now():%Y-%m-%d %H:%M}")
    say()
    say("Grupos: " + ", ".join(f"`{g}` ({k})" for g, (_, k) in GROUPS.items()))
    say()

    # ------------------------------------------------------------- registro
    time.sleep(3)
    reg = http("GET", f"{CENTRAL}/servers")[1]
    say("## 0. Registro en el central")
    say()
    for g in GROUPS:
        say(f"* `{g}`: {'✅ registrado' if g in reg else '❌ no registrado'}")
    say()

    # ------------------------------------------------- conversación global
    tag = f"[global-{uuid.uuid4().hex[:4]}]"
    say("## 1. Conversación global")
    say()
    sent = {}
    for rnd in range(2):
        for g in GROUPS:
            sent[write(g, "user" + g, f"{tag} hola desde {g} ({rnd + 1})")] = g
            time.sleep(0.3)
    time.sleep(6)
    ref = central_order(tag)
    say(f"Mensajes escritos: {len(sent)} (2 por grupo). Orden de referencia: historial del central ordenado por (lamport, origin).")
    say()
    say("| Grupo | Ve todos | Faltan | Duplicados | Mismo orden que el central |")
    say("|---|---|---|---|---|")
    for g in GROUPS:
        lst = listing(g, tag)
        ids = [m["id"] for m in lst]
        missing = len(set(sent) - set(ids))
        dups = sum(c - 1 for c in Counter(ids).values())
        same = [i for i in ids if i in ref] == [i for i in ref if i in ids]
        say(f"| `{g}` | {'✅' if missing == 0 else '❌'} | {missing} | {dups} | {'✅' if same else '❌ (ordena distinto)'} |")
    say()

    # --------------------------------------------- caída y recuperación
    say("## 2. Caída y recuperación por turnos")
    say()
    say("Cada grupo se apaga con `docker kill`; los otros tres escriben 3 mensajes cada uno; queda caído ≈ 8 s en total; se levanta y se esperan 8 s.")
    say()
    say("| Grupo caído | Escritos durante la caída | Recuperados | Faltan | Duplicados en pantalla | Conserva el historial anterior (8 msgs) |")
    say("|---|---|---|---|---|---|")
    for down in GROUPS:
        tag2 = f"[caida-{down}-{uuid.uuid4().hex[:4]}]"
        subprocess.run(COMPOSE + ["kill", down], capture_output=True)
        time.sleep(1)
        written = []
        for i in range(3):
            for g in GROUPS:
                if g != down:
                    written.append(write(g, "user" + g, f"{tag2} mientras {down} está caído #{i}"))
        time.sleep(6)
        subprocess.run(COMPOSE + ["start", down], capture_output=True)
        wait_up(down)
        time.sleep(8)
        lst = listing(down, tag2) or []
        ids = [m["id"] for m in lst]
        missing = len(set(written) - set(ids))
        dups = sum(c - 1 for c in Counter(ids).values())
        prev = len({m["id"] for m in (listing(down, tag) or [])})
        say(f"| `{down}` | {len(written)} | {len(set(written) & set(ids))} | {missing} | {dups} | {'✅' if prev == 8 else f'❌ ({prev}/8)'} |")
    say()

    # --------------------------------- robustez de nuestro servidor
    say("## 3. Robustez de nuestro servidor ante mensajes de otros grupos")
    say()
    say("Se envían directamente a `amaya` `POST /fed/messages` como si el central los reenviara.")
    say()
    url = GROUPS["amaya"][0]
    base = lambda **kw: {"id": str(uuid.uuid4()), "from": "x@ext9", "origin": "ext9", "lamport": 5,
                         "sent_at": "2026-11-10T14:03:22Z", "body": "prueba", **kw}
    cases = [
        ("lamport como texto (\"42\")", base(lamport="42")),
        ("sent_at en otro formato (\"10/11/2026 14:03\")", base(sent_at="10/11/2026 14:03")),
        ("sin sent_at", {k: v for k, v in base().items() if k != "sent_at"}),
        ("campos desconocidos (room, prioridad)", base(room="#general", prioridad="alta")),
        ("falta el campo from", {k: v for k, v in base().items() if k != "from"}),
        ("lamport negativo", base(lamport=-3)),
        ("lamport no numérico (\"abc\")", base(lamport="abc")),
        ("cuerpo que no es JSON válido", None),
    ]
    say("| Caso | Respuesta de `amaya` | Interpretación |")
    say("|---|---|---|")
    for name, body in cases:
        if body is None:
            req = urllib.request.Request(f"{url}/fed/messages", data=b"{no es json", method="POST",
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=3) as r:
                    st = r.status
            except urllib.error.HTTPError as e:
                st = e.code
        else:
            st, _ = http("POST", f"{url}/fed/messages", body)
        meaning = "aceptado (tolerante)" if st == 200 else ("rechazado con 4xx: el central no reintenta" if 400 <= st < 500 else "⚠ 5xx")
        say(f"| {name} | {st} | {meaning} |")
    say()

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "interop_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    logs = subprocess.run(COMPOSE + ["logs", "--no-log-prefix", "--no-color"], capture_output=True, text=True).stdout
    (out / "interop_logs.txt").write_text(logs, encoding="utf-8")
    print(f"\nInforme: {out / 'interop_report.md'}")


if __name__ == "__main__":
    main()
