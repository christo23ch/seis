---
tipo: puente
aliases:
  - Plan Maestro
  - Roadmap
tags:
  - tipo/puente
---

# Plan Maestro

> Nota-puente: el contenido vive en `docs/SEIS_Plan_Maestro_Fases_920.md`. Esta nota no lo copia — lo enlaza y añade la capa de Obsidian (backlinks, tags, Dataview) que el fichero fuente no tiene por sí solo.

📄 Fichero real: `docs/SEIS_Plan_Maestro_Fases_920.md`

## Estado de ejecución, por fase

```dataview
TABLE estado, file.link AS "Nota de fase"
FROM #tipo/fase
SORT numero ASC
```

## Ruta crítica declarada

`9 → 9.5 → 10 → 11 → 13 → 20`. Ver `[[Fase-11-infraestructura]]` para la fase en curso y `[[Fase-10-alta-self-service]]` para la última cerrada.

## Por qué esta nota no duplica el contenido

Ya se pagó el precio de tener dos fuentes de verdad una vez: `docs/PENDIENTES.md` registra como "P2" que las cifras de la suite de tests divergieron entre `CLAUDE.md` y otro documento durante la Fase 12. Esta nota-puente existe precisamente para que eso no vuelva a pasar con el Plan Maestro.
