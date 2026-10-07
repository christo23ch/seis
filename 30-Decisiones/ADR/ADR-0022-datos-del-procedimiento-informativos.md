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
  - area/frontend
---

# ADR-0022: datos del procedimiento de subasta, informativos y fuera del DAG

**Fecha:** 2026-10-07 · **Fase:** 5J-1 (diseño A) · **Base:** `docs/INVESTIGACION_PROCEDIMIENTOS_SUBASTA.md`,
`docs/IMPACTO_MOTOR_UMBRALES_LEGALES.md` (§3, diseño A), especificación P1, P4 y P5.
**Autorización:** expresa del responsable para tocar `app/engine/` (CLAUDE.md §6.8) **solo** para
añadir campos y cálculos informativos; ninguna cifra existente puede cambiar.

## Contexto

La 5J-0 demostró que el informe puede recomendar pujas que la ley no deja aprobar y que el motor
ignora el procedimiento: depósito judicial del 5 % fijo (el régimen de la LO 1/2025 exige el 20 %),
sin umbrales de aprobación, sin régimen judicial y sin vivienda habitual del ejecutado. El
responsable eligió construir el diseño C por capas, empezando por el A: **datos del procedimiento
visibles, sin mover todavía ninguna cifra**.

## Decisión

1. **Preguntas nuevas en el alta**, cada una solo donde cuenta:
   - tipo de procedimiento: judicial, AEAT, TGSS, notarial, extrajudicial, concursal o «no aplica»
     (venta bancaria o privada), preseleccionado con el de la fuente;
   - si el judicial se inició antes o después del 3-4-2025, con «No sé»;
   - si el inmueble es la vivienda habitual del ejecutado: sí / no / no consta (sustituye a la
     casilla, que nadie leía);
   - cantidad reclamada, opcional.
2. **Parámetros T3 por procedimiento y régimen** (`procedimiento.regimenes` en `defaults.yaml`).
   Cada dato es `{valor, articulo, estado[, nota]}`, con `estado` confirmado (literal del BOE) o
   sin confirmar, según la investigación. `valor: null` = dato ausente; clave ausente = la regla no
   existe en ese procedimiento.
3. **Un módulo puro, `app/engine/procedimiento.py`, fuera de `modules/` y del DAG**, como
   `fiscal.py` y `conservacion.py`. Se ejecuta al final del pipeline, **no escribe en la pizarra de
   hechos y nada lo lee**: ni M01-M14 ni las reglas T2. Devuelve `AnalisisResult.procedimiento` con
   régimen aplicable, depósito y capital para pujar, plazo de pago, meses de inmovilización, puja
   mínima aprobable sin depender de la autoridad, puja de aprobación segura, suelo absoluto, base
   legal y avisos.
4. **Dos supuestos prudentes, declarados siempre** (P4/P5):
   - régimen judicial «No sé» ⇒ el desfavorable, el de la LO 1/2025 (depósito 20 %, pago en 20 días,
     y sus umbrales, que nunca son menores que los de 2015). El aviso dice qué cambiaría con el
     régimen anterior;
   - vivienda habitual «No consta» en una vivienda ⇒ se aplica su regla (70 %, y suelo del 60 % aunque
     cubra la deuda), como el «No consta» del estado de conservación (ADR-0020). En un garaje o un
     local no se asume: no pueden ser vivienda habitual.
5. **El informe gana un subapartado al final del §8** con la tabla, los avisos, la base legal y el
   aviso estándar de cálculo orientativo («no es asesoramiento jurídico… estos importes no modifican
   la escalera de precios, el RVC, el semáforo ni la rentabilidad»).
6. **Persistencia** (migración `0016`): `subasta.procedimiento`, `subasta.regimen_judicial`,
   `subasta.cantidad_reclamada` y `activo.vivienda_habitual_ejecutado`, anulables y sin relleno.
   `NULL` = fila anterior a la fase. La entrada completa sigue en `analisis.entrada`.

## Por qué así

- **Nada puede moverse por accidente.** Al no tocar la pizarra, un cambio en este módulo no puede
  alterar vetos, techos ni el semáforo. Lo vigila la guarda de 510 hojas del §19
  (`tests/test_invariante_5h1.py`), que pasa sin cambios, y un test que cambia el procedimiento, el
  régimen o la vivienda habitual y comprueba que **ninguna otra hoja** del resultado se mueve.
- **La foto vigila también la longitud de las listas** (`checklist[#]`, `puja.plan[#]`,
  `decision.condiciones[#]`). Por eso los avisos no se añaden a esas listas, sino a un campo nuevo.
- **El booleano antiguo `es_vivienda_habitual` se conserva** y el formulario lo envía derivado
  (`true` solo con «Sí»): alimenta un hecho de M01, y cambiarlo de tipo habría movido la pizarra.
  Las entradas anteriores sin la respuesta nueva se leen como «si» si el booleano es verdadero y
  como «no_consta» si no, porque un `false` antiguo no distingue «no» de «no marcado».
- **Puja mínima aprobable de la vivienda habitual sin cantidad reclamada = 70 %, no 60 %.** El 60 %
  es el suelo que la norma admite solo si la puja cubre lo debido; sin conocer la deuda no se puede
  afirmar esa vía. El 60 % se muestra como suelo absoluto.

## Consecuencias

- El informe del §19 cambia de texto (el subapartado nuevo), no de cifras. `test_informe_coherencia.py`
  admite esa inserción como la única permitida, igual que en la 5G.4 y la 5H.1.
- **El depósito del alta sigue siendo un 5 % por defecto** y sigue alimentando el plan de puja de
  M13: cambiarlo habría movido cifras. El resultado muestra el depósito legal y avisa si no coincide.
  Corregir el valor por defecto y la táctica de puja del régimen nuevo es trabajo de la 5J-2 o de la
  5J-3, con autorización para cambiar cifras.
- La versión de `defaults.yaml` (`2026.07`) no se ha subido: la sección es nueva y no cambia ningún
  valor existente, y `version_parametros` forma parte de la foto del §19. Los parámetros del
  procedimiento **no son simulables** (el catálogo de la 5C solo cubre M12 y M13).
- **Una base de desarrollo creada con `create_all`** (sin revisión en `alembic_version`) no recibe
  las columnas nuevas al arrancar: hay que marcarla en `0015` y subir a `0016` (`MANUAL_DE_PRUEBAS.md`).
- Los datos **sin confirmar** (toda la TGSS, los meses de inmovilización, la venta extrajudicial y el
  concursal) se usan solo con su aviso; varios dejan el importe en «no consta». Ninguno puede
  convertirse en bloqueo sin la validación jurídica de la D8.

## Alternativas descartadas

- **Añadir los avisos a `decision.condiciones` o al plan de puja:** rompía la foto del §19 (longitud
  de las listas) y mezclaba lo informativo con lo que decide el semáforo.
- **Calcularlo dentro de M13:** M13 escribe en la pizarra (`p_adj_esperado`, `rvc`), y cualquier
  hecho nuevo allí queda al alcance de las reglas T2.
- **Rellenar las filas antiguas con «no_consta»/«no_se» en la migración:** afirmaría respuestas que
  nunca se dieron; el motor ya trata la ausencia como dato ausente.
