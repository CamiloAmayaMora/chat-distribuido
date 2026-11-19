-- Crea el proyecto "Video Chat Distribuido" en DaVinci Resolve con el video final.
-- Uso: Workspace > Scripts > Utility > Armar_video_chat_distribuido
-- V1/A1 = video final (con las voces) · A2 = libre para música · un marcador por escena.
-- (Generado por video/tools/resolve_final.py)
local FILE = "C:/Users/camil/Downloads/Proyecto Final Sistemas Distribuidos/chat-distribuido/video/render/video_final.mp4"
local FRAMES = 13059
local MARCAS = {
  {at=0, name="S01 Apertura", note="Camilo: Cuatro grupos. Cuatro servidores. Una sola sala de chat para todo el curso. Pero, ¿qué le pasa a un mensaje cuando el servidor que lo debía recibir se apaga a mitad de camino?"},
  {at=546, name="S02 Presentación, pregunta e hipótesis", note="Camilo: Hola, somos Camilo, Johen, Daniel y Héctor, del curso de Sistemas Distribuidos de la UIS. Construimos el servidor de chat de nuestro grupo, que se conecta con el servidor central del profesor. Y nos hicimos una pregunta: si nuestro servidor se cae unos segundos, ¿cuántos mensajes se pierden o se repiten? Nuestra hipótesis: ninguno."},
  {at=1401, name="S03 Arquitectura en estrella", note="Camilo: El sistema tiene forma de estrella. En el centro está el servidor del profesor y, alrededor, un servidor por cada grupo. Los grupos nunca se hablan directamente: todo pasa por el central. Cuando Ana escribe en ge a, su servidor envía el mensaje al central, el central lo guarda en su historial y lo reenvía a los demás grupos. Nuestro servidor es un contenedor de Docker con Python y FastAPI. Guarda todo en SQLite, dentro de un volumen que sobrevive a los reinicios, y se configura con variables de entorno: nada queda escrito en el código."},
  {at=2766, name="S04 Capítulo 2: el servidor por dentro", note="Johen: Yo les explico qué pasa dentro de nuestro servidor cuando alguien escribe un mensaje."},
  {at=3019, name="S05 Bandeja de salida", note="Johen: Cuando alguien escribe, hacemos tres cosas en un solo paso, dentro de una transacción: subimos el reloj, guardamos el mensaje para mostrarlo y lo dejamos en una bandeja de salida. Si el servidor se muere justo después, el mensaje no se pierde: sigue en disco y se envía apenas vuelva."},
  {at=3660, name="S06 Reloj de Lamport", note="Johen: Para ordenar los mensajes no usamos la hora, porque cada computador tiene su reloj un poco distinto. Usamos un reloj de Lamport, que es solo un contador. Al enviar, le sumamos uno. Al recibir, nos quedamos con el mayor entre el nuestro y el del mensaje, y le sumamos uno. Todos ordenan por ese número y, si hay empate, por el nombre del servidor. Así, todos los grupos ven exactamente el mismo orden."},
  {at=4597, name="S07 Idempotencia", note="Johen: Cada mensaje nace con un identificador único. Si nos llega uno que ya tenemos, respondemos que sí, pero no lo guardamos otra vez. Eso se llama idempotencia, y es la razón por la que reintentar nunca muestra mensajes repetidos."},
  {at=5135, name="S08 Capítulo 3: conexión con el central", note="Daniel: Yo me encargué de la conexión con el servidor central: cómo enviamos, cómo reintentamos y cómo nos damos cuenta de que algo falló."},
  {at=5459, name="S09 Reintentos con espera exponencial", note="Daniel: Una tarea de fondo va vaciando la bandeja de salida. Si el central responde bien, listo. Si responde con un error suyo, o no responde, reintentamos esperando cada vez el doble: uno, dos, cuatro, ocho segundos, hasta treinta, con un poco de azar para que no reintenten todos a la vez. Si responde que el mensaje está mal, un error cuatrocientos, no insistimos y lo dejamos en el log."},
  {at=6335, name="S10 Detección de fallas y recuperación", note="Daniel: Cada tres segundos le preguntamos al central si está vivo. Si falla tres veces seguidas, lo damos por caído y los mensajes se acumulan en disco. Cuando vuelve, nos registramos de nuevo, pedimos con history todo lo que nos perdimos y enviamos lo pendiente."},
  {at=6942, name="S11 Demo: caída y recuperación", note="Daniel: Esta es la demo real. A la izquierda, el chat del grupo ge a; a la derecha, el de ge be. Abajo, los logs de los dos servidores. / Ana escribe desde ge a y Beto responde desde ge be. Cada mensaje lleva su número de Lamport. / Ahora apagamos ge a de golpe, con docker kill. / Beto sigue escribiendo. Esos mensajes llegan al central, pero ge a no está para recibirlos. / Prendemos ge a otra vez. En el log aparece history request, y un recovered por cada mensaje perdido. / Ahí están: todos los mensajes, una sola vez y en el mismo orden en los dos grupos. / Ahora apagamos el servidor central. Tras tres latidos fallidos, ge a lo marca como caído, y lo que escribe Ana queda pendiente en disco. / El central vuelve. ge a se registra otra vez, vacía la bandeja de salida, y Beto recibe los mensajes sin repetidos."},
  {at=9394, name="S12 Capítulo 4: el experimento", note="Héctor: Y yo les muestro el experimento con el que pusimos a prueba todo esto."},
  {at=9622, name="S13 Experimento: método", note="Héctor: Levantamos un central de prueba y dos servidores nuestros, ge a y ge be. ge be envía cinco mensajes por segundo. A los cuatro segundos apagamos ge a de golpe y lo prendemos tras dos, cinco o diez segundos. Además, el central pierde el diez por ciento de las respuestas y duplica el diez por ciento de los mensajes. Tres repeticiones de cada caso, con y sin pedir el historial: dieciocho corridas."},
  {at=10567, name="S14 Experimento: resultados", note="Héctor: Con recuperación: cero mensajes perdidos y cero repetidos en pantalla en las nueve corridas, aunque llegaron trescientos sesenta y tres duplicados reales que se descartaron por su identificador. ge a se pone al día en menos de un segundo y medio. Sin pedir el historial, las pérdidas crecen con la caída: con diez segundos se pierde el treinta y siete por ciento."},
  {at=11429, name="S15 Interoperabilidad", note="Héctor: También ensayamos la sesión de interoperabilidad con cuatro grupos: dos copias del nuestro y dos implementaciones escritas aparte, una correcta y otra con errores típicos. Todos recibieron todo. Pero la que tenía errores ordena por llegada, y ve otro orden; y como guarda en memoria, al reiniciarse pierde su historial."},
  {at=12204, name="S16 Resumen y cierre", note="Camilo: En resumen: reintentar hasta que llegue y descartar los repetidos hace que cada mensaje se vea exactamente una vez. Y el reloj de Lamport le da a todos el mismo orden, sin un reloj común. Gracias."},
  {at=12789, name="S17 Créditos", note="sin voz: "}
}
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
local items = resolve:GetMediaStorage():AddItemListToMediaPool({FILE})
local item = items and items[1]
if not item then print("No se pudo importar " .. FILE) return end
mp:AddSubFolder(mp:GetRootFolder(), "Musica")
local tl = mp:CreateEmptyTimeline("Video final " .. os.date("%Y-%m-%d %H.%M"))
proj:SetCurrentTimeline(tl)
mp:AppendToTimeline({{ mediaPoolItem = item, startFrame = 0, endFrame = FRAMES - 1, trackIndex = 1, recordFrame = tl:GetStartFrame() }})
tl:AddTrack("audio", "stereo")
tl:SetTrackName("audio", 1, "Video final (voz)")
tl:SetTrackName("audio", 2, "Musica")
for _, m in ipairs(MARCAS) do tl:AddMarker(m.at, "Yellow", m.name, m.note, 1) end
pm:SaveProject()
print("Listo: proyecto con el video final y " .. #MARCAS .. " marcadores.")
