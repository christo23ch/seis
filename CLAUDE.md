# CLAUDE.md — Contexto maestro del proyecto SEIS
**Repositorio:** christo23ch/seis
**Rama de trabajo:** main
**Última actualización:** 2026-07-30
**Fuente de verdad funcional/técnica:** `docs/SEIS_Especificacion_Funcional_y_Tecnica.md` (ya incorporada al repo, junto al Plan Maestro y el informe de ejemplo del §19)

---

## 1 · Qué es SEIS (en una frase)

**SaaS de análisis experto de inversión en subastas inmobiliarias españolas**: un usuario define su perfil inversor y capital disponible, SEIS filtra y puntúa oportunidades captadas de distintos portales de subasta (judicial/BOE, AEAT, TGSS, concursal, bancaria, notarial, privada), y entrega por cada una un informe determinista con decisión (semáforo verde/amarillo/naranja/rojo), escalera de precios (ideal / objetivo / máximo / límite absoluto que el software nunca deja superar), rentabilidad (ROI, ROI anualizado, TIR, cash-on-cash en 3 escenarios), riesgo agregado desglosado en 9 dimensiones y estrategia de puja recomendada. Es un producto B2C/B2B por suscripción: el usuario se loguea y paga un plan antes de operar con el análisis completo.

**Principio rector (no negociable):** decisión determinista, auditable y explicable. **La IA estructura información; nunca decide.** Todo cálculo/puntuación/decisión es reproducible byte a byte con la misma versión de reglas y parámetros (snapshot inmutable por análisis).

---

## 2 · Stack técnico confirmado (verificado contra el repo real)

| Capa | Tecnología |
|---|---|
| Backend | FastAPI (`>=0.115`) + SQLAlchemy 2 (`>=2.0.30`) + Pydantic v2 (`>=2.8`) + Alembic (migraciones con `upgrade`/`downgrade`) |
| Auth | PyJWT, JWT propio (`app/core/security.py`), roles vía deps (`app/api/deps.py`) |
| Async / colas | Celery + Redis (`celery[redis]>=5.4`) — análisis async y tareas beat |
| PDF | fpdf2 |
| Base de datos | PostgreSQL 16 + JSONB para atributos por tipología de activo; SQLite en tests. **La imagen desplegada es `postgis/postgis:16-3.4`, pero el esquema NO usa capacidades geoespaciales**: no hay columna `geometry`, no se declara `geoalchemy2` y `lat`/`lng` son `Numeric(9,6)` (verificado en la Fase 9.5, Bloque J) |
| Frontend | Next.js 15.1.6 (App Router) + React 19 + TypeScript estricto |
| Frontend — forms/datos | React Hook Form + Zod (`lib/schema.ts`), TanStack Query, Recharts (gráficos), Leaflet (`mapa-leaflet.tsx`, geolocalización) |
| Estilos | Tailwind CSS 3.4 |
| Contenedores | Docker Compose: PostgreSQL+PostGIS, Redis, backend, worker Celery, frontend |
| Cliente API | `frontend/lib/api.ts` (tipado end-to-end con `lib/types.ts`) |

**No confirmado / pendiente decidir (según Plan Maestro Fases 9-20):** hosting definitivo (Render/Railway vs VPS+Coolify), proveedor de email transaccional (Postmark/SES), analítica (Plausible/PostHog), Stripe (aún no integrado), WhatsApp BSP (condicional a demanda).

---

## 3 · Estado actual (avance ~40 % según Plan Maestro)

### ✅ Construido y verificado
- **Motor experto completo M01–M14** en `backend/app/engine/modules/` (un fichero por módulo, 1:1 con la especificación), **puro y sin I/O**, sobre una pizarra de hechos (`contracts.py`, `pipeline.py` como DAG).
- **162 tests** en `backend/tests/` — 12 ficheros. A los 11 previos se sumó `test_registro.py` (45) en la Fase 10. Incluye el **caso dorado §19** como test de regresión fundacional y la batería T1-T6 que ejerce Alembic de verdad.
  > Cifra verificada con `python -m pytest tests --collect-only -q` el 2026-07-29 (157 recogidos; parametrizaciones incluidas). Recontar antes de citarla.
- **API REST completa** con JWT y roles (`backend/app/api/`: `auth.py`, `routes.py`, `conocimiento.py`, `deps.py`), Swagger en `/docs`.
- **Gobernanza del conocimiento versionada (T2/T3)**: reglas en YAML versionadas con vigencia temporal (`app/engine/rules/`), parámetros legales/fiscales versionados por ámbito (`app/engine/params/`), editables sin desplegar código.
- **Frontend Next.js 15 completo**: login, dashboard, asistente de nueva inversión (11 pasos), detalle de inversión, comparativa, mapa, configuración, reglas, parámetros, administración.
- **PDF de informe**, **Docker Compose** funcional, **manuales** (instalación, pruebas).
- **Migraciones Alembic**: **una sola revisión fundacional, `0005_esquema_base` (`down_revision = None`)**. Sustituye a la cadena `0001_esquema_inicial` → `0002_multitenancy` → `0003_notificaciones` → `0004_ampliar_auditoria_quien`, retirada en el **Bloque D de la Fase 9.5**; su contenido sigue en el historial de git. Cada cambio de esquema exige nueva migración con `downgrade` funcional. La Fase 10 añadió la **`0006_self_service`** (`down_revision = "0005"`); **la siguiente libre es la `0007`** (Fase 13).

### ✅ Fase 9 — Multi-tenancy por organización (COMPLETADA, 2026-07-14)
- Entidad `Organizacion`; `Usuario` += `organizacion_id`, `rol_org` (propietario|miembro), `es_superadmin` (plataforma); `Analisis` += `organizacion_id`.
- **Modelo de roles en dos ejes** (reconciliación): `rol` (admin|analista|lector) = capacidad dentro de la org; `rol_org` = gestión de miembros; `es_superadmin` = gobierno del conocimiento T2/T3 global.
- Migración **Alembic 0002** con backfill (org por defecto para datos históricos; admin bootstrap → propietario+superadmin). **Retirada por la Fase 9.5** (su contenido vive en el historial de git y el esquema resultante viaja en la fundacional `0005`). Su `INSERT` omitía `creado_en`, columna `NOT NULL`, y era la causa medida de que `alembic upgrade head` fallara sobre una base limpia — el defecto que originó la Fase 9.5.
- Aislamiento por `organizacion_id` en todos los endpoints de análisis; acceso a recurso ajeno = **404** (no 403). `require_superadmin` para conocimiento y alta de usuarios de plataforma. Router nuevo `organizacion.py` (GET /organizacion, POST/PATCH miembros por el propietario).
- Frontend: tipos/api/menú actualizados (oculta «Conocimiento» salvo superadmin), página `/equipo`.
- Tests: `test_multitenant.py` (10 nuevos, aislamiento + permisos + gestión de miembros). **Suite: 59 verdes** (49 previos + 10). `npm run build` limpio.

### ✅ Fase 12 — Notificaciones multicanal y scoring exprés (COMPLETADA, 2026-07-24)
- **Notificadores** con interfaz común en `app/notificadores/` (`base.py` define
  `Notificador.enviar(usuario, mensaje)`): `email.py` (Postmark/SES/SMTP según
  `EMAIL_PROVIDER`; **sin credenciales no rompe**: log + buffer `ultimo_email`) y
  `telegram.py` (Bot API por httpx; sin `TELEGRAM_BOT_TOKEN` es no-op).
- **Telegram por polling**, no webhook (decisión: el webhook exige URL pública HTTPS,
  que es Fase 11). Código de 6 dígitos, 10 min, un solo uso; `/start CÓDIGO` guarda
  el `chat_id`. Migrar a webhook = llamar a `procesar_update()` desde el endpoint.
- **Preferencias por usuario**: canales, modo (`instantaneo|digest_diario|digest_semanal`),
  hora del digest y franja de silencio. Tarea beat `seis.digest` (horaria) agrupa las
  pendientes del periodo en **un solo** mensaje.
- **Baja sin login**: enlace firmado con `crear_token_proposito(..., "baja")` en cada
  email → página pública `/baja`. (Fase 10 reutilizará ese helper.)
- **Scoring exprés** en `app/engine/scoring_expres.py` — **fuera de `modules/` y del DAG**,
  el caso dorado §19 no se toca. Puntúa 0–100 con datos brutos de captación; pesos T3
  en `defaults.yaml` (`scoring_expres`). Cumple P1 (determinista) y P4 (dato ausente ⇒ 0).
  Se guarda en `datos_brutos.score`; las alertas filtran por `score_min` y la UI lo
  etiqueta **«orientativa»**.
- Prerequisitos que no existían y se crearon aquí: modelos `Alerta`/`Notificacion`,
  router `captacion.py` (`POST/GET /subastas`), páginas `/alertas` y `/subastas`.
- Migraciones **Alembic 0003** (4 tablas del subsistema) y **0004** (amplía
  `auditoria.quien` a 120: con `String(36)` un email largo abortaba la transacción
  en PostgreSQL). **Ambas retiradas por la Fase 9.5**; su contenido está en el
  historial de git y el esquema resultante viaja en la fundacional `0005`, ya
  verificada contra PostgreSQL real (`quien VARCHAR(120)`, 19 columnas `jsonb`).
  La `0004` además **nunca pudo ejecutarse en SQLite**: usaba `op.alter_column`,
  que SQLite no implementa.
- **Suite: 118 recogidos — 113 pasan, 2 fallan, 3 se omiten** (medido 2026-07-28).
  Los 2 rojos son de PDF y **preexisten** a esta fase (falta la fuente DejaVu fuera
  de Docker — ver `docs/PENDIENTES.md`). Los 3 omitidos son T5 (exige
  `SEIS_TEST_POSTGRES_URL`) y los dos casos parametrizados de T3, que no tienen
  pares consecutivos que recorrer al existir una sola revisión.
  `npm run build` limpio.
- **Endurecimiento de arranque (cierre de revisión):** `app/core/config.py` valida
  en producción que `JWT_SECRET` y `ADMIN_PASSWORD` sean propios y fuertes
  (longitud, variedad, sin marcadores de plantilla) y **rechaza cualquier
  `SEIS_ENV` no reconocido** en vez de desactivarse en silencio. `.env.example`
  entrega los tres secretos —incluido `POSTGRES_PASSWORD`— **vacíos**, y
  `docker-compose.yml` los declara obligatorios (`${VAR:?...}`) sin ningún
  respaldo embebido. BD y Redis quedan publicadas solo en `127.0.0.1`.
- **Reparado de paso:** `docker-compose.yml` era YAML inválido desde el commit inicial
  (bloque duplicado tras `volumes:`); se eliminó el duplicado y se añadió `--beat` al
  worker, sin el cual el digest y el polling nunca se ejecutan. Creado `.env.example`.
  > **Derogado en parte por la Fase 11 (Bloque C′):** el `--beat` embebido se retiró y
  > el planificador es ahora el servicio **`beat`**, propio y único. Con el planificador
  > dentro del worker, escalar a N réplicas hacía que las N programaran el digest y cada
  > usuario recibiera N copias del mismo mensaje. La necesidad que motivó aquel `--beat`
  > sigue vigente: **sin planificador, el digest y el sondeo de Telegram no se ejecutan
  > jamás.** `beat` no debe escalarse nunca.

### ✅ Fase 10 — Alta self-service (COMPLETADA, 2026-07-29)
- **Registro público** `POST /auth/registro`: crea `Organizacion` propia + `Usuario`
  propietario **inactivo y sin verificar**. Responde **201 exista o no la cuenta**;
  si ya existe, no crea nada y avisa **por correo al titular** («alguien ha
  intentado registrarse»). La respuesta HTTP nunca revela si una dirección está
  registrada — mismo criterio que el 404-y-no-403 de §4.
- **Verificación** (`/verificar`, 24 h) y **recuperación** (`/recuperar` +
  `/resetear`, 1 h), ambas con **uso único real**: nueva tabla `TokenConsumido`
  (`jti` PK). Antes de esta fase `crear_token_proposito` emitía `jti` pero nadie lo
  comprobaba, así que un enlace servía tantas veces como cupiera en su TTL. El
  `jti` se reclama por **clave primaria** —no leyendo antes— y **antes** de aplicar
  el efecto, de modo que dos peticiones simultáneas no pueden pasar las dos.
- **`/reenviar-verificacion`**: sin él, un enlace caducado dejaba la cuenta muerta
  (no puede entrar por no estar verificada, ni verificarse porque el enlace expiró).
- **`/cambiar-password`** (autenticado). Aborda un hueco que el plan no registraba:
  **no existía ninguna ruta de código que modificara `hash_pwd` tras crear la
  cuenta**, así que una contraseña temporal asignada por el propietario era eterna.
  ⚠️ **Existe en la API y NO en la interfaz.** Ningún componente del frontend
  invoca `api.cambiarPassword`, no hay página de cuenta y el menú de navegación no
  tiene entrada para ella (verificado sobre `components/` y `construirNav`). Para
  el usuario el hueco **sigue abierto**: quien recibe una contraseña temporal en
  `/equipo` no puede cambiarla. El cambio de contraseña autenticado **no figura
  entre los seis pasos del §Fase 10 del Plan Maestro**, de modo que no es un
  entregable incumplido de esta fase, pero tampoco está resuelto. Falta asignarle
  fase — ver `docs/PENDIENTES.md`.
- **Login**: contraseña correcta pero email sin verificar ⇒ **403 accionable** con
  reenvío a mano. Cuenta desactivada por su propietario ⇒ sigue devolviendo **401
  genérico**, como fijó la Fase 9. Anti-fuerza-bruta de 5 fallos / 15 min ⇒ **429**;
  un acceso correcto y un reseteo limpian el contador.
- **`app/core/rate_limit.py`**: ventana deslizante en Redis con respaldo en memoria.
  Cubre login y recuperar por email, registro y reenvío por IP.
- **Frontend**: `/registro`, `/verificar`, `/recuperar`, `/resetear`, públicas y
  fuera del grupo `(app)/`. `/login` gana enlaces y el reenvío ante el 403.
- Migración **`0006_self_service`**. Verificada en SQLite (ciclo
  upgrade→downgrade→upgrade) y **en PostgreSQL 16 real**, incluido el backfill
  sobre los usuarios que ya existían.
- **Separación de audiencia entre tokens (cierre de la revisión de seguridad).**
  `crear_token` marca ahora `tipo="sesion"` y `decodificar_token` lo **exige**.
  Antes, como los tokens de propósito se firman con el mismo `jwt_secret`, un
  enlace de verificación o de reseteo enviado por correo valía además como Bearer
  de sesión completo — y seguía valiendo tras consumirse, porque `token_consumido`
  solo lo mira el camino de un solo uso. Defecto nacido en la Fase 12; la 10 lo
  cerró. **Al desplegar, los tokens ya emitidos dejan de servir.**
- **El limitador del login usa clave compuesta `email + origen`.** Con la clave
  solo por email, cualquiera bloqueaba la cuenta de un tercero de forma indefinida
  con cinco contraseñas erróneas. Su efecto pleno depende de la Fase 11 (ver abajo).
- **Suite: 162 recogidos — 159 pasan, 2 fallan, 1 se omite** (medido 2026-07-29).
  Los 2 rojos son los de PDF, preexistentes. El único omitido es T5.
  `npm run build` limpio.
- **Retirado `test_t3_revision_aislada_via_stamp`** (Fase 9.5): era insostenible por
  construcción —`create_all` produce siempre el esquema de HEAD, nunca el de la
  revisión predecesora, así que toda migración aditiva lo rompe— y nunca había
  llegado a ejecutarse por falta de pares en la cadena. Lo que cubría lo cubre
  `test_t3_par_consecutivo_por_la_cadena_natural`, que sí pasa con 0005→0006.

> **Backlog vivo:** el trabajo planificado y no implementado se registra en
> `docs/PENDIENTES.md`.

### ⏳ No construido (Fases 11-20 del Plan Maestro — ver §5)
Infraestructura de producción real, monetización con Stripe, cumplimiento RGPD, landing pública, endurecimiento de seguridad, escalado de captación (el conector BOE existe pero defensivo, sin ajuste empírico contra el portal real), analítica de negocio, beta cerrada.

### 🐛 Gotchas conocidos
- El motor (`app/engine/modules/` + `pipeline.py` + `contracts.py`) es la parte más validada del sistema — **NO tocar sin indicación expresa**; cualquier cambio ahí exige entender el "caso dorado §19" primero. (`app/engine/scoring_expres.py`, Fase 12, vive fuera del DAG y no le afecta.)
- El conector de ingesta BOE es "defensivo" (nunca rompe, pero no está ajustado contra el HTML real del portal) — trabajo pendiente de Fase 17. La ingesta manual (`POST /subastas`) existe desde la Fase 12.
- **2 tests rojos preexistentes**, ambos de PDF: sin la fuente DejaVu instalada (p. ej. Windows local, no en Docker) `pdf_service.py` lanza `FPDFUnicodeEncodingException`. Detalle y arreglo propuesto en `docs/PENDIENTES.md`.
- **Secretos: no hay valores por defecto utilizables.** `JWT_SECRET` y `ADMIN_PASSWORD` se entregan vacíos en `.env.example` y en los **entornos estrictos** el arranque **aborta** si están vacíos, son cortos, poco variados o contienen palabras de plantilla (`app/core/config.py`, `_validar_seguridad_entorno`). En desarrollo y tests la validación no se aplica.
- **`SEIS_ENV` admite cuatro valores: `development` · `test` · `staging` · `production`**, y cualquier otro **aborta el arranque** en vez de ignorarse (hallazgo P1-1). `staging` y `production` son los **entornos estrictos** (`ENTORNOS_ESTRICTOS`): exigen secretos propios y fuertes. Las erratas (`stagging`, `stage`, `prod`, `produccion`) **no** son entornos válidos, y es deliberado. La Fase 11 renombró `_validar_seguridad_produccion` → `_validar_seguridad_entorno` y `SecretoInseguroEnProduccionError` → `SecretoInseguroError`, porque al entrar `staging` los nombres antiguos dejaron de ser ciertos.

---

## 4 · Modelo de datos — entidades reales en `backend/app/models.py`

```
FuenteSubasta · Subasta · Activo · Carga · Comparable
Analisis (snapshot inmutable) · RiesgoEvaluado · Escenario · Decision · ReglaDisparada
Regla (versionada) · Parametro (versionado) · PerfilInversion
ResultadoReal · Usuario · Auditoria
Organizacion (Fase 9) · Alerta · Notificacion · PreferenciasNotificacion · CodigoTelegram (Fase 12)
TokenConsumido (Fase 10: `jti` gastado de un token de propósito, uso único)
```

**Reglas de negocio críticas (de la especificación, no negociables):**
- **P1 Determinismo:** mismo input + misma versión de reglas ⇒ mismo output. Cada `Analisis` es un snapshot inmutable (nunca se sobrescribe; reanalizar crea snapshot nuevo).
- **P4 La ausencia de datos penaliza:** ningún dato ausente se rellena con el valor optimista. Menos información ⇒ ICI baja ⇒ ICO baja ⇒ techo de semáforo.
- **P6 Vetos antes que promedios:** un defecto letal (carga no purgable, imposibilidad de inscripción, ocupación de renta antigua, financiación no preaprobada) **nunca** se compensa con buena ubicación u otras virtudes. Arquitectura lexicográfica: vetos → matriz de riesgos → scoring compensatorio (MCDA) → simulación de escenarios.
- **P_límite es un bloqueo duro de software**: el sistema nunca permite pujar por encima, sin excepción.
- Cuando exista multi-tenancy (Fase 9): `Analisis` y `ResultadoReal` son **privados por organización**; las subastas captadas y el conocimiento T2/T3 son **compartidos**; alertas/favoritos/notificaciones son **privados por usuario**. Acceder a un recurso ajeno por ID directo debe devolver **404, no 403** (no revelar existencia).

---

## 5 · Hoja de ruta — Fases 9 a 20 (Plan Maestro)

**Ruta crítica:** ~~9~~ → ~~**9.5**~~ → ~~10~~ → **11** → 13 → 20. Fase 14 (legal) en paralelo desde la 9. Fase 18 (WhatsApp) es condicional a demanda medida en Fase 12.

| Fase | Nombre | Bloquea a | Modelo recomendado |
|---|---|---|---|
| **9** | Multi-tenancy por organización | Todo lo demás | **Fable 5** (autorización transversal, coste de un fallo = fuga de datos) |
| **9.5** | **Saneamiento del sistema de migraciones** | **Fases 10 y 13** | Sonnet |
| ~~10~~ | Alta self-service + recuperación de cuenta | — | ✅ **Completada** (2026-07-29) |
| **11** | **Infraestructura de producción** | — | Fable 5 (decisiones operativas) |
| ~~12~~ | Notificaciones multicanal + scoring | — | ✅ **Completada** (2026-07-24) |
| 13 | Monetización (Stripe) | Beta real | Fable 5 (ciclo de vida de suscripción, idempotencia de webhooks) |
| 14 | RGPD / legal | — | Fable 5 (borradores) + Sonnet (implementación) |
| 15 | Landing + onboarding | — | Sonnet |
| 16 | Auditoría de seguridad | Antes de tráfico real | Fable 5 (auditoría) + Sonnet (correcciones) |
| 17 | Escalado de captación (BOE real) | — | Sonnet (con HTML real pegado) |
| 18 | WhatsApp (condicional) | — | Sonnet |
| 19 | Analítica y panel de negocio | — | Sonnet/Haiku |
| 20 | Beta cerrada y lanzamiento | Fin del proyecto | — |

**Fase 9.5 — Saneamiento del sistema de migraciones: bloques A-J ejecutados.** Se intercaló porque se demostró experimentalmente que `alembic upgrade head` fallaba sobre una base limpia (revisión 0002, `INSERT` que omitía `creado_en`) y que, como `docker-compose.yml` encadena las migraciones al arranque, **una instalación nueva no podía levantar el backend**. **Ese defecto está cerrado y medido**: `docker compose down -v && up -d --build` sobre volumen destruido deja el backend respondiendo `HTTP 200` en `/api/v1/health`, con `alembic_version = 0005` y 19 columnas `jsonb`. Plan canónico y evidencias bloque a bloque en `docs/FASE_95_PLAN_EJECUCION.md`; diseño de la estrategia en `docs/PLAN_REPARACION_MIGRACIONES.md`.

**Siguiente tarea: Fase 11 — Infraestructura de producción.**

> ⛔ **Puerta de despliegue heredada de la Fase 10.** Bajo `docker compose` la IP de origen **no se conserva**: se midió que todas las peticiones externas llegan con la de la pasarela (`172.18.0.1`). En consecuencia, los límites por origen de `/registro` y `/reenviar-verificacion` actúan como un **cupo global** y un solo atacante sin credenciales puede negar el alta pública a todo el sitio de forma sostenida. **Este `docker-compose.yml` no se expone a Internet** hasta que la Fase 11 aporte un proxy inverso con `uvicorn --proxy-headers` y `--forwarded-allow-ips` acotado a ese proxy. No bloquea la fusión del código; bloquea el despliegue.

Hereda además: purga de `token_consumido` y de las cuentas nunca verificadas, y reintento de Redis en el limitador. Todo anotado en `docs/PENDIENTES.md`.

**Renumeración de migraciones (decisión cerrada, deroga lo anterior):** la Fase 9.5 sustituye las revisiones 0001-0004 por una **revisión fundacional única numerada `0005`** con `down_revision = None`. En consecuencia, **la migración de la Fase 10 pasa a `0006`** y la de la Fase 13 a `0007`. Cualquier nota previa que reserve la `0005` para la Fase 10 está derogada.

**Fase 10 — Alta self-service: cerrada y fusionada a `main` (2026-07-30).** Tag `fase-10` sobre el commit `4f9c247`, ya fusionado. Ver el detalle completo en §3 y en `CHANGELOG.md`.

---

## 6 · Convenciones obligatorias

1. **Idioma: español** en código, comentarios, mensajes de error, UI y commits — sin excepción.
2. Toda la lógica de negocio vive en el **backend**; el frontend solo presenta (Next.js sin lógica de negocio).
3. Cada cambio de esquema = **nueva migración Alembic reversible** (`upgrade` + `downgrade` funcional). Nunca aceptar una migración sin `downgrade`.
4. Cada acción sensible escribe en la tabla `Auditoria` (quién, entidad, acción, delta).
5. Tests en `backend/tests/` con pytest. Fixtures existentes: `api` (TestClient con BD limpia por módulo y admin sembrado), `headers` (token admin). La suite actual **debe seguir verde**. Todo código nuevo lleva tests, **incluidos tests negativos** (permisos, aislamiento entre organizaciones, tokens caducados/reutilizados).
6. El frontend debe compilar limpio: `npm run build` sin errores de tipos.
7. **Protocolo de trabajo por fase:** una rama por fase (`fase-09-multitenant`, etc.) → plan de cambios primero, detenerse para aprobación → implementar → ejecutar `pytest` y `npm run build`, mostrar resultados → resumen de qué cambió y qué decisiones se tomaron → un PR por fase, revisado por el humano antes de fusionar.
8. **NO tocar `app/engine/` sin indicación expresa** — es el núcleo validado por el caso dorado §19.
9. **Prohibido `Base.metadata` dentro de `alembic/versions/`.** Ni `create_all`, ni `drop_all`, ni ninguna otra vía que derive la DDL de los modelos en tiempo de ejecución. Una revisión así no describe un cambio de esquema: reproduce el estado que los modelos tengan **el día que se ejecute**, de modo que dos instalaciones con la misma revisión acaban con esquemas distintos y el historial deja de ser reproducible. Cada revisión emite su DDL explícita (`op.create_table`, `op.add_column`, `op.create_index`…). Patrón de referencia: `0005_esquema_base`. *(La retirada `0001_esquema_inicial` incumplía esto —`Base.metadata.create_all` en su línea 18— y es la razón por la que la cadena antigua no era auditable.)*
10. **Toda DML de migración especifica explícitamente cada columna `NOT NULL`.** Los `default=` de SQLAlchemy son **de cliente**: los aplica Python al construir el objeto, no la base de datos, y por tanto **no existen** para un `INSERT`/`UPDATE` en SQL crudo. Omitir una columna `NOT NULL` sin `server_default` aborta la transacción entera. *(La retirada `0002_multitenancy` hacía `INSERT INTO organizacion (id, nombre)` en su línea 72 omitiendo `creado_en`; el resultado medido fue `IntegrityError: NOT NULL constraint failed: organizacion.creado_en`, y con él **`alembic upgrade head` dejó de funcionar sobre una base limpia**.)*
11. **`render_as_batch` es preventivo de `autogenerate`, jamás correctivo.** Hace que Alembic **escriba** bloques `op.batch_alter_table()` al *generar* una revisión; no cambia en nada lo que ocurre al *ejecutarla*. Medido sobre SQLite (SQLAlchemy 2.0.51 · Alembic 1.18.5): `alter_column` falla con `OperationalError: near "ALTER": syntax error` **tanto con `render_as_batch=True` como sin él**, y `batch_alter_table` funciona **también sin él**. Quien necesite alterar una columna en SQLite debe escribir `op.batch_alter_table()`; activar la opción no le salvará. No documentarlo nunca como arreglo de un `alter_column` que ya falla.

---

## 7 · Cómo levantar y probar (resumen — detalle completo en `MANUAL_DE_PRUEBAS.md`)

```bash
cd /workspace/seis
cp .env.example .env
# OBLIGATORIO: rellenar JWT_SECRET y ADMIN_PASSWORD (vienen vacíos a propósito).
#   JWT_SECRET=$(openssl rand -base64 48)  ·  ADMIN_PASSWORD=$(openssl rand -base64 18)
docker compose up -d --build
# Web:     http://localhost:3000  (admin@seis.local + tu ADMIN_PASSWORD)
# API:     http://localhost:8000/docs
# Health:  http://localhost:8000/api/v1/health
```

```bash
# Suite de tests del motor
cd backend && pip install -r requirements-dev.txt && python -m pytest -q

# Frontend
cd frontend && npm run build
```

Caso de prueba de referencia: **§19 de la especificación**, guion completo con datos exactos en `MANUAL_DE_PRUEBAS.md` §6, resultado esperado en `SEIS_informe_ejemplo_caso19.md`.

---

## 8 · Documentos de referencia (uploads de sesión — considerar mover a `docs/`)

- `SEIS_Especificacion_Funcional_y_Tecnica.md` — **SSOT funcional y técnico** (21 secciones: filosofía P1-P10, arquitectura hexagonal + DAG + blackboard, modelo de datos completo, M01-M14 detallados, algoritmo de precios §9, perfiles de inversión §10, glosario).
- `SEIS_Plan_Maestro_Fases_920.md` — hoja de ruta comercial Fases 9-20, con prompts de ejecución listos para pegar en Claude Code por fase.
- `MANUAL_DE_PRUEBAS.md` — cómo levantar y probar (local, VPS, PaaS, cURL, troubleshooting).
- `SEIS_informe_ejemplo_caso19.md` — salida de referencia para verificar que el motor no ha regresionado.
- `CHANGELOG.md` (raíz) — registro de cambios **por fase**, no por SemVer. Una entrada por fase cerrada, con lo añadido, lo corregido, las migraciones y los cambios incompatibles. Arranca en la Fase 9; lo anterior está en el historial de git.

> **Dónde vive la hoja de ruta.** No existe `ROADMAP.md` y es deliberado: la hoja de ruta contractual es `docs/SEIS_Plan_Maestro_Fases_920.md` y su estado de ejecución es el §5 de este documento. Un tercer fichero con la misma tabla se desincronizaría — ya ocurrió en la Fase 12 con las cifras de la suite (ver `docs/PENDIENTES.md`, P2).

---

## 9 · Notas para la próxima sesión

**TL;DR:** El motor experto (M01-M14), el producto de un solo tenant, multi-tenancy (Fase 9), el saneamiento de migraciones (Fase 9.5), notificaciones multicanal (Fase 12) y el alta self-service (Fase 10) están completos, probados y fusionados a `main`. Lo que falta es todo lo que convierte esto en negocio a partir de aquí: infraestructura real (Fase 11, **siguiente paso**), monetización, legal y salida a mercado. Seguir el Plan Maestro fase a fase, con plan-antes-de-código como regla no negociable.
