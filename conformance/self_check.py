#!/usr/bin/env python3
"""Pruebas de conformidad PROPIAS del servidor de grupo.

El script oficial del profesor es el que cuenta para la nota; este lo
complementa y nos deja verificar el mínimo común en local, antes de la sesión.
Hace de "servidor central" contra la API /fed/* y revisa además el
comportamiento de extremo a extremo usando el central simulado.

    python conformance/self_check.py --server http://localhost:8001 \
        --peer http://localhost:8002 --central http://localhost:9000 \
        --restart "docker compose -f docker-compose.lab.yml restart ga"
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

results: list[tuple[str, bool, str]] = []


def http(method: str, url: str, body=None, timeout=5):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw


def check(name: str, cond: bool, detail: str = "") -> bool:
    results.append((name, bool(cond), detail))
    mark = "\033[32mPASA\033[0m" if cond else "\033[31mFALLA\033[0m"
    print(f"  [{mark}] {name}" + (f"  — {detail}" if detail else ""))
    return cond


def wait_until(fn, timeout=15.0, step=0.3):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if fn():
                return True
        except Exception:
            pass
        time.sleep(step)
    return False


def msg(origin="gtest", lamport=1, body="hola", **extra):
    m = {"id": str(uuid.uuid4()), "from": f"tester@{origin}", "origin": origin,
         "lamport": lamport, "sent_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
         "body": body}
    m.update(extra)
    return m


def messages(server):
    return http("GET", f"{server}/api/messages?limit=5000")[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True, help="servidor de grupo bajo prueba")
    ap.add_argument("--peer", help="otro servidor de grupo conectado al mismo central")
    ap.add_argument("--central", help="URL del central (simulado) para pruebas de extremo a extremo")
    ap.add_argument("--restart", help="comando que reinicia el servidor bajo prueba (persistencia)")
    a = ap.parse_args()
    S = a.server.rstrip("/")

    print(f"\n== Conformidad del servidor {S} ==  {datetime.now().isoformat(timespec='seconds')}\n")

    print("Federación (API fija del protocolo)")
    st, h = http("GET", f"{S}/fed/health")
    check("GET /fed/health responde 200", st == 200, f"status={st}")
    check("/fed/health trae nombre del servidor y reloj de Lamport",
          isinstance(h, dict) and "server" in h and isinstance(h.get("lamport"), int), json.dumps(h))
    me = h["server"]

    clock0 = h["lamport"]
    m1 = msg(lamport=clock0 + 50, body="prueba de recepción")
    st, _ = http("POST", f"{S}/fed/messages", m1)
    check("POST /fed/messages con mensaje nuevo responde 2xx", 200 <= st < 300, f"status={st}")
    ids = [x["id"] for x in messages(S)]
    check("El mensaje recibido aparece en el historial", m1["id"] in ids)

    clock1 = http("GET", f"{S}/fed/health")[1]["lamport"]
    check("Regla de Lamport al recibir: reloj = max(local, recibido) + 1",
          clock1 == max(clock0, m1["lamport"]) + 1, f"antes={clock0} recibido={m1['lamport']} ahora={clock1}")

    st, _ = http("POST", f"{S}/fed/messages", m1)
    n = sum(1 for x in messages(S) if x["id"] == m1["id"])
    check("Reenviar el mismo id responde 200 (idempotente)", st == 200, f"status={st}")
    check("Reenviar el mismo id NO duplica el mensaje", n == 1, f"apariciones={n}")
    clock2 = http("GET", f"{S}/fed/health")[1]["lamport"]
    check("Un duplicado no altera el reloj", clock2 == clock1, f"{clock1} -> {clock2}")

    m2 = msg(lamport=1, body="campos extra", prioridad="alta", meta={"x": 1})
    st, _ = http("POST", f"{S}/fed/messages", m2)
    check("Campos desconocidos se ignoran sin error", 200 <= st < 300, f"status={st}")

    st, _ = http("POST", f"{S}/fed/messages", {"id": str(uuid.uuid4()), "body": "sin campos"})
    check("Cuerpo inválido responde 4xx (no 5xx, para no provocar reintentos)", 400 <= st < 500, f"status={st}")

    # Orden (lamport, origin): dos mensajes con el mismo lamport y distinto origen
    L = clock2 + 10
    mb, ma = msg(origin="gzz", lamport=L, body="orden b"), msg(origin="gaa", lamport=L, body="orden a")
    http("POST", f"{S}/fed/messages", mb)
    http("POST", f"{S}/fed/messages", ma)
    hist = messages(S)
    keys = [(x["lamport"], x["origin"]) for x in hist]
    check("Historial ordenado por (lamport, origin)", keys == sorted(keys))
    pos = {x["id"]: i for i, x in enumerate(hist)}
    check("Empate de lamport se resuelve por origin", pos[ma["id"]] < pos[mb["id"]])

    print("\nUsuarios y envío")
    user = "conf" + uuid.uuid4().hex[:5]
    st, u = http("POST", f"{S}/api/users", {"name": user})
    check("Crear usuario local", st in (200, 201) and u["user"] == f"{user}@{me}", json.dumps(u))
    c_before = http("GET", f"{S}/fed/health")[1]["lamport"]
    st, sent = http("POST", f"{S}/api/messages", {"user": user, "body": "hola #general"})
    check("Enviar mensaje local", st in (200, 201), f"status={st}")
    check("Regla de Lamport al enviar: incrementa antes de enviar", sent["lamport"] == c_before + 1,
          f"reloj={c_before} mensaje={sent['lamport']}")
    try:
        uuid.UUID(sent["id"])
        ok = True
    except ValueError:
        ok = False
    check("El id del mensaje es un UUID", ok, sent["id"])
    check("Formato: from=usuario@gN y origin=gN", sent["from"] == f"{user}@{me}" and sent["origin"] == me)

    if a.central:
        C = a.central.rstrip("/")
        print("\nExtremo a extremo con el central")
        check("El servidor se registró en el central",
              wait_until(lambda: me in http("GET", f"{C}/servers")[1]), "GET /servers del simulador")
        check("El mensaje local llegó al central con el mismo id",
              wait_until(lambda: any(x["id"] == sent["id"] for x in http("GET", f"{C}/history?since=0")[1])))
        if a.peer:
            P = a.peer.rstrip("/")
            check("El central lo reenvió al otro servidor (mismo id)",
                  wait_until(lambda: any(x["id"] == sent["id"] for x in messages(P))))

    if a.restart:
        print("\nPersistencia")
        before = len(messages(S))
        clock_b = http("GET", f"{S}/fed/health")[1]["lamport"]
        subprocess.run(a.restart, shell=True, check=False, capture_output=True)
        up = wait_until(lambda: http("GET", f"{S}/fed/health", timeout=2)[0] == 200, timeout=40)
        check("El servidor vuelve tras el reinicio", up)
        after = messages(S)
        check("El historial sobrevive al reinicio", len(after) >= before, f"antes={before} después={len(after)}")
        check("Los usuarios sobreviven al reinicio",
              f"{user}@{me}" in http("GET", f"{S}/api/users")[1])
        check("El reloj de Lamport no retrocede tras el reinicio",
              http("GET", f"{S}/fed/health")[1]["lamport"] >= clock_b)

    passed = sum(ok for _, ok, _ in results)
    print(f"\nResultado: {passed}/{len(results)} pruebas pasan\n")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
