#!/usr/bin/env python3
"""Genera la tabla y las gráficas del experimento a partir de results.csv.

    python experiment/plot_results.py
Salidas en experiment/results/: summary.md, losses.png/svg, recovery.png/svg
"""
import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RES = Path(__file__).resolve().parent / "results"
rows = list(csv.DictReader(open(RES / "results.csv", encoding="utf-8")))
for r in rows:
    for k in ("duration_s", "sent", "sent_during_outage", "missing", "duplicates_shown",
              "duplicates_discarded", "recovered_via_history"):
        r[k] = int(r[k])
    r["real_outage_s"] = float(r["real_outage_s"])
    r["recovery_time_s"] = float(r["recovery_time_s"]) if r["recovery_time_s"] else None

durations = sorted({r["duration_s"] for r in rows})
modes = [m for m in ("recovery", "norecovery") if any(r["mode"] == m for r in rows)]
LABEL = {"recovery": "Con recuperación (GET /history)", "norecovery": "Control: sin recuperación"}
COLOR = {"recovery": "#2f7d4f", "norecovery": "#b3261e"}

g = defaultdict(list)
for r in rows:
    g[(r["mode"], r["duration_s"])].append(r)


def mean_sd(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, None
    return st.mean(vals), (st.stdev(vals) if len(vals) > 1 else 0.0)


# ------------------------------------------------------------------ tabla
lines = ["# Resultados del experimento: pérdidas ante una caída", "",
         "Tasa de envío: 5 msg/s desde `gb`. `ga` se mata con `docker kill` y se levanta tras D s.",
         "Central con 10 % de respuestas perdidas y 10 % de reenvíos dobles (fallos inyectados).", "",
         "## Todas las repeticiones", "",
         "| Modo | Caída (s) | Rep | Caída real (s) | Enviados | Durante caída | Faltantes | Dup. en pantalla | Dup. descartados | Recuperados vía /history | T. recuperación (s) |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    lines.append(f"| {r['mode']} | {r['duration_s']} | {r['rep']} | {r['real_outage_s']:.1f} | {r['sent']} | "
                 f"{r['sent_during_outage']} | {r['missing']} | {r['duplicates_shown']} | {r['duplicates_discarded']} | "
                 f"{r['recovered_via_history']} | {r['recovery_time_s'] if r['recovery_time_s'] is not None else 'no se recuperó'} |")
lines += ["", "## Resumen (media ± desviación estándar, n = repeticiones)", "",
          "| Modo | Caída (s) | n | Faltantes (msg) | % perdido | Dup. en pantalla | Dup. descartados | T. recuperación (s) |",
          "|---|---|---|---|---|---|---|---|"]
for m in modes:
    for d in durations:
        rs = g[(m, d)]
        mm, ms = mean_sd([r["missing"] for r in rs])
        pct = 100 * sum(r["missing"] for r in rs) / max(1, sum(r["sent"] for r in rs))
        dm, _ = mean_sd([r["duplicates_shown"] for r in rs])
        ddm, dds = mean_sd([r["duplicates_discarded"] for r in rs])
        tm, ts = mean_sd([r["recovery_time_s"] for r in rs])
        tstr = f"{tm:.2f} ± {ts:.2f}" if tm is not None else "—"
        lines.append(f"| {m} | {d} | {len(rs)} | {mm:.1f} ± {ms:.1f} | {pct:.1f} % | {dm:.0f} | {ddm:.1f} ± {dds:.1f} | {tstr} |")
(RES / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

# ------------------------------------------------------------------ gráficas
plt.rcParams.update({"font.size": 12, "axes.spines.top": False, "axes.spines.right": False})

fig, ax = plt.subplots(figsize=(7, 4.5))
width = 0.36
for i, m in enumerate(modes):
    xs = [j + (i - (len(modes) - 1) / 2) * width for j in range(len(durations))]
    means, sds = zip(*[mean_sd([r["missing"] for r in g[(m, d)]]) for d in durations])
    ax.bar(xs, means, width, yerr=sds, capsize=4, color=COLOR[m], alpha=.85, label=LABEL[m])
    for x, d in zip(xs, durations):
        pts = [r["missing"] for r in g[(m, d)]]
        ax.scatter([x] * len(pts), pts, color="black", s=14, zorder=3)
ax.set_xticks(range(len(durations)), [f"{d} s" for d in durations])
ax.set_xlabel("Duración de la caída de ga (s)")
ax.set_ylabel("Mensajes faltantes en ga (msg)")
ax.set_title("Mensajes perdidos tras la caída (5 msg/s, n=3)")
ax.legend(frameon=False)
fig.tight_layout()
for ext in ("png", "svg"):
    fig.savefig(RES / f"losses.{ext}", dpi=200)

if "recovery" in modes:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    means, sds = zip(*[mean_sd([r["recovery_time_s"] for r in g[("recovery", d)]]) for d in durations])
    ax.bar(range(len(durations)), means, 0.5, yerr=sds, capsize=4, color=COLOR["recovery"], alpha=.85)
    for j, d in enumerate(durations):
        pts = [r["recovery_time_s"] for r in g[("recovery", d)] if r["recovery_time_s"] is not None]
        ax.scatter([j] * len(pts), pts, color="black", s=14, zorder=3)
    ax.set_xticks(range(len(durations)), [f"{d} s" for d in durations])
    ax.set_xlabel("Duración de la caída de ga (s)")
    ax.set_ylabel("Tiempo hasta ponerse al día (s)")
    ax.set_title("Tiempo de recuperación tras reiniciar (n=3)")
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(RES / f"recovery.{ext}", dpi=200)

print((RES / "summary.md").read_text(encoding="utf-8"))
