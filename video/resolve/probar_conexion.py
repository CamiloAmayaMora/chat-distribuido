"""Intenta conectarse a DaVinci Resolve desde fuera (scripting externo).
En la versión gratuita normalmente no se permite; en ese caso el script
Armar_video_chat_distribuido se corre desde el menú Workspace > Scripts."""
import os
import sys
import time

api = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
os.environ.setdefault("RESOLVE_SCRIPT_API", api)
os.environ.setdefault("RESOLVE_SCRIPT_LIB", r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll")
sys.path.append(os.path.join(api, "Modules"))
import DaVinciResolveScript as dvr  # noqa: E402

for _ in range(int(sys.argv[1]) if len(sys.argv) > 1 else 1):
    r = dvr.scriptapp("Resolve")
    if r:
        print("CONECTADO", r.GetProductName(), r.GetVersionString())
        break
    time.sleep(3)
else:
    print("SIN_CONEXION")
