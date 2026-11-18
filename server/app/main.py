"""Servidor de chat de grupo (FastAPI).

Dos APIs:
  * Federación (fija, la llama el servidor central):
        GET  /fed/health     -> {"server": "g3", "lamport": 42, ...}
        POST /fed/messages   -> recibe un mensaje reenviado (idempotente)
  * Cliente (libre, la usan nuestro cliente web y el de consola):
        POST /api/users, GET /api/users
        POST /api/messages, GET /api/messages
        GET  /api/status
"""
import asyncio
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from . import config, db, federation
from .events import counters, event


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    event("STARTUP", central=config.CENTRAL_URL, public_url=config.PUBLIC_URL,
          clock=db.clock(), messages=db.count_messages(), pending=db.outbox_size())
    tasks = [
        asyncio.create_task(federation.startup_sequence()),
        asyncio.create_task(federation.register_loop()),
        asyncio.create_task(federation.heartbeat_loop()),
        asyncio.create_task(federation.outbox_loop()),
        asyncio.create_task(federation.sync_loop()),
    ]
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(title=f"Chat distribuido – servidor {config.GROUP_NAME}", lifespan=lifespan)

STATIC = Path(__file__).parent / "static"
USERNAME_RE = re.compile(r"^[a-z0-9_.-]{1,32}$")


# ==========================================================================
# API de federación (protocolo común)
# ==========================================================================
class FedMessage(BaseModel):
    # extra="ignore": los campos desconocidos se ignoran sin error (regla del protocolo)
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = Field(min_length=1)
    from_: str = Field(alias="from", min_length=1)
    origin: str = Field(min_length=1)
    lamport: int = Field(ge=0)
    sent_at: str | None = None
    body: str


@app.get("/fed/health")
def fed_health():
    return {"server": config.GROUP_NAME, "lamport": db.clock(), "status": "ok"}


@app.post("/fed/messages")
def fed_messages(msg: FedMessage):
    data = msg.model_dump(by_alias=True)
    created, local = db.store_remote_message(data, via="push")
    if created:
        event("RECEIVED", id=msg.id, lamport=msg.lamport, origin=msg.origin, clock=local)
        return {"status": "stored", "id": msg.id, "lamport": local}
    # id ya conocido: 200 sin efectos (idempotencia)
    event("DUPLICATE", id=msg.id, lamport=msg.lamport, origin=msg.origin)
    return {"status": "duplicate", "id": msg.id, "lamport": local}


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    # Un cuerpo inválido es un 4xx: lo registramos para que quede rastro.
    event("INVALID_REQUEST", path=request.url.path)
    return JSONResponse(status_code=400, content={"error": "invalid body", "detail": jsonable_encoder(exc.errors())})


# ==========================================================================
# API de cliente (libre)
# ==========================================================================
class NewUser(BaseModel):
    name: str


class NewMessage(BaseModel):
    user: str
    body: str = Field(min_length=1, max_length=2000)


@app.post("/api/users", status_code=201)
def create_user(u: NewUser):
    name = u.name.strip().lower()
    if not USERNAME_RE.match(name):
        raise HTTPException(400, "Nombre inválido: use a-z, 0-9, punto, guion o guion bajo (máx. 32)")
    created = db.create_user(name)
    if created:
        event("USER_CREATED", user=f"{name}@{config.GROUP_NAME}")
    return {"user": f"{name}@{config.GROUP_NAME}", "created": created}


@app.get("/api/users")
def list_users():
    return [f"{n}@{config.GROUP_NAME}" for n in db.list_users()]


@app.post("/api/messages", status_code=201)
def post_message(m: NewMessage):
    name = m.user.split("@")[0].strip().lower()
    if not db.user_exists(name):
        raise HTTPException(404, f"El usuario {name}@{config.GROUP_NAME} no existe")
    msg = db.create_local_message(name, m.body)
    event("LOCAL_MESSAGE", id=msg["id"], lamport=msg["lamport"], user=msg["from"])
    return msg


@app.get("/api/messages")
def get_messages(limit: int = 500):
    return db.list_messages(limit=max(1, min(limit, 5000)))


@app.get("/api/status")
def status():
    c = federation.central
    return {
        "server": config.GROUP_NAME,
        "lamport": db.clock(),
        "central_url": config.CENTRAL_URL,
        "central_up": c.up,
        "registered": c.registered,
        "heartbeat_failures": c.consecutive_failures,
        "last_health_ok": c.last_health_ok,
        "outbox_pending": db.outbox_size(),
        "messages": db.count_messages(),
        "counters": counters,
    }


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
