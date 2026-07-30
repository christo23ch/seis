---
tipo: incidente
fase: ""
estado: en-progreso
criticidad: alta
tags:
  - tipo/incidente
  - criticidad/alta
---

# INC-<% tp.system.prompt("número") %>: <% tp.file.title %>

## Detección

- Hora de inicio (estimada):
- Hora de detección:
- Cómo se detectó (alarma, usuario, revisión manual):

## Impacto

<!-- Qué se rompió, para quién, durante cuánto tiempo -->

## Cronología

| Hora | Evento |
|---|---|

## Mitigación aplicada

<!-- Qué se hizo para pararlo, no para arreglarlo de raíz -->

## Resolución

- Hora de resolución:
- Commit/acción que lo resolvió:

## Postmortem

[[PM-<% tp.system.prompt("mismo número") %>-<% tp.file.title %>]]
