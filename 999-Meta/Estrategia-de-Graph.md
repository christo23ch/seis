---
tipo: meta
---

# Estrategia de Graph View

## El problema por defecto

Con 47 ficheros ya creados hoy (33 carpetas + 14 plantillas) y un proyecto a años vista, el Graph View global se convierte en una maraña ilegible en cuanto el Vault supere unos pocos cientos de notas. Abrirlo "para ver qué hay" deja de aportar nada a partir de ese punto.

## Regla de uso: nunca el grafo global, siempre el grafo local filtrado

Obsidian permite dos vistas de grafo, y solo una es útil a largo plazo en este Vault:

- **Global (`Graph View`)**: se configura una vez con filtros permanentes (ver abajo) y se usa solo para preguntas de tipo "¿qué está desconectado del resto?", nunca para navegar.
- **Local (`Local Graph`, uno por nota)**: es el que se usa a diario, situado junto a cada nota mientras se edita, mostrando solo sus vecinos directos (1-2 saltos).

## Filtros permanentes del grafo global

Configurados para excluir del grafo por defecto:

1. `path:900-Plantillas` — las plantillas no son conocimiento, son moldes; incluirlas crea 14 nodos sin backlinks reales que ensucian cualquier lectura del grafo.
2. `path:999-Meta` — meta-documentación sobre el propio Vault, mismo motivo.
3. `path:00-Inbox` — notas de captura sin procesar, por definición todavía sin enlazar a nada; su ruido es máximo y su información mínima.

## Agrupación por color, no por carpeta

Colorear por **tag de `#tipo/`**, no por carpeta. Motivo: dos notas de tipos distintos pueden vivir en la misma carpeta temporalmente (una Feature recién creada en Backlog antes de que se le asigne subcarpeta), y el color por tag sigue siendo correcto aunque la organización física esté a medias. Grupos de color configurados:

| Color | Tag |
|---|---|
| Rojo | `#tipo/incidente` `#tipo/postmortem` |
| Naranja | `#tipo/bug` |
| Azul | `#tipo/adr` `#tipo/rfc` |
| Verde | `#tipo/fase` `#tipo/release` |
| Gris | `#tipo/runbook` |
| Amarillo | `#tipo/reunion` |

Así, con un vistazo al grafo local de cualquier Fase, se ve de inmediato si tiene incidentes (rojo) sin necesidad de leer texto.

## Qué preguntas debe poder responder el grafo — y cuáles no

**Sí, por diseño:**
- "¿Esta Fase tiene un Postmortem colgando sin ADR que lo explique?" — visible como nodo rojo aislado en el grafo local de la fase.
- "¿Qué ADR nunca se referenció desde ninguna Fase?" — nodo azul sin conexión en el grafo global filtrado.

**No, y no debe forzarse:**
- "¿Cuál es la arquitectura del sistema?" — para eso está `20-Arquitectura/Diagramas` con Mermaid, no el Graph View. El grafo muestra relaciones entre *notas*, no relaciones entre *componentes de software*; confundir ambas cosas es el error más común al adoptar Obsidian en un equipo técnico.

## Umbral de revisión

Si al llegar a ~500 notas el grafo global filtrado sigue siendo ilegible pese a los filtros anteriores, la acción correcta no es añadir más filtros: es que alguna carpeta ha crecido sin la disciplina de enlaces de la Fase 5 (notas huérfanas) y toca una limpieza dirigida, no un ajuste de la vista.
