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

# ADR-0027: aviso de la franja del letrado, sin vetos; reglas sincronizadas al sembrar

**Fecha:** 2026-10-08 · **Fase:** 5J-3 · **Base:** `docs/IMPACTO_MOTOR_UMBRALES_LEGALES.md` (diseño
B), `docs/INVESTIGACION_PROCEDIMIENTOS_SUBASTA.md` §2.5 y §2.8, ADR-0022. **Autorización:** expresa
del responsable para tocar `app/engine/` (CLAUDE.md §6.8) solo para esto; tabla antes/después
aprobada con un cambio (sin techo en la franja «sujeta a mejora»).

## Contexto

Desde la 5J-1 el motor calcula los umbrales de aprobación del remate (LEC 670), pero nada los
comparaba con la puja recomendada. En el §19 la puja máxima (67.941 €, 44,7 % del valor de
subasta) queda por debajo del suelo de la vivienda habitual supuesta (91.200 €, 60 %), que la ley no
aprueba nunca, y el informe salía en amarillo sin advertirlo.

## Decisión

1. **Herramienta de cálculo, sin implicaciones legales y sin vetos.** Lo calcula el motor
   (`procedimiento.aviso_aprobacion`, puro), no una regla T2: funciona aunque la base tenga reglas
   desfasadas. Solo en procedimientos judiciales, cuando **P_max < aprobación segura** (70 %).
2. **Tres franjas** (LEC 670.3):

   | Franja | Cuándo | Techo | Ítem del checklist |
   |---|---|---|---|
   | `sujeta_a_mejora` | mínima aprobable ≤ P_max < segura: el ejecutado puede presentar un tercero que mejore; si nadie mejora, se aprueba | **no** (decisión del responsable) | no bloqueante |
   | `discrecional` | P_max < mínima aprobable (50 %, 40 % si cubre la deuda informada; en el régimen anterior hay que **superar** el 50 %, igualarlo no basta): decide el letrado y puede denegarla. **En vivienda habitual** (umbral del 70 %) no decide el letrado: la ley no aprueba salvo que la postura cubra lo debido, y nunca bajo el 60 % | naranja | bloqueante |
   | `bajo_suelo` | P_max < suelo de la vivienda habitual (60 %): la ley no lo aprueba ni aunque cubra la deuda | naranja | bloqueante |

3. **Lo que hace el aviso:** un bloque destacado bajo el semáforo del informe (riesgo y umbrales
   aplicados, cada uno con su artículo y su estado «confirmado» o «sin confirmar»), una condición en
   la decisión, un ítem «Riesgo de aprobación del remate asumido por escrito» en el checklist y,
   en las dos últimas franjas, techo naranja. El techo nunca sube un semáforo ni veta: un rojo
   sigue rojo. **Ningún número cambia** (escalera, RVC, TIR, VAN, ICO).
4. **Vivienda habitual «no consta» ⇒ se asume que sí** (P4), con aviso en el texto. Régimen
   desconocido ⇒ umbrales de la LO 1/2025, también con aviso. El umbral de «cubre la deuda» solo
   se cita si se informó la cantidad reclamada.
5. **Cesión de remate (LEC 647.3, verificada en la API del BOE):** con la LO 1/2025 la tienen el
   ejecutante **y los acreedores posteriores**; antes, solo el ejecutante. SEM-EJEC-01 pasa a
   **2026.10.07** y el riesgo de ejecución de M13 lo dice según el régimen. La versión lleva formato
   de fecha anterior a cualquier versión que cree la API desde entonces (`AAAA.MM.DD.n`), que así
   ordena después.
6. **Reglas sincronizadas al sembrar** (decisión del responsable): `scripts/sembrar.py` ya no copia
   el catálogo solo con la tabla vacía. Por cada regla del YAML, si la versión vigente vino de la
   siembra (sin autor) y es otra, la cierra y añade la del catálogo, con auditoría. **Nunca toca una
   versión creada por la API** ni resucita una cerrada. Idempotente. Así llegan a las bases ya
   sembradas SEM-EJEC-01 2026.10 (5J-2b) y 2026.10.07.

7. **Revisión de código:** igualar la mínima aprobable en el régimen anterior cae en la franja del
   letrado (la norma dice «supere»), salvo que la mínima la rebaje la deuda; el texto de vivienda
   habitual no atribuye la decisión al letrado; el aviso lleva su `alcance` y sus `umbrales` ya
   redactados, para que la interfaz no reconstruya textos.

## Consecuencias

- El §19 pasa de **amarillo a naranja** (franja `bajo_suelo`, vivienda habitual supuesta). La guarda
  invariante se regenera: 13 hojas por caso, ninguna numérica.
- Con P_max casi siempre por debajo del 70 % del valor de subasta, muchas subastas judiciales
  llevarán el aviso. El techo solo se aplica a las franjas `discrecional` y `bajo_suelo`.
- La AEAT, la TGSS, la subasta notarial y la venta extrajudicial no tienen aviso: la franja se
  limita al letrado. Extenderla a la Mesa de la AEAT queda como posible ampliación.
- Las bases ya sembradas reciben las reglas nuevas en el siguiente `init_db`.

## Alternativas descartadas

- **Reglas T2 nuevas (diseño B literal).** Dependían de que la regla llegase a la base, que era
  justo lo que fallaba; y el aviso necesita textos y datos que ya calcula el motor.
- **Veto por debajo del suelo.** Decisión del responsable: la herramienta no veta por motivos legales.
- **Techo también en la franja sujeta a mejora.** Descartado por el responsable en la parada: el
  riesgo (que un tercero mejore la postura) no hace inviable la operación.
