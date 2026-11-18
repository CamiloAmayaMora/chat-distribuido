"""Servidor central de PRUEBA (simulador del servidor del profesor).

NO es parte de la entrega obligatoria: lo usamos para probar nuestro servidor
de grupo sin depender del servidor real del curso (recomendación de la
sección 10: "levanten dos servidores en su propia máquina").

Implementa el resumen del protocolo (sección 4 del enunciado):
    POST /register                  {"server": "g3", "url": "http://..."}
    POST /messages                  guarda (dedup por id) y reenvía a todos menos al origen
    GET  /history?since={lamport}   mensajes con lamport > since, ordenados por (lamport, origin)
    GET  /health

Además permite inyectar fallos para probar la entrega al menos una vez:
    CHAOS_FAIL_RATE           prob. de responder 503 SIN guardar (el mensaje "se pierde")
    CHAOS_DROP_RESPONSE_RATE  prob. de guardar y responder 503 (se pierde la respuesta)
    CHAOS_DUP_FORWARD_RATE    prob. de reenviar dos veces el mismo mensaje
"""
import asyncio
import os
import random
import time
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

FORWARD_RETRIES = int(os.getenv("FORWARD_RETRIES", "3"))
REGISTRATION_TTL = float(os.getenv("REGISTRATION_TTL", "120"))
CHAOS_FAIL_RATE = float(os.getenv("CHAOS_FAIL_RATE", "0"))
CHAOS_DROP_RESPONSE_RATE = float(os.getenv("CHAOS_DROP_RESPONSE_RATE", "0"))
CHAOS_DUP_FORWARD_RATE = float(os.getenv("CHAOS_DUP_FORWARD_RATE", "0"))

app = FastAPI(title="Servidor central (simulador)")
servers: dict[str, dict] = {}       # nombre -> {"url": ..., "last_seen": epoch}
history: dict[str, dict] = {}       # id -> mensaje
lamport = 0
client = httpx.AsyncClient(timeout=3)


def log(kind: str, **kw) -> None:
    ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    print(f"{ts} central {kind:<14} " + " ".join(f"{k}={v}" for k, v in kw.items()), flush=True)


@app.get("/health")
def health():
    return {"status": "ok", "server": "central", "lamport": lamport,
            "servers": len(servers), "messages": len(history)}


@app.post("/register")
async def register(req: Request):
    data = await req.json()
    name, url = data.get("server"), data.get("url")
    if not name or not url:
        return JSONResponse({"error": "server y url son obligatorios"}, status_code=400)
    is_new = name not in servers
    servers[name] = {"url": url.rstrip("/"), "last_seen": time.time()}
    if is_new:
        log("REGISTER", server=name, url=url)
    return {"status": "registered", "server": name, "ttl": REGISTRATION_TTL}


@app.get("/servers")
def list_servers():
    return {n: {"url": s["url"], "age_s": round(time.time() - s["last_seen"], 1)} for n, s in servers.items()}


@app.post("/messages")
async def messages(req: Request):
    global lamport
    msg = await req.json()
    for k in ("id", "from", "origin", "lamport", "body"):
        if k not in msg:
            return JSONResponse({"error": f"falta el campo {k}"}, status_code=400)

    if random.random() < CHAOS_FAIL_RATE:
        log("CHAOS_FAIL", id=msg["id"][:8])
        return JSONResponse({"error": "chaos"}, status_code=503)

    if msg["id"] in history:
        log("DUPLICATE", id=msg["id"][:8], origin=msg["origin"])
        return {"status": "duplicate", "id": msg["id"]}

    lamport = max(lamport, int(msg["lamport"])) + 1
    history[msg["id"]] = msg
    log("STORED", id=msg["id"][:8], origin=msg["origin"], lamport=msg["lamport"])

    times = 2 if random.random() < CHAOS_DUP_FORWARD_RATE else 1
    for _ in range(times):
        asyncio.create_task(fan_out(msg))

    if random.random() < CHAOS_DROP_RESPONSE_RATE:
        log("CHAOS_DROP_RESP", id=msg["id"][:8])
        return JSONResponse({"error": "chaos (respuesta perdida)"}, status_code=503)
    return {"status": "stored", "id": msg["id"]}


async def fan_out(msg: dict) -> None:
    now = time.time()
    for name, s in list(servers.items()):
        if name == msg["origin"]:
            continue                                   # todos menos el de origen
        if now - s["last_seen"] > REGISTRATION_TTL:
            continue                                   # registro vencido
        asyncio.create_task(forward(name, s["url"], msg))


async def forward(name: str, url: str, msg: dict) -> None:
    for attempt in range(FORWARD_RETRIES):
        try:
            r = await client.post(f"{url}/fed/messages", json=msg)
            if r.status_code < 500:
                log("FORWARDED", id=msg["id"][:8], to=name, status=r.status_code)
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.5 * 2 ** attempt)
    log("FORWARD_GIVEUP", id=msg["id"][:8], to=name)  # el grupo lo recupera con /history


@app.get("/history")
def get_history(since: int = 0):
    msgs = [m for m in history.values() if int(m["lamport"]) > since]
    msgs.sort(key=lambda m: (int(m["lamport"]), m["origin"], m["id"]))
    return msgs
