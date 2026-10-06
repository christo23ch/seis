---
tipo: fase
numero: "5I"
estado: completada
tags:
  - tipo/fase
  - fase/5I
  - estado/completada
  - area/frontend
  - area/motor
---

# Fase 5I — Formulario de alta: errores, validación guiada y datos que faltan

> **Registro canónico: `CHANGELOG.md` §[Fase 5I].** Rama `fase/5i-formulario-alta` (sale de
> `checkpoint/5f6-simulaciones-informes`, `dc812ef`), publicada, sin PR. Viene de [[Fase-5H-1]].

## Objetivo

Corregir lo que encontró la prueba manual del asistente de alta («Nueva inversión»): el 422 con
opcionales vacíos, los valores por defecto invisibles, la antigüedad negativa, la falta de
validación guiada, el depósito solo en %, el estado de conservación sin «no consta» y las
coordenadas sin rellenar.

## Diagnóstico (Paso 0)

- **422:** el formulario enviaba `aPayload(form.getValues())`, el texto crudo de los campos;
  cada opcional vacío viajaba como `""` y Pydantic no lo convierte en número. Presente en `main`
  (`f97f620`) y desde el commit inicial (`56a8116`): no lo introdujo ninguna fase reciente.
- **Antigüedad negativa:** ningún cálculo de antigüedad en todo el código; era el control
  (`type="number"` sin mínimo: flecha ↓ o rueda). Reproducido con Playwright («-2»). En el
  backend, con −6 meses M03 divide por cero (500): deuda abierta, no se toca el motor.
- **lat/lng:** el motor no las usa (ni ICU ni comparables); solo el mapa y la persistencia.

## Requisitos

| # | Bloque | Commit | Estado |
|---|---|---|---|
| A | El alta funciona con los campos opcionales vacíos | `301799c` | ✅ |
| B | Validación guiada del formulario de alta | `ea36a37` | ✅ |
| C | Depósito como importe o porcentaje (y corrección de A: valores perdidos al navegar) | `87b59c4` | ✅ |
| D | Estado de conservación desconocido ([[ADR-0020-estado-de-conservacion-no-consta\|ADR-0020]]) | `d7ee2c6` | ✅ |
| E | Coordenadas aproximadas desde la provincia (CartoCiudad/IGN) | `5e9dfd5` | ✅ |
| F | Documentación y Vault | ver `CHANGELOG.md` | ✅ |

## Criterio de salida

- Suite 1002 passed, 18 skipped, 0 failed; guarda del caso dorado (`test_invariante_5h1`) en
  verde en todos los bloques; 54 tests unitarios de frontend.
- E2E de alta, simulaciones, alta de inversión y validación guiada en verde en local y en la CI;
  `medir-desborde` y `guard-sesion` en verde en una pila aislada.

## Decisiones

- **Valores por defecto:** valor escrito si es el del contrato; marcador/ayuda si vacío
  significa «el motor estima» (escribirlo cambiaría su significado, P4/P5).
- **Coma decimal y miles:** «150.000» es 150000 en importes; en tasas, coeficientes y
  coordenadas el punto es decimal.
- **«No consta» ⇒ «malo»** por parámetro T3 (ADR-0020), y por defecto en el formulario.
- **Coordenada de referencia: la capital**, no el centro geográfico de la provincia.

## Pendiente que nace aquí

Perfil de inversor por cuestionario: [[feat-perfil-inversor-cuestionario]]. Deudas en
`docs/ESTADO_ACTUAL.md` §4 (backend 22-25, pruebas 5-7).
