---
tipo: adr
fase: "[[Fase-5J]]"
estado: aceptado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aceptado
  - area/motor
---

# ADR-0026: el plazo de la operación suma la inmovilización entre el cierre y la posesión

**Fecha:** 2026-10-07 · **Fase:** 5J-2b · **Base:** ADR-0022 (meses de inmovilización por
régimen), especificación §7 y §9. **Autorización:** expresa del responsable para tocar
`app/engine/` (CLAUDE.md §6.8) en esta fase, que **cambia cifras**; tabla antes/después aprobada.

## Contexto

M06 calculaba el plazo como ocupación + obra + comercialización. Faltaba el tramo desde el cierre
de la subasta hasta tener el inmueble: mejora de postura, aprobación del remate, pago del resto y
decreto. Durante ese tramo el capital está inmovilizado y el inmueble genera tenencia. La 5J-1 ya
calculaba esos meses por régimen, al plazo legal máximo, pero solo como dato informativo.

## Decisión

1. **`plazo_P50 = ocupación + obra + comercialización + meses de inmovilización`**, y
   `plazo_P80 = plazo_P50 × 1,4` como antes. El plazo alarga la tenencia (P50 y P80), los
   intereses de la hipoteca dentro de `c_v`, el coste de capital del precio límite (plazo P80),
   los plazos de los escenarios, la TIR, el ROI anualizado, el VAN y el colchón.
2. **Meses por régimen** (T3, `procedimiento.regimenes.*.meses_inmovilizacion`): judicial
   LO 1/2025 1,8 · judicial anterior 2,5 · AEAT 1,7 · TGSS 0,3 · notarial 1,2.
3. **Régimen judicial desconocido ⇒ lo desfavorable en cada dato:** el depósito del régimen de la
   LO 1/2025 (20 %, ADR-0024) y el plazo del régimen más largo (2,5 meses, el anterior). Aviso:
   «Por no constar la fecha de inicio, el plazo de la operación suma 2,5 meses… (con la LO 1/2025
   serían 1,8)». Decisión del responsable.
4. **Sin plazo en la norma** (extrajudicial, concursal) **y venta no reglada:** 2,5 meses
   (`procedimiento.meses_inmovilizacion_si_no_consta`), el mayor de la tabla. El aviso dice
   «estimación prudente, sin base legal». Decisión del responsable.
5. **Aproximación de la TIR (aceptada por el responsable):** los meses de inmovilización alargan
   el horizonte de los flujos (`n = round(plazo_P50)`) y reparten la tenencia en más meses, pero
   no tienen un tramo propio: el pago del resto del precio sigue en el mes 0 y el tramo posesorio
   sigue siendo el 45 % de `n`. En rigor, el resto del precio se paga al final del tramo de
   inmovilización y solo el depósito sale en el mes 0, lo que subiría algo la TIR. Se mantiene la
   estructura de flujos de M11 porque cambiarla movería además la TIR de todas las operaciones por
   un motivo distinto del de esta fase. **El horizonte se redondea a par** (`round` de Python): con
   15,5 meses, `n = 16`; con 14,5, `n = 14`. En el §19 la TIR se calcula sobre 16 meses, no 15,5,
   y parte de su caída viene de ese medio mes. Cambiarlo a «medio hacia arriba» movería la TIR de
   todas las operaciones con plazo fraccionario. **Decisión del responsable (2026-10-08): no se
   toca.** Queda como deuda vinculada al calendario real de la TIR (5H.2, auditoría E3), que
   sustituirá el horizonte entero por los plazos de M06.
7. **Deuda de diseño para la 5M:** la TIR con hipoteca sale idéntica a la TIR sin hipoteca (26,41 %
   en el §19, igual que antes 33,87 % en los dos). M11 calcula la TIR sobre los flujos de la
   operación sin apalancar: el mes 0 paga el precio entero con los intereses dentro de `c_v`, sin
   entrada del préstamo ni amortización, y la escalera fija el mismo ROI objetivo en los dos casos.
   La TIR no mide el efecto del apalancamiento. Comportamiento anterior a la fase.
6. **Lo que queda fuera:** el coste de los depósitos de subastas perdidas (es de cartera).

## Cifras del caso §19 (tabla aprobada)

Plazo 13 → 15,5 meses (P80 18,2 → 21,7); tenencia P50 3.120 → 3.720 €; coste de capital
3.659,05 → 4.362,72 €; escalera 51.317 / 60.011 / 68.731 / 80.022 → 50.753 / 59.447 / 67.941 /
78.529 €; RVC 1,077 → 1,064 (sigue «alcanzable»); semáforo amarillo sin cambio; TIR 33,87 → 26,41 %;
VAN 33.230,42 → 32.721,46 €; colchón 84,8 / 60,9 → 84,8 / 61,5 meses; capital para pujar 30.400 €
sin cambio. El umbral de coste de capital a partir del cual la escalera degenera baja de 6,13 % a
5,14 %, y el aviso del catálogo de parámetros pasa del 6 % al 5 %.

## Consecuencias

- **La foto del invariante (`tests/datos/invariante_5h1.json`) se regenera** con aprobación
  expresa; desde ahora vigila también los campos añadidos desde la 5H.1.
- El informe escribe el plazo con un decimal cuando no es entero («15,5 m (P50) / 21,7 m (P80)»;
  antes `:.0f` lo redondeaba a par y mostraba 16 / 22).
- `costes.plazo_desglose` gana `inmovilizacion`; «Ver cálculo» del plazo lo sustituye y un
  resultado anterior se explica con la fórmula de entonces.
- **Los informes oficiales ya emitidos no cambian** (snapshot por valor). Los análisis guardados
  conservan su resultado; reanalizarlos da las cifras nuevas.
- Sin migración: todo viaja en el JSON del resultado.

## Alternativas descartadas

- **Usar el plazo medio y no el máximo.** P4: la ausencia de datos penaliza; el máximo legal es
  la cota que el inversor debe poder aguantar.
- **Un tramo propio en los flujos de la TIR.** Ver el punto 5.
