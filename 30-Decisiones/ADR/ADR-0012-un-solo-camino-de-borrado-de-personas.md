---
tipo: adr
fase: "[[Fase-14-rgpd]]"
estado: aprobado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aprobado
  - fase/14
  - area/datos
  - area/seguridad
---

# ADR-0012: hay un solo camino de borrado de personas, y la anonimización de la auditoría forma parte de él

## Contexto

La Fase 14 trae `DELETE /cuenta`. La 11-A ya había construido un borrado en `purga_service` para las cuentas nunca verificadas. Son dos motivos distintos para borrar a la misma clase de entidad, y la tentación evidente era escribir el segundo al lado del primero.

Lo que lo desaconseja no es la duplicación en abstracto, sino un hecho medido del esquema: **ni `Usuario` ni `Organizacion` declaran una sola `relationship()`, y ninguna clave foránea que les apunte declara `ondelete`**. No hay cascada, ni de ORM ni de base de datos. Cada tabla hija hay que borrarla a mano y en orden.

Y el modo de fallo no es simétrico entre motores. En PostgreSQL, dejarse una tabla aborta la transacción: ruidoso, se ve. En SQLite —donde las claves foráneas están apagadas por defecto y la suite no las enciende— **pasa en verde y deja filas huérfanas**: datos personales que sobreviven a un borrado que el sistema dio por completo.

Dos implementaciones significan dos listas de tablas hijas que hay que acordarse de mantener a la vez. La segunda vez que alguien añada una tabla, se acordará de una.

### Lo que apareció al mirarlo de cerca

`auditoria.quien` y `auditoria.entidad_id` guardan **la dirección de correo**, no el identificador: la escriben así `registrar_usuario`, `verificar_email` y `cambiar_password` (`app/services/usuario_service.py`). De modo que hasta esta fase **la purga de la 11-A borraba la cuenta y dejaba el correo en la auditoría**. No es un riesgo hipotético que esta fase evita: es un defecto que esta fase corrige.

## Decisión

**`borrado_service.borrar_datos_de_usuario` es el único sitio del sistema que borra a una persona, y anonimiza la auditoría como parte del borrado, no como un paso aparte.** La purga sin verificar y el borrado a petición son dos llamantes con dos predicados distintos sobre la misma función.

## Justificación

### Qué se comparte y qué no

Se comparte **la cascada**: qué tablas hijas hay, en qué orden, y qué se hace con la organización si queda vacía. No se comparte **el predicado**: la purga tiene sus nueve condiciones (ADR-0009), el borrado a petición tiene la gracia vencida. Meter el predicado dentro habría vuelto a mezclar lo que esta separación existe para separar.

`borrar_datos_de_usuario` **no comitea ni revierte** a propósito: el llamante decide la transacción, porque es quien sabe qué más va dentro de ella.

### Por qué anonimizar y no borrar las filas de auditoría

La traza de qué ocurrió en el sistema es legítima y a menudo obligatoria. Lo que no es legítimo es que siga nombrando a quien pidió desaparecer. Se sustituye la dirección por un seudónimo estable derivado del identificador: la traza sigue agrupando las acciones del mismo titular, y una vez borrada la fila de `usuario` no queda nada en el sistema que devuelva ese seudónimo a una persona.

**El orden importa y no es casualidad**: se anonimiza ANTES de borrar la fila de `usuario`, porque después ya no se sabría qué correo sustituir.

### Un detalle que solo apareció en PostgreSQL

El seudónimo se escribe en dos columnas de anchos distintos. `auditoria.quien` es `String(120)` y admite el prefijo `anonimizado:`; `auditoria.entidad_id` es `String(36)`, exactamente un UUID, y `anonimizado:` + UUID son 48 caracteres. En PostgreSQL eso aborta con `StringDataRightTruncation` — que es como se descubrió. **En SQLite se habría guardado entero y nadie se habría enterado hasta el primer despliegue.** De ahí que `entidad_id` lleve el identificador pelado.

Es la justificación de la fila (b) de la puerta escribiéndose sola: sin PostgreSQL en la CI, este bug se habría fusionado en verde.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Un borrador propio para el RGPD, al lado del de la purga | Dos listas de tablas hijas que mantener a la vez. El día que alguien añada una tabla y actualice solo una, el otro camino deja huérfanas — y en SQLite, en verde |
| Declarar `ondelete="CASCADE"` en las claves foráneas y dejar que la base borre | Es la solución correcta en un proyecto nuevo, pero aquí exige una migración que reescriba seis claves foráneas sobre datos existentes, y la cascada de base de datos borraría **también la auditoría**, que es justo lo que hay que conservar. Queda anotado como deuda, no como parte de esta fase |
| Meter el predicado dentro del borrador y distinguir por un parámetro `motivo` | Devuelve al mismo sitio: una función que hace dos cosas según una bandera, con la bandera decidiendo si se borra a alguien |
| Borrar las filas de auditoría del titular en vez de anonimizarlas | La traza de qué pasó en el sistema no es del usuario, y a menudo hay obligación de conservarla. Borrarla para cumplir el RGPD incumpliría otra cosa |

## Consecuencias

### Positivas

- Una sola lista de tablas hijas, y un test que **la deriva del `metadata`** en vez de enumerarla: añadir una tabla colgando de `usuario` sin cubrirla pone el test en rojo con el nombre de la tabla, sin que nadie tenga que acordarse.
- La misma comprobación de filas huérfanas corre en SQLite **y en PostgreSQL**, que es donde de verdad demuestra algo.
- Se corrige de paso un defecto real: la purga dejaba la dirección de correo en la auditoría.
- Demostrado por mutación: quitar una tabla hija de la lista, o dejar la anonimización sin efecto, pone tests en rojo en los dos caminos a la vez — que es exactamente el beneficio de que sea uno solo.

### Negativas / deuda asumida

- **El borrado sigue siendo manual y ordenado.** La solución de fondo es `ondelete` en el esquema; esto es la mejor versión de la solución que no lo es.
- **La cobertura depende de que el escenario siembre todas las tablas hijas.** El test lo comprueba contra el `metadata` y falla si alguna falta, pero eso obliga a mantener `escenario_rgpd.sembrar_titular` al día. Es un aviso ruidoso, no una garantía silenciosa.
- **El seudónimo conserva el identificador.** Es deliberado —la traza tiene que seguir agrupando—, pero significa que la anonimización es seudonimización: si alguien conservara una copia externa que ligue identificador y persona, se podría revertir.
- **Las organizaciones huérfanas siguen solo contándose, no borrándose** (ADR-0009). El borrado a petición no cambia eso.

## Relacionado

- Fase: [[Fase-14-rgpd]]
- [[ADR-0009-purga-de-cuentas-nunca-verificadas]] — el borrado ordenado que esta decisión extiende, y cuyo predicado de nueve condiciones sigue intacto
- `docs/PLAN_FASES.md` §3, Fase 14 — la decisión previa, escrita antes de implementar
- Tests: `backend/tests/test_rgpd.py`, `backend/tests/test_postgres.py`, `backend/tests/escenario_rgpd.py`
