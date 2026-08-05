---
tipo: home
tags:
  - tipo/home
---

# SEIS — Panel del proyecto

## Fase actual

```dataview
TABLE numero AS "Nº", estado
FROM #tipo/fase
WHERE estado = "en-progreso"
SORT numero DESC
```

## Último release

```dataview
TABLE file.link AS "Release"
FROM #tipo/release
SORT file.name DESC
LIMIT 1
```

## Última auditoría

```dataview
TABLE fase, veredicto
FROM #tipo/auditoria
SORT file.name DESC
LIMIT 1
```

## Bugs abiertos, por criticidad

```dataview
TABLE criticidad, prioridad, fase
FROM #tipo/bug
WHERE estado != "cerrado"
SORT criticidad ASC
```

## ADR sin decidir (borrador o en revisión)

```dataview
TABLE fase, estado
FROM #tipo/adr
WHERE estado = "borrador" OR estado = "en-revision"
```

## Tareas críticas (P0/P1) sin cerrar

```dataview
TASK
FROM #tipo/tarea OR #tipo/feature
WHERE !completed AND (prioridad = "p0" OR prioridad = "p1")
```

## Deuda sin fase asignada

```dataview
TABLE prioridad
FROM #tipo/feature
WHERE fase = "" OR !fase
```

## Documentos modificados en los últimos 7 días

```dataview
TABLE file.mtime AS "Última edición"
FROM ""
WHERE file.mtime >= date(today) - dur(7 days) AND !contains(file.path, "900-Plantillas")
SORT file.mtime DESC
LIMIT 15
```

## Próximas reuniones / reuniones recientes

```dataview
TABLE asistentes
FROM #tipo/reunion
SORT file.name DESC
LIMIT 5
```

## Ruta crítica

`9 ✅ → 9.5 ✅ → [[Fase-10-alta-self-service|10 ✅]] → [[Fase-11-infraestructura|11 ⬅ en curso (alcance 11-A)]] → 13 → 20`

Ver [[Plan-Maestro|Plan Maestro]] para el detalle completo por fase.

## KPIs del Vault

```dataview
TABLE length(rows) AS "Cantidad"
FROM #tipo/adr OR #tipo/bug OR #tipo/incidente OR #tipo/feature OR #tipo/runbook
GROUP BY tipo
```
