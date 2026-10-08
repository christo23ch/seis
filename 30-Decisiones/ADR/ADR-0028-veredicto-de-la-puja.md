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

# ADR-0028: puja mínima aprobable como recomendación y veredicto «inviable con estas condiciones»

**Fecha:** 2026-10-09 · **Fase:** 5J-4 · **Base:** `docs/IMPACTO_MOTOR_UMBRALES_LEGALES.md` (diseño
C), `docs/INVESTIGACION_PROCEDIMIENTOS_SUBASTA.md` §2.5, ADR-0022 y ADR-0027. **Autorización:**
expresa del responsable para tocar `app/engine/` (CLAUDE.md §6.8) solo para esto. **Esta fase cambia
cifras y el veredicto**, con la tabla antes/después aprobada en la parada 2 (semáforo C).

## Contexto

Desde la 5J-3 el informe avisaba de que la puja máxima económica (P_max) quedaba por debajo de la
aprobación del remate, pero seguía recomendando pujar entre el precio objetivo y P_max, y calculaba la
rentabilidad a un precio objetivo que la ley no aprobaría sin depender del letrado o de la Mesa. En
el §19 eso daba un ROI del 25 % sobre 59.447 € cuando la menor puja aprobable es 106.400 €.

## Decisión

1. **Tres cifras en el informe**: precio máximo económico (P_max), puja mínima aprobable según
   régimen y vivienda habitual, y puja de aprobación segura (70 % en el judicial). Los umbrales son
   los parámetros T3 de `procedimiento.regimenes` (5J-1). La escalera económica (P_ideal…P_límite)
   no cambia: la ley solo añade un suelo.
2. **Veredicto** (`procedimiento.veredicto_puja`, puro, fuera del DAG; viaja en
   `DecisionFinal.veredicto`):

   | Estado | Cuándo | Puja recomendada | Puja a la que se evalúa la rentabilidad |
   |---|---|---|---|
   | `viable` | mínima aprobable ≤ P_max | máx(P_objetivo, mínima) | la recomendada |
   | `inviable` | mínima aprobable > P_max | **ninguna**: «inviable con estas condiciones» | la mínima aprobable, con aviso |
   | `sin_umbral` | la norma no da mínima (notarial, concursal, venta no reglada) | P_objetivo | P_objetivo |

   En el régimen anterior a la LO 1/2025 la norma exige **superar** el 50 %: la mínima efectiva es
   +1 €, salvo que la rebaje la deuda.
3. **Inviable: qué tendría que cambiar.** El informe da el P_max necesario, el valor de subasta máximo
   con el que la mínima cabría y, si no se informó la cantidad reclamada y cubrirla permitiría una
   puja aprobable, que informarla podría cambiar el veredicto. El plan de puja dice «No pujar con
   estas condiciones» y el checklist deja la escalera como bloqueante pendiente.
4. **Rentabilidad, ICO y margen de seguridad a la puja evaluada** (decisión del responsable): la
   mínima aprobable en los inviables. **El colchón de plazo sigue a P_objetivo y a P_max** (deuda).
5. **Semáforo C** (decisión del responsable):
   - inviable y **mínima aprobable > P_límite** ⇒ **rojo** (ninguna puja aprobable cabe en el
     bloqueo duro del software);
   - inviable y mínima ≤ P_límite ⇒ **como máximo naranja**, con la condición «solo se plantearía
     aceptando por escrito un margen menor que el que exige el perfil»;
   - viables y sin umbral: su semáforo habitual.
   No es un veto: el veredicto es informativo y el usuario puede seguir simulando. El techo nunca
   sube un rojo.
6. **Segunda línea del veredicto inviable** (decisión del responsable): qué pasaría con una puja de
   P_max. No cambia el veredicto. Tres valores, no dos: la vivienda habitual no tiene
   discrecionalidad (LEC 670.3, último párrafo; corrección M2 de la 5J-3):
   - `no_aprobable`: P_max por debajo del suelo de la vivienda habitual (60 %);
   - `solo_si_cubre_deuda`: vivienda habitual, P_max entre el suelo y el umbral;
   - `discrecional`: a decisión del letrado, de la Mesa o del notario. En la AEAT se añade que por
     debajo del 50 % no hay precio mínimo legal (RGR 104 bis).
   La regla de la vivienda habitual solo se aplica en los regímenes que la tienen (LEC y LH): en la
   AEAT `suelo_absoluto` es la puja mínima admitida (10 %), no un suelo de vivienda habitual
   (corrección de la revisión de código).
7. **Cantidad reclamada**: el suelo del 40 % solo si se informó (como en la 5J-1). **Vivienda habitual
   «no consta» ⇒ se asume que sí**, y el informe añade la mínima aprobable si no lo fuera. El
   formulario explica junto al campo que informar la deuda puede bajar la mínima.
8. **El aviso de la 5J-3 se mantiene** y se adapta: llama a P_max «precio máximo económico» y su
   alcance dice que el semáforo lo fija el veredicto (sus franjas con techo son siempre inviables).
   La fila del informe pasa de «Precio máximo recomendado» a «Precio máximo económico».

9. **Revisión de código:** 0 críticos, 0 altos, 4 medios y 7 bajos. Corregidos: la regla de vivienda
   habitual en la AEAT (M-1), los títulos «a precio objetivo» de los escenarios y la inversión en la
   interfaz (M-3), la etiqueta en negrita de la segunda línea sin depender del texto (L-3), «Ver
   cálculo» con los signos del estado del motor (L-4), una prueba que prometía más de lo que probaba
   (L-5) y la cobertura de TGSS, extrajudicial y AEAT con vivienda habitual (L-7). M-2 y M-4 quedan
   escritos abajo; L-1, L-2 y L-6, en la deuda de `docs/ESTADO_ACTUAL.md`.

## Consecuencias

- **§19: naranja → rojo.** Mínima aprobable 106.400 € (70 %, vivienda habitual supuesta) frente a
  P_max 67.941 € y P_límite 78.529 €. Rentabilidad a 106.400 €: ROI −7,6 %, TIR −7,4 %, VAN
  −17.237 €; ICO 64 → 49; margen de seguridad 24,8 % → 0 %. La escalera, los costes y el RVC no
  cambian. Guarda invariante regenerada: 44 hojas en el §19 y 45 en el caso con hipoteca.
- Las variantes con la mínima en el 50 % (vivienda habitual «no», régimen anterior, AEAT) quedan
  inviables pero dentro de P_límite: **naranja**.
- Las pruebas que vigilaban la economía al precio objetivo (caso dorado, coste de capital, VAN) la
  vigilan sobre el mismo §19 como venta no reglada: misma escalera y mismos costes, sin umbral legal.
- Con más meses, la TIR de un inviable sale **menos** negativa: anualizar una pérdida sobre más
  tiempo reduce su tasa. No es un error; el ROI total sí empeora.
- **El rojo de C no distingue la firmeza del umbral** (revisión, M-2). En la AEAT el 50 % no impide
  adjudicar: separa «la adjudica» de «la Mesa decide» (investigación §3); y los umbrales de la TGSS
  están «sin confirmar» (y su 60 % es de la primera subasta; la segunda, al 50 %, no se modela). Aun
  así, si la mínima supera P_límite el semáforo es rojo, como aprobó el responsable. La segunda línea
  dice en la AEAT que por debajo del 50 % no hay precio mínimo legal.
- **El RVC y el plan de puja siguen anclados a la escalera** (P_objetivo), mientras el ICO, el ROI y
  el margen van a la puja evaluada (revisión, M-4). Es lo decidido («la escalera y el RVC no
  cambian»), pero el umbral de RVC del naranja usa un RVC que no corresponde a la puja evaluada.

## Alternativas descartadas

- **A (literal): todo inviable es rojo.** Las variantes del 50 %, en las que una puja aprobable cabe
  en el límite, saldrían rojas como el §19.
- **B: rojo solo por debajo del suelo de la vivienda habitual.** Distinguía por la franja legal y no
  servía fuera del judicial; C usa una frontera que ya existe (P_límite) y vale para cualquier
  procedimiento.
- **«Estirar» la escalera** para recomendar la mínima aprobable aunque supere P_max: inventaría una
  recomendación que el perfil no admite.
