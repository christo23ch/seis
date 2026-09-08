---
tipo: meta
---

# Contador de secuencias

Números ya asignados. QuickAdd los lee y propone el siguiente; actualizar a mano tras cada creación manual.

| Serie | Último asignado |
|---|---|
| ADR | 0010 |
| RFC | 0000 |
| BUG | 0000 |
| INC / PM | 0000 |

## Números reservados (asignados pero aún sin nota)

**Ya no queda ningún número reservado.** [[ADR-0004-create-all-fuera-de-produccion]] (Bloque E) y [[ADR-0005-confianza-en-cabeceras-de-ip-solo-tras-par-declarado]] (Bloque H) se escribieron al cerrar la Fase 11-A.

Ya están escritos, fuera de orden: [[ADR-0003-staging-como-entorno-estricto]] (Bloque D), [[ADR-0006-liveness-y-readiness-separadas]] (Bloque A), [[ADR-0007-planificador-celery-separado-del-worker]] (Bloque C′), [[ADR-0008-loopback-por-defecto-en-los-puertos-publicados]] (Bloque C′ también, tras las revisiones) y [[ADR-0009-purga-de-cuentas-nunca-verificadas]] (Bloque I).

La serie 0003-0009 se escribió **fuera de orden**, porque los números se reservaron por bloque en el plan aprobado y los bloques no se ejecutaron en ese orden. Al cerrar la fase no queda ningún hueco.

El siguiente ADR nuevo que no sea de los bloques E o H toma el **`0010`**.
