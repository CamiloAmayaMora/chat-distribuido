"""Comunicación con el servidor central.

Aquí viven las cuatro tareas de fondo del servidor de grupo:

  * register_loop   – POST /register al arrancar y cada REGISTER_INTERVAL s (req. 4)
  * heartbeat_loop  – GET /health; tras N fallos seguidos marca el central como
                      caído y, cuando vuelve, recupera historial y vacía el outbox (req. 8 y 9)
  * outbox_loop     – entrega los mensajes locales con reintentos y backoff
                      exponencial: entrega al menos una vez (req. 5 y 6)
  * sync_loop       – (opcional) anti-entropía / modo pull con GET /history

Regla de reintentos del protocolo:
  2xx            -> entregado, se borra del outbox
  4xx            -> error del cliente: NO se reintenta, se registra en el log
  5xx / timeout  -> se reintenta con espera base * 2^intentos (con tope y jitter)
"""
import asyncio
import json
import random

import httpx

from . import config, db
from .events import event, now_iso


class CentralState:
    """Estado del detector de fallos (compartido por las tareas)."""

    def __init__(self) -> None:
        self.up = True                 # optimista al arrancar
        self.consecutive_failures = 0
        self.registered = False
        self.last_health_ok: str | None = None
        self.recovering = asyncio.Lock()


central = CentralState()
_client: httpx.AsyncClient | None = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=config.HTTP_TIMEOUT)
    return _client


def backoff(attempts: int) -> float:
    """Espera exponencial: 1, 2, 4, 8, 16, 30, 30... s (+-20 % de jitter para no
    sincronizar los reintentos de todos los servidores)."""
    delay = min(config.RETRY_MAX, config.RETRY_BASE * (2 ** attempts))
    return delay * random.uniform(0.8, 1.2)


# --------------------------------------------------------------------------
# Registro
# --------------------------------------------------------------------------
async def register_once() -> bool:
    payload = {"server": config.GROUP_NAME, "url": config.PUBLIC_URL}
    try:
        r = await client().post(f"{config.CENTRAL_URL}/register", json=payload)
    except httpx.HTTPError as e:
        event("REGISTER_FAIL", error=type(e).__name__)
        return False
    if 200 <= r.status_code < 300:
        if not central.registered:
            event("REGISTERED", url=config.PUBLIC_URL, status=r.status_code)
        central.registered = True
        return True
    event("REGISTER_FAIL", status=r.status_code, detail=r.text[:200])
    return False


async def register_loop() -> None:
    attempts = 0
    while True:
        ok = await register_once()
        if ok:
            attempts = 0
            await asyncio.sleep(config.REGISTER_INTERVAL)
        else:
            central.registered = False
            await asyncio.sleep(backoff(attempts))
            attempts += 1


# --------------------------------------------------------------------------
# Recuperación de historial
# --------------------------------------------------------------------------
def _extract_messages(data) -> list[dict]:
    """El protocolo devuelve una lista de mensajes; aceptamos también
    {"messages": [...]} para ser tolerantes con variaciones de la especificación."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("messages", "items", "history"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def _valid(msg: dict) -> bool:
    return all(k in msg for k in ("id", "from", "origin", "lamport", "body"))


async def recover_history(reason: str) -> int:
    """GET /history?since=X y guarda lo que falte. Devuelve cuántos eran nuevos."""
    if not config.HISTORY_RECOVERY:
        return 0
    async with central.recovering:            # nunca dos recuperaciones a la vez
        if config.HISTORY_OVERLAP < 0:
            since = 0
        else:
            since = max(0, db.max_remote_lamport() - config.HISTORY_OVERLAP)
        event("HISTORY_REQUEST", since=since, reason=reason)
        try:
            r = await client().get(f"{config.CENTRAL_URL}/history", params={"since": since})
        except httpx.HTTPError as e:
            event("HISTORY_FAIL", error=type(e).__name__)
            return 0
        if r.status_code != 200:
            event("HISTORY_FAIL", status=r.status_code)
            return 0
        new = dup = 0
        for msg in _extract_messages(r.json()):
            if not isinstance(msg, dict) or not _valid(msg):
                continue
            created, local = db.store_remote_message(msg, via="history")
            if created:
                new += 1
                event("RECOVERED", id=msg["id"], lamport=msg["lamport"], origin=msg["origin"], clock=local)
            else:
                dup += 1
        event("HISTORY_DONE", since=since, new=new, already_had=dup)
        return new


# --------------------------------------------------------------------------
# Detector de fallos por heartbeat
# --------------------------------------------------------------------------
async def heartbeat_loop() -> None:
    while True:
        ok = False
        try:
            r = await client().get(f"{config.CENTRAL_URL}/health")
            ok = r.status_code == 200
        except httpx.HTTPError:
            ok = False

        if ok:
            had_failures = central.consecutive_failures > 0
            central.consecutive_failures = 0
            central.last_health_ok = now_iso()
            if not central.up:
                central.up = True
                event("CENTRAL_UP")
                # Al volver: renovamos registro, pedimos lo perdido y liberamos el outbox.
                await register_once()
                await recover_history("central_back")
                n = db.outbox_release_all()
                event("OUTBOX_FLUSH", pending=n)
            elif had_failures:
                # Fallo breve (por debajo del umbral): el central pudo reiniciarse y
                # olvidar nuestro registro, o reenviarnos algo que no recibimos.
                # Por si acaso: re-registro y recuperación (la deduplicación lo hace seguro).
                event("CENTRAL_BLIP")
                await register_once()
                await recover_history("central_blip")
        else:
            central.consecutive_failures += 1
            event("HEARTBEAT_FAIL", failures=central.consecutive_failures,
                  limit=config.HEARTBEAT_MAX_FAILURES)
            if central.up and central.consecutive_failures >= config.HEARTBEAT_MAX_FAILURES:
                central.up = False
                event("CENTRAL_DOWN", pending=db.outbox_size())
        await asyncio.sleep(config.HEARTBEAT_INTERVAL)


# --------------------------------------------------------------------------
# Entrega al menos una vez
# --------------------------------------------------------------------------
async def deliver(row) -> None:
    msg = json.loads(row["payload"])
    attempts = row["attempts"]
    try:
        r = await client().post(f"{config.CENTRAL_URL}/messages", json=msg)
        status = r.status_code
    except httpx.HTTPError as e:
        status = None
        error = type(e).__name__

    if status is not None and 200 <= status < 300:
        db.outbox_done(msg["id"])
        event("SENT", id=msg["id"], lamport=msg["lamport"], status=status, attempt=attempts + 1)
    elif status is not None and 400 <= status < 500:
        db.outbox_done(msg["id"])     # 4xx: no tiene sentido reintentar el mismo cuerpo
        event("REJECTED", id=msg["id"], lamport=msg["lamport"], status=status, detail=r.text[:200])
    else:
        delay = backoff(attempts)
        db.outbox_reschedule(msg["id"], attempts + 1, delay)
        event("RETRY", id=msg["id"], lamport=msg["lamport"],
              status=status if status is not None else error,
              attempt=attempts + 1, wait=f"{delay:.1f}s")


async def outbox_loop() -> None:
    while True:
        if central.up:
            rows = db.due_outbox()
            for row in rows:
                if not central.up:
                    break               # si el central cae a mitad, guardamos el resto
                await deliver(row)
        # Si el central está caído no enviamos: los mensajes quedan guardados en
        # el outbox (SQLite) y se liberan cuando el heartbeat detecta que volvió.
        await asyncio.sleep(0.2)


async def sync_loop() -> None:
    """Anti-entropía periódica. También sirve de 'modo pull' si el central no
    puede hacernos POST /fed/messages por restricciones de red."""
    if config.SYNC_POLL_INTERVAL <= 0:
        return
    while True:
        await asyncio.sleep(config.SYNC_POLL_INTERVAL)
        if central.up:
            await recover_history("periodic_sync")


async def startup_sequence() -> None:
    """Al arrancar: registrarse y recuperar lo que se perdió mientras estábamos fuera."""
    await register_once()
    await recover_history("startup")
