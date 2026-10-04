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

# ADR-0018: con hipoteca, el coste de capital del precio límite solo se aplica al capital propio

**Fecha:** 2026-10-04 · **Fase:** 5H.1-B · **Implementa:** la decisión D5 de [[ADR-0016]] ·
**Base:** auditoría 5G.4, punto E1 y hecho H1 (`docs/AUDITORIA_MOTOR_ESPECIFICACION.md`).

## Contexto

[[ADR-0016]] fijó que el coste de capital es el coste de oportunidad del capital **propio** (D1)
y aceptó, para la 5H, no cobrárselo a la parte financiada (D5). Hasta ahora, con hipoteca, el
precio límite contaba dos veces el coste de esa parte:

1. M06 mete los intereses del préstamo en `c_v` (`LTV · i · plazo_P50/12`), y `c_v` entra en el
   P_límite bruto.
2. M12 restaba además `cc · I(P_max, C_F^P80) · plazo_P80/12` sobre **toda** la inversión.

La auditoría (H1) mostró además que `I(P_max, C_F^P80)` no depende de la financiación: en el
§19 vale exactamente VS_pes con cash y con hipoteca. Por eso el coste de capital era idéntico
con y sin préstamo, y la única forma de que la financiación cuente es restar la parte
financiada.

## Decisión

```
capital_propio = max(0, I(P_max, C_F^P80) − LTV · P_max)     # LTV = 0 si no hay hipoteca
coste_capital  = cc · capital_propio · plazo_P80 / 12          # interés simple, como antes
P_límite       = P(0, VS_p, C_F^P80) − coste_capital
```

- **Sin hipoteca** (`financiacion.tipo != "hipoteca"`) la fórmula es **exactamente la de antes**.
- **`max(0, …)`**: con una financiación igual o mayor que la inversión, el coste de capital es
  0, nunca un abono.
- **Trazabilidad:** `decision.precios.detalle["capital_propio"]` guarda la base usada, junto a
  `coste_capital` y `coste_capital_anual`.
- **También en el rentista con hipoteca**, porque D5 es general. Que el rentista reste o no
  coste de capital (§9.2, auditoría E4) es otra decisión y queda fuera.

## Impacto medido

| Caso | Coste de capital | P_límite | Otros cambios |
|---|---|---|---|
| §19 (cash) | 3.659,05 € → 3.659,05 € | 80.022 € → 80.022 € | ninguno (guarda de 510 hojas) |
| §19 con hipoteca (LTV 70 %, 3,5 %) | 3.659,05 € → **2.603,76 €** | 77.100 € → **78.156 €** | el plan de puja y el checklist citan el límite nuevo |

- **Lo que se deja de cobrar** es exactamente la parte financiada:
  `0,015 · 0,7 · 66.266,09 · 18,2/12 = 1.055,29 €` (P_max del caso con hipoteca). El límite sube
  1.056 € por el redondeo al euro. Capital propio: 160.837,44 − 0,7 · 66.266,09 = 114.451,18 €.
- **Fuera del límite no cambia nada:** escalera, semáforo, ICO, puja y RVC siguen igual.
  `tests/test_invariante_5h1.py` lista las cuatro hojas que cambian en el caso con hipoteca
  (`CAMBIOS_HIPOTECA`) y falla ante cualquier otra.

## Consecuencias

- **Los análisis con hipoteca** emitidos a partir de ahora tienen un precio límite algo más alto
  (≈ cc · LTV · P_max · plazo/12).
- **Los informes oficiales ya emitidos no cambian:** son snapshots por valor y el servicio nunca
  vuelve a ejecutar el motor (5F.3). Hay un test que lo comprueba con un informe congelado con el
  límite anterior.
- **Los análisis y simulaciones ya guardados** conservan su resultado hasta que se reanalicen,
  como en cualquier cambio del motor (P1).

## Alcance: dónde NO llega esta decisión ([[ADR-0014]])

1. **No corrige el plazo de los intereses.** M06 los calcula a plazo P50 dentro de un límite que
   lo demás estresa a P80. La auditoría (E1) midió −774 € de P_límite bruto si se calculasen a
   P80. Queda pendiente: cambia `c_v`, que es uno solo para toda la escalera.
2. **No cambia la definición del precio límite** (auditoría, E2 b), que también integraría D5. Si
   se adopta, sustituye a esta fórmula.
3. **No modela la deuda en M11:** ROI, TIR y VAN siguen sobre la inversión total ([[ADR-0017]]).
