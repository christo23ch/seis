---
tipo: documentacion-tecnica
tags:
  - tipo/documentacion-tecnica
  - area/backend
  - area/seguridad
---

# Arquitectura de tokens JWT

Dos familias de token, con audiencia separada desde [[ADR-0001-tipo-sesion-en-tokens-jwt]]:

| | Token de sesión | Token de propósito |
|---|---|---|
| Función | `crear_token(email, rol)` | `crear_token_proposito(sub, proposito, horas)` |
| Claims | `sub`, `rol`, `tipo="sesion"`, `exp` | `sub`, `proposito`, `jti`, `exp` |
| TTL | 12 h (config) | 24 h verificación / 1 h reseteo |
| Un solo uso | No | Sí, vía tabla `token_consumido` (PK sobre `jti`) |
| Validación | `decodificar_token` — exige `tipo="sesion"` | `decodificar_token_proposito` — exige `proposito` coincidente |

## Por qué la separación importa

Antes de [[ADR-0001-tipo-sesion-en-tokens-jwt]], ambas familias compartían secreto y `decodificar_token` no distinguía audiencia: un token de propósito servía también como Bearer de sesión.

## Relacionado

- [[ADR-0001-tipo-sesion-en-tokens-jwt]]
- [[ADR-0002-clave-compuesta-limitador-login]]
- [[Fase-10-alta-self-service]]
