---
tipo: fase
numero: 10
estado: cerrado
tags:
  - tipo/fase
  - fase/10
  - estado/cerrado
---

# Fase 10 — Alta self-service y recuperación de cuenta

## Objetivo (literal del Plan Maestro)

> «Que cualquier persona pueda registrarse sola, verificar su email y recuperar su contraseña, sin intervención tuya.»

Ver [[Plan-Maestro|Plan Maestro]] §Fase 10 para el contrato completo.

## Requisitos

| # | Requisito | Obligatorio/Opcional | Estado |
|---|---|---|---|
| 1 | Registro público + organización propia, pendiente de verificación | Obligatorio | ✅ Cumplido |
| 2 | Verificación por email, token de un solo uso, 24 h | Obligatorio | ✅ Cumplido |
| 3 | Recuperación de contraseña | Obligatorio | ✅ Cumplido |
| 4 | Fuerza bruta por IP+email con Redis | Obligatorio | ✅ Cumplido |
| 5 | Frontend `/registro`, `/verificar`, `/recuperar` | Obligatorio | ✅ Cumplido |
| 6 | OAuth Google | Opcional, diferible | ⬜ No entregado (autorizado) |

## Criterio de salida (literal)

> «un desconocido se registra, verifica, entra, cierra sesión y recupera contraseña sin tocar la base de datos; tests cubren tokens caducados, reutilizados y manipulados.»

Ejecutado paso a paso contra la aplicación real: `registra=201 verifica=200 entra=200 sesión=200 resetea=200 reentra=200 token_reusado=400`. **CUMPLIDO.**

## Deuda que deja abierta

- [[feat-cambio-password-interfaz]] — `/auth/cambiar-password` existe en la API, no en la interfaz. Sin fase asignada.
- Puerta de despliegue: la IP de origen no sobrevive a `docker compose`. Propietario: Fase 11.

## Cambio incompatible

`crear_token` marca `tipo="sesion"`; los tokens emitidos antes de la fase dejan de servir al desplegar. Cierra una confusión de audiencia por la que un token de propósito valía como Bearer de sesión completo. Ver [[ADR-0001-tipo-sesion-en-tokens-jwt]].

## ADR de esta fase

- [[ADR-0001-tipo-sesion-en-tokens-jwt]]
- [[ADR-0002-clave-compuesta-limitador-login]]

## Auditorías de esta fase

- [[2026-07-30-fase-10-auditoria-security-lead]]
- [[2026-07-30-fase-10-auditoria-release-committee]]

## Runbooks derivados

- [[runbook-verificar-migracion-alembic-en-postgresql-real]]

## Tag de release

`fase-10`

## Relacionado

- Rama: `fase-10-alta-self-service`
- [[PENDIENTES-md|PENDIENTES.md]] — deuda 12
- [[Arquitectura-de-tokens-jwt]]
