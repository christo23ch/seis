---
tipo: meta
---

# Convención de nombres del Vault

Regla general: **fecha ISO al inicio cuando la nota es un evento en el tiempo** (ocurrió un día concreto); **slug descriptivo al inicio cuando la nota es una entidad permanente** (no expira). Sin esta distinción, el orden alfabético de la carpeta se vuelve inútil en menos de un año.

Todo en minúsculas con guiones, salvo el prefijo de tipo cuando lleva número (ADR, RFC, Fase), que va en mayúsculas por convención universal fuera de este proyecto también.

## Tabla

| Tipo | Patrón | Ejemplo real | Carpeta |
|---|---|---|---|
| Diario | `AAAA-MM-DD.md` (generado por el plugin Daily Notes, no manual) | `2026-07-30.md` | `02-Diario` |
| ADR | `ADR-NNNN-slug.md` | `ADR-0007-uso-unico-tokens-por-clave-primaria.md` | `30-Decisiones/ADR` |
| RFC | `RFC-NNNN-slug.md` | `RFC-0003-invalidacion-de-sesiones-tras-reseteo.md` | `30-Decisiones/RFC` |
| Fase | `Fase-NN[.N]-slug.md` | `Fase-10-alta-self-service.md` | `40-Fases` |
| Release | `AAAA-MM-DD-fase-NN-vX.md` | `2026-07-29-fase-10-v1.md` | `50-Releases` |
| Auditoría | `AAAA-MM-DD-fase-NN-auditoria-rol.md` | `2026-07-30-fase-10-auditoria-security-lead.md` | `60-Auditorias` |
| Feature (backlog) | `feat-slug.md` | `feat-cambio-password-interfaz.md` | `70-Backlog/Features` |
| Tarea | `tarea-slug.md` | `tarea-purgar-token-consumido.md` | `70-Backlog/Tareas` |
| Bug | `BUG-NNNN-slug.md` | `BUG-0002-cambiar-password-sin-interfaz.md` | `80-Bugs` |
| Investigación | `AAAA-MM-DD-slug.md` | `2026-07-15-comparativa-oauth-providers.md` | `90-Investigacion` |
| Runbook | `runbook-slug.md` (sin fecha: es atemporal, se actualiza in situ) | `runbook-rotar-jwt-secret.md` | `100-Operacion/Runbooks` |
| Incidente | `INC-NNNN-AAAA-MM-DD-slug.md` | `INC-0001-2026-08-02-cupo-global-registro.md` | `100-Operacion/Incidentes` |
| Postmortem | `PM-NNNN-slug.md` (referencia al INC-NNNN correspondiente en el frontmatter) | `PM-0001-cupo-global-registro.md` | `100-Operacion/Postmortems` |
| Despliegue | `AAAA-MM-DD-HHmm-deploy-slug.md` | `2026-07-30-1830-deploy-fase-10.md` | `100-Operacion/Despliegues` |
| Meeting Note | `AAAA-MM-DD-slug.md` | `2026-07-30-revision-fase-10.md` | `120-Reuniones` |
| Doc técnico | `slug.md` (permanente, sin fecha ni número — vive por versión, no por revisión temporal) | `motor-experto-dag-pipeline.md` | `130-Documentacion-Tecnica` |
| Doc funcional | `slug.md` | `perfil-inversion-flip-integral.md` | `140-Documentacion-Funcional` |

## Reglas transversales

1. **Numeración de ADR, RFC, Bug e Incidente es secuencial y global, nunca por carpeta ni por fase.** `ADR-0007` es el séptimo ADR de la historia del proyecto, no el séptimo de la Fase 10. Consulta `999-Meta/contador-secuencias.md` antes de asignar el siguiente número — lo gestiona QuickAdd (Fase 8), no a mano.
2. **El slug nunca repite el tipo.** `ADR-0007-decision-uso-unico-tokens.md` está mal: la palabra "decisión" ya la aporta "ADR".
3. **Las fechas de eventos usan la fecha del evento, no la de creación de la nota.** Una reunión del 28 de julio documentada el 30 se llama `2026-07-28-...md`.
4. **Ningún título de nota repite el nombre de fichero en el `# H1`.** El nombre de fichero es la clave técnica; el `H1` es el título legible y puede cambiar sin romper enlaces (Obsidian actualiza los `[[wikilinks]]` automáticamente al renombrar el fichero, no al cambiar el `H1`).
