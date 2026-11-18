# Resultados del experimento: pérdidas ante una caída

Tasa de envío: 5 msg/s desde `gb`. `ga` se mata con `docker kill` y se levanta tras D s.
Central con 10 % de respuestas perdidas y 10 % de reenvíos dobles (fallos inyectados).

## Todas las repeticiones

| Modo | Caída (s) | Rep | Caída real (s) | Enviados | Durante caída | Faltantes | Dup. en pantalla | Dup. descartados | Recuperados vía /history | T. recuperación (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| recovery | 2 | 1 | 4.8 | 61 | 24 | 0 | 0 | 28 | 21 | 0.01 |
| recovery | 2 | 2 | 4.7 | 61 | 24 | 0 | 0 | 27 | 22 | 0.25 |
| recovery | 2 | 3 | 4.7 | 61 | 24 | 0 | 0 | 24 | 21 | 0.25 |
| recovery | 5 | 1 | 7.6 | 76 | 38 | 0 | 0 | 43 | 36 | 1.09 |
| recovery | 5 | 2 | 7.7 | 76 | 39 | 0 | 0 | 37 | 37 | 0.89 |
| recovery | 5 | 3 | 7.3 | 76 | 37 | 0 | 0 | 46 | 35 | 1.2 |
| recovery | 10 | 1 | 12.7 | 101 | 64 | 0 | 0 | 47 | 62 | 0.02 |
| recovery | 10 | 2 | 12.6 | 101 | 63 | 0 | 0 | 63 | 60 | 0.02 |
| recovery | 10 | 3 | 12.8 | 101 | 64 | 0 | 0 | 48 | 62 | 0.03 |
| norecovery | 2 | 1 | 4.5 | 61 | 23 | 0 | 0 | 5 | 0 | 0.48 |
| norecovery | 2 | 2 | 5.1 | 61 | 26 | 1 | 0 | 1 | 0 | no se recuperó |
| norecovery | 2 | 3 | 5.6 | 61 | 29 | 2 | 0 | 6 | 0 | no se recuperó |
| norecovery | 5 | 1 | 8.8 | 76 | 44 | 4 | 0 | 7 | 0 | no se recuperó |
| norecovery | 5 | 2 | 8.8 | 76 | 44 | 1 | 0 | 7 | 0 | no se recuperó |
| norecovery | 5 | 3 | 9.1 | 76 | 46 | 5 | 0 | 7 | 0 | no se recuperó |
| norecovery | 10 | 1 | 13.1 | 101 | 66 | 25 | 0 | 9 | 0 | no se recuperó |
| norecovery | 10 | 2 | 14.7 | 101 | 74 | 63 | 0 | 4 | 0 | no se recuperó |
| norecovery | 10 | 3 | 12.9 | 101 | 65 | 24 | 0 | 16 | 0 | no se recuperó |

## Resumen (media ± desviación estándar, n = repeticiones)

| Modo | Caída (s) | n | Faltantes (msg) | % perdido | Dup. en pantalla | Dup. descartados | T. recuperación (s) |
|---|---|---|---|---|---|---|---|
| recovery | 2 | 3 | 0.0 ± 0.0 | 0.0 % | 0 | 26.3 ± 2.1 | 0.17 ± 0.14 |
| recovery | 5 | 3 | 0.0 ± 0.0 | 0.0 % | 0 | 42.0 ± 4.6 | 1.06 ± 0.16 |
| recovery | 10 | 3 | 0.0 ± 0.0 | 0.0 % | 0 | 52.7 ± 9.0 | 0.02 ± 0.01 |
| norecovery | 2 | 3 | 1.0 ± 1.0 | 1.6 % | 0 | 4.0 ± 2.6 | 0.48 ± 0.00 |
| norecovery | 5 | 3 | 3.3 ± 2.1 | 4.4 % | 0 | 7.0 ± 0.0 | — |
| norecovery | 10 | 3 | 37.3 ± 22.2 | 37.0 % | 0 | 9.7 ± 6.0 | — |
