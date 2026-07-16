# SEIS — Lista de pendientes (backlog)

Registro vivo del trabajo planificado y aún no implementado. Cada fase se ejecuta
con el protocolo del proyecto: **plan → aprobación → implementación → tests verdes
+ `npm run build` limpio → PR**. Detalle metodológico en `docs/SEIS_Plan_Maestro_Fases_920.md`.

**Estado del recorrido:** Fase 9 (multi-tenancy) ✅ · Fase 11 (infraestructura de
producción, código) ✅ · Fase 10 (alta self-service) ✅ completada. Siguiente: Fase 12.

---

## ✅ Fase 10 — Alta self-service (COMPLETADA)

Registro público, verificación de email, recuperación de contraseña y anti
fuerza-bruta en `/auth/login`. Commits: `fix(alembic): repair migration 0002
backfill` + `feat(auth): self service registration`.

**Decisiones de arquitectura fijadas en esta fase (vinculantes para Fase 12):**
- `EmailBackend` (ABC) + `ConsoleEmailBackend` (única implementación: loguea,
  sin proveedor externo, sin buffer global — DI/monkeypatch en tests). La
  integración real (Postmark/SES) de Fase 12 debe añadirse como una subclase
  nueva, sin tocar la abstracción.
- Tokens de propósito (`crear_token_proposito`/`decodificar_token_proposito`
  en `app/core/security.py`): JWT con `jti` + `iat` + `exp` + `proposito`,
  consumo de un solo uso vía tabla `token_consumido` (jti como PK — la propia
  restricción de unicidad es lo que garantiza la seguridad ante condiciones
  de carrera, verificado con tests de concurrencia real con `ThreadPoolExecutor`).
- Rate-limit de dos cubos independientes (`app/core/rate_limit.py`): login por
  email y login por IP, ambos deben estar libres. Redis con fallback a memoria
  de proceso si Redis no responde (cacheado por proceso, no reintenta en cada
  llamada).
- Mensaje de login siempre genérico: no se distingue entre email inexistente,
  contraseña incorrecta o cuenta inactiva/sin verificar.
- `/auth/recuperar` sobre una cuenta sin verificar reenvía el correo de
  verificación en vez de emitir un token de reseteo (no tiene sentido resetear
  la contraseña de una cuenta que nunca se activó).
- Regla de transacciones: el email se envía siempre **después** de que la
  transacción relevante ya hizo `db.commit()`. Si el commit falla, no se envía
  nada.

---

## 🐛 Deuda técnica registrada

- Endpoints citados en prompts que aún no existen y que deberán heredar el
  scoping por `organizacion_id` cuando se creen: `export.csv`, `geo`,
  `resultado-real`, `/calibracion`.

## ✅ Deuda técnica resuelta

- ~~`downgrade()` de `0002_multitenancy.py` fallaba en SQLite al bajar hasta la
  base~~ — corregido en commit aparte `fix(alembic): repair migration 0002
  downgrade on SQLite` (`op.batch_alter_table` para los `drop_column`/
  `drop_index` de `analisis` y `usuario`; sin cambio de comportamiento en
  Postgres). Verificado el ciclo completo `upgrade head → downgrade base →
  upgrade head` sobre una BD SQLite vacía, con el esquema final idéntico al
  esperado (mismas tablas, columnas, FKs e índices).

---

## ⏳ Fases 12-20 — no iniciadas

Resumen (detalle y prompts de ejecución en `docs/SEIS_Plan_Maestro_Fases_920.md`):

| Fase | Nombre | Notas |
|---|---|---|
| 12 | Notificaciones multicanal + scoring | email real (Postmark/SES) como subclase nueva de `EmailBackend` (Fase 10), Telegram, digest |
| 13 | Monetización (Stripe) | planes/límites, webhooks idempotentes |
| 14 | Cumplimiento legal y RGPD | consentimientos, ARCO, textos legales (revisión de abogado) |
| 15 | Landing pública, onboarding y ayuda | — |
| 16 | Endurecimiento de seguridad | OWASP, rate-limit global, cabeceras |
| 17 | Escalado de la captación (BOE real) | ajuste del conector contra el portal real |
| 18 | Canal WhatsApp (condicional) | solo si Fase 12 demuestra demanda |
| 19 | Analítica y panel de negocio | Plausible/PostHog, embudo, MRR |
| 20 | Beta cerrada y lanzamiento | QA guionizado, carga, go-live |
