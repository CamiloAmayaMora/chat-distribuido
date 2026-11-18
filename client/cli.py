#!/usr/bin/env python3
"""Cliente de consola para el chat distribuido (solo biblioteca estándar).

Habla ÚNICAMENTE con el servidor de su propio grupo (API de cliente libre).

    python client/cli.py --server http://localhost:8001 --user ana

Escribe un mensaje y Enter para enviarlo a #general.
Comandos:  /status   estado del servidor (central, reloj, pendientes)
           /quit     salir
Los mensajes de otros grupos se muestran con un color distinto por servidor.
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

COLORS = [31, 32, 33, 34, 35, 36, 91, 92, 93, 94, 95, 96]
if os.name == "nt":
    os.system("")  # habilita colores ANSI en la consola de Windows


def call(base: str, path: str, data: dict | None = None):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json"},
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())


def color_for(origin: str) -> int:
    return COLORS[sum(map(ord, origin)) % len(COLORS)]


def fmt(m: dict, my_server: str) -> str:
    if m["origin"] == my_server:
        who = f"\033[1m{m['from']}\033[0m"
    else:
        c = color_for(m["origin"])
        who = f"\033[1;{c}m{m['from']}\033[0m \033[{c}m[{m['origin']}]\033[0m"
    return f"\033[2mL{m['lamport']:>5}\033[0m  {who}: {m['body']}"


def poller(base: str, my_server: str, seen: set, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            for m in call(base, "/api/messages?limit=200"):
                if m["id"] not in seen:
                    seen.add(m["id"])
                    print("\r" + fmt(m, my_server) + "\n> ", end="", flush=True)
        except (urllib.error.URLError, OSError):
            print("\r\033[31m(servidor local no responde)\033[0m\n> ", end="", flush=True)
        stop.wait(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Cliente de consola del chat distribuido")
    ap.add_argument("--server", default=os.getenv("CHAT_SERVER", "http://localhost:8000"))
    ap.add_argument("--user", required=True, help="nombre local, sin @gN")
    args = ap.parse_args()
    base = args.server.rstrip("/")

    me = call(base, "/api/users", {"name": args.user})["user"]
    status = call(base, "/api/status")
    my_server = status["server"]
    print(f"Conectado a {base} como \033[1m{me}\033[0m (servidor {my_server}). /quit para salir.\n")

    seen: set = set()
    stop = threading.Event()
    threading.Thread(target=poller, args=(base, my_server, seen, stop), daemon=True).start()
    time.sleep(0.3)
    try:
        while True:
            line = input("> ").strip()
            if not line:
                continue
            if line == "/quit":
                break
            if line == "/status":
                st = call(base, "/api/status")
                print(json.dumps(st, indent=2, ensure_ascii=False))
                continue
            try:
                call(base, "/api/messages", {"user": me, "body": line})
            except urllib.error.HTTPError as e:
                print(f"\033[31mError {e.code}: {e.read().decode()}\033[0m")
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        stop.set()
        print("\nAdiós.")


if __name__ == "__main__":
    sys.exit(main())
