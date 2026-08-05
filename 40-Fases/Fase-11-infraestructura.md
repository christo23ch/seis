---
tipo: fase
numero: 11
estado: en-progreso
tags:
  - tipo/fase
  - fase/11
  - estado/en-progreso
  - area/infra
---

# Fase 11 — Infraestructura de producción

> **Plan canónico: `docs/FASE_11_PLAN.md`** (aprobado por el responsable el 2026-07-30). Esta nota **no lo copia**: enlaza a él y añade la capa de Obsidian. Cualquier detalle que no esté aquí está allí, y allí manda.

## Objetivo (literal del Plan Maestro)

> «Un entorno real en internet con dominio, HTTPS, copias de seguridad probadas y alarmas, más un entorno de pruebas (staging) idéntico.»

Ver [[Plan-Maestro|Plan Maestro]] §Fase 11 para el contrato completo.

## La fase está partida en 11-A y 11-B

Con el proveedor de hosting, el dominio y el proveedor de email **diferidos** (H1, H2, H6), no se puede escribir la IaC, ni los jobs de despliegue, ni un runbook que no sea ficción. Pero los bloques agnósticos del proveedor sí son ejecutables hoy, e incluyen la puerta de despliegue que ahora mismo impide exponer el producto a internet.

- **11-A — de repositorio, agnóstica del proveedor.** Ejecutable ya. Un PR.
- **11-B — dependiente del proveedor.** Bloqueada hasta que se cierren H1, H2 y H6. Otro PR.

**La Fase 11 no se declara cerrada al fusionar 11-A.** Sus criterios de salida son operativos y ninguno es alcanzable sin la 11-B.

## Requisitos

Bloques de la **Fase 11-A**. El detalle fichero a fichero de cada uno está en `docs/FASE_11_PLAN.md` §3.

| # | Requisito | Obligatorio/Opcional | Estado |
|---|---|---|---|
| A | Salud por componente: liveness intacto, readiness pública, detalle autenticado | Obligatorio | ✅ Completado |
| C′ | Higiene de despliegue portable (`.dockerignore`, variables SES/SMTP propagadas, `.env.produccion.example`) | Obligatorio | ⬜ Pendiente |
| D | `staging` como **cuarto entorno estricto**, no solo soportado | Obligatorio | ✅ Completado |
| E | `create_all` fuera de la ruta de producción | Obligatorio | ⬜ Pendiente |
| F′ | CI que ejecute la **suite completa** y `npm run build`, no 1 de 14 ficheros | Obligatorio | ⬜ Pendiente |
| H | IP real tras proxy — la puerta de despliegue heredada de la Fase 10 | Obligatorio | ⬜ Pendiente |
| I | Deudas heredadas con propietario «Fase 11» (reintento de Redis, purga de `token_consumido`, cuentas nunca verificadas) | Obligatorio | ⬜ Pendiente |

## Decisiones tomadas y diferidas (H0-H10)

Resumen. **Detalle completo y evidencia en `docs/FASE_11_PLAN.md` §1.**

| # | Asunto | Resolución |
|---|---|---|
| H0 | ¿Fusionar la Fase 10 o ramificar desde ella? | ✅ **Cerrado, premisa refutada.** La Fase 10 y el Vault ya estaban en `main`. Toda rama nueva sale de `main`. |
| H1 | Proveedor de hosting | ⏸ **Diferido.** No se escribe IaC de ningún proveedor; todo agnóstico. |
| H2 | Dominio y subdominios | ⏸ **Diferido.** Prohibido codificar dominios a fuego; todo por variables de entorno. |
| H3 | Presupuesto | ⏸ **Diferido.** Ninguna decisión técnica se condiciona al coste. |
| H4 | ¿Frontend en un proveedor distinto? | ✅ Mismo proveedor que el backend. |
| H5 | Sentry | ⛔ **Fuera de esta fase** — ver el apartado siguiente. |
| H6 | Proveedor de email | ⏸ **Diferido.** No se integra ninguno; sí se propaga su configuración. |
| H7 | `staging` estricto · beat separado del worker | ✅ Ambas sí. Bloques D y C′. |
| H8 | Quién aprueba el despliegue | ✅ El responsable del proyecto, disparo manual. Se materializa en 11-B. |
| H9 | Numeración de migración | ✅ **Esta fase no lleva migraciones. No se crea la `0007`.** |
| H10 | Downtime | ✅ Corte aceptado en el primer despliegue; a partir de ahí, migraciones retrocompatibles. |
| CF | Cloudflare | ✅ El Bloque H se diseña con Cloudflare desde el inicio: no basta con leer `X-Forwarded-For`. |

## Sentry queda fuera de la fase

El **requisito 2 del prompt del Plan Maestro** pide integración de Sentry en backend y frontend, activada solo si existe `SENTRY_DSN`. **No se entrega, por decisión del responsable (H5).**

Se anota sin maquillar: **esto incumple deliberadamente ese requisito del contrato.** No es un olvido ni un «pendiente menor». La huella completa de Sentry en esta fase es **una variable `SENTRY_DSN` declarada y vacía**, documentada como sin consumidor. Queda como deuda abierta **sin fase propietaria asignada**.

## Suite de tests

**Línea base oficial de la fase, fijada por el responsable:**

> **162 recogidos · 159 pasan · 2 fallan (los de PDF, preexistentes) · 1 omitido.**

Es la **única cifra citable** en documentación y auditorías. Las anteriores (118, 104) quedan derogadas.

**Tras el Bloque A (medido):** **172 recogidos · 169 pasan · 2 fallan · 1 omitido.** Es decir, **+10 verdes y 0 regresiones**; los 2 rojos siguen siendo los mismos de PDF y el omitido sigue siendo T5.

**Tras el Bloque D (medido):** **181 recogidos · 178 pasan · 2 fallan · 1 omitido.** Acumulado frente a la línea base: **+19 verdes y 0 regresiones**.

## Criterio de salida (literal)

> «app accesible en `https://app.tudominio.com`, staging funcionando, un deploy automático a staging al fusionar en `main`, alarma recibida al simular una caída, y restauración documentada.»

**ABIERTO.** Ninguno de estos cuatro puntos es alcanzable sin la 11-B **y sin ejecución humana**:

- [ ] Despliegue real sirviendo la aplicación por **HTTPS**
- [ ] **Restauración de un backup ejecutada de verdad, con el tiempo anotado** — un backup no probado no existe
- [ ] **Alarma de caída recibida** al simular una caída
- [ ] **Email de verificación llegado a una bandeja real** — no basta con que el log diga «enviado»

## ADR de esta fase

- [[ADR-0006-liveness-y-readiness-separadas]] — Bloque A. Tres endpoints en vez del `/health` único que pedía el prompt.
- [[ADR-0003-staging-como-entorno-estricto]] — Bloque D. `staging` entra en `ENTORNOS_SOPORTADOS` **y** en `ENTORNOS_ESTRICTOS`; si un entorno merece existir en internet, merece secretos propios.

Los números **0003, 0004 y 0005 están reservados** para los ADR de los bloques D, E y H, que aún no se han implementado. Ver [[contador-secuencias]].

## Deuda que deja abierta

- **Sentry (H5), sin fase propietaria.** Ver arriba.
- **Toda la Fase 11-B:** IaC del proveedor, jobs de despliegue, `docs/RUNBOOK.md`, runbooks temáticos del Vault y el ADR de elección de hosting.
- **Requisito operativo para el runbook de 11-B:** la plataforma de hosting debe apuntar su health check a `/api/v1/health`, **nunca** a `/health/listo`. Detalle y motivo en [[ADR-0006-liveness-y-readiness-separadas]].
- **Ampliar `/health/detalle` con un apartado de red** (`par_tcp`, `ip_resuelta`, política de proxies) al ejecutar el Bloque H: es la única forma práctica de verificar **en producción** que la resolución de IP no está mal configurada.
- Las tres deudas heredadas del Bloque I siguen abiertas mientras el bloque no se ejecute. Ver [[PENDIENTES-md|PENDIENTES.md]].

## Relacionado

- Rama: `fase-11-infraestructura`, creada desde `main` (`679fc4d`)
- Plan de ejecución: `docs/FASE_11_PLAN.md` — sustituye a `docs/FASE_11_PLAN_BORRADOR.md`
- Migración Alembic: **ninguna** (H9)
- [[Fase-10-alta-self-service]] — de ella hereda la **puerta de despliegue** (bajo `docker compose` la IP de origen no sobrevive: todo llega con la de la pasarela) y tres deudas del Bloque I
- [[ADR-0002-clave-compuesta-limitador-login]] — su efecto pleno **depende del Bloque H** de esta fase
- [[Plan-Maestro|Plan Maestro]] §Fase 11
- [[PENDIENTES-md|PENDIENTES.md]]
