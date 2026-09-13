---
tipo: adr
fase: "[[Fase-6-motor]]"
estado: aprobado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aprobado
  - fase/6
  - area/motor
  - area/fiscal
---

# ADR-0015: el impuesto de la adquisición se calcula sobre el mayor valor, no sobre la puja

## Contexto

Hasta el 2026-09-11 SEIS liquidaba el ITP sobre el precio de remate: el tipo vivía dentro de `c_v` y `c_v` multiplicaba a P (`m11_rentabilidad.py`, `m06_costes.py`).

**Eso es incorrecto por ley.** El art. 10 TRLITPAJD, en la redacción de la Ley 11/2021, fija la base imponible en **el mayor** de: valor de referencia del Catastro, valor declarado y precio pagado.

Y no es un error indiferente: en una subasta **todo el atractivo consiste en rematar por debajo del valor**, así que el error va siempre en la misma dirección —infraestimar— y es **mayor cuanto mejor parece la operación**. Un remate de 40.000 € sobre un valor de referencia de 100.000 € al 6 % pagaba 2.400 € en el informe cuando debía pagar 6.000 €.

Descubierto el 2026-09-10 recorriendo una subasta real de la AEAT, no con una fixture.

## Decisión

**1 · El impuesto pasa a ser `t · max(P, B)`**, con `B = max(valor de referencia, valor declarado)`.

Como `t·max(P,B) = t·P + t·max(0, B−P)`, `c_v` se queda **exactamente como estaba** y aparece un sobrecoste que solo actúa en el tramo `P < B`. La función de inversión y —lo que de verdad importa— **su inversa**, que es lo que calcula la escalera de precios de M12, pasan a tener dos tramos. Todo en `app/engine/fiscal.py`.

**2 · Sin valor de referencia ni valor declarado, la base es la puja, declarada como suelo.**

Es la decisión que había que tomar y se toma explícitamente: **no se estima un valor de referencia a partir de nada**. Ni del valor de subasta, ni del valor catastral, ni de la tasación. Un valor de referencia inventado produciría una cuota con apariencia de exacta, que es peor que una cuota declarada como mínimo.

A cambio, la carencia **sale del motor y llega al cliente**:

- el informe dice, con esas palabras, que el impuesto es un **MÍNIMO** y que el real puede ser mayor;
- el ítem fiscal del checklist —que es bloqueante— pasa de `ok` a `pendiente`.

**Consecuencia asumida:** todo análisis sin valor de referencia muestra desde ahora un bloqueante más. Es el comportamiento correcto —ese dato falta de verdad— y es también lo que hace visible la necesidad de la Fase 17-C.

**3 · No se toca el ICI.** La ausencia de valor de referencia *podría* penalizar el índice de confianza por P4, pero eso movería la contingencia y el semáforo de **todos** los análisis existentes. Es una decisión distinta, con otro alcance, y se toma aparte si procede.

## Alcance: dónde NO llega esta decisión

Se escribe aquí por [[ADR-0014]]: un mecanismo que no declara su alcance acaba pareciendo que cubre más de lo que cubre.

1. **Solo régimen ITP.** En IVA la base es el precio convenido y este mecanismo no actúa (`tipo_base_minima = 0`).
2. **No cubre el AJD.** La Ley 11/2021 también tocó su base (art. 30.1), pero aquí la base mínima se aplica únicamente al tipo de TPO. En una operación con IVA + AJD la cuota gradual se sigue calculando sobre el precio. Limitación conocida, no olvido.
3. **No verifica el dato.** El motor no comprueba que el valor de referencia aportado sea el del inmueble ni el del ejercicio corriente, ni lo busca: es entrada. Obtenerlo automáticamente es la **Fase 17-C**.
4. **No cubre reducciones ni tipos autonómicos especiales** sobre el valor de referencia.
5. **No recalcula los análisis ya emitidos.** Son inmutables por P1. Los generados antes de hoy sin valor de referencia llevan el impuesto infraestimado y no se tocan; lo que cambia es lo que se emite a partir de ahora.

## Cómo se sabe que funciona

La propiedad que hace revisable el cambio: **con `B = 0` el sobrecoste es 0 en todo el dominio y todas las fórmulas recuperan su forma anterior al último decimal**. El caso dorado §19 pasó sin tocar ni un número.

Nueve mutaciones aplicadas, nueve detectadas (`tests/test_base_fiscal.py`), incluidas las dos que no eran obvias: elegir siempre el mismo tramo en la inversa, y olvidar el sobrecoste en el flujo de caja del mes 0 —que cuadraría el total y mentiría en la TIR—.

**Y una advertencia que vale más que el resto de este apartado:** de esas nueve, la del aviso del informe **sobrevivió en la primera pasada porque la mutación era falsa** —sustituía el texto del aviso por otro que seguía conteniendo el aviso—. No sobrevivió el código: sobrevivió una mutación que no mutaba nada. Es la segunda vez en el proyecto que el fallo aparece **dentro de la herramienta de verificación** y no en lo verificado; queda nombrado como patrón en el punto 6 de [[ADR-0014]].
