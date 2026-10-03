---
tipo: adr
fase: "[[Fase-5G-4]]"
estado: aceptado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aceptado
  - area/motor
  - area/parametros
---

# ADR-0016: el coste de capital es el coste de oportunidad del capital propio, con rango 0–15 % y aviso desde el 6 %

**Fecha:** 2026-10-01 · **Fase:** 5G.4 · **Decide:** el responsable del producto (decisiones D1–D5)

## Contexto

`capital.coste_capital_anual` (por defecto 0,015) es el único parámetro de coste del capital
del motor. Hasta la 5G.4:

- **Solo se resta del precio límite** (§9.1, `m12_decision.py:121-126`):
  `coste_capital = cc · I(P_max, C_F^P80) · plazo_p80 / 12` y `P_límite = P(0, VS_p, C_F^P80) − coste_capital`.
  ROI, ROI anualizado y TIR (M11) **no lo incluyen**, y el P_ideal, el P_objetivo y el P_max
  tampoco dependen de él.
- **No tenía significado declarado.** El catálogo lo describía como «coste anual de
  oportunidad» sin decir de qué capital, y la especificación usa `coste_capital(plazo)` en
  §9.1/§9.3 **sin definir nunca la función** (ver la auditoría de la 5G.4,
  `docs/AUDITORIA_MOTOR_ESPECIFICACION.md`, punto E2).
- **No tenía rango.** Rango, advertencia y nivel de riesgo valían `pendiente_de_definir`, y se
  aceptaban sin aviso valores como 0,31, 0,4 o 0,95 (simulaciones de 5G.1/5G.2 y fixtures de
  test), que bastan para degenerar la escalera.
- **Con hipoteca cuenta dos veces** la parte financiada: los intereses del préstamo ya están en
  `c_v` (M06) y el coste de capital se aplica además sobre toda la inversión.

Sensibilidad medida con el motor en memoria sobre el caso de referencia §19 (flip integral,
cash), variando solo este parámetro:

| Coste de capital | Importe restado | P_límite | Escalera degenerada | Semáforo |
|---|---|---|---|---|
| 0 | 0 € | 83.681 € | no | amarillo |
| 0,015 (defecto) | 3.659 € | 80.022 € | no | amarillo |
| 0,03 | 7.318 € | 76.363 € | no | amarillo |
| 0,05 | 12.197 € | 71.484 € | no | amarillo |
| 0,08 | 19.515 € | 64.166 € | **sí** | **rojo** |
| 0,10 | 24.394 € | 59.287 € | sí | rojo |
| 0,15 | 36.591 € | 47.091 € | sí | rojo |
| 0,20 | 48.787 € | 34.894 € | sí | rojo |

En todas las filas P_ideal = 51.317 €, P_objetivo = 60.011 €, P_max = 68.731 €, ROI 25,0 %,
ROI anualizado 22,87 %, TIR 33,87 % y RVC 1,077: el parámetro **no los mueve**.

**Umbral de degeneración en el §19: cc = 0,061285 (6,13 %).** Se obtuvo de dos formas que
coinciden: algebraicamente, `(83.681 − 68.731) / (160.837 · 18,2/12)`, y por bisección sobre el
motor completo (0,0612 no degenera; 0,0613 sí). Por encima, P_límite cae por debajo de P_max, la
escalera es degenerada (§9.3) y el semáforo pasa a rojo sin que cambie nada más.

## Decisión

**D1 · Significado.** `capital.coste_capital_anual` es el **coste de oportunidad del capital
propio**: lo que rendiría ese dinero en otra inversión de riesgo comparable. No es el tipo de
un préstamo (eso es `financiacion.interes_anual_pct`, dato de entrada) ni una tasa libre de
riesgo.

**D2 · Rango técnico admitido: 0 a 0,15, ambos incluidos.** Fuera de él el valor se
**rechaza** (HTTP 422), tanto en una simulación como en la edición global
(`PUT /parametros`). Es un límite de negocio que fija este ADR, no una cota técnica derivada
del código como las de ICO, ICI, RA o margen de seguridad. Con la misma función
(`simulacion_service.validar_rangos`), esas 11 cotas técnicas que ya estaban en el catálogo
pasan también a ser vinculantes.

**D3 · Aviso no bloqueante desde 0,06.** El catálogo lleva `umbral_aviso = 0,06` y el texto:
«Por encima del 6 % la escalera de precios suele degenerar (umbral medido en el caso de
referencia §19: 6,13 %)». El editor de simulaciones lo muestra en el campo y **no impide
crear** la simulación.

**D4 · Valor por defecto 0,015, editable.** Se mantiene, y sigue siendo editable por
simulación (editor) y de forma global (`/app/parametros`, superadmin).

**D5 · Con hipoteca, el coste de capital se aplicará solo al capital propio.** Aceptada, **no
implementada en la 5G.4**: cambia el cálculo del precio límite y queda para la **5H**. La parte
financiada (LTV · P) ya soporta su coste real como intereses dentro de `c_v`; aplicarle además
el coste de oportunidad la cuenta dos veces. Diseño y medida del impacto en la auditoría de la
5G.4, punto E1.

## Consecuencias

- **Ningún cálculo cambia en la 5G.4.** Los tests de la fase fijan los valores de M11, M12 y M13
  del caso §19 capturados antes del cambio. M12 solo añade la tasa aplicada a
  `precios.detalle["coste_capital_anual"]`, para que el resultado explique de dónde sale el
  importe.
- **El informe y la interfaz lo explican.** M14 y la tarjeta de la escalera de precios dicen:
  «El coste de capital (X % anual, coste de oportunidad del capital propio) solo se descuenta del
  precio límite (§9.1); ROI y TIR no lo incluyen. Importe aplicado: Y €.» Si falta la tasa o el
  importe —resultados anteriores a 5G.4—, no se afirma nada.
- **Datos ya guardados.** Las simulaciones creadas antes con valores fuera de rango (p. ej. 0,31)
  se siguen leyendo: el rango solo se comprueba al crear. No se revalida lo histórico (P1).
- **Tests.** Los fixtures que usaban valores fuera del nuevo rango a través de la API o del
  servicio pasan a valores dentro (0,07–0,14). Los que ejercen el motor directamente, sin
  validación, conservan el 0,31 del hallazgo de 5G.2.
- **Una simulación por encima del 6 % no se prohíbe:** puede ser legítimo en un perfil de capital
  caro. Por eso es un aviso y no un rango más estrecho.

## Alcance: dónde NO llega esta decisión ([[ADR-0014]])

1. **No aplica D5.** Hasta la 5H, con hipoteca el precio límite sigue contando dos veces el
   coste del tramo financiado.
2. **No define `coste_capital()` en la especificación.** La fórmula sigue siendo la del código;
   la propuesta de definición está en la auditoría (E2) y es decisión de la 5H.
3. **No añade la comparación TIR − coste de capital ni el VAN** (opción «D» de la
   investigación previa). Diseño en la auditoría (E6).
4. **No cambia el perfil rentista,** que según §9.2 no debería restar coste de capital y en el
   código sí lo resta (auditoría, E4).
5. **El umbral de aviso es el del §19.** En otros activos la escalera puede degenerar antes o
   después del 6 %: el aviso dice «suele», no «degenera».
6. **El editor global de `/app/parametros` no muestra el aviso**: es un editor libre de JSON sin
   los metadatos del catálogo. Sí recibe el 422 con el rango si el valor está fuera.
