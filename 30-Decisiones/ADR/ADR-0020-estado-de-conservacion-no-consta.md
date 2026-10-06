---
tipo: adr
fase: "[[Fase-5I]]"
estado: aceptado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aceptado
  - area/motor
  - area/frontend
---

# ADR-0020: estado de conservación «No consta» — se asume «malo» por parámetro T3

**Fecha:** 2026-10-06 · **Fase:** 5I-D · **Base:** especificación P4, P5, §6.5 (M05), §7.2
(ocupación desconocida), §19 (caso dorado). **Decisión revisable:** el estado asumido es un
parámetro T3 (`conservacion.desconocido_usa`), editable sin desplegar.

## Contexto

La prueba manual del alta pidió poder decir que el estado de conservación **no se conoce**, lo
habitual en subasta: el interior casi nunca se puede visitar. El asistente obligaba a elegir uno
de cinco niveles y venía con **«regular»** marcado de fábrica: un supuesto que nadie había
declarado y que no es el prudente (P4: la ausencia de datos no se rellena con el valor optimista).

El estado del inmueble pesa en dos sitios del motor, y en ninguno más:

| Dónde | Qué hace con el estado | Efecto de un estado peor |
|---|---|---|
| M03 `k_estado` (`valoracion.k_estado`) | valor en el estado ACTUAL, VM = VS_m² · k · m²; contraste de sanidad de la tasación | VM más bajo |
| M05 `nivel_por_estado` (`reforma.nivel_por_estado`) | nivel de reforma, si ni el usuario ni el perfil lo fijan | obra más cara, más plazo, más honorarios |

El ICI no mira el estado: penaliza la falta de `fotos_interior_o_visita` (peso 10), que es el
dato documental que de verdad falta cuando el estado no consta. Ninguna regla del catálogo T2 usa
el estado ni pide una visita interior o fotos interiores.

## Decisión

1. **Nuevo valor `desconocido` («No consta»)** en el estado de conservación del INMUEBLE
   (`EstadoActivo`). Los comparables no lo admiten: un testigo sin estado no se puede normalizar.
2. **El motor usa el estado de `conservacion.desconocido_usa`, «malo» de fábrica**, resuelto en
   un solo sitio (`app/engine/conservacion.py`) que piden M03 y M05. Mismo patrón que
   `ocupacion.desconocida.usa: precario`.
3. **No cambia ningún peso ni fórmula** (ICO, ICI, semáforo, matrices): con «No consta» el
   resultado numérico es idéntico al del estado asumido (lo fija un test).
4. **Se declara, no se esconde:**
   - el informe dice «estado de conservación **no consta**: se asume «malo» (P5) hasta
     verificarlo con visita interior o fotos interiores»;
   - el checklist gana, AL FINAL (no desplaza la numeración de §13), el ítem «Estado de
     conservación verificado con visita interior o fotos interiores», **no bloqueante** y
     **pendiente mientras el estado siga sin declararse**: si ya hay fotos interiores o visita,
     el detalle pide elegir el estado real (dar el ítem por hecho contradiría el informe, que
     sigue diciendo «no consta»).
5. **«No consta» es el valor por defecto del formulario**, en lugar de «regular».

## Por qué «malo» y no otro nivel

- **P5 pide estimar al alza los costes desconocidos**, como la deuda de comunidad; y §6.5 dice
  «sin fotos ⇒ nivel asumido = el peor compatible con la evidencia». Descarta «regular», «bueno»
  y «reformado».
- **«Ruina» no es compatible con la evidencia habitual.** Implica reforma estructural (1.150 €/m²,
  8 meses) y un inmueble no habitable: en una vivienda en subasta eso suele verse en el edicto,
  la tasación, las fotos exteriores o la ITE. Asumirlo siempre haría inviable casi cualquier
  análisis sin información nueva, y un supuesto que tumba todo deja de discriminar.
- **El precedente del propio motor es el mismo:** la ocupación desconocida no se asume como la
  peor posible (renta antigua), sino como «precario», el caso prudente y típico.
- **El caso dorado §19 es exactamente esto:** «Estado: malo (sin visita interior)». La
  especificación ya usa «malo» como lectura de un interior que no se ha visto.
- «Malo» lleva a reforma **media** (obra mayor, honorarios del 9 %, 3 meses) y a k = 0,72. El
  spread P80 «sin visita» ensancha además el presupuesto pesimista cuando no se ha visitado el
  interior, que es el caso normal de «No consta» (si se marca la visita, se aplica el de «con
  visita», y lo coherente es elegir el estado real).
- Si el perfil fija su propio nivel de reforma (p. ej. «flip ligero»), manda el perfil, igual que
  con un estado conocido.

Si la experiencia (resultados reales) muestra que el interior desconocido suele ser peor, se
cambia el parámetro a «ruina», sin tocar código. El valor se valida **al escribirlo**
(`PUT /parametros` responde 400 con los estados admitidos: los que entienden a la vez M03 y M05),
no al analizar. No está en el catálogo de parámetros simulables (M12/M13), así que una simulación
no puede cambiarlo: es una política de prudencia de la casa, no una hipótesis del caso.

### En qué se aparta del precedente de la ocupación

La ocupación desconocida lleva además **techo de semáforo amarillo** e **ítem bloqueante** (§7.2).
Aquí no: la fase no puede tocar el semáforo, y la diferencia tiene motivo: la ocupación
desconocida es un riesgo jurídico y de plazo que el motor no puede acotar, mientras que el
estado desconocido ya se presupuesta con el nivel prudente y su spread P80. Si se quisiera el
techo, sería una regla T2 nueva (con su migración de datos, ver abajo), no un cambio de este ADR.

## Por qué no se toca el ICI ni se añade una regla

- **ICI:** ya penaliza que falten fotos interiores o visita. Penalizar además «No consta»
  contaría dos veces la misma carencia y exigiría cambiar la fórmula, que esta fase no puede
  tocar.
- **Regla T2:** el catálogo no tiene ninguna sobre visita interior o fotos, y las reglas solo se
  siembran en una base VACÍA (`scripts/sembrar.py`): una regla nueva en el YAML no llegaría a las
  bases existentes sin una migración de datos. El checklist (M14) es el sitio que ya recoge
  verificaciones de este tipo.
- **No bloqueante:** en subasta judicial la visita interior casi nunca es posible. Un ítem
  bloqueante impediría pujar en la mayoría de los casos por un dato que el presupuesto ya cubre
  de forma prudente.

## Por qué es el valor por defecto

El defecto anterior («regular») era un dato inventado y optimista; «No consta» es lo que se sabe
cuando no se ha elegido nada, y su consecuencia (prudente y avisada) es la que pide P4.

## Consecuencias

- Un alta que antes salía con «regular» sin que nadie lo eligiera sale ahora con reforma media y
  k = 0,72: precios recomendados más bajos. Es intencionado.
- El caso dorado §19 (estado «malo») no cambia ni un valor (guarda `test_invariante_5h1`).
- Los análisis guardados no cambian: son instantáneas.

## Verificación

`backend/tests/test_conservacion_no_consta_5i.py`: mismo resultado que «malo» salvo informe y
checklist; ICI, ICO y semáforo iguales; aviso en el informe; ítem del checklist al final y pendiente;
perfil con nivel propio; valores inválidos rechazados al escribir (400) y al analizar;
parámetro T3 efectivo (con «ruina» da reforma estructural); comparables sin «No consta»;
`/opciones` lo ofrece. Frontend: `tests/schema.test.ts` (valor por defecto) y la e2e
`nueva-inversion.mjs` (el alta mínima se guarda con «desconocido»).
