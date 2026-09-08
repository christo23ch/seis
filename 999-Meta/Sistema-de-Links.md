---
tipo: meta
---

# Sistema de links

## Regla de oro

**Toda nota que no sea una nota atómica de Inbox debe tener al menos un link entrante y uno saliente antes de considerarse terminada.** Una nota sin enlaces es indistinguible de una nota que no existe: nadie la encontrará salvo por búsqueda de texto, y el Graph View no la mostrará conectada a nada.

## Los cinco mecanismos y cuándo usar cada uno

### 1. `[[Wikilinks]]` — la relación por defecto

Uso: cualquier mención a otra nota del Vault. `[[ADR-0007-planificador-celery-separado-del-worker]]`.

**Con alias siempre que el nombre de fichero no fluya en la frase**: `[[ADR-0007-planificador-celery-separado-del-worker|el ADR del planificador separado del worker]]`. Un texto lleno de `[[nombres-de-fichero-en-kebab-case]]` sin alias es ilegible en 6 meses.

> Los ejemplos de esta nota van **entrecomillados como código a propósito**: aquí se enseña la sintaxis, y un enlace renderizado esconde precisamente lo que se quiere mostrar. El enlace vivo a ese ADR está en [[Fase-11-infraestructura]], que es donde toca.

### 2. Backlinks — no se escriben, se leen

No hay convención de escritura aquí; es el panel automático de Obsidian. La única disciplina necesaria es la de arriba (poner el link hacia adelante): los backlinks son gratis en cuanto el link directo existe.

**Uso operativo real:** antes de marcar un ADR como `#estado/superado`, revisar sus backlinks — si 6 notas de Bugs lo enlazan, superarlo sin avisar a esas 6 rompe la trazabilidad de por qué se tomó cada decisión que dependía de él.

### 3. Graph View — para descubrir, no para navegar a diario

Tratado en detalle en Fase 12. Regla de uso: si necesitas el Graph View para *ir* de una nota a otra en tu trabajo diario, es que falta un link explícito en alguna de las dos. El grafo es para preguntas del tipo "¿qué parte del Vault está huérfana?", no para navegación cotidiana.

### 4. Canvas — para relaciones que un link simple no expresa

Uso: cuando la relación entre notas **no es "A menciona a B"** sino algo espacial o secuencial — el flujo de una migración a través de sus tres entornos (SQLite → PostgreSQL real → producción), o el mapa de dependencias entre fases del Plan Maestro.

**No usar Canvas como sustituto de una nota.** Un Canvas que solo contiene texto libre sin nodos-nota debería ser una nota normal.

### 5. Properties (frontmatter) — para relaciones tipadas y consultables

Uso: cuando la relación debe ser filtrable por Dataview, no solo navegable a mano. Las siguientes propiedades son **obligatorias** en todo tipo de nota que las tenga aplicables:

```yaml
---
tipo: bug                          # una de las 12 de #tipo/, sin el prefijo tag
fase: "[[Fase-10-alta-self-service]]"   # link tipado a la fase, NO tag de fase
relacionado_con: "[[ADR-0007-...]]"     # 0 o más
supersede: "[[ADR-0003-...]]"           # solo si aplica
superado_por: ""                        # se rellena cuando deje de ser vigente
estado: en-progreso
prioridad: p2
---
```

**Por qué `fase` es una propiedad de tipo enlace y no un tag `#fase/10`, si ya existe ese tag en el sistema de tags:** ambos coexisten a propósito. El tag sirve para filtrar rápido ("todo lo de la Fase 10"); la propiedad sirve para que Dataview haga `JOIN`s reales — por ejemplo, listar en el dashboard de la Fase 10 todas las notas cuya propiedad `fase` apunte a ella, con una sola consulta, sin depender de que nadie haya escrito el tag correctamente en texto libre.

### 6. Embeds `![[...]]` — para transcluir, nunca para citar

Uso: cuando el contenido de una nota debe *aparecer* dentro de otra sin copiarlo — por ejemplo, embeber la sección de evidencia de una Auditoría dentro de la nota de la Fase, para que se actualice si la auditoría cambia. `![[2026-07-30-fase-10-auditoria-security-lead#Evidencia]]` embebe solo esa sección, no la nota entera.

**Prohibido embeber ficheros del proyecto que no son notas del Vault** (código fuente, `.py`, `.tsx`). Un embed de código se desincroniza en cuanto alguien edite el fichero real y Obsidian no lo sabrá. Para referenciar código: link a la ruta con formato `` `backend/app/api/auth.py:145` `` como texto plano, nunca embed.

## Aliases

Todo documento del proyecto que ya existía fuera de Obsidian (`CLAUDE.md`, `PENDIENTES.md`, el Plan Maestro) recibe, al crear su nota-puente en `10-Proyecto/`, un alias que permite enlazarlo por su nombre corto habitual:

```yaml
---
aliases:
  - Plan Maestro
  - Roadmap
---
```

para poder escribir `[[Plan Maestro]]` en vez de recordar el nombre de fichero completo cada vez.
