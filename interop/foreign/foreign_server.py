"""Implementación AJENA del servidor de grupo (para el ensayo de interoperabilidad).

Está escrita a propósito de forma distinta a la nuestra (solo biblioteca
estándar, memoria en RAM, sin FastAPI) para simular el servidor de OTRO grupo
que no controlamos.

Con BUGGY=1 reproduce errores típicos que podría tener otro grupo:
  * envía "lamport" como texto ("42") y "sent_at" con otro formato
  * no deduplica: si le llega dos veces el mismo id, lo muestra dos veces
  * ordena por orden de llegada (no por lamport, origin)
  * no recupera historial al arrancar
  * responde 500 en 1 de cada 5 POST /fed/messages
"""
import json
import os
import random
import threading
import time
import urllib.request
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

NAME = os.environ["GROUP_NAME"]
PUBLIC_URL = os.environ["PUBLIC_URL"]
CENTRAL = os.environ["CENTRAL_URL"].rstrip("/")
BUGGY = os.getenv("BUGGY", "0") == "1"

lock = threading.Lock()
clock = 0
messages = []          # lista en memoria (se pierde al reiniciar: otra limitación)
seen = set()
outbox = []


def log(*a):
    print(datetime.now().strftime("%H:%M:%S.%f")[:-3], NAME, *a, flush=True)


def post(url, data):
    req = urllib.request.Request(url, json.dumps(data).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as r:
        return r.status


def get(url):
    with urllib.request.urlopen(url, timeout=3) as r:
        return json.loads(r.read().decode())


def store(m):
    global clock
    with lock:
        if not BUGGY and m["id"] in seen:
            return False
        seen.add(m["id"])
        clock = max(clock, int(m["lamport"])) + 1
        messages.append(m)
        return True


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/fed/health"):
            return self.reply(200, {"server": NAME, "lamport": clock})
        if self.path.startswith("/api/messages"):
            msgs = list(messages) if BUGGY else sorted(messages, key=lambda m: (int(m["lamport"]), m["origin"], m["id"]))
            return self.reply(200, msgs)
        self.reply(404, {"error": "no existe"})

    def do_POST(self):
        global clock
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/fed/messages":
            if BUGGY and random.random() < 0.2:
                log("500 simulado", data.get("id", "")[:8])
                return self.reply(500, {"error": "fallo interno"})
            new = store(data)
            log("RECIBIDO" if new else "DUPLICADO", data["id"][:8], "L", data["lamport"])
            return self.reply(200, {"ok": True})
        if self.path == "/api/messages":       # API de cliente de este "grupo"
            with lock:
                clock += 1
                m = {"id": str(uuid.uuid4()), "from": f"{data['user']}@{NAME}", "origin": NAME,
                     "lamport": str(clock) if BUGGY else clock,
                     "sent_at": datetime.now().strftime("%d/%m/%Y %H:%M") if BUGGY else datetime.utcnow().isoformat() + "Z",
                     "body": data["body"]}
                seen.add(m["id"])
                messages.append(m)
                outbox.append(m)
            return self.reply(201, m)
        self.reply(404, {"error": "no existe"})


def background():
    last_reg = 0
    while True:
        if time.time() - last_reg > 10:
            try:
                post(f"{CENTRAL}/register", {"server": NAME, "url": PUBLIC_URL})
                last_reg = time.time()
            except Exception as e:
                log("registro falló", e)
        with lock:
            pending = list(outbox)
        for m in pending:
            try:
                post(f"{CENTRAL}/messages", m)
                with lock:
                    outbox.remove(m)
                log("ENVIADO", m["id"][:8])
            except Exception as e:
                log("reintento", m["id"][:8], e)
        time.sleep(0.5)


if __name__ == "__main__":
    if not BUGGY:                                  # la versión correcta sí recupera historial
        time.sleep(1)
        try:
            for m in get(f"{CENTRAL}/history?since=0"):
                store(m)
        except Exception as e:
            log("history falló", e)
    threading.Thread(target=background, daemon=True).start()
    log("escuchando en :8000", "(BUGGY)" if BUGGY else "")
    ThreadingHTTPServer(("0.0.0.0", 8000), H).serve_forever()
