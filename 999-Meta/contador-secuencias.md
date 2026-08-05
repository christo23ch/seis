---
tipo: meta
---

# Contador de secuencias

Números ya asignados. QuickAdd los lee y propone el siguiente; actualizar a mano tras cada creación manual.

| Serie | Último asignado |
|---|---|
| ADR | 0008 |
| RFC | 0000 |
| BUG | 0000 |
| INC / PM | 0000 |

## Números reservados (asignados pero aún sin nota)

**ADR-0004 y ADR-0005 están reservados** para los bloques E (`create_all` fuera de producción) y H (confianza en `X-Forwarded-For` solo tras proxy declarado) de la [[Fase-11-infraestructura|Fase 11]]. Aún no se han implementado esos bloques, así que las notas no existen todavía: **no reutilizar esos dos números**.

Ya están escritos, fuera de orden: [[ADR-0003-staging-como-entorno-estricto]] (Bloque D), [[ADR-0006-liveness-y-readiness-separadas]] (Bloque A), [[ADR-0007-planificador-celery-separado-del-worker]] (Bloque C′) y [[ADR-0008-loopback-por-defecto-en-los-puertos-publicados]] (Bloque C′ también, tras las revisiones).

Por eso el último asignado es `0008` y quedan dos huecos por debajo: la reserva se hizo **por bloque en el plan aprobado, no por orden de escritura**, y los bloques no se han ejecutado en el orden en que se numeraron. Ni el `0007` ni el `0008` estaban reservados a nadie, así que fueron en su momento el siguiente libre de verdad; **los dos huecos siguen intactos** hasta que se escriban sus notas.

El siguiente ADR nuevo que no sea de los bloques E o H toma el **`0009`**.
