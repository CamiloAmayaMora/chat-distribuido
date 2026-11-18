"""Configuración del servidor de grupo.

Toda la configuración se lee de variables de entorno (requisito 1 y 4 del
enunciado): el nombre del grupo, la URL pública y la URL del servidor central
NUNCA están escritos en el código.
"""
import os
import sys


def _env(name: str, default=None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        print(f"[config] Falta la variable de entorno obligatoria {name}", file=sys.stderr)
        sys.exit(1)
    return value


def _bool(name: str, default: str) -> bool:
    return _env(name, default).strip().lower() in ("1", "true", "yes", "si", "sí", "on")


# --- Identidad del servidor -------------------------------------------------
GROUP_NAME = _env("GROUP_NAME", required=True)          # p. ej. "g3"
PUBLIC_URL = _env("PUBLIC_URL", required=True).rstrip("/")  # URL con la que nos alcanza el central
CENTRAL_URL = _env("CENTRAL_URL", required=True).rstrip("/")

# --- Almacenamiento ---------------------------------------------------------
DB_PATH = _env("DB_PATH", "/data/chat.db")
EVENTS_LOG = _env("EVENTS_LOG", "/data/events.jsonl")   # log JSON (fuente del experimento)

# --- Registro y heartbeat ---------------------------------------------------
REGISTER_INTERVAL = float(_env("REGISTER_INTERVAL", "15"))      # s entre renovaciones
HEARTBEAT_INTERVAL = float(_env("HEARTBEAT_INTERVAL", "3"))     # s entre GET /health
HEARTBEAT_MAX_FAILURES = int(_env("HEARTBEAT_MAX_FAILURES", "3"))  # fallos seguidos => caído
HTTP_TIMEOUT = float(_env("HTTP_TIMEOUT", "3"))

# --- Reintentos con backoff exponencial -------------------------------------
RETRY_BASE = float(_env("RETRY_BASE", "1"))   # primera espera (s)
RETRY_MAX = float(_env("RETRY_MAX", "30"))    # tope de la espera (s)

# --- Recuperación de historial ----------------------------------------------
HISTORY_RECOVERY = _bool("HISTORY_RECOVERY", "true")   # se apaga solo para el experimento de control
# Cuántas marcas de Lamport "hacia atrás" pedimos al recuperar. Un servidor con
# el reloj atrasado puede generar mensajes con lamport menor que el nuestro;
# pedir con solapamiento evita perderlos y la deduplicación por id elimina lo repetido.
# Un valor negativo significa "pedir siempre desde 0".
HISTORY_OVERLAP = int(_env("HISTORY_OVERLAP", "100"))
# Sincronización periódica (anti-entropía / modo alternativo "pull").
# 0 = desactivada. Útil si la red no permite que el central nos haga POST.
SYNC_POLL_INTERVAL = float(_env("SYNC_POLL_INTERVAL", "0"))

LOG_LEVEL = _env("LOG_LEVEL", "INFO")
