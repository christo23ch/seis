# Impacto en el motor de los umbrales legales de puja — análisis y diseños

**Fase:** 5J-0 (solo análisis; ningún cambio de código ni de base de datos)
**Fecha:** 2026-10-06
**Base legal:** `docs/INVESTIGACION_PROCEDIMIENTOS_SUBASTA.md` (las referencias «Inv. §x» remiten a ella)

> Cualquiera de los diseños toca `app/engine/`, y CLAUDE.md §6.8 exige indicación expresa para
> ello. Todos cambian el informe del caso dorado §19 y los diseños B y C cambian además alguna
> cifra o el semáforo. Este documento sirve para decidir **antes** de pedir esa autorización.

---

## 1 · Dónde se usan hoy los precios y el depósito

### 1.1 Escalera de precios (P_ideal, P_objetivo, P_max, P_límite)

Nacen en `m12_decision.calcular_escalera` (`backend/app/engine/modules/m12_decision.py:65-148`)
como **techos económicos**: el precio más alto que deja el margen exigido. Ninguna fórmula
conoce el procedimiento de subasta, salvo `inp.perfil` y la financiación.

| Consumidor | Qué usa | Fichero |
|---|---|---|
| Marca `degenerada` (exige 0 < ideal < objetivo < máx < límite) | los cuatro | `m12_decision.py:146-147` |
| Rentabilidad y escenarios **a P_objetivo** | P_objetivo | `pipeline.py:90-91`, `m11_rentabilidad.evaluar` |
| Margen de seguridad (MS_valor) | P_objetivo | `pipeline.py:103`, `m12_decision.py:295` |
| Colchón de plazo | P_objetivo y P_max | `pipeline.py:116-119`, `m11_rentabilidad.colchon_plazo` |
| Viabilidad VPO | P_objetivo | `pipeline.py:82-84` |
| **RVC = P_max / P_adj** | P_max | `m13_puja.py:36` |
| Regla T2 VETO-COMP-01 (RVC < `rvc_veto` del perfil) | RVC | `rules/catalogo.yaml:141-151` |
| Semáforo (umbrales de RVC por color) | RVC | `m12_decision.py:263-277`, `defaults.yaml:151-154` |
| Plan de puja (texto «Cargar límites…») | objetivo, máx., límite | `m13_puja.py:63-68` |
| Informe Markdown (página de decisión y §7) | los cuatro | `m14_informe.py:103, 198-200, 239-241, 281` |
| Persistencia | columnas `p_ideal…p_limite` de `Decision` | `models.py:197-200`, `analisis_service.py:126-127` |
| Listados, comparativa y simulaciones | P_objetivo, P_max, RVC | `api/routes.py:310`, `analisis_service.py:199`, `parametros_simulables_service.py:163-166` |
| Frontend | escalera, métricas, comparación de simulaciones | `components/resultado.tsx:46-109, 238-270`, `components/simulaciones/comparacion.tsx:151-154` |

### 1.2 Precio de adjudicación esperado (P_adj) y RVC

`m13_puja.py:8-36`: `P_adj = VT · ratio`, con `ratio` sacado de `adjudicacion.ratios` por fuente,
tipología y ocupación (`defaults.yaml:217-232`), −8 pp por cada subasta previa desierta, +6 pp
si VT/VM < 0,6, y acotado a [0,10; 1,10]. Para la vía judicial: **vivienda ocupada 0,42,
vacía 0,55, ocupación desconocida 0,45, resto 0,50**.

### 1.3 Depósito

| Uso | Detalle | Fichero |
|---|---|---|
| Entrada | `SubastaInput.deposito_pct`, **por defecto 0,05** | `engine/contracts.py:49` |
| Modelo | `subasta.deposito_pct`, `default=0.05` | `models.py:60` |
| Ingesta del BOE | importe ÷ valor; si falta alguno, **0,05** | `ingesta/boe.py:164`, `ingesta/contratos.py:29` |
| Plan de puja | «Depósito requerido: X € (5 % del valor de subasta)» | `m13_puja.py:53, 71` |
| Checklist | «Depósito disponible y transferido en plazo» | `m14_informe.py:82-83` |
| Condición T2 judicial | texto fijo «depósito del 5 %» | `rules/catalogo.yaml:224` |
| Costes (C_F) | **No entra.** Ni el coste del capital inmovilizado ni su importe (auditoría E5) | `m06_costes.py` |
| Capital del usuario | **No se compara** con ningún capital disponible: el motor no recibe ese dato | — |

### 1.4 Datos que el motor necesitaría y no tiene

| Dato | Para qué | Hoy |
|---|---|---|
| Régimen judicial (incoado antes o después del 3‑4‑2025) | depósito, plazos, umbrales, táctica | no existe |
| Vivienda habitual **del ejecutado** | suelo absoluto del 60 % | `activo.es_vivienda_habitual` existe, pero ninguna regla lo lee y vale `False` por defecto |
| Cantidad reclamada (principal, intereses y costas) | ruta del 40 % y cobertura de la deuda en la TGSS | no existe |
| Número de convocatoria (AEAT/TGSS) | coeficiente 0,8/0,6 del tipo; reglas de la 2.ª subasta de la TGSS | solo `subastas_desiertas_previas` |
| Puja mínima publicada | suelo de la AEAT (10 %) | `subasta.puja_minima` se captura y **ningún módulo la lee** |

---

## 2 · Qué ocurre hoy cuando un precio queda por debajo del mínimo legal

**Nada.** Ningún módulo compara un peldaño con un umbral. El caso dorado §19 (subasta judicial,
VT = 152.000 €, vivienda en precario) lo muestra con sus propias cifras:

| Peldaño | Importe | % de VT | Zona legal en el régimen nuevo (inmueble que no es vivienda habitual) |
|---|---|---|---|
| P_ideal | 51.317 € | 33,8 % | **< 40 %**: solo la aprueba el LAJ de forma discrecional |
| P_objetivo | 60.011 € | 39,5 % | **< 40 %**: ídem. Es el precio con el que se calculan ROI, TIR y escenarios |
| P_adj esperado | 63.840 € | 42,0 % | 40-50 %: aprobación automática solo si cubre la deuda (dato que no tenemos) |
| P_max | 68.731 € | 45,2 % | 40-50 %: ídem |
| P_límite | 80.022 € | 52,6 % | 50-70 %: aprobable si nadie mejora en 10 días |
| *50 % / 60 % / 70 %* | *76.000 / 91.200 / 106.400 €* | | |

Consecuencias, por orden de gravedad:

1. **El escenario central del informe puede ser jurídicamente inalcanzable.** ROI, TIR, VE y el
   margen de seguridad se calculan a P_objetivo, que en el §19 solo podría aprobarse por
   decisión discrecional del LAJ.
2. **Si fuera vivienda habitual del deudor, toda la escalera sería inaprobable** (el suelo es
   91.200 € y P_límite son 80.022 €) y el informe seguiría en **amarillo**.
3. **El RVC mide «ganar la puja», no «obtener el remate».** RVC = 1,08 («alcanzable») compara
   P_max con un P_adj del 42 %, que con la ley nueva tampoco es aprobable de forma automática.
4. **El depósito real es cuatro veces mayor** (régimen nuevo: 30.400 € frente a los 7.600 €
   que se anuncian).
5. **La táctica de puja es incorrecta para el régimen nuevo** (Inv. §2.4).

---

## 3 · Diseños propuestos

Los tres comparten una **capa de datos** común que conviene construir en cualquier caso:

- **Parámetros T3 por procedimiento** (sección nueva, p. ej. `procedimientos:` en
  `defaults.yaml`), con vigencia como el resto: depósito, puja mínima, umbrales de aprobación,
  suelos duros, plazos de pago y visibilidad de las pujas. Una entrada por clave
  `fuente × régimen` (`judicial_lec_2025`, `judicial_lec_2015`, `aeat`, `tgss_1a`, `tgss_2a`,
  `notarial_extrajudicial`…). Los valores salen de Inv. §5; las celdas ⚠️ quedan en `null` y el
  motor las trata como **dato ausente** (P4), nunca como «sin umbral».
- **Campos de entrada nuevos:** régimen judicial (`nuevo | anterior | desconocido`), vivienda
  habitual del ejecutado (`si | no | desconocido`, sustituyendo el booleano) y cantidad
  reclamada opcional. Exige una migración `0016` reversible.
- **Depósito por defecto desde el parámetro**, no desde el 0,05 fijo del contrato.

### Diseño A — Parámetros T3 y «zona legal» informativa

**Qué hace.** Un módulo puro nuevo, fuera de `modules/` como `fiscal.py`
(`engine/procedimiento.py`), clasifica cada peldaño y P_adj en una zona: `aprobacion_inmediata`,
`sujeta_a_mejora`, `aprobable_sin_mejora`, `solo_si_cubre_deuda`, `discrecional` o
`prohibida`. Se añade al resultado y al informe. **No cambia ningún precio, RVC ni semáforo.**

| Pros | Contras |
|---|---|
| Riesgo mínimo: ninguna cifra del caso dorado cambia, solo el texto | **No arregla el problema denunciado**: el informe sigue recomendando como objetivo un precio que no se puede aprobar; solo lo etiqueta |
| Prepara la capa de datos para B y C | Una etiqueta que el usuario puede pasar por alto, en contra de «P_límite es un bloqueo duro» |
| Deja medir cuántos análisis reales caen en cada zona antes de endurecer | |

**Esfuerzo:** pequeño-medio (parámetros, módulo, M14, interfaz y tests; migración solo para los
campos nuevos).

### Diseño B — A + veredicto de inviabilidad (reglas T2)

**Qué hace.** Sobre A, reglas T2 nuevas que actúan como cualquier veto o techo (P6, vetos antes
que promedios):

- **VETO-LEG-01 (rojo):** P_límite por debajo del **suelo duro** (vivienda habitual al 60 %, o
  la puja mínima de la AEAT). Ninguna puja económica es legal.
- **TECHO-LEG-02 (naranja + condición):** P_max en zona `discrecional`. Se puede pujar, pero la
  aprobación no depende del inversor.
- **CONDICION-LEG-03:** P_max en `sujeta_a_mejora` (riesgo de que un tercero la mejore en 10
  días).
- Dato ausente (régimen o vivienda habitual `desconocido`): se aplica el **supuesto más
  restrictivo** (P4) y se añade la carencia al ICI.

| Pros | Contras |
|---|---|
| Encaja en la arquitectura lexicográfica existente (vetos → techos); se audita igual que el resto | Los precios siguen siendo solo económicos: un naranja dice «cuidado», pero no dice **qué pujar** |
| Cumple «P_límite infranqueable» también en lo legal | **Cambia el caso dorado:** con P_max al 45 % en zona discrecional, el §19 pasaría de amarillo a **naranja** |
| Las reglas se editan sin desplegar (T2) | El umbral de «discrecional» es jurídicamente blando: vetar ahí sería excesivo, y por eso solo se propone techo |

**Esfuerzo:** medio (A + 3 reglas, hechos nuevos en la pizarra y tests negativos).

### Diseño C — A + B + escalera con precio económico y precio legal

**Qué hace.** Mantiene la escalera económica intacta (los techos, P1) y añade una **escalera de
puja recomendada** que respeta los umbrales:

```
suelo_util     = umbral de la zona que se elija como objetivo (p. ej. aprobable_sin_mejora)
P_puja(x)      = max(P_x, suelo_util)        si max(P_x, suelo_util) ≤ P_max
               = «no recomendable»          si suelo_util > P_max
P_adj_legal    = max(VT · ratio, umbral mínimo aprobable)   → RVC_legal = P_max / P_adj_legal
```

- El informe muestra ambas columnas: «precio económico» (lo máximo que conviene pagar) y «puja
  recomendada» (lo mínimo que la ley deja aprobar sin depender del LAJ, sin pasar del máximo).
- **ROI, TIR y escenarios se calculan a la puja recomendada**, no a un P_objetivo inaprobable. Es
  el cambio que corrige de raíz el informe de la prueba manual.
- La táctica de M13 sale del parámetro de visibilidad: puja sellada con un único límite
  (régimen nuevo) o puja abierta con prórroga (régimen anterior, AEAT y notarial).

| Pros | Contras |
|---|---|
| **Responde a la pregunta del usuario**: qué pujar, legal y rentable a la vez | El mayor cambio: M11, M12 (presentación), M13, M14, el contrato de resultado, la interfaz y las simulaciones |
| Separa lo que decide la economía (techos) de lo que decide la ley (suelos): ambas cosas trazables | **Cambia el resultado del caso dorado** y obliga a re-basar `invariante_5h1.json` y el informe de ejemplo. Con suelo del 50 %, el §19 **se queda sin puja recomendada**: la menor aprobable sin el LAJ (76.000 €) supera P_max (68.731 €), aunque no P_límite (80.022 €). RVC_legal = 68.731 / 76.000 ≈ 0,90 |
| La escalera económica no se toca: los análisis antiguos siguen siendo reproducibles con su versión (P1) | Elegir `suelo_util` es una decisión de producto (¿apuntar a ≥ 50 % o aceptar la zona discrecional?) |

**Esfuerzo:** grande. Conviene trocearlo en subfases: 5J-1 (datos y A), 5J-2 (reglas B),
5J-3 (escalera legal y rentabilidad), 5J-4 (interfaz).

### 3.1 Comparativa

| Criterio | A | B | C |
|---|---|---|---|
| Corrige la recomendación ilegal | No (solo la etiqueta) | Parcialmente (avisa y bloquea el caso extremo) | **Sí** |
| Cambia el caso dorado | Solo texto | Semáforo (amarillo → naranja) | Cifras y semáforo |
| Toca `app/engine/` | Sí, sin cambiar cálculos | Sí (reglas y hechos) | Sí (M11-M14) |
| Riesgo de regresión | Bajo | Medio | Alto |
| Esfuerzo | Pequeño-medio | Medio | Grande |

---

## 4 · Recomendación

**C, construido por capas en el orden A → B → C, en subfases separadas con su propio PR.**

1. **Lo que se denunció es la recomendación, no la etiqueta.** Solo C cambia lo que el informe
   recomienda pujar. A no lo resuelve y B solo avisa.
2. **El orden reduce el riesgo.** A no mueve ninguna cifra y deja medir sobre análisis reales
   cuántos caen en cada zona antes de endurecer; B añade la parte que sí debe bloquear; C cambia
   las cifras cuando la capa de datos ya está probada.
3. **No se sube nunca un techo.** La escalera económica sigue siendo la que es; la ley solo
   añade suelos. Si el suelo supera el techo, la operación no se recomienda, sin «estirar» la
   rentabilidad.
4. **Correcciones que no esperan al diseño.** Son pequeñas y no cambian cifras: depósito
   judicial por régimen, texto de la regla T2 de la vía judicial, táctica de puja según
   visibilidad y nota sobre el testimonio para hipotecar (Inv. §2.13, filas 1, 2, 3 y 7). Las
   haría en la 5J-1, junto con A.

**Suelo útil propuesto para C:** «aprobable sin depender del LAJ», que en inmuebles del régimen
nuevo es **el 50 %** (o el 60 % en vivienda habitual), y el 50 % en la AEAT. La zona del 40 %
(«cubre la deuda») solo cuando el usuario informe la cantidad reclamada.

**Qué diría el §19 con C.** Ninguna puja dentro de P_max es aprobable sin depender del LAJ. El
informe tendría que decirlo así: «la menor puja aprobable (76.000 €) supera el precio máximo;
solo cabe entre el máximo y el límite (80.022 €), con la doble firma que ya exige superar el
máximo, o pujando por debajo del 50 % a expensas del LAJ». Es un resultado **más incómodo que
el actual y más honesto**: hoy el informe recomienda 60.011 € sin advertir que, con la ley
nueva, ese remate no se aprueba de forma automática.

---

## 5 · Pregunta abierta: meses de inmovilización del depósito (5H.2, auditoría E5)

La auditoría (`docs/AUDITORIA_MOTOR_ESPECIFICACION.md` §E5) dejó pendiente el coste del
depósito porque «necesita un dato que hoy no existe: los meses de inmovilización». La
investigación lo acota **con los plazos máximos legales**. Son estimaciones, no plazos medidos:

| Procedimiento | Si se gana (consignación → pago del resto) | Si se pierde (→ devolución) | Base legal |
|---|---|---|---|
| Judicial nuevo, ≥ 70 % | ≤ 20 días de subasta + 20 de pago ≈ **1,3 meses** | Inmediata al cierre (≤ 0,7 meses); con reserva de postura, hasta que pague el rematante | LEC 649, 650.1, 652, 670.1 |
| Judicial nuevo, 50-70 % | 20 + 10 (mejora) + notificación + 20 ≈ **1,8 meses** | Si un tercero mejora: ≈ 1 mes | LEC 670.3-4 |
| Judicial anterior | 20 + 40 ≈ **2 meses** (≈ 2,5 si < 70 %) | Inmediata | LEC 670 (2015) |
| AEAT | 20 + ≤ 15 (Mesa) + notificación + 15 ≈ **1,7 meses** | Inmediata salvo reserva | RGR 104, 104 bis |
| TGSS | Acto + 5 días hábiles ≈ **0,3 meses** desde el acto | En el acto | RGRSS 120.8 |
| Suspensión > 15 días | Cancelación y devolución; cuenta como «subasta perdida» | | LEC 649.2 |

**Lo que mueve en el caso §19** (coste de capital del 1,5 %):

- Régimen anterior: 7.600 € × 1,5 % × 2/12 ≈ **19 €**.
- Régimen nuevo: 30.400 € × 1,5 % × 1,8/12 ≈ **68 €**.

Es poco dinero en C_F. Lo que de verdad cambia con el régimen nuevo es el **capital necesario
para pujar** (×4), y el motor no lo compara con ningún capital disponible.

**Preguntas que necesito que respondas:**

1. ¿Los meses salen de **parámetros T3 por procedimiento** con los valores de la tabla (mi
   propuesta), o quieres una entrada por análisis?
2. ¿Escenario base al **plazo legal máximo** (prudente, P4) o a uno medio? No tenemos datos
   observados de cuánto tardan los decretos.
3. ¿Se añade el tramo «cierre → pago del resto → posesión» al plazo de la operación? Hoy M06
   empieza a contar en la posesión (`m06_costes.py:72`: ocupación + obra + comercialización), y
   esos 1-2 meses no generan tenencia ni coste de capital.
4. El coste de los depósitos de **subastas perdidas** es de cartera (§11.3), no de un análisis.
   ¿Lo dejamos fuera, como proponía la auditoría?
5. ¿Añadimos al perfil del usuario el **capital disponible** para advertir cuando el depósito
   (o depósito + resto del precio en 20 días) lo supera?

---

## 6 · Decisiones que necesito antes de la 5J-1

| # | Decisión | Opciones | Mi propuesta |
|---|---|---|---|
| D1 | Diseño | A / B / C | **C, por capas A → B → C** |
| D2 | Autorización para tocar `app/engine/` y re-basar el caso dorado §19 | sí / no | Sí, por subfases y con un PR cada una |
| D3 | Régimen judicial desconocido: qué se asume | nuevo / anterior / el más restrictivo en cada regla | **El más restrictivo en cada regla** (P4): depósito del 20 % y pago en 20 días (nuevo); el umbral más alto de los dos |
| D4 | Vivienda habitual del ejecutado desconocida | no / sí | **Sí** (P4): suelo del 60 % hasta que el usuario diga que no lo es |
| D5 | Suelo útil de la puja recomendada (C) | 40 % / 50 % / 70 % | **50 %** (60 % en vivienda habitual); el 40 % solo con cantidad reclamada informada |
| D6 | Zona «discrecional» del LAJ en B | veto / techo naranja / solo condición | **Techo naranja + condición** |
| D7 | Meses de inmovilización del depósito | ver §5 | Parámetro T3 por procedimiento, al plazo legal máximo |
| D8 | Validación jurídica externa de Inv. §5 antes de activar vetos | sí / no | **Sí** para el VETO-LEG-01; A puede salir antes |
