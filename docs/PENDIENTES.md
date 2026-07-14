# SEIS — Lista de pendientes (backlog)

Registro vivo del trabajo planificado y aún no implementado. Cada fase se ejecuta
con el protocolo del proyecto: **plan → aprobación → implementación → tests verdes
+ `npm run build` limpio → PR**. Detalle metodológico en `docs/SEIS_Plan_Maestro_Fases_920.md`.

**Estado del recorrido:** Fase 9 (multi-tenancy) ✅ completada. Siguiente: Fase 10.

---

## 🔜 Fase 10 — Alta self-service (PLANIFICADA, pendiente de implementar)

Registro público, verificación de email y recuperación de contraseña.
Plan aprobado en su estructura; **pendiente de arrancar la implementación.**

### Punto a confirmar antes de codificar
- **`email_service.py` como abstracción honesta sin proveedor real** (en dev/test:
  log + buffer del último email para testear el enlace; en producción sin
  credenciales: stub documentado). El envío transaccional real (Postmark/SES) es
  Fase 12; adelantarlo aquí exigiría credenciales inexistentes. → **¿OK?**

### Reconciliación con la realidad del repo (el prompt asumía otro estado)
- Migración nueva = **0003** (no "0005"; solo existen 0001 y 0002).
- `email_service.py` **no existe** → se crea.
- Rate-limiting: Redis **con fallback a memoria** en tests.

### Cambios previstos, fichero a fichero

**Backend — modelos y migración**
- `app/models.py`: `Usuario` += `email_verificado: bool` (default False). Nueva tabla
  `TokenConsumido(jti PK, proposito, consumido_en)` (uso único de tokens).
- `alembic/versions/0003_self_service.py` (idempotente + reversible): add column
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
| 12 | Notificaciones multicanal + scoring | email real (Postmark/SES) detrás de `email_service`, Telegram, digest |
| 13 | Monetización (Stripe) | planes/límites, webhooks idempotentes |
| 14 | Cumplimiento legal y RGPD | consentimientos, ARCO, textos legales (revisión de abogado) |
| 15 | Landing pública, onboarding y ayuda | — |
| 16 | Endurecimiento de seguridad | OWASP, rate-limit global, cabeceras |
| 17 | Escalado de la captación (BOE real) | ajuste del conector contra el portal real |
| 18 | Canal WhatsApp (condicional) | solo si Fase 12 demuestra demanda |
| 19 | Analítica y panel de negocio | Plausible/PostHog, embudo, MRR |
| 20 | Beta cerrada y lanzamiento | QA guionizado, carga, go-live |

### Deuda técnica menor detectada
- No existe `.env.example` en la raíz del repo (el `MANUAL_DE_PRUEBAS.md` y
  `docker-compose.yml` lo referencian). Conviene crearlo con las variables reales
  (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `ADMIN_PASSWORD`, `SEIS_CORS_ORIGINS`,
  y las de Fase 10: `FRONTEND_URL`, `EMAIL_FROM`). Solo existe `frontend/.env.example`.
- Endpoints citados en prompts que aún no existen y que deberán heredar el scoping
  por `organizacion_id` cuando se creen: `export.csv`, `geo`, `resultado-real`, `/calibracion`.
