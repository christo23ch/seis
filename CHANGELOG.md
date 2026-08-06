# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

Este proyecto **no versiona por SemVer**: versiona por **fases del Plan Maestro**
(`docs/SEIS_Plan_Maestro_Fases_920.md`). Cada entrada corresponde a una fase
cerrada, con la fecha en que se dio por terminada, salvo entradas de
infraestructura transversal (como la de Obsidian) que no pertenecen a ninguna
fase concreta.

Las fases 1-8 construyeron el motor experto y el producto de un solo tenant.
Este registro arranca en la Fase 9, que es cuando el proyecto empieza a
convertirse en un SaaS. Lo anterior está en el historial de git.

---

## [Fase 11-A] — Infraestructura de producción, parte agnóstica del proveedor — 2026-08-05

La Fase 11 se parte en dos por decisión del responsable: **11-A** es de repositorio
y no depende del proveedor; **11-B** (IaC, jobs de despliegue, RUNBOOK) queda
bloqueada hasta elegir hosting, dominio y proveedor de correo.

> **La Fase 11 NO se cierra con esta entrada.** Sus criterios de salida son
> operativos —HTTPS sirviendo, staging desplegado, backup restaurado con tiempo
> medido, alarma recibida, email de verificación llegado a una bandeja real— y
> ninguno es alcanzable sin la 11-B y sin ejecución humana.

### Añadido

- **Salud por componente** (Bloque A): `GET /health` intacto como liveness,
  `/health/listo` como readiness pública que responde 503, y `/health/detalle`
  autenticado con revisión de Alembic, versiones T2/T3, latencias y diagnóstico
  de red. Tres audiencias con necesidades opuestas, no una.
- **`staging` como cuarto entorno, y estricto** (Bloque D): entra en
  `ENTORNOS_SOPORTADOS` **y** en `ENTORNOS_ESTRICTOS`.
- **Higiene de despliegue portable** (Bloque C′): `backend/.dockerignore`,
  ancla YAML de entorno compartida, servicio `beat` propio, `healthcheck` del
  backend, puertos con loopback por defecto y `.env.produccion.example`.
- **Mantenimiento periódico** (Bloque I): tarea `seis.purgar` con horario
  `crontab`, purga de `token_consumido` y purga de cuentas nunca verificadas
  **con el borrado desactivado de fábrica**.
- **IP real tras proxy** (Bloque H): `app/core/red.py`, tres variables de
  política, guardia de arranque y `--no-proxy-headers` explícito.
- **CI con la suite completa** (Bloque F′): `.github/workflows/ci.yml` con el
  backend entero y `npm run build`.

### Corregido

- **`create_all` fuera de la ruta de producción** (Bloque E). El antipatrón que
  `CLAUDE.md` §6.9 prohíbe en `alembic/versions/` vivía en el arranque, y el
  compose lo encadenaba **después** de `alembic upgrade head`: un modelo con una
  tabla que ninguna migración creara se creaba en silencio en producción.
- **Puerta de despliegue de la Fase 10**: el límite por origen dejaba de ser un
  cupo global para todo el sitio.
- **P1 de la Fase 12**: las siete variables de SES/SMTP no llegaban al
  contenedor y el correo fallaba en silencio. La causa raíz eran dos bloques
  `environment` duplicados que derivaron, no un olvido.
- **El limitador anti-abuso no reintentaba Redis** tras el primer fallo, ni
  soltaba un cliente muerto, ni conservaba los bloqueos vigentes al recuperarse.
- **`.gitignore` no protegía `.env.produccion`**, que es el nombre que la
  plantilla nueva invita a crear.
- **`smtp.starttls()` sin contexto TLS** usaba `CERT_NONE`. Rama inalcanzable
  bajo Docker hasta que este mismo trabajo la activó al propagar las credenciales.
- **`VERSION_REGLAS` y `VERSION_PARAMETROS` no llegaban a ningún contenedor**,
  de modo que ajustarlas en `.env` no tenía efecto (principio P1).
- **El informe PDF reventaba sin la fuente DejaVu** *(corregido con autorización
  expresa; queda fuera del alcance original de la fase)*. Una viñeta `•` se
  concatenaba **fuera** del saneador, y Helvetica —el respaldo— solo admite
  latin-1, así que `fpdf2` lanzaba `FPDFUnicodeEncodingException` y **el informe
  entero se perdía** en cualquier máquina sin la fuente: todo Windows de
  desarrollo y cualquier imagen que no sea `backend/Dockerfile`. El backlog
  llevaba dos fases diagnosticándolo mal («tabla de transliteración incompleta»).
  Se corrigió la causa raíz y se añadió una tabla de equivalencias tipográficas
  para que el respaldo produzca texto legible en vez de «?».
  **Con esto la suite queda en 0 fallos por primera vez desde que hay registro.**

### Desviaciones del plan, registradas

- La siembra **sigue corriendo en todos los entornos**, en contra de lo que el
  plan proponía: es idempotente, y sacarla del arranque haría que
  `docker compose up` no baste para tener un sistema en pie — el defecto que
  originó la Fase 9.5.
- Se tocó **la publicación de puertos**, que el plan difería a la Fase 16: la
  premisa del diferimiento caducó cuando este trabajo convirtió el compose en
  base de un despliegue portable.
- **`--no-proxy-headers`** en lugar del `--proxy-headers` con `--forwarded-allow-ips`
  que pedían el plan y el backlog de la Fase 10. Razonado en `ADR-0005`.
- **La corrección de `pdf_service.py`**, fuera del alcance original y autorizada
  expresamente por el responsable.

### Deuda que queda abierta

- **Sentry queda fuera de la fase** por decisión del responsable. Incumple
  deliberadamente el requisito 2 del prompt del Plan Maestro y **no tiene fase
  propietaria**. Mientras siga así, **un error 500 en producción no avisa a nadie**.
- **La purga de cuentas nace desactivada**: la deuda no está cerrada en
  producción hasta que alguien mire un informe real y active el modo `borrar`.
- **El arranque en frío desde volumen destruido no se ha verificado** (ver Evidencia).
- **Seis requisitos que bloquean el despliegue**, inventariados en `docs/PENDIENTES.md`
  con propietario Fase 11-B: `/docs` y `/openapi.json` abiertos · `/health/listo` sin
  límite de tasa y revelando el estado por componente · dependencias sin fijar ni
  auditar bajo una CI que ahora es puerta de despliegue · la purga en modo informe no
  deja rastro cuando no hay candidatas.
- Toda la **Fase 11-B**.

### ⚠️ Cambio incompatible al actualizar una instalación existente

**Un `.env` anterior a esta fase impide arrancar toda la pila.** Medido sobre una
instalación real: `SEIS_ENV` sin declarar vale `production` por el defecto del compose,
que es entorno estricto, y ahí la guardia del Bloque H **aborta** si
`PROXIES_DE_CONFIANZA` no está. No solo el backend: `worker` y `beat` también, porque
`celery_app` valida al importarse.

El mensaje es accionable y la guardia está haciendo su trabajo —forzar una decisión que,
tomada mal en silencio, deja el límite por origen como cupo global para todo el sitio—,
pero exige **una línea nueva** en cada `.env` existente:

```
PROXIES_DE_CONFIANZA=ninguno        # si no hay proxy delante
PROXIES_DE_CONFIANZA=10.0.0.5/32    # o la IP/CIDR de su proxy, con CABECERA_IP_CLIENTE
```

### Evidencia

Cifras **medidas** al cerrar, no citadas:

```
suite      365 recogidos · 363 pasan · 0 fallan · 2 omitidos
build      npm run build → exit 0
compose    docker compose config → exit 0, 6 servicios
```

Las 2 omisiones son condicionales y no son fallos: T5 exige `SEIS_TEST_POSTGRES_URL`, y
el test de la rama con la fuente DejaVu se omite si no está instalada — **en CI esa
omisión es un fallo deliberado**, para que un `apt-get` roto no deje de probar esa rama
en silencio.

**Verificación de arranque en frío: EJECUTADA y satisfactoria**, sobre volumen
destruido (`docker compose down -v && up -d --build`):

```
servicios          6/6 arriba; backend healthy
/health            200  {"status":"ok"}
/health/listo      200  {"estado":"ok","componentes":{"bd":"ok","redis":"ok"}}
/health/detalle    401 sin token
alembic_version    0006 · 26 tablas
create_all         NO ejecutado: «entorno production: el esquema lo gobierna Alembic»
siembra            1 usuario · 7 fuentes · 6 perfiles · 17 reglas
idempotencia       tras reiniciar el backend: cifras idénticas, 26 tablas
login del admin    200 con la contraseña sembrada, sin intervención manual
frontend           200
imagen             824 K, sin `.env`, sin `*.db`, sin `.venv`
```

Los 824 K contrastan con los **147 MB** de contexto de build que se medían antes del
`.dockerignore`, y son la prueba directa de la tesis del Bloque C′.

### Sin cambios de esquema

Ninguna migración Alembic. La siguiente libre sigue siendo la **`0007`** (Fase 13).

---

## [Infraestructura de conocimiento] — Obsidian como Vault del proyecto — 2026-07-30

Implantación de Obsidian sobre el propio repositorio como memoria permanente del proyecto. **No es una fase del Plan Maestro**; es infraestructura transversal de documentación.

### Añadido
- 20 carpetas numeradas en la raíz del repo (`00-Inbox` … `999-Meta`), el propio repositorio actúa como Vault — cero duplicación con `docs/`, `CLAUDE.md` ni `PENDIENTES.md`.
- 10 plugins de comunidad instalados desde release oficial de GitHub: Templater, Dataview, QuickAdd, Tasks, Obsidian Git, Metadata Menu, Tag Wrangler, Advanced Tables, Linter, Calendar.
- Daily Notes (núcleo) configurado con plantilla propia en `02-Diario/`.
- 15 plantillas Templater (ADR, RFC, Bug, Incidente, Postmortem, Runbook, Reunión, Investigación, Feature, Tarea, Checklist, Fase, Release, Auditoría, Diaria).
- 14 comandos QuickAdd para creación asistida de cada tipo de nota.
- Dashboard `01-Home/Home.md` con 10 consultas Dataview.
- Configuración de Graph View con filtros permanentes y agrupación por color según tipo de nota.
- Primer Canvas real: mapa de dependencias de las Fases 11-20 del Plan Maestro.
- Primer contenido real (no de ejemplo): 2 ADR, 2 notas de auditoría, 1 Runbook, 1 documento técnico, la nota de la Fase 10 y su deuda de backlog, todos enlazados entre sí.

### Corregido
- **Incompatibilidad de versión en Templater y QuickAdd.** Las últimas releases de GitHub de ambos plugins declaran `minAppVersion: 1.13.0`, que es la rama Beta/Insider de Obsidian, no la estable (confirmado contra el catálogo oficial `desktop-releases.json`: `latestVersion` estable es `1.12.7`). Se bajó a la última versión de cada plugin compatible con la rama estable: Templater `2.20.6` (`minAppVersion: 1.12.2`) y QuickAdd `2.12.3` (`minAppVersion: 1.11.4`).
- **Integración Daily Notes ↔ Templater.** El plugin nativo "Daily Notes" no invoca a Templater: copia el texto de la plantilla sin procesar la sintaxis `undefined`. Se resolvió activando la función "folder templates" de Templater (`enable_folder_templates` + `folder_templates: [{folder: "02-Diario", template: "..."}]`), que sí dispara el motor de Templater al crear un fichero en esa carpeta.
- **Cuatro notas con `tipo:` sin su tag `#tipo/x` correspondiente**, detectadas por auditoría estática (enlaces rotos, YAML, consistencia tag↔tipo, convención de nombres): `Home.md`, las tres notas-puente de `10-Proyecto/`, y `Arquitectura-de-tokens-jwt.md`.

### Estado de implantación
- Verificado en ejecución real (no solo por fichero): Dataview renderiza tablas, Templater procesa plantillas y dispara por carpeta en Daily Notes, Tasks reconoce casillas, QuickAdd registra sus 14 comandos, Calendar muestra panel y crea notas diarias, Canvas renderiza el mapa de fases sin nodos rotos.
- Auditoría estática posterior: 0 enlaces rotos, 0 YAML inválido, 100% de convención de nombres cumplida, 0 notas huérfanas reales tras la corrección de enlaces.
- Detalle completo en `999-Meta/Estado-de-Implantacion.md`.

### Pendiente
- Poblar `20-Arquitectura`, `50-Releases`, `110-Legal`, `120-Reuniones`, `140-Documentacion-Funcional` — vacías por ausencia legítima de material, no por omisión.

---

## [Fase 10] — Alta self-service — 2026-07-29

Registro público, verificación de correo y recuperación de cuenta. Objetivo
contratado: *«que cualquier persona pueda registrarse sola, verificar su email y
recuperar su contraseña, sin intervención tuya»*.

### Añadido
- `POST /auth/registro`: crea una organización propia y su usuario propietario,
  inactivo y sin verificar. Responde **201 exista o no la cuenta**; si ya existe,
  no crea nada y avisa por correo al titular.
- `POST /auth/verificar`: activa la cuenta. Un solo uso, caducidad 24 h.
- `POST /auth/reenviar-verificacion`: reenvía el correo de activación. Sin él, un
  enlace caducado dejaba la cuenta sin salida.
- `POST /auth/recuperar`: solicita el restablecimiento. Responde 200 siempre.
- `POST /auth/resetear`: fija una contraseña nueva. Un solo uso, caducidad 1 h.
- `POST /auth/cambiar-password`: cambio de contraseña con sesión iniciada.
  **Disponible en la API; sin interfaz de usuario en esta fase.**
- Páginas públicas `/registro`, `/verificar`, `/recuperar` y `/resetear`, fuera
  del grupo `(app)/` y por tanto fuera del guardia de sesión.
- `app/core/rate_limit.py`: limitador de ventana deslizante sobre Redis con
  respaldo en memoria. Cubre login y recuperación por email; registro y reenvío
  por origen; reenvío también por destinatario.
- Tabla `token_consumido`: registro de `jti` gastados que impone el uso único
  real de los tokens de propósito.
- Columna `usuario.email_verificado`.
- Variables de entorno `LOGIN_MAX_INTENTOS` (5) y `LOGIN_VENTANA_MIN` (15),
  propagadas en `docker-compose.yml`.
- `tests/test_registro.py`: 42 funciones de test, 45 casos con parametrización.

### Cambiado
- El login devuelve **403 accionable** cuando la contraseña es correcta pero el
  correo no está verificado, con reenvío de la verificación a mano. Una cuenta
  desactivada por su propietario sigue devolviendo el **401 genérico** que fijó
  la Fase 9.
- `crear_usuario` acepta `activo` y `email_verificado`, ambos `True` por defecto:
  las altas administrativas son confiadas y no reciben correo de verificación.
  Solo el registro público pasa `False`.
- Los correos transaccionales viajan **sin enlace de baja**: nadie debe poder
  darse de baja del mensaje que le permite activar su cuenta.
- `obtener_por_email` recorta espacios además de pasar a minúsculas.

### Corregido
- **Confusión de audiencia entre tokens.** Un enlace de verificación o de reseteo
  enviado por correo valía como Bearer de sesión completo, heredando el rol real
  de la cuenta, y seguía valiendo **después de consumirse**. Defecto nacido en la
  Fase 12. Ver la sección de cambios incompatibles.
- **Denegación de servicio dirigida en el login.** Con la clave del limitador
  solo por email, cualquiera bloqueaba la cuenta de un tercero de forma
  indefinida con cinco contraseñas erróneas, sin que la cuenta tuviera siquiera
  que existir. La clave pasa a componerse de **email y origen**.
- **Condición de carrera en el alta duplicada.** Dos registros simultáneos del
  mismo email producían un 500 y dejaban una organización huérfana.
- `/verificar` consumía el token al cargar la página, de modo que los escáneres
  corporativos de enlaces lo gastaban antes que su destinatario. Ahora exige un
  clic explícito.
- `admin@seis.local` no podía usar `/recuperar`: `EmailStr` rechaza `.local` por
  ser un dominio de uso especial (RFC 6762) y devolvía un 422 que rompía la
  promesa de «200 siempre».

### Retirado
- `test_t3_revision_aislada_via_stamp`, barrera de la Fase 9.5. Era insostenible
  por construcción: `Base.metadata.create_all` produce siempre el esquema de
  HEAD, nunca el de la revisión predecesora, de modo que toda migración aditiva
  lo rompía. Nunca había llegado a ejecutarse. Lo que cubría lo cubre
  `test_t3_par_consecutivo_por_la_cadena_natural`.

### Migraciones
- **`0006_self_service`** (`down_revision = "0005"`). Añade
  `usuario.email_verificado` con `server_default`, aplica un backfill que da por
  verificados a los usuarios preexistentes, y crea `token_consumido`.
  Reversible; verificada en SQLite y en PostgreSQL 16.4 real.

### ⚠️ Cambios incompatibles
- **Los tokens de sesión emitidos antes de esta fase dejan de ser válidos.**
  `crear_token` marca `tipo="sesion"` y `decodificar_token` lo exige como lista
  blanca. Al desplegar se produce un **cierre de sesión único** para todos los
  usuarios conectados. No hay pérdida de datos ni migración de credenciales.

### Pendiente
- OAuth con Google: paso 6 del contrato, clasificado como **opcional y
  diferible** por el propio Plan Maestro.
- Interfaz para `/auth/cambiar-password`.

### Evidencia
- Suite: **162 recogidos · 159 pasan · 2 fallan · 1 omitido**. Los 2 rojos son de
  PDF y preexisten a la fase.
- Cobertura de los módulos de la fase: **90 %** con la suite completa.
- Deriva de esquema (T4): sin divergencia — 22 tablas, 175 columnas, 22 índices.
- `npm run build` limpio, 21 rutas.

---

## [Fase 9.5] — Saneamiento del sistema de migraciones — 2026-07-28

Fase intercalada, no prevista en el Plan Maestro. Se demostró experimentalmente
que `alembic upgrade head` fallaba sobre una base limpia y que, como
`docker-compose.yml` encadena las migraciones al arranque, **una instalación
nueva no podía levantar el backend**.

### Cambiado
- Las revisiones `0001`-`0004` se sustituyen por una **revisión fundacional
  única, `0005_esquema_base`**, con `down_revision = None`. Su contenido
  permanece en el historial de git.

### Corregido
- La revisión `0002` hacía un `INSERT` que omitía `creado_en`, columna
  `NOT NULL`. Era la causa medida del fallo de arranque.
- La revisión `0004` usaba `op.alter_column`, que SQLite no implementa: **nunca
  pudo ejecutarse en SQLite**.

### Añadido
- Batería T1-T6 en `tests/test_migraciones.py`, que ejerce Alembic de verdad.
- Barrera anti-recurrencia en CI: `.github/workflows/migraciones.yml`.
- Endurecimiento del arranque: `app/core/config.py` valida en producción que
  `JWT_SECRET` y `ADMIN_PASSWORD` sean propios y fuertes, y rechaza cualquier
  `SEIS_ENV` no reconocido.

---

## [Fase 12] — Notificaciones multicanal y scoring exprés — 2026-07-24

### Añadido
- `app/notificadores/`: interfaz común con implementaciones de email
  (Postmark/SES/SMTP) y Telegram. Sin credenciales no rompe: registra en log y
  bufferiza.
- Telegram por polling, no webhook: el webhook exige URL pública HTTPS, que es
  Fase 11.
- Preferencias por usuario: canales, modo instantáneo o digest, hora y franja de
  silencio. Tarea beat `seis.digest`.
- Baja sin login mediante enlace firmado, con página pública `/baja`.
- `app/engine/scoring_expres.py`, **fuera de `modules/` y del DAG**: el caso
  dorado §19 queda intacto.
- Modelos `Alerta`, `Notificacion`, `PreferenciasNotificacion`,
  `CodigoTelegram`; router `captacion.py`; páginas `/alertas` y `/subastas`.

### Corregido
- `docker-compose.yml` era **YAML inválido** desde el commit inicial: contenía un
  bloque duplicado tras `volumes:`. `docker compose up` nunca pudo funcionar pese
  a estar documentado como vía principal de arranque.
- El worker no llevaba `--beat`, sin el cual el digest y el polling nunca se
  ejecutan.

---

## [Fase 9] — Multi-tenancy por organización — 2026-07-14

### Añadido
- Entidad `Organizacion`. `Usuario` gana `organizacion_id`, `rol_org` y
  `es_superadmin`; `Analisis` gana `organizacion_id`.
- Modelo de roles en dos ejes: `rol` (capacidad dentro de la organización) y
  `rol_org` (gestión de miembros), más `es_superadmin` para el gobierno del
  conocimiento global.
- Router `organizacion.py` y página `/equipo`.

### Cambiado
- Aislamiento por `organizacion_id` en todos los endpoints de análisis. **El
  acceso a un recurso ajeno devuelve 404, no 403**: no se revela su existencia.
