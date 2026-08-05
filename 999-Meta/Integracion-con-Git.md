---
tipo: meta
---

# Integración con Git

## Decisión central: el Vault ES el repositorio, no un espejo de él

Ya justificado en la Fase 1 de la implantación. Consecuencia práctica: **no hay un segundo repositorio Git para el Vault**. Todo commit de una nota es un commit de `christo23ch/seis`, en la rama en la que se esté trabajando.

## Qué se versiona de `.obsidian/` y qué no

| Se versiona | Se ignora |
|---|---|
| `community-plugins.json` (qué plugins usa el equipo) | `workspace.json` (qué pestañas tenías abiertas tú) |
| `plugins/*/data.json` (config de cada plugin — plantillas de QuickAdd, reglas de Linter) | `cache/`, `.smart-env` (índices reconstruibles) |
| `snippets/`, `themes/` si se añaden | `plugins/*/data.json.bak` |
| `900-Plantillas/*.md` (son notas normales, no van en `.obsidian/`) | `.trash/` (papelera local de Obsidian) |

Regla de decisión rápida: **si el fichero determina el comportamiento que verá cualquiera que abra el Vault, se versiona. Si solo describe el estado de tu sesión de trabajo, se ignora.**

## Por qué Obsidian Git NO hace auto-commit ni auto-push

Configurado deliberadamente con `autoSaveInterval: 0`, `autoPushInterval: 0`. Dos motivos:

1. **Este proyecto trabaja por ramas de fase** (`fase-10-alta-self-service`, etc.), con el protocolo de `CLAUDE.md` §6.7: plan → aprobación → implementación → tests → PR revisado por humano. Un commit automático de una nota a medianoche mezclado en el historial de una rama de feature contamina el `git log` que un revisor necesita leer limpio.
2. **Evita condiciones de carrera con el propio trabajo de código.** Si Claude Code está a mitad de escribir una migración y Obsidian Git decide auto-commitear en ese instante, el commit de la nota queda intercalado entre commits de código no relacionados.

**Flujo real:** se edita el Vault con normalidad; al terminar una sesión de documentación, se ejecuta el commit desde Obsidian (icono de Git en la barra lateral, o `Ctrl+P` → "Git: Commit all changes") con el prefijo `vault:` que ya lleva configurado el mensaje por defecto — así un `git log --oneline | grep -v '^vault:'` separa historia de código de historia de documentación en un segundo.

## Convención de commits del Vault

```
vault: <qué cambió, en 3-6 palabras>
```

Ejemplos reales que se generarán con este Vault:

```
vault: RFC-0003 invalidación de sesiones tras reseteo
vault: postmortem INC-0001 cupo global de registro
vault: dashboard home con métricas de la Fase 11
```

Nunca se mezcla un commit `vault:` con cambios de código en el mismo commit — es lo que permite que la política de conflictos de abajo funcione.

## Sin conflictos: la regla de una sola rama activa para el Vault

El riesgo real no es Git en sí —Markdown es texto plano, se fusiona bien—, es que **dos personas editen la misma nota en ramas distintas simultáneamente**. Mitigación en tres capas:

1. **Las notas operativas** (Fases, ADR, Bugs, Incidentes) se editan siempre sobre `main` o sobre la rama de la fase en curso — nunca se crea una "rama de documentación" paralela, porque eso es exactamente la duplicación que se prohibió en la Fase 1.
2. **Pull antes de push, siempre** (`pullBeforePush: true` en la config de arriba). Un conflicto de merge en una nota Markdown se resuelve igual que en cualquier otro fichero de texto — Git lo marca con `<<<<<<<`, se edita a mano, se resuelve.
3. **`syncMethod: merge`**, no `rebase`. Se prioriza no reescribir historia sobre notas que otra persona pueda tener ya en su copia local — el mismo motivo por el que el resto del proyecto usa *fast-forward* y evita reescrituras de historia salvo decisión explícita.

## Backups

El propio historial de Git **es** el backup: cada commit `vault:` es una copia recuperable de todo el conocimiento hasta ese punto, con el mismo mecanismo de `git revert`/`git checkout <sha> -- ruta` que ya usa el resto del repositorio. No se añade un sistema de backup adicional (Fase 13 trata la escalabilidad a largo plazo; no hace falta una segunda copia paralela mientras exista `origin`).
