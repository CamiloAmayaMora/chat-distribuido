-- Arma el proyecto "Video Chat Distribuido" en DaVinci Resolve.
-- Uso: en Resolve, menú  Workspace (Espacio de trabajo) > Scripts > Utility >
--      Armar_video_chat_distribuido
-- Crea el proyecto (1920x1080, 30 fps), importa todos los medios en carpetas
-- y monta la línea de tiempo completa:
--   V1 = escenas en orden (animaciones, tomas a cámara de relleno y demo)
--   V2 = rótulos con el nombre de cada integrante
--   A1 = voz guía (voz sintética, se reemplaza por la voz real)
--   A2 = libre para la voz real · A3 = libre para música
-- Cada escena tiene un marcador con el texto que se dice.
-- (Archivo generado por video/tools/preparar_medios.py; no editar a mano.)

local CLIPS = {
--@@CLIPS@@
}
local VOCES = {
--@@VOCES@@
}
local ROTULOS = {
--@@ROTULOS@@
}
local MARCAS = {
--@@MARCAS@@
}

local resolve = resolve or (Resolve and Resolve()) or bmd.scriptapp("Resolve")
if not resolve then print("No se encontró Resolve") return end
local pm = resolve:GetProjectManager()
local NAME = "Video Chat Distribuido"
local proj = pm:CreateProject(NAME)
if not proj then
  proj = pm:LoadProject(NAME)
end
if not proj then
  print("No se pudo crear ni abrir el proyecto " .. NAME)
  return
end
proj:SetSetting("timelineFrameRate", "30")
proj:SetSetting("timelineResolutionWidth", "1920")
proj:SetSetting("timelineResolutionHeight", "1080")
proj:SetSetting("timelinePlaybackFrameRate", "30")

local mp = proj:GetMediaPool()
local ms = resolve:GetMediaStorage()
local root = mp:GetRootFolder()

local function folder(name)
  for _, f in pairs(root:GetSubFolderList() or {}) do
    if f:GetName() == name then return f end
  end
  return mp:AddSubFolder(root, name)
end

local function import(list, folderName)
  mp:SetCurrentFolder(folder(folderName))
  local paths, items = {}, {}
  for i, c in ipairs(list) do paths[i] = c.file end
  local got = ms:AddItemListToMediaPool(paths) or {}
  -- mapear por nombre de archivo
  local byName = {}
  for _, it in pairs(got) do byName[it:GetClipProperty("File Name")] = it end
  for i, c in ipairs(list) do
    local fname = c.file:match("([^/]+)$")
    items[i] = byName[fname]
    if not items[i] then print("No se importó: " .. c.file) end
  end
  return items
end

local vClips = import(CLIPS, "01 Escenas")
local vVoces = import(VOCES, "02 Voz guia")
local vRot = import(ROTULOS, "03 Rotulos")
folder("04 Tomas reales (caras)")
folder("05 Voz real")
folder("06 Musica")

local stamp = os.date("%Y-%m-%d %H.%M")
local tl = mp:CreateEmptyTimeline("Video sustentacion " .. stamp)
proj:SetCurrentTimeline(tl)
tl:AddTrack("video")
tl:AddTrack("audio", "mono")
tl:AddTrack("audio", "stereo")
tl:SetTrackName("video", 1, "Escenas")
tl:SetTrackName("video", 2, "Rotulos")
tl:SetTrackName("audio", 1, "Voz guia")
tl:SetTrackName("audio", 2, "Voz real")
tl:SetTrackName("audio", 3, "Musica")
local start = tl:GetStartFrame()

-- V1: escenas una detrás de otra
local rec = start
for i, c in ipairs(CLIPS) do
  local it = vClips[i]
  if it then
    mp:AppendToTimeline({{ mediaPoolItem = it, startFrame = 0, endFrame = c.frames - 1,
                           trackIndex = 1, recordFrame = rec, mediaType = 1 }})
    if c.tipo == "CARA" then it:SetClipColor("Orange")
    elseif c.tipo == "DEMO" then it:SetClipColor("Teal")
    else it:SetClipColor("Blue") end
  end
  rec = rec + c.frames
end
-- V2: rótulos
for i, r in ipairs(ROTULOS) do
  local it = vRot[i]
  if it then
    pcall(function() it:SetClipProperty("Alpha mode", "Straight") end)
    mp:AppendToTimeline({{ mediaPoolItem = it, trackIndex = 2, recordFrame = start + r.at, mediaType = 1 }})
  end
end
-- A1: voz guía
for i, v in ipairs(VOCES) do
  local it = vVoces[i]
  if it then
    mp:AppendToTimeline({{ mediaPoolItem = it, trackIndex = 1, recordFrame = start + v.at, mediaType = 2 }})
  end
end
-- marcadores con el texto de cada escena
for _, m in ipairs(MARCAS) do
  tl:AddMarker(m.at, "Yellow", m.name, m.note, 1)
end
pm:SaveProject()
print("Listo: línea de tiempo creada con " .. #CLIPS .. " escenas, " .. #VOCES .. " voces guía y " .. #ROTULOS .. " rótulos.")
