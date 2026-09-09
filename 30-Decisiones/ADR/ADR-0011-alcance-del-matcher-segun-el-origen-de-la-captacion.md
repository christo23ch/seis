---
tipo: adr
fase: "[[Fase-17-captacion]]"
estado: aprobado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aprobado
  - fase/17
  - area/producto
  - area/seguridad
---

# ADR-0011: el alcance del matcher lo decide el origen de la captación, y el origen es un tipo, no un parámetro opcional

## Contexto

La Fase 12 cerró una fuga real: un analista de la organización A podía disparar notificaciones —privadas— hacia usuarios de B, C y D con solo captar una subasta. La regla que la cerró restringe el matcher a las alertas de la organización de quien capta. Sigue siendo correcta.

Lo que cambia en la Fase 17-A es que **aparece un captador que no es un tenant**: la ingesta automática del BOE. Y la regla de la Fase 12 no tenía forma de expresarlo, porque el alcance viajaba como `organizacion_id: str | None`.

Ahí está el defecto que obliga a decidir. `None` parece «todas las organizaciones» y no lo es: el filtro `Usuario.organizacion_id == None` significa «los usuarios que no tienen organización», que en un sistema donde toda alta crea organización propia **no es nadie**. Una tarea nocturna que pasara `None` habría corrido cada noche, insertado sus subastas, escrito su registro de auditoría con todo en verde y **no habría notificado a nadie**. Sin excepción, sin log de error y sin ningún test en rojo: la funcionalidad central del producto —avisar de una subasta que encaja— habría quedado inerte y el sistema habría seguido informando de normalidad.

### El trade-off original, citado

De `evaluar_subasta`, commit `29fb156` («feat: Fase 12 — notificaciones multicanal y scoring exprés», 25-07-2026), verbatim:

> Trade-off asumido: si NINGÚN usuario de la organización B vuelve a captar esta misma subasta, sus alertas coincidentes no dispararán notificación automática — aunque la subasta sigue siendo visible para B vía GET /subastas en cualquier momento. Se prioriza el aislamiento del efecto colateral sobre la cobertura completa de notificación cross-organización; ampliar esa cobertura es una decisión de producto futura, no asumida aquí.

Aquel párrafo hizo dos cosas bien: nombró la pérdida en vez de esconderla, y dejó dicho que ampliarla sería **una decisión de producto futura**. Este ADR es esa decisión. No se revisa porque la regla fuera un error; se revisa porque su premisa cambió.

### Por qué la premisa ya no se sostiene

La Fase 12 daba por hecho que **alguien capta**. Con captación solo manual, «si nadie de B vuelve a captar esta subasta» era el caso raro: las subastas entraban de una en una, por decisión de un humano de una organización concreta.

Con ingesta diaria, ese caso raro pasa a ser **el único**. El conector capta por todos, nadie capta a mano, y aplicar la regla de la Fase 12 tal cual dejaría todas las alertas de la plataforma sin disparar para siempre. La regla no habría fallado: habría acertado en un mundo que dejó de existir.

## Decisión

**Quién capta viaja como tipo —`OrigenCaptacion`— y decide el alcance: `manual(org)` evalúa solo las alertas de esa organización; `plataforma()` evalúa las de todas.**

`evaluar_subasta` ya no acepta un `str | None` ambiguo. Acepta un `OrigenCaptacion` que obliga a decir cuál de los dos casos es, y el constructor `plataforma()` no admite organización porque no la tiene.

## Justificación

### Por qué ampliar el alcance no rompe el aislamiento de la Fase 9

El invariante de la Fase 9 es que **ninguna acción de un tenant produce efectos observables en otro**. La ingesta automática no es acción de ningún tenant: es la plataforma leyendo un boletín público. El BOE no es un tenant. La regla de la Fase 12 sigue vigente palabra por palabra para el origen que sí lo es —el manual—, y hay un test de regresión que lo comprueba (`test_el_alta_manual_sigue_sin_salir_de_su_organizacion`).

Dicho de otro modo: lo que la Fase 12 acotó no fue «quién puede ser notificado», sino «qué efectos puede provocar el acto de un tenant». Ese acotamiento no se toca.

### Alcance ampliado no es datos compartidos

Que el matcher alcance a todas las organizaciones significa que cada usuario recibe **su** aviso sobre un dato común —la subasta, que ya era pública y ya era legible por todos vía `GET /subastas`—, construido únicamente con su propia alerta. No significa que el aviso lleve nada de otra organización.

Esa distinción no se queda en la intención: `test_una_notificacion_de_plataforma_no_contiene_datos_de_otra_organizacion` falla si en el cuerpo aparece el nombre de una alerta ajena, el correo de otro usuario o el identificador de otra organización. Verificado por mutación: una fuga plausible del tipo «otras alertas que también casan» lo pone en rojo.

### Por qué un tipo y no un booleano o un `None`

Un `bool notificar_a_todas=False` habría funcionado igual y habría vuelto a admitir el descuido: quien escriba el segundo conector no lo pasa, hereda el valor por defecto, y el fallo vuelve a ser silencioso. `OrigenCaptacion` no tiene valor por defecto: hay que elegir uno de los dos constructores, y cada uno lleva escrito en su nombre lo que hace.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Mantener la regla de la Fase 12 también para la ingesta automática | Deja todas las alertas de la plataforma sin disparar: nadie capta a mano una subasta que ya trajo el conector. Es exactamente el escenario que la Fase 12 dejó anotado como pérdida aceptable **mientras la captación fuera manual** |
| Pasar `organizacion_id=None` y que el filtro lo interprete como «todas» | Es la trampa que motiva este ADR. `== None` significa «sin organización» y ese filtro compila, corre y no notifica a nadie. Un valor centinela cuyo significado depende de leerse la implementación no es un contrato |
| Un booleano `notificar_a_todas` | Admite valor por defecto, y el valor por defecto es justo el descuido que se quiere impedir. El tipo obliga a elegir; el booleano invita a no pensarlo |
| Atribuir la ingesta automática a una organización «plataforma» ficticia | Mete una fila falsa en el modelo de tenants para eludir el problema. Cualquier consulta que agregue por organización empieza a mentir, y el aislamiento pasa a depender de que nadie olvide excluirla |
| Notificar solo a las organizaciones con alguna alerta que case, resuelto en SQL | Es la optimización, no la decisión. Se anota en la nota de volumen; hoy el coste medido no la justifica |

## Consecuencias

### Positivas

- La ingesta automática notifica a quien tiene una alerta que casa, que es el producto.
- El alcance es imposible de colar por descuido: no hay valor por defecto que heredar.
- El modo de fallo que se evitaba —notificar a nadie en silencio— tiene ahora dos tests que lo detectan, comprobados por mutación.
- La regla de la Fase 12 queda intacta y con regresión propia para el origen manual.

### Negativas / deuda asumida

- **El matcher pasa a evaluar todas las alertas activas de la plataforma en cada lote.** Coste medido y acotado en `docs/VOLUMEN_MATCHER.md`; el cuello no es emparejar, es despachar.
- **El despacho instantáneo sigue siendo síncrono dentro de la ingesta.** Con captación manual era una notificación por acto humano; con ingesta diaria es una ráfaga. Está medido y anotado, no resuelto: cerrarlo es sacar el envío a la cola, y eso es fase propia.
- **Nadie ha pedido esto todavía.** No hay usuarios reales, así que la decisión se toma sobre el comportamiento del sistema, no sobre demanda observada. Si al haber clientes resulta que quieren alertas solo de lo que su organización sigue, esto se revisa — y entonces se revisará con datos, que es más de lo que hay hoy.
- **El usuario recibe avisos de subastas que su organización no captó.** Es el efecto buscado, pero cambia lo que significaba una notificación hasta ahora. Cuando haya usuarios reales conviene comprobar que no se percibe como ruido.

## Relacionado

- Fase: [[Fase-17-captacion]] — bloque 17-A (andamiaje)
- Revisa el trade-off de: Fase 12, cierre P0.2 (commit `29fb156`), que sigue vigente para el origen manual
- Nota de volumen: `docs/VOLUMEN_MATCHER.md`
- Tests: `backend/tests/test_ingesta.py` — alcance, regresión manual y aislamiento de datos
