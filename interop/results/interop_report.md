# Ensayo de interoperabilidad — 2026-11-17 19:14

Grupos: `amaya` (nuestro), `amaya2` (nuestro (copia)), `ext1` (ajeno correcto), `ext2` (ajeno con errores)

## 0. Registro en el central

* `amaya`: ✅ registrado
* `amaya2`: ✅ registrado
* `ext1`: ✅ registrado
* `ext2`: ✅ registrado

## 1. Conversación global

Mensajes escritos: 8 (2 por grupo). Orden de referencia: historial del central ordenado por (lamport, origin).

| Grupo | Ve todos | Faltan | Duplicados | Mismo orden que el central |
|---|---|---|---|---|
| `amaya` | ✅ | 0 | 0 | ✅ |
| `amaya2` | ✅ | 0 | 0 | ✅ |
| `ext1` | ✅ | 0 | 0 | ✅ |
| `ext2` | ✅ | 0 | 0 | ❌ (ordena distinto) |

## 2. Caída y recuperación por turnos

Cada grupo se apaga con `docker kill`; los otros tres escriben 3 mensajes cada uno; queda caído ≈ 8 s en total; se levanta y se esperan 8 s.

| Grupo caído | Escritos durante la caída | Recuperados | Faltan | Duplicados en pantalla | Conserva el historial anterior (8 msgs) |
|---|---|---|---|---|---|
| `amaya` | 9 | 9 | 0 | 0 | ✅ |
| `amaya2` | 9 | 9 | 0 | 0 | ✅ |
| `ext1` | 9 | 9 | 0 | 0 | ✅ |
| `ext2` | 9 | 9 | 0 | 0 | ❌ (0/8) |

## 3. Robustez de nuestro servidor ante mensajes de otros grupos

Se envían directamente a `amaya` `POST /fed/messages` como si el central los reenviara.

| Caso | Respuesta de `amaya` | Interpretación |
|---|---|---|
| lamport como texto ("42") | 200 | aceptado (tolerante) |
| sent_at en otro formato ("10/11/2026 14:03") | 200 | aceptado (tolerante) |
| sin sent_at | 200 | aceptado (tolerante) |
| campos desconocidos (room, prioridad) | 200 | aceptado (tolerante) |
| falta el campo from | 400 | rechazado con 4xx: el central no reintenta |
| lamport negativo | 400 | rechazado con 4xx: el central no reintenta |
| lamport no numérico ("abc") | 400 | rechazado con 4xx: el central no reintenta |
| cuerpo que no es JSON válido | 400 | rechazado con 4xx: el central no reintenta |

