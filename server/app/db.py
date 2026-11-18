"""Persistencia en SQLite (requisito 2) y reloj de Lamport (requisito 7).

El archivo vive en un volumen de Docker (/data), así que usuarios, historial,
mensajes pendientes y el valor del reloj sobreviven a `docker compose restart`.

Todas las operaciones pasan por un único candado: el reloj de Lamport y la
inserción del mensaje deben ocurrir de forma atómica, si no dos peticiones
concurrentes podrían leer el mismo valor del reloj.
"""
import json
import os
import sqlite3
import threading
import time
import uuid

from . import config
from .events import now_iso

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    name        TEXT PRIMARY KEY,           -- nombre local, sin @gN
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id          TEXT PRIMARY KEY,           -- UUID: clave de deduplicación
    sender      TEXT NOT NULL,              -- campo "from" (ana@g3)
    origin      TEXT NOT NULL,              -- servidor de origen (g3)
    lamport     INTEGER NOT NULL,
    sent_at     TEXT,
    body        TEXT NOT NULL,
    received_at TEXT NOT NULL,              -- reloj físico local, solo informativo
    via         TEXT NOT NULL               -- local | push | history
);
CREATE INDEX IF NOT EXISTS idx_messages_order ON messages (lamport, origin, id);

CREATE TABLE IF NOT EXISTS outbox (
    id              TEXT PRIMARY KEY,       -- mismo id del mensaje
    payload         TEXT NOT NULL,          -- JSON exacto que se envía (nunca cambia)
    attempts        INTEGER NOT NULL DEFAULT 0,
    next_attempt_at REAL NOT NULL           -- epoch en segundos
);

CREATE TABLE IF NOT EXISTS state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def init() -> None:
    global _conn
    os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
    _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False, isolation_level=None)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA journal_mode=WAL")    # escrituras seguras ante caídas
    _conn.execute("PRAGMA synchronous=NORMAL")
    _conn.executescript(SCHEMA)


# --------------------------------------------------------------------------
# Reloj de Lamport
# --------------------------------------------------------------------------
def _get_clock() -> int:
    row = _conn.execute("SELECT value FROM state WHERE key='lamport'").fetchone()
    return int(row["value"]) if row else 0


def _set_clock(value: int) -> None:
    _conn.execute(
        "INSERT INTO state(key, value) VALUES('lamport', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(value),),
    )


def clock() -> int:
    with _lock:
        return _get_clock()


# --------------------------------------------------------------------------
# Usuarios
# --------------------------------------------------------------------------
def create_user(name: str) -> bool:
    """Devuelve True si se creó, False si ya existía (operación idempotente)."""
    with _lock:
        cur = _conn.execute(
            "INSERT OR IGNORE INTO users(name, created_at) VALUES(?, ?)", (name, now_iso())
        )
        return cur.rowcount == 1


def user_exists(name: str) -> bool:
    with _lock:
        return _conn.execute("SELECT 1 FROM users WHERE name=?", (name,)).fetchone() is not None


def list_users() -> list[str]:
    with _lock:
        return [r["name"] for r in _conn.execute("SELECT name FROM users ORDER BY name")]


# --------------------------------------------------------------------------
# Mensajes
# --------------------------------------------------------------------------
def create_local_message(user: str, body: str) -> dict:
    """Mensaje escrito por un usuario de este grupo.

    Regla de Lamport para envío: incrementar el reloj ANTES de enviar y poner
    el nuevo valor en el mensaje. El mensaje se guarda en el historial y en la
    bandeja de salida (outbox) en la misma transacción: si el contenedor muere
    justo después, el mensaje no se pierde y se reintenta al volver.
    """
    with _lock:
        _conn.execute("BEGIN IMMEDIATE")
        try:
            lamport = _get_clock() + 1
            _set_clock(lamport)
            msg = {
                "id": str(uuid.uuid4()),
                "from": f"{user}@{config.GROUP_NAME}",
                "origin": config.GROUP_NAME,
                "lamport": lamport,
                "sent_at": now_iso(),
                "body": body,
            }
            _insert_message(msg, via="local")
            _conn.execute(
                "INSERT INTO outbox(id, payload, attempts, next_attempt_at) VALUES(?, ?, 0, ?)",
                (msg["id"], json.dumps(msg, ensure_ascii=False), time.time()),
            )
            _conn.execute("COMMIT")
            return msg
        except Exception:
            _conn.execute("ROLLBACK")
            raise


def _insert_message(msg: dict, via: str) -> None:
    _conn.execute(
        "INSERT INTO messages(id, sender, origin, lamport, sent_at, body, received_at, via) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        (msg["id"], msg["from"], msg["origin"], int(msg["lamport"]),
         msg.get("sent_at"), msg["body"], now_iso(), via),
    )


def store_remote_message(msg: dict, via: str) -> tuple[bool, int]:
    """Guarda un mensaje que viene del central (push o /history).

    Devuelve (nuevo, reloj_local). Si el id ya existe NO hace nada: es la
    deduplicación que vuelve idempotente la recepción. Si es nuevo aplica la
    regla de recepción de Lamport: reloj = max(local, recibido) + 1.
    """
    with _lock:
        _conn.execute("BEGIN IMMEDIATE")
        try:
            exists = _conn.execute("SELECT 1 FROM messages WHERE id=?", (msg["id"],)).fetchone()
            if exists:
                _conn.execute("COMMIT")
                return False, _get_clock()
            local = max(_get_clock(), int(msg["lamport"])) + 1
            _set_clock(local)
            _insert_message(msg, via=via)
            _conn.execute("COMMIT")
            return True, local
        except Exception:
            _conn.execute("ROLLBACK")
            raise


def list_messages(limit: int = 500) -> list[dict]:
    """Historial ordenado por (lamport, origin) como exige el requisito 7.
    El id se usa solo como desempate final para que el orden sea determinista."""
    with _lock:
        rows = _conn.execute(
            "SELECT * FROM (SELECT * FROM messages ORDER BY lamport DESC, origin DESC, id DESC LIMIT ?) "
            "ORDER BY lamport, origin, id",
            (limit,),
        ).fetchall()
    return [
        {"id": r["id"], "from": r["sender"], "origin": r["origin"], "lamport": r["lamport"],
         "sent_at": r["sent_at"], "body": r["body"], "received_at": r["received_at"], "via": r["via"]}
        for r in rows
    ]


def count_messages() -> int:
    with _lock:
        return _conn.execute("SELECT COUNT(*) AS n FROM messages").fetchone()["n"]


def max_remote_lamport() -> int:
    """Mayor marca de Lamport recibida de OTROS servidores: punto de partida de /history."""
    with _lock:
        row = _conn.execute(
            "SELECT MAX(lamport) AS m FROM messages WHERE origin <> ?", (config.GROUP_NAME,)
        ).fetchone()
        return row["m"] or 0


# --------------------------------------------------------------------------
# Outbox (mensajes pendientes de entregar al central)
# --------------------------------------------------------------------------
def due_outbox(limit: int = 50) -> list[sqlite3.Row]:
    with _lock:
        return _conn.execute(
            "SELECT * FROM outbox WHERE next_attempt_at <= ? ORDER BY rowid LIMIT ?",
            (time.time(), limit),
        ).fetchall()


def outbox_done(msg_id: str) -> None:
    with _lock:
        _conn.execute("DELETE FROM outbox WHERE id=?", (msg_id,))


def outbox_reschedule(msg_id: str, attempts: int, delay: float) -> None:
    with _lock:
        _conn.execute(
            "UPDATE outbox SET attempts=?, next_attempt_at=? WHERE id=?",
            (attempts, time.time() + delay, msg_id),
        )


def outbox_release_all() -> int:
    """Cuando el central vuelve, todo lo pendiente se envía de inmediato."""
    with _lock:
        return _conn.execute("UPDATE outbox SET next_attempt_at=?", (time.time(),)).rowcount


def outbox_size() -> int:
    with _lock:
        return _conn.execute("SELECT COUNT(*) AS n FROM outbox").fetchone()["n"]
