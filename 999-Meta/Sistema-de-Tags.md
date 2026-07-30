---
tipo: meta
---

# Sistema de tags

Principio: **un tag por dimensión ortogonal, nunca combinaciones**. `#seguridad/alta` en vez de un único tag inventado `#bug-seguridad-critico`. Con dimensiones separadas, Dataview puede filtrar por cualquier cruce sin que el número de tags explote combinatoriamente — 6 dimensiones con 4-5 valores cada una dan cobertura total con ~30 tags, no con cientos.

Todas las dimensiones usan **namespace con `/`** (tags anidados de Obsidian), lo que además permite plegar la jerarquía en el panel de tags en vez de tener una lista plana de 30 líneas.

## Las 6 dimensiones (y solo estas 6)

### 1. `#estado/...` — dónde está el ciclo de vida
```
#estado/borrador
#estado/en-revision
#estado/aprobado
#estado/en-progreso
#estado/bloqueado
#estado/cerrado
#estado/superado       ← para ADR reemplazados por uno posterior
```

### 2. `#prioridad/...` — cuándo debe atenderse
```
#prioridad/p0    ← ahora mismo
#prioridad/p1    ← este sprint / esta fase
#prioridad/p2    ← próximo trimestre
#prioridad/p3    ← algún día
```
Deliberadamente P0-P3, no "alta/media/baja": un número ordena en Dataview sin mapeo adicional; una palabra no.

### 3. `#criticidad/...` — cuánto duele si se ignora (solo para Bugs e Incidentes)
```
#criticidad/critica    ← producción caída o dato corrupto
#criticidad/alta       ← funcionalidad rota, sin rodeo
#criticidad/media      ← rodeo existe
#criticidad/baja       ← cosmético
```
Distinta de prioridad a propósito: un bug puede ser `criticidad/alta` pero `prioridad/p2` porque afecta a una función que casi nadie usa todavía.

### 4. `#tipo/...` — qué género de nota es
```
#tipo/adr
#tipo/rfc
#tipo/bug
#tipo/incidente
#tipo/postmortem
#tipo/runbook
#tipo/release
#tipo/auditoria
#tipo/reunion
#tipo/investigacion
#tipo/feature
#tipo/tarea
#tipo/diario           ← añadido al instalar Daily Notes
#tipo/home             ← el dashboard, nota única
#tipo/puente           ← nota que enlaza a un fichero fuera del Vault (CLAUDE.md, Plan Maestro...), sin duplicar su contenido
#tipo/documentacion-tecnica
```
Redundante con la carpeta, y es intencional: permite una consulta Dataview única (`FROM #tipo/bug`) que funcione aunque alguien mueva la nota de carpeta por error. La carpeta es la organización física; el tag es la verdad lógica.

### 5. `#area/...` — qué parte del sistema toca
```
#area/backend
#area/frontend
#area/motor          ← app/engine/ — máxima cautela, ver CLAUDE.md §6.8
#area/infra
#area/datos
#area/seguridad
#area/legal
#area/producto
```

### 6. `#fase/...` — a qué fase del Plan Maestro pertenece
```
#fase/09
#fase/09-5
#fase/10
#fase/11
...
#fase/20
```
Numeración con guion para 9.5, no punto: Obsidian trata el punto en un tag como separador de jerarquía y `#fase/9.5` se rompería en `#fase/9` + `.5`.

## Lo que NO se etiqueta como tag

- **Personas y equipos** → van en `properties` (`asignado:: [[Nombre]]`), no en tag. Un tag `#equipo/backend` no permite preguntarle a Dataview "¿qué tiene asignado esta persona ahora mismo?" tan bien como una propiedad de tipo enlace.
- **Fechas** → nunca en tag. Van en `properties` (`fecha:: 2026-07-30`) o en el nombre de fichero. Un tag `#2026-07-30` no aporta nada que Dataview no saque ya del nombre de fichero o del frontmatter.
- **Relaciones entre notas** → nunca en tag. Eso es lo que son los `[[links]]` (Fase 5). Un tag no lleva contexto sobre *por qué* se relacionan dos notas; un link con texto alrededor sí.

## Ejemplo real, con las 6 dimensiones a la vez

```yaml
---
tipo: bug
tags:
  - tipo/bug
  - estado/en-progreso
  - prioridad/p2
  - criticidad/media
  - area/frontend
  - fase/10
---
```

Corresponde, por ejemplo, a la nota del hueco de `/auth/cambiar-password` sin interfaz: no bloquea nada hoy (`p2`), pero si nadie lo prioriza para la Fase 15 se queda perpetuamente en la deuda — de ahí que la relación real con «no tiene fase asignada» viva en un `[[link]]` a `70-Backlog/Features/feat-cambio-password-interfaz.md`, no en un tag.
