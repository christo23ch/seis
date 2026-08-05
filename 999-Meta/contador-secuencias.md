---
tipo: meta
---

# Contador de secuencias

Números ya asignados. QuickAdd los lee y propone el siguiente; actualizar a mano tras cada creación manual.

| Serie | Último asignado |
|---|---|
| ADR | 0006 |
| RFC | 0000 |
| BUG | 0000 |
| INC / PM | 0000 |

## Números reservados (asignados pero aún sin nota)

**ADR-0004 y ADR-0005 están reservados** para los bloques E (`create_all` fuera de producción) y H (confianza en `X-Forwarded-For` solo tras proxy declarado) de la [[Fase-11-infraestructura|Fase 11]]. Aún no se han implementado esos bloques, así que las notas no existen todavía: **no reutilizar esos dos números**.

`ADR-0003` ya está escrito: [[ADR-0003-staging-como-entorno-estricto]] (Bloque D).

Por eso el último asignado es `0006` ([[ADR-0006-liveness-y-readiness-separadas]], Bloque A) y no `0003`: la reserva se hizo por bloque en el plan aprobado, no por orden de escritura.
