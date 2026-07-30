---
tipo: fase
numero: ""
estado: en-progreso
tags:
  - tipo/fase
---

# <% tp.file.title %>

## Objetivo (literal del Plan Maestro)

<!-- Citar textualmente, no parafrasear. Es el contrato. -->

## Requisitos

| # | Requisito | Obligatorio/Opcional | Estado |
|---|---|---|---|

## Criterio de salida (literal)

<!-- Citar textualmente -->

## Decisiones tomadas durante la fase

```dataview
LIST
FROM #tipo/adr
WHERE fase = link(this.file.link)
```

## Bugs encontrados durante la fase

```dataview
TABLE estado, criticidad
FROM #tipo/bug
WHERE fase = link(this.file.link)
```

## Releases de esta fase

```dataview
LIST
FROM #tipo/release
WHERE fase = link(this.file.link)
```

## Auditorías de esta fase

```dataview
TABLE estado
FROM #tipo/auditoria
WHERE fase = link(this.file.link)
```

## Deuda que deja abierta

<!-- Enlazar a 70-Backlog/ -->
