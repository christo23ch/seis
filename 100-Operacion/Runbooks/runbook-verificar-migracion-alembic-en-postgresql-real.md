---
tipo: runbook
area: "backend"
tags:
  - tipo/runbook
  - area/backend
---

# Verificar una migración Alembic contra PostgreSQL real

> Nota atemporal. Procedimiento usado para verificar `0006_self_service` en la Fase 10; reutilizable para toda migración futura (`0007` en adelante).

## Cuándo usar este runbook

Antes de fusionar cualquier PR que incluya una migración Alembic nueva.

## Prerrequisitos

- [ ] Docker Desktop arrancado
- [ ] `docker compose up -d --build` completado, `db` en estado `healthy`

## Procedimiento

1. `docker compose exec -T db psql -U seis -d seis -tc "SELECT version_num FROM alembic_version;"` — confirmar la revisión esperada.
2. `docker compose exec -T backend alembic downgrade <revision_anterior>` — comprobar que el downgrade no falla.
3. `docker compose exec -T db psql ... -tc "SELECT count(*) FROM information_schema.columns WHERE table_name='<tabla>' AND column_name='<columna_nueva>';"` — debe ser `0` tras el downgrade.
4. `docker compose exec -T backend alembic upgrade head` — re-subir.
5. Repetir paso 1 para confirmar el ciclo completo.
6. `docker compose exec -T backend alembic upgrade head` una segunda vez — debe ser no-op (idempotencia).

## Verificación de que ha funcionado

Los 6 pasos completan sin error y el paso 1 devuelve la misma revisión antes y después del ciclo.

## Rollback si algo sale mal

`docker compose exec -T backend alembic downgrade <revision_anterior>` y revisar manualmente cualquier fila que la migración nueva haya podido dejar inconsistente (ver salvedades de cada migración concreta).

## Última vez ejecutado

2026-07-29, Fase 10, migración `0006_self_service`. Ver [[ADR-0001-tipo-sesion-en-tokens-jwt]] y [[Fase-10-alta-self-service]].
