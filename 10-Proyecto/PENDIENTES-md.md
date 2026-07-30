---
tipo: puente
aliases:
  - PENDIENTES.md
  - Backlog oficial
tags:
  - tipo/puente
---

# PENDIENTES.md — backlog vivo

> Nota-puente. El contenido vive en `docs/PENDIENTES.md`.

📄 Fichero real: `docs/PENDIENTES.md`

## Relación con `70-Backlog/` de este Vault

**`docs/PENDIENTES.md` sigue siendo la fuente de verdad del backlog técnico entre fases** — no se migra a notas individuales de `70-Backlog/Features` de golpe, porque duplicaría lo que ya funciona. La regla desde hoy:

- **Deuda ya registrada en `PENDIENTES.md` con propietario y fase asignados** → se queda ahí, tal cual.
- **Deuda nueva sin fase asignada** (como la del hueco de `/auth/cambiar-password`) → se crea también como nota `[[feat-cambio-password-interfaz]]` en `70-Backlog/Features/`, enlazada desde aquí, precisamente porque *no tener fase asignada* es el caso que Dataview necesita poder listar en el dashboard sin que se pierda entre el resto del fichero.

## Deuda sin fase asignada, agregada desde el Vault

```dataview
TABLE prioridad, fase
FROM #tipo/feature
WHERE !fase
```
