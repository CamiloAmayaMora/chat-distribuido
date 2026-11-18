# Bitácora de interoperabilidad

Integrantes: Camilo Amaya Mora · Johen Gustavo Castañeda García · Daniel Rodriguez Anaya · Hector Felipe Higuera Jurado

> Sección 7 del enunciado: "una incompatibilidad encontrada y bien explicada vale tanto como una
> prueba que pasó sin problemas". Esta bitácora tiene tres partes: pruebas en laboratorio,
> el ensayo de la sesión con implementaciones ajenas (17/11/2026) y la sesión de clase.

## 1. Pruebas en laboratorio local (central simulado, `docker-compose.lab.yml`)

| # | Prueba | Resultado | Observación |
|---|---|---|---|
| L1 | Registro de `ga` y `gb` en el central | ✅ | Evento `REGISTERED` en ambos logs |
| L2 | Conversación `ga` ↔ `gb` en `#general` | ✅ | Mismo orden `(lamport, origin)` en ambos |
| L3 | `docker kill ga` 2/5/10 s mientras `gb` envía a 5 msg/s (9 corridas) | ✅ | 0 faltantes, 0 duplicados en pantalla (ver experimento) |
| L4 | Central detenido ~20 s mientras `ga` escribe 3 mensajes | ✅ | `HEARTBEAT_FAIL`×3 → `CENTRAL_DOWN`, outbox = 3; al volver `CENTRAL_UP` → `OUTBOX_FLUSH` → 3×`SENT`; `gb` los recibe una vez |
| L5 | Central reiniciado (pierde los registros en memoria) | ✅ tras corrección | **Hallazgo propio**: `ga` dejaba de recibir hasta renovar el registro. Corrección: evento `CENTRAL_BLIP` → re-registro + `/history` tras cualquier fallo de heartbeat |
| L6 | 10 % de respuestas perdidas + 10 % de reenvíos dobles | ✅ | Reintentos con el mismo id; el central y `ga` descartan duplicados |
| L7 | `docker compose restart` | ✅ | Usuarios, historial y reloj de Lamport sobreviven (volumen) |
| L8 | Script de conformidad propio | ✅ 24/24 | `conformance/self_check_output.txt` |

## 2. Ensayo de la sesión con implementaciones ajenas (17/11/2026)

Montaje: `interop/docker-compose.interop.yml`. Un central simulado y cuatro "grupos":

| Grupo | Implementación |
|---|---|
| `amaya` | la nuestra |
| `amaya2` | otra copia de la nuestra |
| `ext1` | **ajena correcta**: escrita aparte, solo biblioteca estándar, datos en RAM, recupera historial al arrancar |
| `ext2` | **ajena con errores típicos**: `lamport` como texto, `sent_at` en otro formato, no deduplica, ordena por llegada, no recupera historial, responde 500 en 1 de cada 5 recepciones |

Script: `python interop/run_interop.py` · informe crudo: `interop/results/interop_report.md` · logs: `interop/results/interop_logs.txt`.

### 2.1 Conversación global (2 mensajes por grupo = 8)

| Grupo | ¿Ve los 8? | Faltan | Duplicados | ¿Mismo orden que el central? |
|---|---|---|---|---|
| `amaya` | ✅ | 0 | 0 | ✅ |
| `amaya2` | ✅ | 0 | 0 | ✅ |
| `ext1` | ✅ | 0 | 0 | ✅ |
| `ext2` | ✅ | 0 | 0 | ❌ ordena por llegada |

### 2.2 Caída y recuperación por turnos (≈ 8 s caído, los otros 3 escriben 3 mensajes c/u)

| Grupo caído | Escritos durante la caída | Recuperados | Faltan | Duplicados | ¿Conserva el historial anterior? |
|---|---|---|---|---|---|
| `amaya` | 9 | 9 | 0 | 0 | ✅ |
| `amaya2` | 9 | 9 | 0 | 0 | ✅ |
| `ext1` | 9 | 9 | 0 | 0 | ✅ (lo vuelve a pedir con `/history?since=0`) |
| `ext2` | 9 | 9 | 0 | 0 | ❌ 0 de 8: lo tenía solo en RAM |

### 2.3 Robustez de nuestro servidor ante mensajes de otros grupos

| Caso que nos reenvía el central | Respuesta | Decisión |
|---|---|---|
| `lamport` como texto `"42"` | 200 | Se acepta y se convierte a número (tolerancia) |
| `sent_at` en otro formato o ausente | 200 | Es informativo: nunca se usa para ordenar |
| Campos desconocidos | 200 | Se ignoran (regla del protocolo) |
| Falta `from`, `lamport` negativo o no numérico, JSON roto | 400 | Error del emisor: 4xx para que **no** se reintente |

### 2.4 Hallazgos e incompatibilidades

| # | Grupo | Síntoma | Causa | Cómo lo explicamos |
|---|---|---|---|---|
| H1 | `ext2` | Muestra los mensajes en otro orden que el resto | Ordena por llegada, no por `(lamport, origin)` | La llegada depende de la red; Lamport da el mismo orden en todos |
| H2 | `ext2` | Tras reiniciar no tiene nada de lo anterior | Guarda en RAM y no pide `/history` | Viola el requisito 2 (persistencia) y el 9 (recuperación) |
| H3 | `ext2` | Aun así recibió lo enviado durante su caída | El central reintenta el reenvío ~12 s (3 intentos × timeout 3 s + esperas) | Tuvo suerte: con caídas más largas pierde mensajes (en nuestro experimento de control: 37 % con 10 s) |
| H4 | `ext2` | Responde 500 a veces | Error interno simulado | El central reintenta los 5xx: no se perdió nada |
| H5 | `ext2` | Envía `lamport` como texto | Error de tipos | Nuestro servidor lo tolera; un servidor estricto lo rechazaría con 400 y ese mensaje nunca le llegaría |
| H6 | nosotros | Tras reinicio del central dejábamos de recibir | El central olvida registros y solo renovábamos cada 30 s | Corregido: re-registro inmediato ante cualquier fallo de heartbeat (L5) |

## 3. Sesión de clase con el servidor del profesor

> Se llena el día de la sesión. Comandos útiles:
>
> ```bash
> docker compose logs -f server | grep -E "RECEIVED|DUPLICATE|REJECTED|INVALID|CENTRAL_"
> curl -s localhost:8000/api/status
> ```

| Hora | Prueba | ¿Funcionó? | Qué vimos en los logs | Por qué |
|---|---|---|---|---|
| | Conversación global | | | |
| | Nuestra caída y recuperación | | | |
| | Caída de otro grupo | | | |

Incompatibilidades con otros grupos:

| Grupo | Síntoma | Causa probable | ¿Se avisó? |
|---|---|---|---|
| | | | |
