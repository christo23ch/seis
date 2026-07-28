# FASE 13: PLAN DE EJECUCIÓN — Monetización con Stripe

**Fecha:** 2026-07-25
**Versión:** 2.0 — revisada por diseño y seguridad
**Proyecto:** SEIS
**Rama propuesta:** `feature/fase-13-stripe` (a crear)
**Estado:** **NO implementable tal cual.** Cuatro correcciones bloqueantes y cinco decisiones
pendientes del humano (§12). No se ha escrito código.

**Documento hermano:** [`FASE_13_MAPA_IMPACTO_STRIPE.md`](FASE_13_MAPA_IMPACTO_STRIPE.md) —
**parcialmente superado por este documento**; ver §11 para la lista de secciones erróneas.
En caso de conflicto, **manda este documento**.

---

## 0 · Qué cambió en la v2.0

La v1.0 fue revisada en paralelo por dos pases: uno de arquitectura y uno de seguridad. Ambos
convergieron de forma independiente en el mismo defecto central: **el modelo de datos heredado
del mapa de impacto no soporta la idempotencia sobre la que descansa toda la fase.**

Cambios respecto de la v1.0:

| Área | v1.0 | v2.0 |
|---|---|---|
| Nº de migración | `0005` («verificado») | **Error mío: la `0005` estaba reservada.** Ver §1 y §12-Q1. **Derogado por la Fase 9.5: la `0005` es la revisión fundacional; la Fase 13 toma la `0007`, con `down_revision = "0006"`** |
| Orden de bloques | A‖B → C → **D → E** → … | A‖B → C → **E → D** → … (§7) |
| `EventoFacturacion` | Idempotencia por `evento.id` | **El esquema no tiene esa columna.** Corrección bloqueante B1 |
| `Organizacion`↔`Suscripcion` | 1:1 con `unique=True` | **1:N**; el 1:1 destruye el histórico (§4) |
| Campos de plan en `Organizacion` | 4 columnas nuevas | **Solo `stripe_customer_id`**; las otras 3 son desincronización (§4) |
| Cancelación | Fin de periodo (plan) / inmediata (mapa) | **Contradicción real.** Se resuelve a fin de periodo (D5) |
| Token en `localStorage` | Diferido a Fase 16 sin más | Diferido **con control compensatorio** en esta fase (§12-Q3) |
| Dependencias npm de Stripe | 2 paquetes | **Ninguna** — con Checkout por redirección no hacen falta (§8) |
| D1–D5 | Abiertas | **Cerradas** (§2) |

---

## 1 · Estado verificado del repo

### Corrección: el número de migración de la v1.0 era incorrecto

La v1.0 afirmaba, como dato «comprobado directamente contra el código», que la siguiente
migración libre era la `0005`. **Es cierto respecto del código y falso respecto del backlog.**
Verificado en `docs/PENDIENTES.md`:

- **línea 29:** «Migración nueva = **0005**» (Fase 10)
- **línea 38:** `alembic/versions/0005_self_service.py`

> *Cita del estado de `PENDIENTES.md` en el momento de escribir este plan. Ambas líneas fueron
> corregidas después, en la Fase 9.5 (Bloque J): hoy dicen `0006`.*

Y `CLAUDE.md` §5 sitúa la **Fase 10 antes que la 13** en la ruta crítica (9→10→11→13), con su
migración ya numerada `0005`. Si ambas ramas fijan `revision = "0005"` y
`down_revision = "0004"`, al fusionar se obtiene una **cadena de Alembic bifurcada**.

→ **Resuelto (§12-Q1): la Fase 13 toma la `0006`**, con `down_revision = "0005"`. La Fase 10
conserva la `0005` que ya tiene documentada.

> **Derogado por la Fase 9.5 (Bloque J).** Aquella resolución presuponía la cadena `0001`-`0004`,
> retirada desde entonces. La numeración vigente es: **fundacional `0005`** (`down_revision = None`),
> **Fase 10 → `0006`**, **Fase 13 → `0007`** con **`down_revision = "0006"`**. La consecuencia de
> orden se mantiene intacta: la Fase 13 sigue sin ser desplegable antes que la Fase 10.

**Consecuencia de orden que hay que asumir explícitamente:** la migración de la Fase 13 —hoy la
`0007`— **no puede aplicarse hasta que exista la de la Fase 10, hoy la `0006`**. Es decir, **la Fase 13 no es desplegable antes que la Fase 10**. Coincide
con la ruta crítica del plan maestro (9→10→11→13), pero deja de ser una preferencia y pasa a ser
una dependencia técnica dura. Si se decidiera implementar la 13 antes que la 10, habría que
renumerar en ese momento.

### Otros datos verificados (estos sí, contra código)

- **`backend/alembic/versions/0001_esquema_inicial.py:18`** →
  `Base.metadata.create_all(bind=op.get_bind())`. **Consecuencia grave para el Bloque A:** en
  cuanto se añadan las tres tablas nuevas a `models.py`, la revisión `0001` ya las creará. Sobre
  una BD vacía, la migración de facturación será un **no-op** y `alembic upgrade head` en verde
  **no probará absolutamente nada** sobre la ruta real de actualización en producción. El único
  test honesto construye el esquema previo con DDL explícita. **Ese andamiaje no existe** (no hay
  `test_migraciones.py` en `backend/tests/`) y la v1.0 no lo presupuestaba.
- **`backend/alembic/env.py:20-22,31`** → `context.configure(...)` **sin `render_as_batch=True`**.
  SQLite no soporta `ALTER TABLE ... ALTER COLUMN`, y la `0004` usa
  `op.alter_column(..., type_=sa.String(120))`. **La evidencia se contradice:**
  `docs/PENDIENTES.md:134` afirma que la `0003` y la `0004` tienen «upgrade/downgrade verificados
  en SQLite». **No especular: hay que ejecutarlo** antes de aceptar el criterio de «hecho» del
  Bloque A (§12-Q5).
- **`backend/app/models.py:302`** → `Auditoria.entidad_id` es `String(36)`. Los ids de Checkout
  Session de Stripe (`cs_test_a1...`) rondan **66–70 caracteres**. Es **exactamente el bug que
  obligó a escribir la migración `0004`**, documentado en el propio código
  (`models.py:299`: *«antes String(36), truncaba emails»*). SQLite ignora la longitud de
  `VARCHAR` → pasa verde en toda la suite y **mata el webhook en producción con
  `22001 string_data_right_truncation`**.
- **`backend/app/api/deps.py:51`** → `require_propietario` comprueba
  `user.rol_org != "propietario" and not user.es_superadmin` → 403. Nada más. **No** comprueba
  `organizacion_id is not None`; `organizacion.py:52` lo parchea a mano con un 400.
- **`backend/app/main.py`** → **no hay autenticación global**; la auth es por endpoint vía
  `Depends`. La redacción de la v1.0 («el router de webhooks debe registrarse aparte, sin la
  autenticación estándar») podía inducir a inventar un middleware inexistente. Basta con **no
  añadir la dependencia**, y registrarlo bajo `settings.api_v1_prefix` como los demás.
- **`frontend/lib/api.ts`** → confirmado: el token vive en **`localStorage`** (clave `seis_token`,
  `getToken`/`setToken`), enviado como `Authorization: Bearer`. Queda cerrado el punto que la v1.0
  dejaba sin confirmar.
- **No existe rate limiting en ningún punto del backend** (verificado por búsqueda: sin `slowapi`
  ni equivalente). No es regresión de la Fase 13, pero la Fase 13 es **la primera vez que se
  expone un endpoint público sin JWT**.
- **`backend/app/services/pdf_service.py`** → expone `informe_a_pdf(markdown, titulo)`, orientado
  a informes de análisis. **No reutilizable para facturas** (ver D4).
- Convenciones reales de `models.py`: PK `String(36)` con `default=_uuid` en entidades de dominio;
  `Auditoria`/`ReglaDisparada` usan `Integer` autoincremental; **el repo nunca usa `Enum`** —
  siempre `String(n)` con comentario; dinero en `Numeric(14,2)`; fechas en
  `DateTime(timezone=True)`.

---

## 2 · Decisiones de diseño cerradas

### D1 — Correlación organización↔Stripe

**Resuelta: cascada, con `metadata.organizacion_id` como canal primario.** Orden de resolución
dentro del webhook:

1. **`metadata.organizacion_id`**, estampado en **tres** objetos, no en uno: el `Customer`, la
   `Checkout Session` y —**esto es lo que la v1.0 no decía**— `subscription_data.metadata` al
   crear la sesión. **La metadata de una Checkout Session no se propaga a la `Subscription` ni a
   las `Invoice` que esa suscripción genera después.** Si solo se estampa en la sesión,
   `invoice.paid` del segundo mes llega sin metadata y la correlación **falla en producción, no
   en test**.
2. `client_reference_id = organizacion_id` en la sesión, como canal redundante y barato.
3. `Organizacion.stripe_customer_id` (indexado) como último recurso, para eventos sin metadata
   propia (`customer.updated`, disputas).
4. Si los tres fallan: **persistir el evento como huérfano** (`organizacion_id = NULL`), responder
   **200** y alertar. Nunca 4xx ni 5xx — un evento irresoluble con respuesta de error hace que
   Stripe reintente durante días y acabe **deshabilitando el endpoint**.

**Caso de arranque, corregido.** La carrera real no es «el primer evento llega antes de que exista
`stripe_customer_id`», sino que **`checkout.session.completed` puede llegar mientras el
`POST /suscripcion/cambiar-plan` que creó la sesión todavía no ha hecho commit.** Con `metadata`
la correlación es autocontenida en el payload y esa carrera desaparece; con `customer_id` no.

**Validación cruzada obligatoria (defensa en profundidad).** Resuelta la organización por
metadata, verificar que `evento.data.object.customer == organizacion.stripe_customer_id`. Si no
coincide: **no aplicar el efecto**, registrar la anomalía en `Auditoria`, responder 200. Sin esta
comprobación, un `stripe_customer_id` desactualizado (regeneración manual del customer en el
dashboard, error humano) aplicaría el efecto **sobre la organización equivocada en silencio**.

**Implicación de esquema:** `EventoFacturacion.organizacion_id` debe ser **nullable**, lo que
contradice el mapa §2.1.

### D2 — `require_propietario` vs. dependencia nueva

**Resuelta: reutilizar `require_propietario`. No crear `require_facturacion_access()`.** La
semántica no diverge: «quien gestiona la organización» y «quien compromete dinero de la
organización» son el mismo sujeto en el modelo de roles de la Fase 9, y no existe hoy un rol de
facturación delegado.

Tres matices que la v1.0 no cubría:

1. **Lo que falta no es una segunda `require_*`, sino un helper de resolución de tenant.**
   `require_propietario` no comprueba `organizacion_id is not None`; los seis endpoints
   necesitarán el mismo parche que `organizacion.py:52`. La extracción DRY correcta es
   `organizacion_actual(user)`, que devuelve la org o lanza.
2. **El superadmin pasa `require_propietario`.** En `organizacion.py:69` eso es un bypass
   cross-org deliberado. **En facturación no debe serlo.** La org efectiva es **siempre**
   `user.organizacion_id`, sin excepción para superadmin. *(Hoy es inocuo porque
   `organizacion_id` sale del token; sería escalada cross-tenant inmediata en cuanto alguien
   añadiera un parámetro `org_id` a la ruta. Debe quedar escrito.)*
3. **Descartar `require_metodo_pago_valido()`** del mapa §2.5. «Tener `stripe_customer_id`
   válido» es una precondición de negocio, no una decisión de autorización; como dependencia
   produciría un **403 ante un estado de negocio**. Va en el servicio.

**Quién ve las facturas:** el mapa marca `/facturas*` como `auth` — cualquier miembro, **incluido
un `lector`**, vería importes e historial de pagos. Ambos revisores lo señalaron como decisión no
razonada. **Recomendación:** `GET /suscripcion` accesible a cualquier miembro (lo necesitan
`/equipo` y `/nueva` para pintar límites); **todo `/facturas*` bajo `require_propietario`**.
Decisión en §12-Q4.

### D3 — Concurrencia sobre `Suscripcion`

**Resuelta: tres capas. Ninguna de ellas es el bloqueo optimista por `actualizado_en` que la v1.0
sugería.**

Se descarta esa opción de entrada: `actualizado_en` es una marca de tiempo **local**, no una
versión, y no dice nada sobre la antigüedad relativa de dos eventos de Stripe. Evita escrituras
concurrentes pero **no evita aplicar un evento viejo encima de uno nuevo**, que es el fallo real.

- **Capa 1 — Idempotencia garantizada por la BD.** `UNIQUE` sobre
  `evento_facturacion.stripe_evento_id`. El handler **inserta la fila del evento y hace commit
  antes de procesar nada**; si salta `IntegrityError`, el evento ya se vio → 200 y salir. Elimina
  el duplicado con independencia de la concurrencia y funciona **idéntico en SQLite y
  PostgreSQL** → plenamente testeable en CI.
- **Capa 2 — Reconciliación en lugar de delta.** *La decisión arquitectónica importante.* El
  handler **no aplica el contenido del evento**: lo toma como *señal*, relee el objeto canónico
  desde la API de Stripe (`Subscription.retrieve`, `Invoice.retrieve`) y **sobrescribe** el estado
  local. Dos eventos desordenados del mismo ciclo **convergen al mismo estado final** porque ambos
  leen la misma verdad. Colateral: es literalmente la afirmación que el plan ya hacía («Stripe es
  la fuente de verdad»), y hace que `webhook_service` y `stripe_tasks` (Bloque G) compartan **la
  misma** función reconciliadora, cumpliendo R8 sin código paralelo.
- **Capa 3 — `SELECT ... FOR UPDATE`** sobre la fila de `Suscripcion` (`.with_for_update()`).
  **No es representable en SQLite**: el dialecto omite la cláusula silenciosamente. El mismo
  código corre en tests sin ramificar, pero **esta capa no queda ejercitada por la suite**.
  Documentarlo y validarlo **una vez a mano contra PostgreSQL**.

**Cobertura real en CI:** la dan las capas 1 y 2. Test concreto: aplicar los mismos dos eventos
**en ambos órdenes** y afirmar que el estado final es idéntico.

**Procesamiento síncrono.** El mapa §7.2 sugería responder 202 y procesar en Celery. Es compatible
con la capa 1, pero solo hace falta si el handler supera los pocos segundos, y no lo hará —
siempre que **el envío de notificaciones no ocurra dentro del handler** (ver §5, Bloque E).

### D4 — PDF de factura

**Resuelta: proxy autenticado, con re-resolución de la URL contra la API de Stripe en cada
descarga. Nunca servir la URL cacheada. Nunca regenerar con `pdf_service.py`.**

- Se persiste `stripe_invoice_id` (estable). `url_pdf` se trata como caché volátil, o no se
  almacena.
- `GET /facturas/{id}/descargar` → resolver la factura **acotada por `organizacion_id`**
  (**404** si es de otra org, no 403) → `Invoice.retrieve(stripe_invoice_id)` para URL fresca →
  descargar los bytes en el backend → devolver con `Content-Disposition: attachment`.

**Por qué no la URL cacheada (ni un 302 a Stripe).** Una redirección entrega al navegador una URL
de Stripe **pública y no autenticada**. En cuanto está en el historial, en un `Referer`, en un
correo reenviado o pegada en Slack, cualquiera accede a la factura de esa organización. **Perfora
exactamente la frontera multi-tenant que el resto de la fase construye**, y la regla heredada
«recurso ajeno = 404» deja de significar nada si el recurso se alcanza por otra vía sin sesión.
Además, una redirección no es auditable como «descarga efectuada», y §6.4 exige rastro.

**Por qué no regenerar con `pdf_service.py`.** La factura que emite Stripe **es** el documento
fiscal; generar un segundo PDF con el mismo número produce **dos documentos distintos para un
mismo asiento**. Es un problema contable en España, no estético.

**Si se implementa el proxy:** validar que el host de la URL pertenece al dominio de Stripe antes
de la petición saliente (defensa anti-SSRF, cinturón y tirantes).

### D5 — Momento de efecto de la cancelación

**Resuelta: al final del periodo pagado (`cancel_at_period_end=True`).**

**Contradicción real entre documentos, no ambigüedad:** el plan v1.0 §6 decía «efecto al final del
periodo pagado», pero el mapa §5.4 especifica el flujo contrario —
*«Actualizar en BD: `Suscripcion.estado = 'canceled'`, `fecha_fin = hoy`»*. **Implementar el mapa
retira el acceso a un periodo que el cliente ya pagó.** Es un defecto.

**Diseño correcto:**
- Stripe: `Subscription.modify(id, cancel_at_period_end=True)`.
- Local: **no se toca `estado`**. Se añade `cancelar_al_final_periodo: bool` y
  `fecha_fin = current_period_end` (futura). `estado` pasa a `canceled` **únicamente** cuando
  llega `customer.subscription.deleted` — es decir, **la cancelación también la aplica el
  reconciliador, no el endpoint**.

**Implicación para el Bloque F:** el chequeo de límites **no puede leer `estado` como cadena**.
Hace falta **una sola** función `plan_efectivo(suscripcion, ahora)` que consuman
`analisis_service`, `usuario_service` y el endpoint que alimenta al frontend. Durante la ventana
de cancelación pendiente, los límites siguen siendo los del plan pagado.

**Implicación para el frontend:** «Plan Pro · activa hasta el 26/08/2026 · no se renovará», con
botón «Reactivar» = `cancel_at_period_end=False`. Un campo, coste cero, **sin nuevo checkout**.

**Por qué no inmediata:** exige prorrateo y reembolso, que §8 declara fuera de alcance — elegir
inmediato **contradice el propio alcance de la fase**. Y destruye la suscripción en Stripe, de
modo que «reactivar» pasa a crear una con `stripe_subscription_id` distinto, lo que colisiona con
el `unique=True` del modelo 1:1 propuesto.

---

## 3 · Correcciones bloqueantes

**No se puede empezar a implementar sin resolver estas cuatro.**

### B1 — `EventoFacturacion` no tiene columna para el id de evento de Stripe

*Detectado de forma independiente por ambos revisores.*

El esquema del mapa §2.1 es: `id` (BigInt autoincremental), `organizacion_id`, `tipo`,
`referencia_stripe` (documentado como *«invoice_id, subscription_id»*), `payload_stripe`, `quien`,
`creado_en`, `procesado`.

**No existe ninguna columna para `evento.id` de Stripe.** `referencia_stripe` es el id del
*sub-objeto* (`evento.data.object.id`), **no** el id del objeto `Event` (`evt_...`), que es el que
hay que deduplicar. El único sitio donde quedaría es dentro del JSONB, sin índice.

→ **La idempotencia que el Bloque E y §10 dan por sentada no tiene soporte en el esquema.**

**Corrección:** `stripe_evento_id String(64)` con **`UNIQUE NOT NULL` a nivel de BD**, poblada con
`evento["id"]`. Es un cambio de esquema: debe cerrarse **antes** de escribir la migración.

### B2 — La idempotencia debe ser *insert-first*, no `SELECT`-then-`INSERT`

Con comprobación en lógica de aplicación, dos entregas simultáneas leen ambas «no existe» y ambas
procesan. Stripe reintenta agresivamente ante timeouts y **no garantiza serialización**.

**Corrección:** intentar el `INSERT` con `stripe_evento_id` como **primera operación**; capturar
`IntegrityError` → «ya procesado» → 200 sin ejecutar ningún efecto de negocio.

### B3 — La migración debe hacer backfill de suscripciones para las organizaciones existentes

*El riesgo más grave que la v1.0 no recogía.*

> **B3 es consumidora de la convención de DML de `CLAUDE.md` §6.10** (escrita en la Fase 9.5,
> Bloque I). El backfill de B3 es un `INSERT` de migración, exactamente la clase de operación que
> tumbó la revisión `0002`: aquel `INSERT INTO organizacion (id, nombre)` omitía `creado_en`, una
> columna `NOT NULL` cuyo `default=_now` es **de cliente** y por tanto inexistente para el SQL crudo,
> y el resultado medido fue `IntegrityError: NOT NULL constraint failed: organizacion.creado_en`,
> con `alembic upgrade head` inservible sobre base limpia. **El `INSERT` de B3 debe enumerar
> explícitamente todas las columnas `NOT NULL` de `Suscripcion` sin `server_default`**, incluidas
> las de marca temporal. No es una recomendación de estilo: es la barrera que impide repetir el
> defecto que motivó la Fase 9.5.

Ni el plan ni el mapa dicen qué pasa con los tenants que ya existen —incluida la «Organización por
defecto» que crea el backfill de la `0002` y la org del admin bootstrap que siembra
`conftest.py`—. Quedan **sin fila en `Suscripcion`**. Entonces llega el Bloque F y
`validar_limite_analisis` encuentra `suscripcion is None`:

- **si falla en cerrado:** la migración **inutiliza a todos los tenants existentes** en el
  instante del despliegue, y revienta los tests que crean análisis (`test_api.py`,
  `test_golden_caso19.py`, `test_multitenant.py`);
- **si falla en abierto:** el límite se salta trivialmente no teniendo suscripción, y **toda la
  fase es decorativa**.

**Corrección:** backfill en la migración, con el patrón que la `0002` ya estableció — una fila de
`Suscripcion` por organización existente, `estado='trialing'`, `fecha_fin = now + 14 días`, sin
ids de Stripe; y borrado en el `downgrade`.

### B4 — Colisión del número de migración con la Fase 10 ✅ RESUELTA

~~**Fase 13 = `0006_facturacion_y_suscripciones.py`, `down_revision = "0005"`.** La Fase 10 conserva
la `0005`.~~

**Vigente tras la Fase 9.5 (Bloque J): Fase 13 = `0007_facturacion_y_suscripciones.py`, con
`down_revision = "0006"`.** La `0005` es la revisión **fundacional** (`down_revision = None`, 21
tablas) y la Fase 10 toma la `0006`. Ver §1 para la consecuencia de orden de despliegue, que no
cambia: la Fase 13 sigue sin ser desplegable antes que la Fase 10.

---

## 4 · Modelo de datos corregido

### Eliminar la duplicación de estado en `Organizacion`

**Quitar `plan_actual`, `estado_suscripcion` y `proxima_facturacion`. Conservar solo
`stripe_customer_id`** (con índice único).

No es denormalización justificada, es una fuente de desincronización:
- **No hay presión de lectura que la justifique.** El acceso es siempre
  `WHERE organizacion_id = ?` sobre una tabla indexada de a lo sumo una fila activa por tenant.
- Son tres campos escritos desde handlers de webhook concurrentes: **el vector de desincronización
  que D3 intenta cerrar, multiplicado por dos ubicaciones.** Síntoma visible: «el usuario ve el
  plan equivocado» o «el usuario queda bloqueado sin deberlo».
- `stripe_customer_id` **sí** pertenece a `Organizacion`: es la clave de correlación del tenant,
  estable a través de suscripciones sucesivas, y es el fallback de D1.
- Señal reveladora: `Organizacion.proxima_facturacion` vs. `Suscripcion.proxima_fecha_facturacion`
  — **dos nombres para el mismo concepto ya en la especificación.**

### `Organizacion`↔`Suscripcion`: 1:N, no 1:1

**Quitar `unique=True` de `Suscripcion.organizacion_id`; conservarlo en
`stripe_subscription_id`.**

El 1:1 impide conservar el histórico, y no de forma hipotética:
- Cancelar y reactivar **después** del fin de periodo crea una suscripción nueva en Stripe, con
  id distinto. Con 1:1 hay que sobrescribir, y se pierde **qué suscripción generó qué facturas**.
- `Factura.suscripcion_id` apuntaría a una fila mutada en el sitio: las facturas históricas
  acaban referenciando un registro cuyo `plan_codigo` y `fecha_inicio` **ya no son los vigentes
  cuando se emitieron**. La FK deja de significar lo que dice.
- **Choca con el estilo de la casa.** El principio P1 de `CLAUDE.md` es «snapshot inmutable, nunca
  se sobrescribe». Una fila de suscripción mutable es lo contrario, **en la única parte del
  sistema que maneja dinero**.

**Concesión al argumento a favor del 1:1** (una restricción `UNIQUE` es garantía real contra el
bug de doble suscripción): índice único **parcial** de PostgreSQL sobre
`organizacion_id WHERE estado IN ('active','trialing')`, más guarda en el servicio. No es
expresable en SQLite → declararlo condicionado al dialecto y documentar que la suite no lo
ejercita.

### `EventoFacturacion` — rediseño

Además de B1 y de la nulabilidad de `organizacion_id` (D1):

- **Sustituir `procesado: Boolean` por `estado: String(16)`** (`recibido | procesado | error |
  huerfano`). Un booleano no distingue «todavía no» de «falló definitivamente», y sin esa
  distinción no se puede construir una alerta operativa útil.
- **Añadir `tipo_stripe String(64)`** con el tipo crudo. El enum interno propuesto
  (`plan_created | plan_changed | … | invoice_failed`) **no puede representar**
  `customer.subscription.updated` ni `customer.subscription.deleted`, que son dos de los seis
  eventos que el propio mapa se compromete a manejar.
- **Separar orígenes.** La tabla mezcla eventos de dominio disparados por un administrador
  (`quien` = email) y eventos entrantes de Stripe (`quien` = `'stripe-webhook'`). Mezclarlos
  obliga a que el `UNIQUE` sobre el id de evento sea nullable, **lo que debilita la garantía de
  B1**. Como mínimo, columna `origen`; idealmente, dos tablas.
- **`payload_stripe` es dato personal con retención indefinida** (email, nombre, dirección de
  facturación, últimos cuatro dígitos). Ningún endpoint de `facturacion.py` debe exponerlo.
  **La tabla `Auditoria`, que sí es user-facing, nunca debe copiarlo**: solo id de evento, tipo,
  organización y resultado. Recortar el payload o añadir purga.

### Convenciones de tipos y PKs

| Propuesta del mapa | Convención real del repo | Dictamen |
|---|---|---|
| `id String(36)` en `Suscripcion`/`Factura` | `String(36), default=_uuid` | ✅ Correcto |
| `EventoFacturacion.id BigInt` | `Auditoria`/`ReglaDisparada` usan `Integer` | ❌ Tercera convención sin motivo → `Integer` |
| `estado (Enum: …)` en tres tablas | **El repo nunca usa `Enum`**: `String(n)` + comentario | ❌ Un `ENUM` nativo además complica el `downgrade` (`DROP TYPE`), y §6.3 exige reversibilidad → `String(16)` |
| `Numeric(12,2)` | El repo usa `Numeric(14,2)` | ❌ Ver nota abajo |
| `fecha_emision (Date)` | Todo el repo usa `DateTime(timezone=True)` | ❌ Stripe entrega UNIX en UTC; degradar a `Date` naive produce **errores de un día en frontera de periodo** para usuarios en CET/CEST |
| `Factura.pagado_por String(50)` | — | ❌ El nombre sugiere persona; contiene un `payment_intent` → `stripe_payment_intent_id` |
| `Suscripcion.stripe_customer_id` | — | ❌ Duplicado con `Organizacion.stripe_customer_id`, ambos `unique` → eliminar el de `Suscripcion` |

**Importes — lo de más valor aquí.** Stripe devuelve los importes como **entero en unidades
mínimas (céntimos)**. Convertir a `Numeric` en la frontera introduce una multiplicación/división
por 100 en el camino del dinero. Y **en SQLite, SQLAlchemy no soporta `Decimal` nativo**: los
`Numeric` viajan por `float`, de modo que **las aserciones monetarias de la suite serían
comparaciones de coma flotante**. → Almacenar `importe_total_centimos: Integer` tal cual llega de
Stripe, sin que ningún `float` toque nunca el valor; convertir solo para presentación.

### Ausencias del modelo

- **No hay dónde guardar la sesión de checkout pendiente.** R5 proponía «rechazo en backend si ya
  existe una sesión pendiente no expirada». Con el esquema propuesto **es inimplementable**:
  ninguna tabla guarda `checkout_session_id` ni su caducidad. **R5 no tenía mitigación real.**
- **No hay fin de trial.** El trial de 14 días está en alcance, F debe probar «trial vencido»,
  pero **nada almacena la fecha de fin** salvo ambiguamente `proxima_fecha_facturacion`, y
  **ninguna tarea del Bloque G vence trials**. Ver §9-R11.
- **No hay inicio de periodo vigente** — *consecuencia de la decisión Q2 (cuota por periodo).*
  El modelo propuesto tiene `proxima_fecha_facturacion` (el **fin** del periodo), pero contar
  `COUNT(*) WHERE creado_en >= inicio_periodo` exige el **inicio**. → Añadir
  `periodo_actual_inicio` y `periodo_actual_fin` (`DateTime(timezone=True)`), poblados desde
  `current_period_start`/`current_period_end` de Stripe por el reconciliador, y **eliminar
  `proxima_fecha_facturacion`**, que queda redundante con `periodo_actual_fin`. Durante el trial,
  el periodo es `inicio_trial → fin_trial`.
- **`Factura.numero String(20) unique`** con ejemplo `'INV-2025-001'`: ¿lo genera SEIS o se copia
  de Stripe? Si lo genera SEIS hay **segunda fuente de verdad de numeración** y una carrera entre
  webhooks concurrentes sobre una secuencia global. → Copiar `invoice.number` de Stripe,
  **nullable** (las facturas en `draft` no tienen número).
- **No persistir `cantidad_usuarios_autorizados` ni `cantidad_analisis_incluidos`.** §8 declara
  los planes como configuración estática; persistirlos crea una **tercera** fuente de verdad y la
  clase de bug «el usuario subió de plan pero los límites no cambiaron». Derivarlos de un catálogo
  `PLANES` en código. Si algún día hace falta *grandfathering*, se añaden con una migración barata.

---

## 5 · Subbloques de trabajo

*Solo se detallan aquí los cambios respecto de la v1.0. Los objetivos y archivos de cada bloque se
mantienen salvo lo indicado.*

### Bloque A — Modelo de datos y migración

**Cambios v2.0:** incorpora B1 (columna `stripe_evento_id` con `UNIQUE`), B3 (backfill), B4
(numeración), y el modelo corregido de §4. **Añade** la ampliación de `Auditoria.entidad_id`
(§9-R3).

**Criterio de «hecho» corregido.** El de la v1.0 era inalcanzable: por `0001` haciendo
`create_all`, un `alembic upgrade head` en verde sobre BD vacía **no prueba nada**. El criterio
real es:
- test de migración que **construye el esquema previo con DDL explícita**, aplica el upgrade,
  verifica el backfill y aplica el downgrade (**andamiaje que hay que crear: no existe
  `test_migraciones.py`**);
- `alembic upgrade head` verificado también **sobre PostgreSQL real**, no solo SQLite.

### Bloque B — Configuración

**Cambios v2.0:** el snippet del mapa §2.8 es un borrador **erróneo** y debe descartarse (§11).
Seguir el patrón ya probado de `jwt_secret`/`admin_password`: defaults `""` en el modelo, y
comprobación de prefijo (`sk_live_`, `whsec_`, `pk_live_`) dentro de
`_validar_seguridad_produccion(s)`. **No** meter las claves en `_CAMPOS_SECRETOS`, cuyo escaneo de
marcadores de plantilla **rechazaría claves legítimas de Stripe**.

### Bloque C — Cliente Stripe y dominio puro

**Cambios v2.0:**
- **Allowlist server-side de planes.** `cambiar_plan`/`crear_sesion_checkout` deben validar
  `plan_codigo` contra un allowlist estático `{starter, pro, enterprise}` **definido en el
  backend** antes de resolver el Price ID. Si el valor del cliente se reenviara tal cual hacia
  Stripe, un cliente podría enviar un Price ID arbitrario (de otro producto, de otro entorno) y
  obtener **una sesión de checkout con un precio no previsto**. Cualquier otro valor → 400.
- **El reconciliador vive aquí** (D3-capa 2), no en `webhook_service`. Consecuencia: **G deja de
  depender de E** y desaparece el acoplamiento de una tarea Celery importando un módulo de
  webhooks.
- `plan_efectivo(suscripcion, ahora)` como **única** fuente de límites (D5).
- Helper `organizacion_actual(user)` (D2).
- *Se mantiene el mejor criterio del documento:* **0 imports directos de `stripe` en
  `suscripcion_service.py`**, verificable con un grep.

### Bloque E — Webhook *(adelantado: ahora va antes que D)*

**Criterios de «hecho» endurecidos.** A los de la v1.0 se añaden:
- **el handler es `async def`, lee `await request.body()` crudo y lo pasa sin modificar a
  `construct_event`; no existe ningún modelo Pydantic como parámetro de la ruta** (FastAPI
  re-serializaría y **la firma dejaría de validar**);
- **una única transacción de BD** cubre el efecto de negocio; solo el commit exitoso devuelve 200.
  Cualquier excepción → rollback completo → **500** (Stripe reintenta dentro de su ventana, y la
  tarea del Bloque G es la red de seguridad de segundo orden). *La v1.0 terminaba siempre en 200,
  sin rama de fallo parcial: un 200 falso pierde el evento para siempre;*
- **validación cruzada `customer_id`↔`organizacion_id`** (D1);
- **tolerancia temporal por defecto de `construct_event` (300 s) conservada** — es lo que evita el
  *replay* de un payload válido antiguo. **Merece test explícito;**
- **límite de tamaño de cuerpo** (~1 MB) rechazado **antes** de parsear: el cuerpo hay que leerlo
  entero para poder verificar la firma, y no hay rate limiting en el repo;
- **las notificaciones no se envían dentro del handler.** La Fase 12 ya dejó el patrón: encolar
  fila en `Notificacion` y dejar que el beat la envíe. Enviarlas aquí **acopla el timeout de
  Stripe a la latencia de Postmark**.

### Bloque D — Endpoints de facturación *(ahora después de E)*

**Cambios v2.0:**
- **El endpoint nunca acepta `success_url`/`cancel_url`/`return_url` del cuerpo de la petición**;
  siempre los valores de `settings`. (Hoy no hay open redirect; esto evita que se cuele un
  parámetro «conveniente» durante la implementación.)
- *Idempotency key* propia en `Session.create`, derivada de `(organizacion_id, plan, ventana
  temporal)` — **esto sí mitiga R5**, a diferencia del rate limiting, que no existe en el repo.
- **Timeout explícito** en el cliente Stripe (~10 s con reintentos acotados). El SDK trae ~80 s por
  defecto, **suficiente para colgar workers de FastAPI**.
- Excepciones de Stripe → **502/503 con mensaje en español**, nunca un 500 con traza.
- **Nunca escribir estado local antes de que Stripe confirme.**
- Alcance de lectura según §12-Q4.

**Control compensatorio sobre las mutaciones de dinero (Q3 = reconfirmación + notificación).**
Aplica a `POST /suscripcion/cambiar-plan` y `DELETE /suscripcion/cancelar`:

1. **Reconfirmación por contraseña**, usando `verify_password` (`security.py:22`), que ya existe
   y funciona. **No** usar un código de un solo uso vía `crear_token_proposito` — ver el aviso de
   abajo.
2. **Notificación síncrona al propietario** en el propio endpoint, antes de responder — encolando
   la fila en `Notificacion` (patrón Fase 12), no enviando el correo en la petición. Es un control
   de seguridad, no una cortesía: no espera al webhook.

> ⚠️ **`crear_token_proposito` no garantiza un solo uso hoy.** Verificado en
> `backend/app/core/security.py:45-56`: el token emite un `jti`, y su propio docstring dice que es
> *«para permitir el marcado de un solo uso **cuando el propósito lo exija**»* — pero **no existe
> ningún mecanismo de consumo** en `backend/app/` (búsqueda de `TokenConsumido`/`jti`/`consumido`:
> sin resultados fuera de la propia emisión). La tabla `TokenConsumido(jti PK, proposito,
> consumido_en)` la crea la **Fase 10** (`docs/PENDIENTES.md:37`).
>
> Consecuencia: un código de un solo uso emitido por Fase 13 sería **replayable hasta su
> caducidad** — inaceptable como control sobre una mutación de dinero. Las dos salidas son
> (a) contraseña, que no necesita nada nuevo, o (b) adelantar `TokenConsumido` desde la Fase 10,
> que es alcance ajeno. **Se elige (a).**

### Bloque F — Límites de uso

**Cambios v2.0:** consume `plan_efectivo()` (D5), no `estado` como cadena. Depende **solo de C**
(el diagrama de la v1.0 lo colgaba de E: era un error de dibujo, el texto decía «requiere C»).
Añade: **los límites nunca filtran lecturas** (§9-R6).

**Cuota por periodo (Q2).** `COUNT(*) WHERE organizacion_id = ? AND creado_en >=
periodo_actual_inicio`. Casos que los tests deben cubrir explícitamente:
- **frontera de periodo:** un análisis creado el último segundo del periodo anterior **no** cuenta
  contra el nuevo;
- **cuota de trial:** no se renueva a mitad de trial;
- **sin periodo vigente** (trial vencido, suscripción cancelada y pasada `fecha_fin`): el límite
  cae a «sin plan», que **bloquea creación pero nunca lectura** (R6-bis);
- **caso límite exacto:** N−1 permitido, N bloqueado, con mensaje accionable, **no un 500**.

### Bloque G — Tareas Celery

**Cambios v2.0:** depende **solo de C** (el reconciliador se movió allí). **Añade una tercera
tarea: vencimiento de trials** (§9-R11).

### Bloque H — Frontend: capa de datos

**Criterio corregido.** El de la v1.0 era **falso**: *«`npm run build` compila sin errores de
tipos contra el backend real del Bloque D»* — `tsc` no verifica nada contra un backend en
ejecución; los tipos de `lib/types.ts` se escriben a mano, y **un build verde con tipos inventados
es igual de verde**. Para que signifique algo: generar los tipos desde el OpenAPI de FastAPI, o un
test de contrato.

### Bloque I — Frontend: checkout y dashboard

**Cambios v2.0:** **sin dependencias npm de Stripe** (§8). Añade UI de cancelación pendiente y
botón «Reactivar» (D5).
**Se mantiene intacto el punto fuerte de la v1.0: I después de E** (R1).

### Bloque J — Tests e2e y notificaciones

**Cambios v2.0:** confirmar que `pytest-cov` está en `requirements-dev.txt` antes de comprometer
el «≥80 %». **Las cifras del mapa (190 tests nuevos para ~1400 líneas) son aspiracionales** —
compárese con 104 tests para todo el motor experto. **No tratarlas como criterio de aceptación.**
Renombrar `test_stripe_integración_e2e.py` → `test_stripe_integracion_e2e.py` (la regla de idioma
español aplica a contenido, no a identificadores de módulo).

---

## 6 · Dependencias corregidas

```
A (esquema)  ──┐
B (config)   ──┼──► C (dominio + wrapper + reconciliador) ──┬──► E (webhook) ──► D (endpoints)
               │                                            ├──► F (límites de uso)
               │                                            └──► G (tareas Celery)
               │
D ──► H (frontend: datos) ──┐
E ──────────────────────────┴──► I (frontend: checkout/dashboard)

(C, D, E, F, G) ──► J (tests e2e + notificaciones, incremental)
```

Diferencias respecto de la v1.0: **E antes que D**; **F depende solo de C** (el diagrama lo
colgaba de E, contradiciendo su propio texto); **G depende solo de C** (al mover el reconciliador
a C).

---

## 7 · Orden de trabajo corregido

**`A ‖ B → C → E → D → (F ‖ G) → H → I → J`**

### Por qué E va antes que D

La v1.0 justificaba `E → requiere D` con *«necesita que el flujo de `cambiar-plan` ya genere la
sesión de checkout»*. Pero **según el propio plan, `crear_sesion_checkout` vive en C**
(`suscripcion_service.py`), no en D. **D es una carcasa HTTP delgada sobre C.** Todo lo que el
webhook necesita —modelos (A), secreto de firma (B), reconciliador y la función que estampa la
metadata (C)— está completo al cerrar C.

El argumento más fuerte: **los requisitos de E son los que determinan el esquema de A y el
contrato de D**, no al revés. Es E quien exige la columna de id de evento, la nulabilidad de
`organizacion_id` para huérfanos y el estado de cancelación pendiente. Construir D primero
**congela un contrato de API antes de saber qué necesita almacenar el webhook**.

La v1.0 lo admitía sin darse cuenta al decir que D1 y D4 «deben decidirse en C porque bloquean E»:
si las decisiones de E dominan el diseño, **E debe ir temprano, cuando cambiar el esquema todavía
es barato**.

### Lo que no cambia

**I después de E** (R1). Ese razonamiento de la v1.0 es correcto y se conserva.

---

## 8 · Alcance del PR

### Dentro (cambios respecto de la v1.0 en **negrita**)

Tres planes fijos como configuración estática · Stripe Checkout hospedado por redirección ·
tarjeta como único método (nunca se persiste un PAN) · facturación mensual · webhook con firma,
idempotencia **garantizada por BD** y auditoría · cancelación **`cancel_at_period_end`** ·
validación de límites **con cuota por periodo de facturación** · listado y **descarga por proxy**
de facturas · trial de 14 días **con mecanismo de vencimiento** · migración `0006` reversible
**con backfill** · tests de firma, idempotencia, aislamiento multi-tenant y permisos ·
**reconfirmación por contraseña + notificación síncrona al propietario en las dos mutaciones de
dinero** (Q3).

### Fuera

Se mantienen las exclusiones de la v1.0 (prorrateo, múltiples métodos de pago, cupones,
facturación anual, medios de pago fuera de Stripe, Customer Portal completo, dunning avanzado).

**Nuevas exclusiones:**

| Excluido | Por qué |
|---|---|
| **`@stripe/stripe-js` y `@stripe/react-stripe-js`** | §8 fija Checkout hospedado **por redirección**. Si el backend devuelve `checkout_url` y el frontend hace `window.location.href = url`, **no hacen falta los paquetes ni la clave publicable**. El mapa §3.1/§3.5 añadía dos dependencias y un script de terceros al bundle (contra el presupuesto de bundle del proyecto) para usar `redirectToCheckout`, **que además está obsoleto**. |
| **Migración del token a cookie `httpOnly`** | Se mantiene fuera (razonamiento de la v1.0, confirmado por el pase de seguridad), **pero ya no sin compensación** → §12-Q3. |
| **Rate limiting general del backend** | No existe infraestructura hoy. Fase 13 añade **solo** el límite de tamaño de cuerpo del webhook; el limitador general es materia de la Fase 16. |

---

## 9 · Riesgos — actualizados

Se mantienen R1, R2, R6, R7 y R8 de la v1.0. **R3 se amplía**, **R4 y R5 se corrigen** (sus
mitigaciones originales no funcionaban: `actualizado_en` no es una versión, y R5 no tenía dónde
guardar la sesión pendiente). Riesgos nuevos:

- **R3-bis — Desbordamiento de `Auditoria.entidad_id`.** `String(36)` (`models.py:302`) vs. ids
  de Checkout Session de ~66-70 caracteres. **Es el mismo bug que obligó a la migración `0004`.**
  SQLite ignora la longitud → **verde en toda la suite, muerte en producción**. Ampliar en la
  migración, o guardar el UUID local en `entidad_id` y el id de Stripe en `delta`.
- **R9 — Stripe caído durante un cambio de plan.** Sin estrategia de errores en ninguno de los dos
  documentos. Mitigaciones en el Bloque D (§5).
- **R10 — Doble escritura en el alta de organización.** El flujo del mapa §5.1 crea el `Customer`
  dentro de la transacción de registro: si el commit falla después, queda un customer huérfano;
  el usuario reintenta y se crea un segundo, y el `UNIQUE` empieza a dar guerra. **Peor: la
  disponibilidad del registro de usuarios pasaría a depender de Stripe** — una caída de Stripe
  impediría darse de alta. → Crear el customer **de forma perezosa en el primer checkout** (D1 ya
  no lo necesita antes), o como tarea Celery con clave de idempotencia.
- **R6-bis — Bajada de plan con uso por encima del nuevo límite.** Indefinido. Una org con 40
  análisis y 6 miembros en `pro` baja a `starter` (10 y 2). P1 prohíbe destruir análisis, y
  desactivar miembros en silencio es hostil. → Permitir la bajada y **bloquear solo la creación**.
  **Corolario que debe quedar escrito: los límites de plan nunca filtran lecturas.** Si lo
  hicieran, una bajada ocultaría análisis que la organización pagó — **pérdida de datos desde la
  perspectiva del usuario**.
- **R11 — Vencimiento del trial: no hay mecanismo.** §8 mete el trial en alcance y el Bloque F
  menciona «trial vencido» como caso de prueba, pero **ninguna ruta de código produce ese
  estado**. Hace falta tarea beat o manejar `customer.subscription.trial_will_end`, y decidir el
  estado del día 15.
- **R12 — Retención legal vs. RGPD (Fase 14).** `Factura`/`EventoFacturacion` contienen PII sujeta
  tanto a derecho de supresión como a **obligación legal de conservación de facturas** (varios
  años en España). Dejar escrito ahora —sin implementarlo— que **no deben borrarse en cascada** al
  eliminar una `Organizacion` o un `Usuario`. Evita que la Fase 14 se encuentre con un modelo que
  asume borrado simple.
- **R13 — Semántica de la cuota de análisis. ✅ RESUELTA: por periodo de facturación.** La consulta
  es `COUNT(*) WHERE organizacion_id = ? AND creado_en >= inicio_periodo_vigente`. **Riesgo
  residual:** exige que el inicio del periodo vigente sea conocible en todo momento — ver §4,
  campos de periodo. Y durante el trial, el «periodo» es `inicio_trial → fin_trial`: la cuota del
  trial **no se renueva** a mitad de trial.
- **R14 — Riesgo de proceso: un PR de ~2600 líneas + 190 tests no es revisable por un humano.**
  §6.7 impone «un PR por fase». → §12-Q5.

---

## 10 · Verificaciones mínimas

Se mantienen las de la v1.0, **con estas correcciones**:

- **Test de migración con DDL explícita del esquema previo**, no `alembic upgrade head` sobre BD
  vacía (que por `0001`+`create_all` no prueba nada). **El andamiaje no existe y hay que
  crearlo.**
- **Upgrade/downgrade verificados también contra PostgreSQL real**, no solo SQLite.
- **Test de convergencia por desorden:** aplicar los mismos dos eventos en ambos órdenes y afirmar
  que el estado final es idéntico (D3-capa 2).
- **Test de replay:** payload válido pero con timestamp fuera de la ventana de 300 s → rechazado.
- **Test de idempotencia concurrente:** dos inserciones del mismo `stripe_evento_id` → una
  `IntegrityError` capturada, un solo efecto.
- **Test de allowlist de planes:** `plan_codigo` arbitrario o Price ID directo → 400.
- **Test de backfill:** organizaciones preexistentes tienen suscripción tras el upgrade, y la
  suite de análisis **sigue verde**.
- **Verificación manual única contra PostgreSQL** de la capa 3 de D3 (`FOR UPDATE`), que SQLite no
  ejercita.
- Verificación de que `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` no aparecen en logs.

---

## 11 · Correcciones al mapa de impacto

`FASE_13_MAPA_IMPACTO_STRIPE.md` tiene **errores confirmados**. Secciones superadas por este
documento:

| Sección del mapa | Problema |
|---|---|
| **§2.1** (`EventoFacturacion`) | Sin columna para el id de evento → idempotencia inservible (B1). `organizacion_id` no nullable. `Boolean procesado` insuficiente. Enum de tipos incapaz de representar `customer.subscription.*` |
| **§2.1** (`Organizacion`, `Suscripcion`) | 3 columnas duplicadas; 1:1 destructivo del histórico; `Enum` contra la convención; `Numeric(12,2)` en vez de céntimos; `Date` en vez de `DateTime(timezone=True)` |
| **§2.5** (`require_metodo_pago_valido`) | Precondición de negocio disfrazada de autorización → produciría 403 ante estado de negocio |
| **§2.8** (snippet de `config.py`) | `Field(...)` haría las claves **obligatorias en todos los entornos**, contra el Bloque B y rompiendo `conftest.py`. Y el `@field_validator` referencia `settings.seis_env` **desde dentro de la propia clase `Settings`** — referencia circular que **fallaría en el import** |
| **§3.1 / §3.5** (npm) | Dos dependencias y un script de terceros innecesarios con Checkout por redirección; `redirectToCheckout` está obsoleto |
| **§5.1** (alta) | Crea el `Customer` en la transacción de registro → acopla el alta de usuarios a la disponibilidad de Stripe (R10) |
| **§5.4** (cancelación) | `estado='canceled', fecha_fin=hoy` → **retira acceso ya pagado.** Contradice §8 (prorrateo fuera de alcance) |
| **§7.2** (async) | Recomienda 202 + Celery; se resuelve **síncrono** (D3), siempre que las notificaciones salgan del handler |
| **§Tests** | `test_stripe_integración_e2e.py` — identificador de módulo no ASCII |

---

## 12 · Decisiones que requieren al humano

### Resueltas (2026-07-25)

| # | Decisión | Resolución | Consecuencia propagada |
|---|---|---|---|
| **Q1** | Numeración de migración | ~~`0006` para Fase 13, `down_revision = "0005"`~~ → **derogado por la Fase 9.5: `0007` para Fase 13, `down_revision = "0006"`; la Fase 10 toma la `0006`** | §1, B4. **La Fase 13 deja de ser desplegable antes que la Fase 10** — dependencia técnica dura, no preferencia |
| **Q2** | Semántica de la cuota de análisis | **Por periodo de facturación** | §4 (**faltan `periodo_actual_inicio`/`_fin`**; `proxima_fecha_facturacion` queda redundante), Bloque F, R13 |
| **Q3** | Control compensatorio sobre mutaciones de dinero | **Reconfirmación + notificación síncrona**, ambas | Bloque D, Bloque I, §8. **Reconfirmación por contraseña, no por código de un solo uso** — ver aviso abajo |

> **Aviso sobre Q3, descubierto al propagarla.** `crear_token_proposito` (`security.py:45`)
> **no garantiza un solo uso hoy**: emite `jti` pero no existe mecanismo de consumo en
> `backend/app/`; la tabla `TokenConsumido` la crea la **Fase 10** (`PENDIENTES.md:37`). Un código
> de un solo uso emitido por la Fase 13 sería **replayable hasta caducar**. Por eso la
> reconfirmación se implementa con **contraseña** (`verify_password`, que ya existe), evitando una
> segunda dependencia de la Fase 10. Si prefieres el código de un solo uso, hay que adelantar
> `TokenConsumido` — dilo y lo reflejo.

### Pendientes

| # | Decisión | Recomendación |
|---|---|---|
| **Q4** | **Quién ve las facturas** dentro del tenant: ¿cualquier miembro (incluido `lector`) o solo propietario? | **Solo propietario** para `/facturas*`; `GET /suscripcion` para cualquier miembro. No bloquea arrancar: se decide al llegar al Bloque D |
| **Q5** | **Estructura de entrega.** §6.7 impone «un PR por fase», pero ~2600 líneas no son revisables | **PRs apilados** sobre `feature/fase-13-stripe`: `(A+B+C)`, `(E+D+F+G)`, `(H+I+J)`. Requiere tu excepción explícita a §6.7. No bloquea arrancar |

**Además, antes de aceptar el criterio del Bloque A:** ejecutar `alembic upgrade head` sobre
SQLite para resolver la contradicción entre `PENDIENTES.md:134` («verificado en SQLite») y la
ausencia de `render_as_batch=True` en `env.py`. **No asumir ninguna de las dos.**

---

## 13 · Protocolo

1. Rama `feature/fase-13-stripe`.
2. Plan (v1.0) → **revisión de diseño y seguridad (hecha)** → **corrección (esta v2.0)** →
   **resolución de §12 por el humano** → **aprobación explícita**.
3. Implementación por bloques en el orden de §7.
4. `pytest` y `npm run build`, mostrando resultados.
5. Resumen de qué cambió y qué decisiones se tomaron.
6. PR(s) según Q5, revisados por humano antes de fusionar.

**Este plan no modifica ningún archivo de código.** La implementación queda bloqueada hasta que se
resuelvan las cuatro correcciones de §3 y las cinco decisiones de §12.

---

**Versión:** 2.0 — planificación revisada, sin código
**Revisiones aplicadas:** arquitectura (D1–D5, secuencia, modelo de datos) y seguridad (webhook,
autorización, secretos, PII)
