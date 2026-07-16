# CLAUDE.md — Contexto maestro del proyecto SEIS
**Repositorio:** christo23ch/seis
**Rama de trabajo:** claude/wizardly-wright-nkscpg
**Última actualización:** 2026-07-16
**Fuente de verdad funcional/técnica:** `SEIS_Especificacion_Funcional_y_Tecnica.md` (no está en el repo; vive en los uploads de la sesión — considerar incorporarla a `docs/`)

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
| Base de datos | PostgreSQL 16 + PostGIS (geoespacial) + JSONB para atributos por tipología de activo; SQLite en tests |
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
- **49 tests** en `backend/tests/` (`test_golden_caso19.py` 14 · `test_precios.py` 9 · `test_vetos.py` 7 · `test_api.py` 6 · `test_conocimiento.py` 6 · `test_auth.py` 5 · `test_pdf_async.py` 2), incluido el **caso dorado §19** de la especificación como test de regresión.
  > Nota: la documentación de uploads (Manual de Pruebas / Plan Maestro) menciona 49 y 58 tests en distintos sitios; el conteo real verificado en el repo ahora mismo es **49**. Verificar antes de citar la cifra.
- **API REST completa** con JWT y roles (`backend/app/api/`: `auth.py`, `routes.py`, `conocimiento.py`, `deps.py`), Swagger en `/docs`.
- **Gobernanza del conocimiento versionada (T2/T3)**: reglas en YAML versionadas con vigencia temporal (`app/engine/rules/`), parámetros legales/fiscales versionados por ámbito (`app/engine/params/`), editables sin desplegar código.
- **Frontend Next.js 15 completo**: login, dashboard, asistente de nueva inversión (11 pasos), detalle de inversión, comparativa, mapa, configuración, reglas, parámetros, administración.
- **PDF de informe**, **Docker Compose** funcional, **manuales** (instalación, pruebas).
- **Migraciones Alembic**: solo `0001_esquema_inicial.py` existe — a partir de la Fase 9, cada cambio de esquema exige nueva migración con `downgrade` funcional.

### ✅ Fase 9 — Multi-tenancy por organización (COMPLETADA, 2026-07-14)
- Entidad `Organizacion`; `Usuario` += `organizacion_id`, `rol_org` (propietario|miembro), `es_superadmin` (plataforma); `Analisis` += `organizacion_id`.
- **Modelo de roles en dos ejes** (reconciliación): `rol` (admin|analista|lector) = capacidad dentro de la org; `rol_org` = gestión de miembros; `es_superadmin` = gobierno del conocimiento T2/T3 global.
- Migración **Alembic 0002** idempotente + reversible con backfill (org por defecto para datos históricos; admin bootstrap → propietario+superadmin). Verificada upgrade/downgrade sobre BD real.
- Aislamiento por `organizacion_id` en todos los endpoints de análisis; acceso a recurso ajeno = **404** (no 403). `require_superadmin` para conocimiento y alta de usuarios de plataforma. Router nuevo `organizacion.py` (GET /organizacion, POST/PATCH miembros por el propietario).
- Frontend: tipos/api/menú actualizados (oculta «Conocimiento» salvo superadmin), página `/equipo`.
- Tests: `test_multitenant.py` (10 nuevos, aislamiento + permisos + gestión de miembros). **Suite: 59 verdes** (49 previos + 10). `npm run build` limpio.

### ✅ Fase 11 — Infraestructura de producción, código (COMPLETADA)
- `GET /health` ampliado: verifica BD, Redis y versiones de conocimiento; 503 solo si BD (crítica) falla, `degraded` si solo Redis falla.
- Sentry opcional (backend y frontend), activado solo si `SENTRY_DSN` existe.
- `render.yaml` (IaC): backend, frontend, worker Celery, beat, Postgres, Redis.
- CI/CD: `.github/workflows/ci.yml` (lint+test+build) · `deploy-staging.yml` (auto en push a main) · `deploy-production.yml` (manual, con aprobación).
- `docs/RUNBOOK.md` + `docs/RENDER_DEPLOYMENT.md`; `.env.example` en la raíz del repo.
- Fail-fast: la app rechaza arrancar en producción con `JWT_SECRET`/`ADMIN_PASSWORD`/`DATABASE_URL` de fábrica.
- Pendiente (fuera de alcance de código): compra de dominio, alta real en Render/Cloudflare/Sentry/UptimeRobot.

### ✅ Fase 10 — Alta self-service (COMPLETADA, 2026-07-16)
- Registro público (`POST /auth/registro`), verificación de email (24 h, un solo uso), recuperación de contraseña (1 h, un solo uso), anti fuerza-bruta de dos cubos independientes (email + IP) en `/auth/login`.
- `EmailBackend` (ABC) + `ConsoleEmailBackend` única implementación: loguea, sin proveedor externo, sin buffer global — inyectable por DI/monkeypatch en tests. La integración real (Postmark/SES, Fase 12) se añade como subclase nueva.
- Tokens de propósito con `jti`+`iat`+`exp`+`proposito` (`app/core/security.py`); consumo de un solo uso vía tabla `token_consumido` (PK = jti, verificado con tests de concurrencia real).
- Migración Alembic **0003** idempotente + reversible. Se detectó y corrigió en commit aparte un bug preexistente del backfill de **0002** (INSERT sin `creado_en`, bloqueaba `alembic upgrade head` en BD nueva).
- Login siempre con mensaje genérico (no distingue email inexistente / password incorrecta / cuenta inactiva o sin verificar). `/auth/recuperar` sobre cuenta sin verificar reenvía verificación en vez de token de reseteo.
- Frontend: `/registro`, `/verificar`, `/resetear`, `/recuperar` (hermanas de `/login`).
- Tests: **80 verdes** (59 previos + 21 nuevos), incl. verificación/reseteo simultáneos del mismo token con `ThreadPoolExecutor`. `npm run build` limpio.
- Deuda técnica registrada (no bloqueante, ver `docs/PENDIENTES.md`): `downgrade()` de 0002 falla en SQLite al bajar hasta la base (limitación de Alembic batch mode con FKs); no afecta a Postgres ni al runbook de rollback real.

> **Backlog vivo:** `docs/PENDIENTES.md` registra deuda técnica y el resumen de fases 12-20.

### ⏳ No construido (Fases 12-20 del Plan Maestro — ver §5)
Notificaciones multicanal (email/Telegram/WhatsApp) + scoring de alertas, monetización con Stripe, cumplimiento RGPD, landing pública, endurecimiento de seguridad, escalado de captación (el conector BOE existe pero defensivo, sin ajuste empírico contra el portal real), analítica de negocio, beta cerrada.

### 🐛 Gotchas conocidos
- El motor (`app/engine/`) es la parte más validada del sistema (58/49 tests de regresión) — **NO tocar sin indicación expresa**; cualquier cambio ahí exige entender el "caso dorado §19" primero.
- El conector de ingesta BOE es "defensivo" (nunca rompe, pero no está ajustado contra el HTML real del portal) — trabajo pendiente de Fase 17.
- Credenciales de arranque `admin@seis.local` / `admin` — cambiar antes de cualquier despliegue real.
- `docs/PENDIENTES.md` §"Deuda técnica registrada": `downgrade()` de la migración 0002 falla en SQLite al bajar hasta la base (no bloqueante en Postgres).

---

## 4 · Modelo de datos — entidades reales en `backend/app/models.py`

```
FuenteSubasta · Subasta · Activo · Carga · Comparable
Analisis (snapshot inmutable) · RiesgoEvaluado · Escenario · Decision · ReglaDisparada
Regla (versionada) · Parametro (versionado) · PerfilInversion
ResultadoReal · Usuario · Auditoria
```

**Reglas de negocio críticas (de la especificación, no negociables):**
- **P1 Determinismo:** mismo input + misma versión de reglas ⇒ mismo output. Cada `Analisis` es un snapshot inmutable (nunca se sobrescribe; reanalizar crea snapshot nuevo).
- **P4 La ausencia de datos penaliza:** ningún dato ausente se rellena con el valor optimista. Menos información ⇒ ICI baja ⇒ ICO baja ⇒ techo de semáforo.
- **P6 Vetos antes que promedios:** un defecto letal (carga no purgable, imposibilidad de inscripción, ocupación de renta antigua, financiación no preaprobada) **nunca** se compensa con buena ubicación u otras virtudes. Arquitectura lexicográfica: vetos → matriz de riesgos → scoring compensatorio (MCDA) → simulación de escenarios.
- **P_límite es un bloqueo duro de software**: el sistema nunca permite pujar por encima, sin excepción.
- Cuando exista multi-tenancy (Fase 9): `Analisis` y `ResultadoReal` son **privados por organización**; las subastas captadas y el conocimiento T2/T3 son **compartidos**; alertas/favoritos/notificaciones son **privados por usuario**. Acceder a un recurso ajeno por ID directo debe devolver **404, no 403** (no revelar existencia).

---

## 5 · Hoja de ruta — Fases 9 a 20 (Plan Maestro)

**Ruta crítica:** 9 → 10 → 11 → 13 → 20. Fase 14 (legal) en paralelo desde la 9. Fase 18 (WhatsApp) es condicional a demanda medida en Fase 12.

| Fase | Nombre | Bloquea a | Modelo recomendado |
|---|---|---|---|
| **9** | Multi-tenancy por organización | Todo lo demás | **Fable 5** (autorización transversal, coste de un fallo = fuga de datos) |
| 10 | Alta self-service + recuperación de cuenta | — | Sonnet |
| 11 | Infraestructura de producción | — | Fable 5 (decisiones operativas) |
| 12 | Notificaciones multicanal + scoring | — | Fable 5 |
| 13 | Monetización (Stripe) | Beta real | Fable 5 (ciclo de vida de suscripción, idempotencia de webhooks) |
| 14 | RGPD / legal | — | Fable 5 (borradores) + Sonnet (implementación) |
| 15 | Landing + onboarding | — | Sonnet |
| 16 | Auditoría de seguridad | Antes de tráfico real | Fable 5 (auditoría) + Sonnet (correcciones) |
| 17 | Escalado de captación (BOE real) | — | Sonnet (con HTML real pegado) |
| 18 | WhatsApp (condicional) | — | Sonnet |
| 19 | Analítica y panel de negocio | — | Sonnet/Haiku |
| 20 | Beta cerrada y lanzamiento | Fin del proyecto | — |

**Siguiente tarea urgente: Fase 12 — Notificaciones multicanal + scoring.** Fases 9, 10 y 11 (código) ya completadas. El prompt de ejecución está en `SEIS_Plan_Maestro_Fases_920.md` §Fase 12; el envío real de email (Postmark/SES) se añade como subclase nueva de `EmailBackend` (Fase 10), sin tocar la abstracción. Antes de tocar código: **exigir plan de cambios fichero a fichero y detenerse para aprobación** — es la regla de oro de este proyecto.

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

---

## 7 · Cómo levantar y probar (resumen — detalle completo en `MANUAL_DE_PRUEBAS.md`)

```bash
cd /workspace/seis
cp .env.example .env
docker compose up -d --build
# Web:     http://localhost:3000  (admin@seis.local / admin)
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

---

## 9 · Notas para la próxima sesión

**TL;DR:** El motor experto (M01-M14), el multi-tenancy (Fase 9), el alta self-service (Fase 10) y el código de infraestructura de producción (Fase 11) están completos y probados. Lo que falta es todo lo que convierte esto en negocio operando: alta real en Render/Cloudflare/Sentry (pasos humanos de Fase 11), notificaciones multicanal (Fase 12, siguiente paso de código), monetización, legal y salida a mercado. Seguir el Plan Maestro fase a fase, con plan-antes-de-código como regla no negociable.
