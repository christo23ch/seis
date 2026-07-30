---
tipo: puente
aliases:
  - CLAUDE.md
  - Contexto Maestro
tags:
  - tipo/puente
---

# CLAUDE.md — Contexto maestro

> Nota-puente. El contenido vive en `CLAUDE.md`, raíz del repositorio.

📄 Fichero real: `CLAUDE.md`

## Qué contiene, para quien busca en el Vault y no recuerda dónde

- §1-2: qué es SEIS y stack técnico
- §3: estado actual construido, fase a fase
- §4: modelo de datos y las reglas P1-P10 no negociables
- §5: hoja de ruta y ruta crítica
- §6: convenciones obligatorias (11 reglas, la más citada en este Vault es §6.8: no tocar `app/engine/`)

## Notas de este Vault que dependen de sus reglas

```dataview
LIST
FROM "30-Decisiones/ADR"
WHERE contains(file.outlinks, this.file.link)
```

## Ejemplo de cumplimiento verificado

[[Fase-10-alta-self-service|Fase 10]] es la fase donde se verificó por análisis sintáctico —no solo por lectura— que §6.8 (no tocar `app/engine/`) se cumplió: 0 ficheros de esa carpeta aparecen en el diff de la fase.
