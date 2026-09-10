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

# ADR-0013: la purga de cuentas sin verificar pasa a anonimizar la auditoría, y por qué eso no se hizo en la Fase 10

## Contexto

La Fase 14 unificó el borrado de personas en `borrado_service` ([[ADR-0012]]). Al hacerlo, la purga de cuentas nunca verificadas —que era el único borrado existente— **cambió de comportamiento**: ahora anonimiza la auditoría del titular antes de borrar su fila.

Eso no estaba en la ficha de la Fase 14. Va aquí porque un cambio de comportamiento que nadie pidió y que nadie documenta es exactamente lo que dentro de seis meses parece un descuido.

### El hecho que lo motiva

`auditoria.quien` y `auditoria.entidad_id` **guardan la dirección de correo, no el identificador**. Lo hacen así tres funciones de `app/services/usuario_service.py`:

- `registrar_usuario` → `Auditoria(quien=u.email, entidad_id=u.email, accion="registro_self_service")`
- `verificar_email` → ídem, `accion="verificar_email"`
- `cambiar_password` → ídem, `accion="cambiar_password"`

De modo que la purga de la 11-A borraba la cuenta, borraba sus cuatro tablas hijas, borraba su organización si quedaba vacía… **y dejaba el correo en la auditoría**. Una cuenta «purgada» seguía nombrando a su titular en el dato más identificativo que hay en el sistema.

No es un riesgo que esta fase evita. Es un defecto que esta fase corrige.

## Decisión

**El borrado de una persona sustituye su dirección en la auditoría por un seudónimo estable, y eso vale para los dos llamantes: la purga y el borrado a petición.** Las filas de auditoría **no se borran**.

Concretamente:

| Columna | Antes | Después | Por qué |
|---|---|---|---|
| `auditoria.quien` | la dirección | `anonimizado:<uuid>` | `String(120)`: cabe el prefijo, y el prefijo hace evidente que es un seudónimo |
| `auditoria.entidad_id` | la dirección | `<uuid>` pelado | `String(36)` es exactamente un UUID: `anonimizado:` + UUID son 48 y **PostgreSQL aborta** |
| `auditoria.cuando`, `accion`, `entidad`, `delta` | — | intactos | son el qué y el cuándo, no el quién |

## Justificación

### Qué se conserva y qué se seudonimiza

Se conserva **la traza**: que ocurrió un registro, una verificación, un cambio de contraseña, y cuándo. Eso no es dato del usuario, es constancia de lo que hizo el sistema, y a menudo hay obligación de conservarla. Borrarla para cumplir el RGPD incumpliría otra cosa.

Se seudonimiza **la identidad**: quién. El seudónimo conserva el identificador para que la traza siga agrupando las acciones de un mismo titular; una vez borrada la fila de `usuario` no queda nada en el sistema que devuelva ese identificador a una persona.

**En rigor esto es seudonimización, no anonimización**, y conviene llamarlo por su nombre: quien conservara una copia externa que ligue identificador y persona podría revertirlo. Dentro del sistema, no.

### Por qué no se hizo en la Fase 10, que es donde nació el problema

La respuesta honesta es que en la Fase 10 **no había nada que anonimizar al borrar, porque no había borrado**. La Fase 10 creó el alta self-service y con ella las tres escrituras de auditoría que guardan el correo; el borrado de cuentas llegó en la 11-A, y la 11-A se ocupó del problema difícil que tenía delante —el orden de borrado sin `ondelete`, documentado en el [[ADR-0009]]— sin mirar una tabla que ninguna clave foránea conectaba con `usuario`.

Ahí está la razón de fondo de que se escapara: **`auditoria` no tiene clave foránea a `usuario`**. El test que deriva las tablas hijas del `metadata` —el que ha funcionado tan bien en esta fase, detectando `consentimiento` solo— no la ve y no puede verla. La ligadura es por valor, no por referencia, y ninguna herramienta que razone sobre el esquema la encuentra.

Se corrige en la 14 y no antes porque es la primera fase que se pregunta qué queda de una persona después de borrarla, en vez de si el borrado se ejecuta sin error.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Borrar las filas de auditoría del titular | La traza de qué pasó en el sistema no es del usuario, y a menudo hay obligación de conservarla. Cumplir el RGPD rompiendo la auditoría es cambiar un incumplimiento por otro |
| Dejar la purga como estaba y anonimizar solo en el borrado a petición | Sería decir que el dato personal molesta cuando lo reclama su titular y no cuando lo limpia el sistema. Además obligaría a una bandera «no anonimices» en el camino compartido, que es la puerta por la que vuelve el segundo borrador |
| Sustituir la dirección por una cadena fija («anónimo») | La traza dejaría de agrupar: dos acciones del mismo titular pasarían a ser indistinguibles de acciones de personas distintas, y la auditoría perdería su utilidad para investigar un incidente |
| Arreglar el origen: que `usuario_service` audite por identificador y no por email | **Es lo correcto y hay que hacerlo**, pero no aquí: reescribe auditoría existente, toca tres funciones del camino de alta y no arregla las filas ya escritas. Queda como deuda anotada abajo |

## Consecuencias

### Positivas

- Una cuenta purgada deja de nombrar a su titular. El defecto llevaba abierto desde la 11-A.
- Vale para los dos borrados sin código duplicado, porque hay un solo camino.
- Demostrado por mutación: dejar la anonimización sin efecto pone en rojo tres tests, en los dos caminos.
- El bug de anchura de columna se encontró **en PostgreSQL**, antes de desplegar. En SQLite se habría guardado un valor de 48 caracteres en una columna de 36 sin protestar.

### Negativas / deuda asumida

- **El origen sigue sin arreglar.** `registrar_usuario`, `verificar_email` y `cambiar_password` continúan escribiendo el correo en la auditoría; lo que hay es una limpieza posterior. Mientras la cuenta viva, la dirección está duplicada ahí. **Deuda con dueño: la Fase 16** (endurecimiento), que es la que revisa qué se registra y dónde.
- **`auditoria` no tiene clave foránea a `usuario`**, así que el test que deriva las tablas hijas del `metadata` no la vigila. La cobertura de esta parte depende de un test escrito a mano que comprueba que la dirección no sobrevive. Si mañana alguien añade otra tabla que guarde correos por valor y no por referencia, **nada lo detectará solo**.
- **Es seudonimización, no anonimización.** Ver arriba.
- **No se tocan las direcciones que pudieran estar dentro de `delta`.** Hoy no las hay: se revisaron las 23 construcciones de `Auditoria(...)` del código y el único `delta` que se arma con entrada del usuario es el de `actualizar_preferencias`, cuyo esquema (`PreferenciasUpdate`) solo admite `canales`, `modo` y tres horas. Pero es una comprobación hecha a mano sobre el código de hoy, no una garantía: es otra ligadura por valor y tiene el mismo punto ciego que `auditoria.quien`.

## Relacionado

- Fase: [[Fase-14-rgpd]]
- [[ADR-0012-un-solo-camino-de-borrado-de-personas]] — el camino compartido del que esto forma parte
- [[ADR-0009-purga-de-cuentas-nunca-verificadas]] — la purga que cambia de comportamiento
- Deuda que abre: arreglar el origen (auditar por identificador) → Fase 16
