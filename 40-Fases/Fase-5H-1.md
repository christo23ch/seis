---
tipo: fase
numero: "5H.1"
estado: completada
tags:
  - tipo/fase
  - fase/5H-1
  - estado/completada
  - area/motor
---

# Fase 5H.1 — Motor: correcciones y añadidos sin cambio del caso dorado

> **Registro canónico: `CHANGELOG.md` §[Fase 5H.1].** Base: `docs/AUDITORIA_MOTOR_ESPECIFICACION.md`
> (puntos E1, E5, E6 y el punto 5 del orden E7) y [[ADR-0016-coste-de-capital-como-coste-de-oportunidad|ADR-0016]] (D5).
> Rama `checkpoint/5f6-simulaciones-informes`, sin PR. Viene de [[Fase-5G-4]].

## Objetivo

Aplicar los puntos de la auditoría del motor que **no cambian el caso dorado §19**, con
autorización expresa para tocar `app/engine/` solo para ellos.

## Requisitos

| # | Bloque | Commits | Estado |
|---|---|---|---|
| A | VAN y diferencial TIR − coste de capital (E6) | `31dd511` | ✅ |
| B | Coste de capital solo sobre el capital propio (D5, E1) + correcciones de la revisión | `5cb0634`, `1386faa` | ✅ |
| C | Colchón de plazo (§9.5, E5) | `f2bc04a` | ✅ |
| D | Especificación coherente con el motor (§9.1, §19) y documentación | ver `CHANGELOG.md` | ✅ |

## Criterio de salida

- **Guarda invariante:** `backend/tests/datos/invariante_5h1.json` (foto del resultado completo
  del §19 y del §19 con hipoteca, tomada con el motor de `ea60803` antes de empezar).
  `test_invariante_5h1.py` exige que el §19 no cambie ni una de sus 510 hojas y que el caso con
  hipoteca solo cambie lo listado en `CAMBIOS_HIPOTECA` (cuatro hojas, todas de D5).
- CI en verde tras cada bloque; suite al cerrar: 965 passed, 18 skipped, 0 failed.

## Cifras nuevas

| Caso | Magnitud | Valor |
|---|---|---|
| §19 | VAN al coste de capital (1,5 %) | 33.230,42 € |
| §19 | TIR − coste de capital | +32,37 puntos |
| §19 | Colchón de plazo | 84,8 meses a P_objetivo · 60,9 a P_max |
| §19 con hipoteca (LTV 70 %, 3,5 %) | Precio límite | 77.100 € → **78.156 €** |
| §19 con hipoteca | Coste de capital | 3.659,05 € → 2.603,76 € |

## Revisión de código

Los bloques B y C pasaron por el agente `code-reviewer`, con la guarda y el ADR como contexto.
Resultado: 0 críticos y 0 altos en los dos. Se corrigió todo lo que caía dentro de la fase:

- **B:** el test del `max(0, …)` no saturaba con LTV 1,2.
- **C:** con escalera degenerada se evaluaba a un precio ficticio; además, un supuesto que el
  ADR no declaraba.

Cada corrección de test se comprobó **mutando el código**: el test nuevo falla sin el arreglo.

## Decisiones tomadas durante la fase

```dataview
LIST
FROM #tipo/adr
WHERE fase = link(this.file.link)
```

## Deuda que deja abierta

En `docs/ESTADO_ACTUAL.md` §4:
- **Backend 18:** lo que queda de la auditoría para la 5H.2 (E3, E2 b, depósito, E4, E8).
- **Backend 19:** los intereses del préstamo van a plazo P50 dentro de un límite P80.
- **Backend 20:** `ltv` sin validar.
- **Backend 21:** supuestos revisables del colchón.
- **Pruebas 5:** carrera intermitente en el paso 4 de la e2e de simulaciones.
