"""Registro de eventos (requisito 11).

Cada evento se escribe dos veces:
  * en la salida estándar, en una línea legible (lo que se ve con `docker compose logs`);
  * en un archivo JSON Lines dentro del volumen, que usan el experimento y la demo.

Formato legible:
  2026-11-17T14:03:22.120Z g3 SENT      id=6f1c2a9e lamport=42 status=200
"""
import json
import logging
import threading
from datetime import datetime, timezone

from . import config

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(message)s",
)
_log = logging.getLogger("chat")
logging.getLogger("httpx").setLevel(logging.WARNING)  # sin ruido de cada petición HTTP
_lock = threading.Lock()

# Contadores en memoria para /api/status (se reinician con el proceso).
counters = {
    "sent": 0,          # mensajes aceptados por el central (2xx)
    "retry": 0,         # reintentos programados
    "rejected": 0,      # 4xx: no se reintentan
    "received": 0,      # mensajes nuevos recibidos del central
    "duplicate": 0,     # mensajes descartados por id repetido
    "recovered": 0,     # mensajes nuevos obtenidos vía /history
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def event(kind: str, **fields) -> None:
    """Registra un evento. `kind` en mayúsculas: SENT, RETRY, RECEIVED, DUPLICATE..."""
    ts = now_iso()
    key = kind.lower()
    if key in counters:
        counters[key] += 1

    short = dict(fields)
    if "id" in short and isinstance(short["id"], str):
        short["id"] = short["id"][:8]  # el id completo va al JSON; en consola basta el prefijo
    pretty = " ".join(f"{k}={v}" for k, v in short.items())
    _log.info(f"{ts} {config.GROUP_NAME} {kind:<14} {pretty}")

    record = {"ts": ts, "server": config.GROUP_NAME, "event": kind, **fields}
    try:
        with _lock, open(config.EVENTS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass  # el log en archivo es de apoyo; nunca debe tumbar el servidor
