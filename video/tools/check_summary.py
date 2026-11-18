"""Resume el último informe de `hyperframes check` (errores y advertencias)."""
import glob, json, os, sys
d = sys.argv[1] if len(sys.argv) > 1 else "."
f = max(glob.glob(os.path.join(d, ".hyperframes/artifacts/checks/*.json")), key=os.path.getmtime)
r = json.load(open(f, encoding="utf-8"))
print("ok:", r.get("ok"))
def items(sec):
    v = r.get(sec)
    if isinstance(v, dict):
        for k in ("findings", "issues", "errors", "warnings", "items", "results"):
            if isinstance(v.get(k), list):
                yield from v[k]
    elif isinstance(v, list):
        yield from v
for sec in ("lint", "runtime", "layout", "motion", "contrast", "craft", "audio"):
    seen = {}
    for it in items(sec):
        if not isinstance(it, dict):
            continue
        key = (it.get("severity") or it.get("level"), it.get("code") or it.get("rule") or it.get("kind"))
        seen.setdefault(key, []).append(it)
    for (sev, code), lst in seen.items():
        it = lst[0]
        msg = (it.get("message") or it.get("text") or "")[:200]
        where = it.get("selector") or it.get("elementId") or it.get("file") or ""
        t = it.get("time", it.get("t", ""))
        print(f"[{sec}] {sev} {code} x{len(lst)} | {msg} | {where} {t}")
