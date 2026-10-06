---
tipo: adr
fase: "[[Fase-5H-1]]"
estado: aceptado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aceptado
  - area/motor
---

# ADR-0017: VAN al coste de capital y diferencial TIR − coste de capital, informativos y con los flujos de la TIR

**Fecha:** 2026-10-04 · **Fase:** 5H.1-A · **Base:** auditoría 5G.4, punto E6
(`docs/AUDITORIA_MOTOR_ESPECIFICACION.md`) y [[ADR-0016]] (el coste de capital es el coste de
oportunidad del capital propio).

## Contexto

Desde la 5G.4 el coste de capital solo se descuenta del precio límite (§9.1). El ROI y la TIR
de M11 no lo incluyen, y el informe lo explica, pero no había ninguna cifra que respondiera a la
pregunta del inversor: **¿cuánto rinde esta operación por encima de lo que rendiría mi dinero en
otra parte?** P7 de la especificación («el capital tiene coste y el tiempo es un coste») lo pide,
y la especificación no define ni VAN ni tasa de descuento.

## Decisión

M11 calcula dos indicadores **informativos**:

- **`van_coste_capital`**: VAN, en euros, de los flujos mensuales descontados al coste de capital.
- **`diferencial_tir_coste_capital`**: TIR − coste de capital, en **puntos porcentuales**.

Convenciones, todas para no inventar ningún supuesto nuevo:

1. **Los mismos flujos que la TIR:** `_flujos_detallados`, escenario **base**, a **precio
   objetivo**, con el mismo calendario (`m11_rentabilidad.py`). Si el calendario cambia algún día
   (auditoría, E3), los dos indicadores cambian con él y siguen siendo coherentes.
2. **El coste de capital es una tasa efectiva anual** y se pasa a mensual con
   `r = (1 + cc)^(1/12) − 1`. Es la misma equivalencia con la que `_tir_anual` anualiza la TIR
   mensual (`(1 + r)^12 − 1`). Consecuencia comprobada en los tests: **el VAN vale 0 exactamente
   cuando cc = TIR**, y el diferencial y el VAN siempre tienen el mismo signo.
3. **El diferencial usa la TIR redondeada a 4 decimales**, la misma que se muestra, para que
   `TIR mostrada − cc = diferencial mostrado` sin descuadres de redondeo.
4. **Son informativos:** no entran en el ICO, el semáforo, los vetos ni la escalera.
5. **Campos opcionales** (`None` por defecto). Los resultados anteriores a la 5H.1 no los traen,
   se leen igual y la interfaz no muestra la fila.

Presentación:
- Informe (M14), sección 7: «VAN al coste de capital (1,5 %): 33.230 € · TIR frente a coste de
  capital: +32,37 puntos». Si falta el dato, no se imprime.
- Interfaz: dos filas en «Métricas de decisión» y dos en la comparación de simulaciones, sin
  colores de mejor o peor.

## Valores en el caso §19

| Coste de capital | VAN | TIR − coste de capital |
|---|---|---|
| 0 | 35.348,68 € (= beneficio base) | +33,87 puntos |
| **0,015 (defecto)** | **33.230,42 €** | **+32,37 puntos** |
| 0,05 | 28.545 € | +28,87 puntos |
| 0,10 | 22.417 € | +23,87 puntos |
| 0,15 | 16.871 € | +18,87 puntos |

Con hipoteca (LTV 70 %, 3,5 %) el VAN es el mismo salvo céntimos: M11 trabaja sobre la inversión
total (auditoría, H1 y H2), y la diferencia de 0,72 € sale del redondeo de P_objetivo al euro.

## Consecuencias

- **Ningún valor existente cambia.** La guarda `tests/test_invariante_5h1.py` compara 510 hojas
  del resultado del §19 con su foto anterior a la fase.
- El catálogo de `capital.coste_capital_anual` dice ahora que el parámetro también mueve estos
  dos indicadores.
- El informe del §19 gana una línea, recogida de forma explícita en
  `test_informe_coherencia.py`.

## Alcance: dónde NO llega esta decisión ([[ADR-0014]])

1. **No usa el capital propio.** El VAN se calcula sobre la inversión total, como la TIR: no
   modela la deuda (principal y cuotas) ni el apalancamiento. Con hipoteca no es un VAN del
   equity.
2. **Solo el escenario base y a precio objetivo.** No hay VAN pesimista ni VAN a P_max.
3. **Hereda el calendario de la TIR**, que es una decisión del código con fracciones fijas
   (auditoría, E3). Mientras no se corrija, el VAN tampoco usa los plazos reales de M06.
4. **Interés compuesto mensual**, a diferencia del precio límite, que aplica el coste de capital
   como interés simple (ADR-0016). Son cifras distintas y miden cosas distintas: no deben
   sumarse ni compararse sin explicarlo.
