# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

Este proyecto **no versiona por SemVer**: versiona por **fases del Plan Maestro**
(`docs/SEIS_Plan_Maestro_Fases_920.md`). Cada entrada corresponde a una fase
cerrada, con la fecha en que se dio por terminada.

Las fases 1-8 construyeron el motor experto y el producto de un solo tenant.
Este registro arranca en la Fase 9, que es cuando el proyecto empieza a
convertirse en un SaaS. Lo anterior está en el historial de git.

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
