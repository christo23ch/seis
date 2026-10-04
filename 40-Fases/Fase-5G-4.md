---
tipo: fase
numero: "5G.4"
estado: completada
tags:
  - tipo/fase
  - fase/5G-4
  - estado/completada
  - area/motor
---

# Fase 5G.4 — Coste de capital, decimales en formato español y e2e en CI

> **Registro canónico: `CHANGELOG.md` §[Fase 5G.4].** Esta nota no lo copia: resume y enlaza.
> Rama `checkpoint/5f6-simulaciones-informes`, sin PR. Cerrada el 2026-10-03.

## Objetivo

Decidir qué es el coste de capital del motor y cómo se explica, sin tocar ningún cálculo
(decisiones D1–D5 del responsable), dejar el informe en formato español, llevar las dos e2e a la
CI y preparar la 5H con una auditoría del motor frente a la especificación.

## Requisitos

| # | Bloque | Commit | Estado |
|---|---|---|---|
| A | Coste de capital como coste de oportunidad: rango 0–0,15 vinculante, aviso desde 0,06, explicación en informe e interfaz | `3ecc9c8` | ✅ |
| B | Decimales en formato español en el informe («25,0 %», «RVC 1,08») | `729efd5` | ✅ |
| C | E2E en CI, lanzadores unificados (`CHROMIUM_PATH`), desbordamiento de `/app` | `e2284da` | ✅ |
| C′ | Corrección tras la primera CI: escalera a 390 px en Linux/macOS y tasa «1, %» | `b74abd0` | ✅ |
| D | [[ADR-0016-coste-de-capital-como-coste-de-oportunidad\|ADR-0016]] y documentación | `e1dd01f` | ✅ |
| E | Auditoría del motor frente a la especificación (`docs/AUDITORIA_MOTOR_ESPECIFICACION.md`) | `ea60803` | ✅ |

**CI en verde con los cuatro jobs** (suite, PostgreSQL, frontend y el nuevo `e2e`):
[36921942152](https://github.com/christo23ch/seis/actions/runs/36921942152) (tras `b74abd0`),
[37138547350](https://github.com/christo23ch/seis/actions/runs/37138547350) (D) y
[37138832309](https://github.com/christo23ch/seis/actions/runs/37138832309) (E).
Suite al cerrar: 922 passed, 18 skipped, 0 failed.

## Criterio de salida

- **Ningún cálculo del motor cambia.** Guardas que fijan los valores de M11, M12 y M13 del caso
  §19 capturados antes de la fase.
- **El job `e2e` de la CI ejecuta las dos e2e** (alta y simulaciones) y está en verde.

## Lo que hay que saber de esta fase

- **La primera ejecución del job `e2e` falló, y era un defecto del producto anterior a la fase.**
  La escalera de precios desbordaba 8 px a 390 px en Linux y macOS, donde la monoespaciada del
  sistema es más ancha que Consolas. La e2e mide ahora también con una monoespaciada ancha
  forzada, para verlo en Windows.
- **Un defecto propio:** la tasa del coste de capital salía «1, %» en la interfaz (una expresión
  regular perdió una barra al escribirse).
- **Umbral de degeneración del §19: coste de capital 6,13 %.** Por encima, la escalera es
  degenerada y el semáforo rojo.
- **La auditoría (E)** encontró que el §19 de la especificación no es reproducible, que la TIR
  del motor (33,87 %) no es la del documento (≈23 %, que era el ROI anualizado) y que la utilidad
  de rentabilidad del ICO no depende de la operación (E8).

## Decisiones tomadas durante la fase

```dataview
LIST
FROM #tipo/adr
WHERE fase = link(this.file.link)
```

## Deuda que deja abierta

En `docs/ESTADO_ACTUAL.md` §4: Backend 16–18 (doble cuenta con hipoteca, «depósito del 5%» de
SEM-EJEC-01, puntos de la auditoría), Frontend 11–14 y Entorno 7 (duración variable de la
suite). La continuación es [[Fase-5H-1]].
