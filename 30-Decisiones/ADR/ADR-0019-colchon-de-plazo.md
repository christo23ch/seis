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

# ADR-0019: colchón de plazo (§9.5) con el beneficio base y el coste mensual de mantener la operación

**Fecha:** 2026-10-04 · **Fase:** 5H.1-C · **Base:** especificación §9.5 y auditoría 5G.4, punto
E5 (`docs/AUDITORIA_MOTOR_ESPECIFICACION.md`). **Decisión revisable:** §9.5 deja supuestos sin
definir y aquí se eligen; se marcan abajo.

## Contexto

§9.5 enumera como «salida obligatoria del informe»:

> Colchón de plazo = meses extra soportables hasta B=0 (por coste de tenencia+capital mensual)

y pide reportarlo «a P_objetivo y a P_max». El motor no lo calculaba. La especificación no dice
con qué beneficio (base o pesimista), qué es exactamente el «capital mensual», ni qué hacer con
la hipoteca.

## Decisión

```
colchón(P) = max(0, B_base(P)) / coste_mensual(P)

B_base(P)        = VS_p − I(P, C_F^P50)                     # beneficio del escenario base
coste_mensual(P) = tenencia_mensual                          # IBI, comunidad, seguros… (M06)
                 + LTV · P · i / 12                          # intereses del préstamo (solo hipoteca)
                 + cc · capital_propio(P) / 12               # coste de oportunidad (ADR-0016)
capital_propio(P) = I(P, C_F^P50) − LTV · P                   # como en el precio límite (ADR-0018)
```

Se calcula a **P_objetivo** (`decision.colchon_plazo_meses`) y a **P_max**
(`decision.colchon_plazo_meses_p_max`), con un decimal.

**Supuestos que §9.5 no fija (revisables):**

1. **Beneficio del escenario base, no el pesimista.** El colchón responde a cuánto puede
   alargarse el plan antes de perder dinero. Con el pesimista se mezclarían dos estreses (precio
   y plazo) y el número dejaría de leerse como «meses de margen». Si se quisiera el pesimista,
   bastaría con cambiar `B_base` por `B_pesimista`.
2. **«Capital mensual» = coste de oportunidad del capital propio + intereses reales del
   préstamo.** Es la misma lectura del capital que hacen [[ADR-0016]] y [[ADR-0018]]: el capital
   propio cuesta su coste de oportunidad y la parte financiada cuesta sus intereses, no las dos
   cosas.
3. **Coste mensual constante.** Un mes más de plazo cuesta lo mismo que el anterior. No modela
   que la reforma ya pagada inmovilice más capital con el tiempo ni subidas de tipos.
4. **Sin beneficio, 0 meses; sin ningún coste mensual (o negativo), `None`; con la escalera
   degenerada, `None`** (no hay precios utilizables y pueden ser ≤ 0). No se devuelve infinito
   ni un número negativo, ni se evalúa a un precio ficticio.
5. **B_base no descuenta el coste de oportunidad del plazo ya previsto.** Sí descuenta la
   tenencia (en C_F^P50) y, con hipoteca, los intereses del préstamo de ese plazo (en `c_v`,
   M06). El colchón cuenta los meses **extra** desde un beneficio que, como el ROI, no incluye
   el coste de oportunidad (ADR-0016). Restar también `cc · capital_propio · plazo_P50/12`
   daría un colchón menor: es la alternativa si se quiere una lectura más prudente. Señalado en
   la revisión de código del bloque.

**Informativo:** no entra en el ICO, el semáforo, los vetos ni la escalera.

## Valores

| Caso | A P_objetivo | A P_max |
|---|---|---|
| §19 (cash, cc 1,5 %, tenencia 240 €/mes) | **84,8 meses** | **60,9 meses** |
| §19 sin coste de capital (solo tenencia) | 147,3 meses | — |
| §19 con hipoteca (LTV 70 %, 3,5 %) | menor: suma 118 €/mes de intereses y resta el coste de oportunidad de la parte financiada | — |

Comprobación del §19 a P_objetivo: B = 35.348,68 €; coste mensual = 240 + 0,015 · 141.395,76 / 12
= 416,74 €/mes; 35.348,68 / 416,74 = 84,8 meses.

## Presentación

- Informe (M14), sección 7: «Colchón de plazo: 84,8 meses a precio objetivo (60,9 a precio
  máximo), hasta beneficio cero por tenencia y coste de capital.» Sin dato, no se imprime.
- Interfaz: fila «Colchón de plazo» en «Métricas de decisión» y en la comparación de
  simulaciones, a precio objetivo.

## Consecuencias

- **Ningún valor existente cambia:** son dos campos nuevos y opcionales. La guarda
  `tests/test_invariante_5h1.py` lo comprueba sobre el §19 y el caso con hipoteca.
- **Los resultados anteriores** no traen el campo y la interfaz no muestra la fila.

## Alcance: dónde NO llega esta decisión ([[ADR-0014]])

1. No incluye el **coste del depósito** inmovilizado (auditoría E5, fuera de la 5H.1).
2. No usa los **plazos reales por fase** de M06: el colchón se mide desde el plazo total
   previsto, no fase a fase.
3. No es un **análisis de sensibilidad**: no dice qué pasa si además cae el valor de salida.
