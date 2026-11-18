#!/usr/bin/env python3
"""Experimento: pérdidas ante una caída (pregunta 1 del enunciado, sección 5).

Pregunta: ¿cuántos mensajes se pierden o se duplican cuando el servidor del
grupo se cae durante unos segundos? ¿Cuánto tarda en ponerse al día?

Montaje (docker-compose.lab.yml): central simulado + servidores `ga` y `gb`.
  1. `gb` envía mensajes a tasa fija (RATE msg/s) a #general.
  2. A los KILL_AT s se hace `docker kill` de `ga` (caída abrupta, sin apagado limpio).
  3. Tras D segundos se levanta de nuevo (`docker compose start ga`).
  4. Al terminar se compara lo que envió `gb` con lo que tiene `ga`:
       faltantes  = enviados − recibidos
       duplicados = filas repetidas en el historial de `ga` (lo que vería el usuario)
       descartados = eventos DUPLICATE en el log de `ga` (duplicados que llegaron y se filtraron)
       t_recuperación = desde que `ga` vuelve a responder hasta que tiene todos los
                        mensajes enviados durante la caída.

Se repite para varias duraciones de caída (parámetro variado) y en dos modos:
  * recovery    – servidor completo (GET /history al arrancar)
  * norecovery  – control: HISTORY_RECOVERY=false, solo depende del reenvío del central

El central se configura con fallos inyectados (respuestas perdidas y reenvíos
dobles) para forzar reintentos y duplicados reales.

Uso:
    python experiment/run_experiment.py                       # todo (≈15 min)
    python experiment/run_experiment.py --durations 5 --reps 3 --modes recovery
"""
import argparse
import csv
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "experiment" / "results"
COMPOSE = ["docker", "compose", "-f", str(ROOT / "docker-compose.lab.yml")]
GA, GB, CENTRAL = "http://localhost:8001", "http://localhost:8002", "http://localhost:9000"


# ---------------------------------------------------------------- utilidades
def http(method, url, body=None, timeout=3):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def compose(*args, env=None, check=True):
    return subprocess.run(COMPOSE + list(args), env=env, check=check,
                          capture_output=True, text=True)


def wait_health(url, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        try:
            http("GET", f"{url}/fed/health", timeout=1)
            return time.time()
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"{url} no respondió en {timeout}s")


def ga_ids(run_tag):
    msgs = http("GET", f"{GA}/api/messages?limit=5000", timeout=5)
    return [m["id"] for m in msgs if m["body"].startswith(run_tag)]


def count_events(service, event, since_iso):
    """Cuenta eventos del log JSON del servidor desde una marca de tiempo."""
    out = compose("exec", "-T", service, "cat", "/data/events.jsonl", check=False).stdout
    n = 0
    for line in out.splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("event") == event and e.get("ts", "") >= since_iso:
            n += 1
    return n


def log(*a):
    print(datetime.now().strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- una corrida
def run_once(mode, duration, rep, rate, kill_at, after):
    run_tag = f"[exp-{mode}-{duration}s-r{rep}-{uuid.uuid4().hex[:4]}]"
    total = kill_at + duration + after
    since_iso = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    sent = []                         # (id, t_envío)
    stop = threading.Event()

    def sender():
        seq, t0 = 0, time.time()
        while time.time() - t0 < total:
            target = t0 + seq / rate
            if (d := target - time.time()) > 0:
                time.sleep(d)
            try:
                m = http("POST", f"{GB}/api/messages", {"user": "exp", "body": f"{run_tag} #{seq}"})
                sent.append((m["id"], time.time()))
            except Exception as e:
                log("  error enviando:", e)
            seq += 1
        stop.set()

    th = threading.Thread(target=sender)
    t0 = time.time()
    th.start()

    time.sleep(kill_at)
    t_kill = time.time()
    compose("kill", "ga")
    log(f"  ga KILL  (t={t_kill - t0:.1f}s)")
    time.sleep(duration)
    compose("start", "ga")
    t_up = wait_health(GA)
    log(f"  ga START (caída real {t_up - t_kill:.1f}s)")

    # Tiempo de recuperación: hasta que ga tiene TODO lo enviado durante la caída.
    outage_ids = {i for i, ts in sent if t_kill <= ts <= t_up}
    t_rec = None
    while time.time() - t_up < 30:
        try:
            if outage_ids <= set(ga_ids(run_tag)):
                t_rec = time.time() - t_up
                break
        except Exception:
            pass
        time.sleep(0.1)

    th.join()
    time.sleep(6)                     # margen para que terminen reintentos y reenvíos

    expected = {i for i, _ in sent}
    got_list = ga_ids(run_tag)
    got = set(got_list)
    row = {
        "mode": mode,
        "duration_s": duration,
        "rep": rep,
        "rate_msg_s": rate,
        "real_outage_s": round(t_up - t_kill, 2),
        "sent": len(expected),
        "sent_during_outage": len(outage_ids),
        "received": len(got & expected),
        "missing": len(expected - got),
        "duplicates_shown": len(got_list) - len(got),
        "duplicates_discarded": count_events("ga", "DUPLICATE", since_iso),
        "recovered_via_history": count_events("ga", "RECOVERED", since_iso),
        "recovery_time_s": round(t_rec, 2) if t_rec is not None else "",
    }
    log(f"  => enviados={row['sent']} faltan={row['missing']} dup_pantalla={row['duplicates_shown']} "
        f"dup_descartados={row['duplicates_discarded']} t_rec={row['recovery_time_s']}")
    return row


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--durations", type=int, nargs="+", default=[2, 5, 10])
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--rate", type=float, default=5.0, help="mensajes por segundo")
    ap.add_argument("--kill-at", type=float, default=4.0)
    ap.add_argument("--after", type=float, default=6.0, help="s de envío tras la caída")
    ap.add_argument("--modes", nargs="+", default=["recovery", "norecovery"])
    ap.add_argument("--out", default=str(RESULTS / "results.csv"))
    a = ap.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = []
    for mode in a.modes:
        env = dict(os.environ,
                   GA_HISTORY_RECOVERY="true" if mode == "recovery" else "false",
                   CHAOS_DROP_RESPONSE_RATE="0.10",   # 10 % de respuestas perdidas -> reintentos
                   CHAOS_DUP_FORWARD_RATE="0.10")     # 10 % de reenvíos dobles -> duplicados
        log(f"=== modo {mode}: levantando laboratorio limpio ===")
        compose("down", "-v", env=env, check=False)
        compose("up", "-d", "--build", env=env)
        wait_health(GA), wait_health(GB)
        time.sleep(3)                                # que ambos se registren
        http("POST", f"{GB}/api/users", {"name": "exp"})
        for d in a.durations:
            for r in range(1, a.reps + 1):
                log(f"--- {mode} | caída {d}s | repetición {r}/{a.reps}")
                rows.append(run_once(mode, d, r, a.rate, a.kill_at, a.after))
                time.sleep(2)

    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log(f"Resultados guardados en {a.out}")


if __name__ == "__main__":
    main()
