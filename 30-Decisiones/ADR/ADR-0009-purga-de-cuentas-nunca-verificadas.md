---
tipo: adr
fase: "[[Fase-11-infraestructura]]"
estado: aprobado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aprobado
  - fase/11
  - area/infra
  - area/seguridad
---

# ADR-0009: la purga de cuentas nunca verificadas borra la organización solo si está vacía, y nace desactivada

## Contexto

`docs/PENDIENTES.md` asignaba a la Fase 11 la deuda 10: **las cuentas registradas y jamás verificadas no caducan**. Parecía higiene de tabla. No lo es, por dos motivos que aparecieron al mirarla de cerca.

**El primero: no se puede borrar el usuario y ya está.** Un usuario sin verificar es **propietario de una `Organizacion` propia**, que su propia alta creó. Verificado sobre el mapeo real, no supuesto:

- `Usuario` y `Organizacion` tienen **cero `relationship()`**.
- **Ninguna** de las seis claves foráneas que les apuntan declara `ondelete`.

De modo que no hay cascada de ningún tipo, ni de ORM ni de base de datos. En PostgreSQL, un borrado desordenado **aborta la transacción entera**. En SQLite —donde las claves foráneas están **apagadas por defecto** y la suite del proyecto no las activa— pasa algo peor: **pasa en verde y deja filas huérfanas**, es decir, datos personales que sobreviven a un borrado que el sistema dio por completo.

**El segundo, que eleva la deuda de higiene a defecto funcional: una cuenta zombi secuestra la dirección de correo de forma indefinida.** `registrar_usuario` no crea nada si el email ya existe y el endpoint responde **201 neutro** —comportamiento correcto y deliberado, para no convertir `/registro` en un oráculo de enumeración—. La consecuencia no deseada es que hoy cualquiera puede registrar la dirección de un tercero, no verificarla nunca, y **negarle el alta a su titular para siempre**. La purga es la única salida automática.

## Decisión

**Predicado de nueve condiciones acumulativas.** Una cuenta se purga solo si: no está verificada · no está activa · no es superadmin · es propietaria de su organización · tiene organización · no es el correo del admin bootstrap · se creó antes de la ventana · **no hay ningún otro miembro en su organización** · **no hay ningún `Analisis` en su organización**.

**Borrado manual y ordenado**, hijos antes que padres, porque no hay cascada. **Revalidación del predicado bajo bloqueo**, dentro de la transacción de borrado: es lo único que cierra la carrera con `/verificar`, porque la selección ocurre fuera del bloqueo y el estado puede haber cambiado. **La organización se borra solo si queda sin miembros y sin análisis, recomprobado y no asumido** — un superadmin puede añadir un usuario a cualquier organización entre la selección y el borrado.

**Y nace desactivada: `PURGA_CUENTAS_MODO=informar` de fábrica.** Cuenta las candidatas, lo registra y no borra nada.

## Justificación

### Por qué nueve condiciones y no una

Cada una tapa un camino por el que un borrado ingenuo destruiría algo que no debe. Las dos últimas son las que protegen a terceros: sin ellas, borrar al único usuario de una organización con análisis dejaría esos snapshots —inmutables por el principio P1— **sin ninguna vía de acceso y sin forma de restaurarlos**, porque nadie podría volver a autenticarse en esa organización.

### Por qué el modo seguro por defecto

Un borrado irreversible **no debe ser el comportamiento por defecto de algo que aún no se ha visto correr contra datos reales**. Entregar el mecanismo completo con el interruptor en la posición segura no es diferir: es entregar y dejar que la activación sea una decisión con evidencia delante. Y activarlo es una variable de entorno, no un despliegue de código.

El corolario incómodo, que se dice sin adornar: **la deuda no queda cerrada en producción hasta que alguien mire un informe real y active el modo `borrar`.**

### Por qué la auditoría no se borra jamás

Tres razones, en orden de peso:

1. **No hay integridad que arreglar.** `auditoria.quien` no es una clave foránea: es texto. Un usuario borrado no deja ni una fila inconsistente, así que el argumento «hay que limpiar las referencias» no aplica.
2. **La traza sobrevive al actor, por definición.** La convención 4 del proyecto —«cada acción sensible escribe en `Auditoria`»— pierde todo sentido si la traza se puede eliminar borrando al autor. **Un registro de auditoría cuya vida depende de la existencia del auditado no es auditoría.**
3. **Es la única evidencia de que la purga ocurrió.** Sin ella, una cuenta purgada es indistinguible de una que nunca existió, y un defecto en el predicado sería indetectable a posteriori.

La fila que la purga escribe usa el **UUID** y no el correo, y su delta no lleva dirección: no hay motivo para duplicar por tercera vez una dirección jamás verificada que puede pertenecer a alguien que no pidió nada.

### Por qué las organizaciones huérfanas se cuentan y no se borran

`crear_organizacion` comitea por su cuenta antes de crear al usuario, así que un proceso que muera entre ambos commits deja una organización sin dueño. El predicado, anclado en usuarios, no la ve. Su criterio de seguridad es **distinto** —habría que razonar sobre `analisis.organizacion_id`, que es nulable— y sin esa evidencia **informar es la respuesta correcta e improvisar un borrado no lo es**.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Añadir `ondelete="CASCADE"` a las claves foráneas | Sería lo elegante y haría innecesario el orden manual. **Exige migración Alembic**, y esta fase no lleva ninguna. |
| Marcar las cuentas con una columna `caducada` | Ídem: migración. |
| Avisar por correo antes de borrar | **Enviar correo a una dirección no verificada es exactamente lo que no se debe hacer**, y reabre el canal de bombardeo que la Fase 10 se esforzó en cerrar. |
| Borrar el usuario y dejar la organización | Deja tenants huérfanos y no resuelve nada. |
| Diferir el bloque entero | La deuda tiene propietario nominal en esta fase; no entregar nada la dejaría incumplida. El modo informe entrega el mecanismo sin asumir el riesgo. |

## Consecuencias

### Positivas

- Cierra el secuestro indefinido de direcciones de correo por cuentas zombi.
- El borrado es ordenado y completo: las cuatro tablas hija se vacían antes que el usuario.
- El modo por defecto no destruye nada, y una errata en los plazos **aborta el arranque** en lugar de borrar.

### Negativas / deuda asumida

- **La deuda no está cerrada en producción.** Ver arriba.
- **La carrera perdida devuelve 500.** Si la purga gana la carrera contra `/verificar`, este puede responder 500 en vez del 400 neutro, con el `jti` ya consumido. Requiere verificar en el instante exacto del día 30 tras 30 días de silencio. Se acepta y se documenta; cerrarlo exige tocar `auth.py`, fuera del alcance del bloque.
- **En SQLite el bloqueo se ignora en silencio**, así que la suite demuestra el **predicado**, no el **cerrojo**. Este último solo se ejerce en PostgreSQL.
- **El test que demuestra el orden de borrado enumera las tablas a mano.** Cuando una fase futura añada una tabla hija de `usuario` —la 13, con la suscripción—, la purga dejará de ser completa y **ningún test lo dirá**. En PostgreSQL el fallo sería ruidoso; en el SQLite de desarrollo, filas huérfanas en silencio.
- **La suite entera corre sin integridad referencial** salvo en el único test que activa el PRAGMA. Es un hueco preexistente y anotado, pero pesa más en un bloque que borra.

## Relacionado

- Fase: [[Fase-11-infraestructura]] — Bloque I
- [[ADR-0007-planificador-celery-separado-del-worker]] — la tarea vive en `beat`, que sigue sin escalarse
- Deudas que cierra: 2, 7 y 10 de `docs/PENDIENTES.md`
- Plan del bloque: `docs/FASE_11_PLAN.md` §3
