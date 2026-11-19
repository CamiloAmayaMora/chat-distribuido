"""Proyecto de DaVinci Resolve para el VIDEO FINAL (para agregar música o retocar).

Genera video/resolve/Armar_video_chat_distribuido.lua (lo copia al menú de scripts
de Resolve) y video/resolve/linea_de_tiempo.fcpxml, ambos con video_final.mp4 en la
pista 1 y un marcador por escena.

    python video/tools/resolve_final.py
"""
import json
import os
import shutil
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import quoteattr

VIDEO = Path(__file__).resolve().parents[1]
FPS = 30
plan = json.loads((VIDEO / "render" / "plan_final.json").read_text(encoding="utf-8"))
guion = {e["id"]: e for e in json.loads((VIDEO / "guion_video.json").read_text(encoding="utf-8"))["escenas"]}
final = (VIDEO / "render" / "video_final.mp4").resolve()
frames = round(plan["total"] * FPS)


def note(sid):
    e = guion[sid]
    t = e.get("texto") or " / ".join(l["texto"] for l in e.get("lineas", []))
    return f"{e['voz'] or 'sin voz'}: {t}"[:900]


def lua_str(s):
    return '"' + s.replace("\\", "/").replace('"', '\\"').replace("\n", " ") + '"'


marks = ",\n".join(f'  {{at={round(e["inicio"] * FPS)}, name={lua_str(e["id"] + " " + guion[e["id"]]["titulo"])}, note={lua_str(note(e["id"]))}}}'
                   for e in plan["escenas"])
lua = f"""-- Crea el proyecto "Video Chat Distribuido" en DaVinci Resolve con el video final.
-- Uso: Workspace > Scripts > Utility > Armar_video_chat_distribuido
-- V1/A1 = video final (con las voces) · A2 = libre para música · un marcador por escena.
-- (Generado por video/tools/resolve_final.py)
local FILE = {lua_str(str(final))}
local FRAMES = {frames}
local MARCAS = {{
{marks}
}}
local resolve = resolve or (Resolve and Resolve()) or bmd.scriptapp("Resolve")
if not resolve then print("No se encontró Resolve") return end
local pm = resolve:GetProjectManager()
local NAME = "Video Chat Distribuido"
local proj = pm:CreateProject(NAME) or pm:LoadProject(NAME)
if not proj then print("No se pudo crear ni abrir el proyecto") return end
proj:SetSetting("timelineFrameRate", "30")
proj:SetSetting("timelineResolutionWidth", "1920")
proj:SetSetting("timelineResolutionHeight", "1080")
local mp = proj:GetMediaPool()
local items = resolve:GetMediaStorage():AddItemListToMediaPool({{FILE}})
local item = items and items[1]
if not item then print("No se pudo importar " .. FILE) return end
mp:AddSubFolder(mp:GetRootFolder(), "Musica")
local tl = mp:CreateEmptyTimeline("Video final " .. os.date("%Y-%m-%d %H.%M"))
proj:SetCurrentTimeline(tl)
mp:AppendToTimeline({{{{ mediaPoolItem = item, startFrame = 0, endFrame = FRAMES - 1, trackIndex = 1, recordFrame = tl:GetStartFrame() }}}})
tl:AddTrack("audio", "stereo")
tl:SetTrackName("audio", 1, "Video final (voz)")
tl:SetTrackName("audio", 2, "Musica")
for _, m in ipairs(MARCAS) do tl:AddMarker(m.at, "Yellow", m.name, m.note, 1) end
pm:SaveProject()
print("Listo: proyecto con el video final y " .. #MARCAS .. " marcadores.")
"""
out = VIDEO / "resolve" / "Armar_video_chat_distribuido.lua"
out.write_text(lua, encoding="utf-8")
dest = Path(os.environ["APPDATA"]) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Utility"
dest.mkdir(parents=True, exist_ok=True)
shutil.copy(out, dest / out.name)

fr = lambda sec: f"{round(sec * FPS)}/{FPS}s"
url = "file:///" + quote(final.as_posix(), safe="/:")
mk = "".join(f'<marker start="{fr(e["inicio"])}" duration="1/{FPS}s" value={quoteattr(e["id"] + " " + guion[e["id"]]["titulo"])} note={quoteattr(note(e["id"]))}/>'
             for e in plan["escenas"])
xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.10"><resources>'
       f'<format id="r1" name="FFVideoFormat1080p30" frameDuration="1/{FPS}s" width="1920" height="1080"/>'
       f'<asset id="a1" name="video_final" start="0s" duration="{fr(plan["total"])}" hasVideo="1" hasAudio="1" format="r1" '
       f'audioSources="1" audioChannels="2" audioRate="48000"><media-rep kind="original-media" src={quoteattr(url)}/></asset>'
       '</resources><library><event name="Video Chat Distribuido"><project name="Video final (FCPXML)">'
       f'<sequence format="r1" duration="{fr(plan["total"])}" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k"><spine>'
       f'<asset-clip ref="a1" offset="0s" duration="{fr(plan["total"])}" start="0s" name="video_final">{mk}</asset-clip>'
       '</spine></sequence></project></event></library></fcpxml>\n')
(VIDEO / "resolve" / "linea_de_tiempo.fcpxml").write_text(xml, encoding="utf-8")
print("Lua y FCPXML listos")
