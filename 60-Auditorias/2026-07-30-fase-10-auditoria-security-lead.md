---
tipo: auditoria
fase: "[[Fase-10-alta-self-service]]"
rol_auditor: "Staff Software Engineer (auditoría adversarial)"
veredicto: "APROBADA"
tags:
  - tipo/auditoria
  - fase/10
---

# Auditoría adversarial de la Fase 10 (Staff Engineer)

## Alcance revisado

Los 10 commits de `fase-10-alta-self-service` frente a `origin/main`.

## Metodología

Ejecución real, no solo lectura: suite completa con y sin Redis, prueba de mutación sobre `rate_limit.limpiar()`, reproducción forzada de la condición de carrera en el alta duplicada, ejecución literal del criterio de salida del Plan Maestro, `git worktree` con checkout real de cada uno de los 10 commits para verificar bisect.

## Hallazgos

| # | Hallazgo | Severidad | Confirmado/Refutado |
|---|---|---|---|
| 1 | `/auth/cambiar-password` sin interfaz | Alta | Confirmado — ver [[feat-cambio-password-interfaz]] |
| 2 | Bloqueo permanente para cuentas sin verificar | Alta | **Refutado**: el botón "Reenviar verificación" en `/login` cierra el ciclo, verificado end-to-end |
| 3 | Aserción vacua en test del limitador con Redis arriba | Media | Confirmado, pero **la regresión real sí se detecta** por otro test (`test_resetear_desbloquea_el_login`), verificado por mutación |
| 4 | Condición de carrera en alta duplicada | — | Confirmado que el fix funciona (reproducido forzando la carrera); sin cobertura de test |

## Evidencia

Suite: 162 recogidos, 159 pasan, 2 fallan (PDF preexistentes), 1 omitido. Bisect íntegro en los 10 commits. Criterio de salida del Plan Maestro ejecutado paso a paso: `201·200·200·200·200·400`.

## Veredicto

**APROBADA.** Ningún hallazgo real incumple el contrato del Plan Maestro §Fase 10.

## No demostrado

- La condición de carrera bajo concurrencia real en PostgreSQL (solo simulada).
- El comportamiento del frontend en un navegador real (nunca se abrió uno en toda la fase).
- El pipeline de CI ejecutado en GitHub Actions.
