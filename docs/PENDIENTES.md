# SEIS — Lista de pendientes (backlog)

Registro vivo del trabajo planificado y aún no implementado. Cada fase se ejecuta
con el protocolo del proyecto: **plan → aprobación → implementación → tests verdes
+ `npm run build` limpio → PR**. Detalle metodológico en `docs/SEIS_Plan_Maestro_Fases_920.md`.

**Estado del recorrido:** Fase 9 (multi-tenancy) ✅ y Fase 12 (notificaciones +
scoring) ✅ completadas. Siguiente: Fase 10 (alta self-service), que reutiliza
`crear_token_proposito` y el patrón de email honesto ya introducidos por la 12.

---

## 🔜 Fase 10 — Alta self-service (PLANIFICADA, pendiente de implementar)

Registro público, verificación de email y recuperación de contraseña.
Plan aprobado en su estructura; **pendiente de arrancar la implementación.**

### Punto a confirmar antes de codificar
- ~~**`email_service.py` como abstracción honesta sin proveedor real**~~ →
  **RESUELTO por la Fase 12**: ya existe `app/notificadores/` con esa misma
  abstracción (interfaz común, Postmark/SES/SMTP y buffer `ultimo_email` sin
  credenciales). La Fase 10 debe **reutilizarlo**, no crear un `email_service.py`
  paralelo; las referencias de más abajo a ese fichero quedan obsoletas.
- `crear_token_proposito` / `decodificar_token_proposito` **ya existen** en
  `app/core/security.py` (los introdujo la Fase 12 para el enlace de baja).
  Falta solo la tabla `TokenConsumido` para el uso único por `jti`.

### Reconciliación con la realidad del repo (el prompt asumía otro estado)
- Migración nueva = **0005**. (Esta nota decía "0003" cuando solo existían 0001 y 0002; la Fase 12 consumió 0003 y 0004, así que la siguiente libre es la 0005.)
- `email_service.py` **no existe** → se crea.
- Rate-limiting: Redis **con fallback a memoria** en tests.

### Cambios previstos, fichero a fichero

**Backend — modelos y migración**
- `app/models.py`: `Usuario` += `email_verificado: bool` (default False). Nueva tabla
  `TokenConsumido(jti PK, proposito, consumido_en)` (uso único de tokens).
- `alembic/versions/0005_self_service.py` (idempotente + reversible): add column
  `usuario.email_verificado` (backfill: usuarios existentes → `True`); create table
  `token_consumido`. `downgrade` elimina ambos.

**Backend — seguridad, email y rate-limit**
- `app/core/security.py`: `crear_token_proposito(sub, proposito, horas)` (con `jti`,
  `proposito`, `exp`) y `decodificar_token_proposito(token, proposito)`.
- `app/services/email_service.py` (nuevo): `enviar_email(...)` honesto + helpers
  `enviar_verificacion` / `enviar_reseteo` (enlace `{FRONTEND_URL}/verificar?token=…`);
  buffer de último email para tests.
- `app/core/rate_limit.py` (nuevo): `registrar_fallo`, `bloqueado`, `limpiar`,
  `limpiar_todo`. Redis con fallback a memoria; ventana 15 min / máx 5 (configurable).
- `app/core/config.py`: += `frontend_url`, `email_from`, `login_max_intentos=5`,
  `login_ventana_min=15`.

**Backend — servicios y endpoints**
- `app/services/usuario_service.py`: `registrar_usuario(...)` (crea Organizacion propia
  + Usuario propietario inactivo: `activo=False`, `email_verificado=False`, `rol="admin"`,
  `rol_org="propietario"`, `es_superadmin=False`); `verificar_email(...)`;
  `resetear_password(...)`; `jti_consumido(...)` / `marcar_jti(...)`. Todo con `Auditoria`.
- `app/api/auth.py` (endpoints nuevos, públicos):
  - `POST /auth/registro` {email, password≥8, nombre} → 201, envía verificación.
  - `POST /auth/verificar` {token} → activa cuenta (propósito "verificar", 24 h, un solo uso).
  - `POST /auth/recuperar` {email} → **respuesta idéntica exista o no** el email; si existe, envía reseteo (1 h).
  - `POST /auth/resetear` {token, nueva≥8} → cambia contraseña (propósito "resetear", un solo uso).
  - `POST /auth/login` → envuelto en anti-fuerza-bruta: ≥5 fallos/email/15 min ⇒ **429** en español; éxito limpia el contador.
  - Validación `≥8` con Pydantic (`Field(min_length=8)`).

**Frontend (páginas públicas, hermanas de `/login`)**
- `app/registro/page.tsx`, `app/verificar/page.tsx` (lee `?token=`),
  `app/recuperar/page.tsx`, `app/resetear/page.tsx` (lee `?token=`). Botones
  deshabilitados durante el envío; textos en español.
- `app/login/page.tsx`: enlaces a `/registro` y `/recuperar`.
- `lib/api.ts`: `registro`, `verificar`, `recuperar`, `resetear`.

**Tests**
- `tests/conftest.py`: fixture autouse `rate_limit.limpiar_todo()` por test.
- `tests/test_registro.py`: registro feliz (usuario inactivo, email capturado);
  email duplicado → 400; verificar OK → login funciona; token caducado → 400;
  token reutilizado (jti) → 400; token con propósito equivocado → 400; recuperar
  idéntico exista/no exista el email; resetear feliz; login brute-force
  (5 fallos → 6º = 429) y desbloqueo temporal (envejeciendo timestamps vía hook de reloj).

**No se toca:** `app/engine/**` ni la gobernanza salvo lo listado.

---

## ⏳ Fases 11-20 — no iniciadas

Resumen (detalle y prompts de ejecución en `docs/SEIS_Plan_Maestro_Fases_920.md`):

| Fase | Nombre | Notas |
|---|---|---|
| 11 | Infraestructura de producción | render.yaml, health por componente, Sentry, runbook |
| ~~12~~ | ~~Notificaciones multicanal + scoring~~ | ✅ **Completada** — ver sección propia más abajo |
| 13 | Monetización (Stripe) | planes/límites, webhooks idempotentes |
| 14 | Cumplimiento legal y RGPD | consentimientos, ARCO, textos legales (revisión de abogado) |
| 15 | Landing pública, onboarding y ayuda | — |
| 16 | Endurecimiento de seguridad | OWASP, rate-limit global, cabeceras |
| 17 | Escalado de la captación (BOE real) | ajuste del conector contra el portal real |
| 18 | Canal WhatsApp (condicional) | solo si Fase 12 demuestra demanda |
| 19 | Analítica y panel de negocio | Plausible/PostHog, embudo, MRR |
| 20 | Beta cerrada y lanzamiento | QA guionizado, carga, go-live |

### Deuda técnica menor detectada
- ~~No existe `.env.example` en la raíz del repo~~ → **creado en la Fase 12** con
  todas las variables reales, incluidas las de notificaciones.
- Endpoints citados en prompts que aún no existen y que deberán heredar el scoping
  por `organizacion_id` cuando se creen: `export.csv`, `geo`, `resultado-real`, `/calibracion`.

### 🐛 Deuda técnica detectada durante la Fase 12 (NO corregida — decisión pendiente)
- **`pdf_service.py` rompe sin la fuente DejaVu.** `tests/test_pdf_async.py::test_informe_pdf`
  y `test_multitenant.py::…[/informe.pdf]` fallan con `FPDFUnicodeEncodingException`
  cuando `DejaVuSans.ttf` no está instalada (p. ej. Windows local). El fallback a
  *helvetica* llama a `_limpiar(texto, unicode_ok=False)`, que no translitera todos
  los caracteres del informe. En Docker no se manifiesta porque la imagen incluye
  `fonts-dejavu-core`. **Preexistente a la Fase 12** (verificado sobre árbol limpio).
  Arreglo propuesto: completar la tabla de transliteración de `_limpiar`. Toca
  `pdf_service.py`, fuera del alcance de la 12 → requiere aprobación.

---

## ✅ Fase 12 — Notificaciones multicanal y scoring exprés (COMPLETADA)

**Decisiones tomadas (aprobadas antes de codificar):**
1. **Telegram por polling** (tarea Celery `seis.telegram_polling`, cada 30 s) en lugar
   de webhook: no exige URL pública HTTPS, que es Fase 11. El procesado del mensaje
   vive en `procesar_update(db, update)`, así que migrar a webhook es llamar a esa
   función desde el endpoint.
2. **Email honesto sin credenciales**: `EMAIL_PROVIDER=postmark|ses|smtp`; vacío ⇒
   log + buffer `ultimo_email` (los tests lo inspeccionan). Nunca lanza.
3. **Scoring fuera del DAG**: `app/engine/scoring_expres.py`, hermano de `pipeline.py`,
   NO en `modules/`. El caso dorado §19 queda intacto.
4. **Prerequisitos mínimos creados aquí** (no existían): modelos `Alerta`/`Notificacion`,
   router `captacion.py`, páginas `/alertas` y `/subastas`.

**Entregado:** migraciones `0003` (4 tablas) y `0004` (amplía `auditoria.quien` a 120), ambas con upgrade/downgrade verificados en SQLite —**no contra PostgreSQL**—;
`app/notificadores/` (base + email + telegram + registro); `notificaciones_service.py`;
routers `notificaciones.py` (+ `/alertas`) y `captacion.py`; tareas `seis.digest`
(beat horario) y `seis.telegram_polling`; parámetros T3 `scoring_expres` editables;
páginas `/alertas` (Alertas + Preferencias), `/subastas` y `/baja` (pública);
`test_notificaciones.py` (18 tests).

**Reparado de paso (bloqueaba la fase):** `docker-compose.yml` era **YAML inválido**
desde el commit de importación inicial — a partir de `volumes:` contenía una copia
antigua duplicada de db/redis/backend/worker. `docker compose up` nunca pudo funcionar
pese a estar documentado como vía principal de arranque. Se eliminó el duplicado y se
añadió `--beat` al worker (sin él, digest y polling nunca se ejecutan).

### P1 detectados en Fase 12 (Release Committee)

- **Proveedores SES y SMTP no funcionales vía `docker compose up`.** `docker-compose.yml`
  propaga `POSTMARK_TOKEN` pero **no propaga** `SES_REGION`, `SES_ACCESS_KEY`, 
  `SES_SECRET_KEY`, `SMTP_HOST`, `SMTP_PUERTO`, `SMTP_USUARIO`, `SMTP_PASSWORD`. 
  Con `EMAIL_PROVIDER=ses` o `smtp` dentro del contenedor, las credenciales llegan 
  vacías y `NotificadorEmail.disponible()` devuelve False; el sistema cae silenciosamente 
  en la rama sin proveedor. El diagnóstico es engañoso (*«Email sin proveedor configurado»*
  cuando el operador sí configuró uno). No compromete seguridad ni rompe tests (el 
  email de prueba funciona), pero notificaciones desaparecen silenciosamente en 
  producción. **Tarea Fase 11**: detectar y propagar las 7 variables de SES/SMTP 
  en compose y documentación.

### P2 detectados en Fase 12 (Release Committee)

- **Desglose de tests incorrecto en `CLAUDE.md:40`.** El total es correcto (104), pero
  dos cifras de desglose están erradas:
  - `test_seguridad_arranque.py`: documento dice 14, realidad es **27**
  - `test_multitenant.py`: documento dice 7, realidad es **10**
  - La suma del desglose total es 88, no 104.
- **Cifra de `test_notificaciones.py` errónea en `docs/PENDIENTES.md:139` (línea anterior)**:
  documento decía 15 tests, realidad es **18**. Corregido en esta edición.
