# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

Este proyecto **no versiona por SemVer**: versiona por **fases del Plan Maestro**
(`docs/SEIS_Plan_Maestro_Fases_920.md`), salvo entradas de infraestructura
transversal (como esta) que no pertenecen a ninguna fase concreta.

---

## [Infraestructura de conocimiento] — Obsidian como Vault del proyecto — 2026-07-30

Implantación de Obsidian sobre el propio repositorio como memoria permanente del proyecto. **No es una fase del Plan Maestro**; es infraestructura transversal de documentación.

### Añadido
- 20 carpetas numeradas en la raíz del repo (`00-Inbox` … `999-Meta`), el propio repositorio actúa como Vault — cero duplicación con `docs/`, `CLAUDE.md` ni `PENDIENTES.md`.
- 10 plugins de comunidad instalados desde release oficial de GitHub: Templater, Dataview, QuickAdd, Tasks, Obsidian Git, Metadata Menu, Tag Wrangler, Advanced Tables, Linter, Calendar.
- Daily Notes (núcleo) configurado con plantilla propia en `02-Diario/`.
- 15 plantillas Templater (ADR, RFC, Bug, Incidente, Postmortem, Runbook, Reunión, Investigación, Feature, Tarea, Checklist, Fase, Release, Auditoría, Diaria).
- 14 comandos QuickAdd para creación asistida de cada tipo de nota.
- Dashboard `01-Home/Home.md` con 10 consultas Dataview.
- Configuración de Graph View con filtros permanentes y agrupación por color según tipo de nota.
- Primer Canvas real: mapa de dependencias de las Fases 11-20 del Plan Maestro.
- Primer contenido real (no de ejemplo): 2 ADR, 2 notas de auditoría, 1 Runbook, 1 documento técnico, la nota de la Fase 10 y su deuda de backlog, todos enlazados entre sí.

### Corregido
- **Incompatibilidad de versión en Templater y QuickAdd.** Las últimas releases de GitHub de ambos plugins declaran `minAppVersion: 1.13.0`, que es la rama Beta/Insider de Obsidian, no la estable (confirmado contra el catálogo oficial `desktop-releases.json`: `latestVersion` estable es `1.12.7`). Se bajó a la última versión de cada plugin compatible con la rama estable: Templater `2.20.6` (`minAppVersion: 1.12.2`) y QuickAdd `2.12.3` (`minAppVersion: 1.11.4`).
- **Integración Daily Notes ↔ Templater.** El plugin nativo "Daily Notes" no invoca a Templater: copia el texto de la plantilla sin procesar la sintaxis `undefined`. Se resolvió activando la función "folder templates" de Templater (`enable_folder_templates` + `folder_templates: [{folder: "02-Diario", template: "..."}]`), que sí dispara el motor de Templater al crear un fichero en esa carpeta.
- **Cuatro notas con `tipo:` sin su tag `#tipo/x` correspondiente**, detectadas por auditoría estática (enlaces rotos, YAML, consistencia tag↔tipo, convención de nombres): `Home.md`, las tres notas-puente de `10-Proyecto/`, y `Arquitectura-de-tokens-jwt.md`.

### Estado de implantación
- Verificado en ejecución real (no solo por fichero): Dataview renderiza tablas, Templater procesa plantillas y dispara por carpeta en Daily Notes, Tasks reconoce casillas, QuickAdd registra sus 14 comandos, Calendar muestra panel y crea notas diarias, Canvas renderiza el mapa de fases sin nodos rotos.
- Auditoría estática posterior: 0 enlaces rotos, 0 YAML inválido, 100% de convención de nombres cumplida, 0 notas huérfanas reales tras la corrección de enlaces.
- Detalle completo en `999-Meta/Estado-de-Implantacion.md`.

### Pendiente
- Poblar `20-Arquitectura`, `50-Releases`, `110-Legal`, `120-Reuniones`, `140-Documentacion-Funcional` — vacías por ausencia legítima de material, no por omisión.
