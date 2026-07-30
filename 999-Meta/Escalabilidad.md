---
tipo: meta
---

# Escalabilidad del Vault a varios años

## Dónde aparecen los límites reales de Obsidian, y cuándo llegan

| Límite | Umbral aproximado | Mitigación ya incorporada en este diseño |
|---|---|---|
| Rendimiento de Dataview con consultas `FROM ""` (todo el vault) | ~5.000-10.000 notas | Las plantillas de la Fase 6 nunca usan `FROM ""`; siempre `FROM #tipo/X`, que Dataview indexa por tag y es órdenes de magnitud más rápido que escanear rutas |
| Legibilidad del Graph View | Cientos de notas | Resuelto en Fase 12 con filtros permanentes + grafo local como flujo por defecto |
| Búsqueda nativa por texto | Decenas de miles de notas | Ver "Omnisearch diferido" abajo — es la palanca que se activa cuando este umbral se acerque, no antes |
| Un solo Vault gigante vs. varios Vaults enlazados | Sin límite duro, pero la navegación cruzada entre Vaults es peor que dentro de uno | Se mantiene un único Vault mientras el proyecto sea un solo repositorio; si SEIS se descompusiera en microservicios con repos separados, ahí sí se reconsideraría |

## Por qué NO se activa Omnisearch ya (revirtiendo la Fase 7)

Quedó diferido en la Fase 7 con la condición explícita "hasta que el Vault supere unos miles de notas". Activarlo antes añade un índice propio (basado en BM25) que consume CPU en cada arranque sin necesidad real todavía — con 47 notas hoy, la búsqueda nativa de Obsidian es instantánea. La condición de activación queda registrada aquí para que sea revisable objetivamente, no una intuición: **activar Omnisearch cuando `git ls-files "*.md" | wc -l` supere 3.000**, no antes.

## Disciplina de archivo, no de borrado

`990-Archivo/` (Fase 2) es la válvula de escape estructural: nada se borra nunca, todo lo obsoleto se mueve ahí. Es lo que evita que carpetas activas como `40-Fases` o `80-Bugs` degraden su relevancia con el tiempo — a los 3 años, `40-Fases` debería seguir teniendo únicamente las fases relevantes al trabajo actual y sus vecinas inmediatas, no las 20 fases completas del Plan Maestro amontonadas sin distinción entre "activa ahora mismo" y "cerrada hace dos años".

Regla operativa: una nota de Fase se archiva cuando **todas** sus dependientes (Releases, Auditorías, Bugs enlazados) llevan más de 6 meses cerradas. Se revisa manualmente cada trimestre, no de forma automática, porque decidir qué sigue siendo relevante requiere criterio humano.

## Convenciones que ya anticipan el crecimiento (referencia cruzada)

- **Numeración con huecos de 10** (Fase 2) — insertar categorías nuevas sin renumerar.
- **Numeración secuencial global de ADR/RFC/Bug/Incidente, nunca por fase** (Fase 3) — un ADR sigue siendo localizable por su número aunque el proyecto lleve 20 fases y el nombre de la fase original ya no diga nada a nadie.
- **6 dimensiones ortogonales de tags, no combinatorias** (Fase 4) — con ~30 tags totales el sistema cubre cualquier cruce futuro sin que la lista de tags crezca de forma descontrolada; el crecimiento del Vault añade *notas*, no *tags nuevos*.

## Lo que este diseño NO resuelve, y se declara explícitamente

- **Migración de plugins de comunidad abandonados** (como el caso ya descartado de Juggl en la Fase 7): un plugin activo hoy puede dejar de mantenerse en 3 años. No hay mitigación automática; la revisión trimestral de la sección anterior debe incluir "¿siguen actualizándose los 9 plugins instalados?".
- **Migración de formato si Obsidian desapareciera como producto**: mitigado solo parcialmente por el hecho de que todo es Markdown plano con YAML frontmatter — legible y portable sin la aplicación —, pero las consultas Dataview en bloques ` ```dataview ` dejarían de ejecutarse fuera de Obsidian. Riesgo aceptado, no resuelto, y coherente con el resto del stack del proyecto, que tampoco se blinda contra la desaparición de FastAPI o de PostgreSQL.
