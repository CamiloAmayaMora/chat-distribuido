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
  {id="S01", tipo="ANIM", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/escenas/S01_Apertura.mp4", frames=480},
  {id="S02", tipo="CARA", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/caras/S02_CARA_Camilo.mp4", frames=837},
  {id="S03", tipo="ANIM", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/escenas/S03_Arquitectura_en_estrella.mp4", frames=1230},
  {id="S04", tipo="CARA", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/caras/S04_CARA_Johen.mp4", frames=216},
  {id="S05", tipo="ANIM", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/escenas/S05_Bandeja_de_salida.mp4", frames=660},
  {id="S06", tipo="ANIM", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/escenas/S06_Reloj_de_Lamport.mp4", frames=990},
  {id="S07", tipo="ANIM", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/escenas/S07_Idempotencia.mp4", frames=570},
  {id="S08", tipo="CARA", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/caras/S08_CARA_Daniel.mp4", frames=318},
  {id="S09", tipo="ANIM", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/escenas/S09_Reintentos_con_espera_exponencial.mp4", frames=960},
  {id="S10", tipo="ANIM", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/escenas/S10_Deteccion_de_fallas_y_recuperacion.mp4", frames=600},
  {id="S11", tipo="DEMO", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/demo.mp4", frames=2452},
  {id="S12", tipo="CARA", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/caras/S12_CARA_Hector.mp4", frames=189},
  {id="S13", tipo="ANIM", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/escenas/S13_Experimento__metodo.mp4", frames=930},
  {id="S14", tipo="ANIM", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/escenas/S14_Experimento__resultados.mp4", frames=780},
  {id="S15", tipo="ANIM", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/escenas/S15_Interoperabilidad.mp4", frames=750},
  {id="S16", tipo="CARA", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/caras/S16_CARA_Camilo.mp4", frames=489},
  {id="S17", tipo="ANIM", file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/escenas/S17_Creditos.mp4", frames=270}
}
local VOCES = {
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S01.wav", at=18},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S02.wav", at=498},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S03.wav", at=1335},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S04.wav", at=2565},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S05.wav", at=2781},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S06.wav", at=3441},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S07.wav", at=4431},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S08.wav", at=5001},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S09.wav", at=5319},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S10.wav", at=6279},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S11_01_inicio.wav", at=6870},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S11_02_conversacion.wav", at=7151},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S11_03_kill_ga.wav", at=7429},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S11_04_gb_escribe.wav", at=7573},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S11_05_start_ga.wav", at=7895},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S11_06_ga_al_dia.wav", at=8181},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S11_07_stop_central.wav", at=8376},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S11_08_start_central.wav", at=8880},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S12.wav", at=9331},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S13.wav", at=9520},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S14.wav", at=10450},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S15.wav", at=11230},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/tts/S16.wav", at=11980}
}
local ROTULOS = {
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/rotulos/rotulo_Camilo.mov", at=504},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/rotulos/rotulo_Johen.mov", at=2571},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/rotulos/rotulo_Daniel.mov", at=5007},
  {file="C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/rotulos/rotulo_Hector.mov", at=9337}
}
local MARCAS = {
  {at=0, name="S01 Apertura", note="ANIM · Camilo: Cuatro grupos. Cuatro servidores. Una sola sala de chat para todo el curso. Pero, ¿qué le pasa a un mensaje cuando el servidor que lo debía recibir se apaga a mitad de camino?"},
  {at=480, name="S02 Presentación y pregunta", note="CARA · Camilo: Hola, somos Camilo, Johen, Daniel y Héctor, del curso de Sistemas Distribuidos de la UIS. Construimos el servidor de chat de nuestro grupo, que se conecta con el servidor central del profesor. Y nos hicimos una pregunta: si nuestro servidor se cae unos segundos, ¿cuántos mensajes se pierden o se repiten? Nuestra hipótesis: ninguno."},
  {at=1317, name="S03 Arquitectura en estrella", note="ANIM · Camilo: El sistema tiene forma de estrella. En el centro está el servidor del profesor y, alrededor, un servidor por cada grupo. Los grupos nunca se hablan directamente: todo pasa por el central. Cuando Ana escribe en ge a, su servidor envía el mensaje al central, el central lo guarda en su historial y lo reenvía a los demás grupos. Nuestro servidor es un contenedor de Docker con Python y FastAPI. Guarda todo en SQLite, dentro de un volumen que sobrevive a los reinicios, y se configura con variables de entorno: nada queda escrito en el código."},
  {at=2547, name="S04 Johen entra", note="CARA · Johen: Yo les explico qué pasa dentro de nuestro servidor cuando alguien escribe un mensaje."},
  {at=2763, name="S05 Bandeja de salida", note="ANIM · Johen: Cuando alguien escribe, hacemos tres cosas en un solo paso, dentro de una transacción: subimos el reloj, guardamos el mensaje para mostrarlo y lo dejamos en una bandeja de salida. Si el servidor se muere justo después, el mensaje no se pierde: sigue en disco y se envía apenas vuelva."},
  {at=3423, name="S06 Reloj de Lamport", note="ANIM · Johen: Para ordenar los mensajes no usamos la hora, porque cada computador tiene su reloj un poco distinto. Usamos un reloj de Lamport, que es solo un contador. Al enviar, le sumamos uno. Al recibir, nos quedamos con el mayor entre el nuestro y el del mensaje, y le sumamos uno. Todos ordenan por ese número y, si hay empate, por el nombre del servidor. Así, todos los grupos ven exactamente el mismo orden."},
  {at=4413, name="S07 Idempotencia", note="ANIM · Johen: Cada mensaje nace con un identificador único. Si nos llega uno que ya tenemos, respondemos que sí, pero no lo guardamos otra vez. Eso se llama idempotencia, y es la razón por la que reintentar nunca muestra mensajes repetidos."},
  {at=4983, name="S08 Daniel entra", note="CARA · Daniel: Yo me encargué de la conexión con el servidor central: cómo enviamos, cómo reintentamos y cómo nos damos cuenta de que algo falló."},
  {at=5301, name="S09 Reintentos con espera exponencial", note="ANIM · Daniel: Una tarea de fondo va vaciando la bandeja de salida. Si el central responde bien, listo. Si responde con un error suyo, o no responde, reintentamos esperando cada vez el doble: uno, dos, cuatro, ocho segundos, hasta treinta, con un poco de azar para que no reintenten todos a la vez. Si responde que el mensaje está mal, un error cuatrocientos, no insistimos y lo dejamos en el log."},
  {at=6261, name="S10 Detección de fallas y recuperación", note="ANIM · Daniel: Cada tres segundos le preguntamos al central si está vivo. Si falla tres veces seguidas, lo damos por caído y los mensajes se acumulan en disco. Cuando vuelve, nos registramos de nuevo, pedimos con history todo lo que nos perdimos y enviamos lo pendiente."},
  {at=6861, name="S11 Demo: caída y recuperación", note="DEMO · Daniel: Esta es la demo real. A la izquierda, el chat del grupo ge a; a la derecha, el de ge be. Abajo, los logs de los dos servidores. / Ana escribe desde ge a y Beto responde desde ge be. Cada mensaje lleva su número de Lamport. / Ahora apagamos ge a de golpe, con docker kill. / Beto sigue escribiendo. Esos mensajes llegan al central, pero ge a no está para recibirlos. / Prendemos ge a otra vez. En el log aparece history request, y un recovered por cada mensaje perdido. / Ahí están: todos los mensajes, una sola vez y en el mismo orden en los dos grupos. / Ahora apagamos el servidor central. Tras tres latidos fallidos, ge a lo marca como caído, y lo que escribe Ana queda pendiente en disco. / El central vuelve. ge a se registra otra vez, vacía la bandeja de salida, y Beto recibe los mensajes sin repetidos."},
  {at=9313, name="S12 Héctor entra", note="CARA · Héctor: Y yo les muestro el experimento con el que pusimos a prueba todo esto."},
  {at=9502, name="S13 Experimento: método", note="ANIM · Héctor: Levantamos un central de prueba y dos servidores nuestros, ge a y ge be. ge be envía cinco mensajes por segundo. A los cuatro segundos apagamos ge a de golpe y lo prendemos tras dos, cinco o diez segundos. Además, el central pierde el diez por ciento de las respuestas y duplica el diez por ciento de los mensajes. Tres repeticiones de cada caso, con y sin pedir el historial: dieciocho corridas."},
  {at=10432, name="S14 Experimento: resultados", note="ANIM · Héctor: Con recuperación: cero mensajes perdidos y cero repetidos en pantalla en las nueve corridas, aunque llegaron trescientos sesenta y tres duplicados reales que se descartaron por su identificador. ge a se pone al día en menos de un segundo y medio. Sin pedir el historial, las pérdidas crecen con la caída: con diez segundos se pierde el treinta y siete por ciento."},
  {at=11212, name="S15 Interoperabilidad", note="ANIM · Daniel: También ensayamos la sesión de interoperabilidad con cuatro grupos: dos copias del nuestro y dos implementaciones escritas aparte, una correcta y otra con errores típicos. Todos recibieron todo. Pero la que tenía errores ordena por llegada, y ve otro orden; y como guarda en memoria, al reiniciarse pierde su historial."},
  {at=11962, name="S16 Cierre", note="CARA · Camilo: En resumen: reintentar hasta que llegue y descartar los repetidos hace que cada mensaje se vea exactamente una vez. Y el reloj de Lamport le da a todos el mismo orden, sin un reloj común. Gracias."},
  {at=12451, name="S17 Créditos", note="ANIM · : "}
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
