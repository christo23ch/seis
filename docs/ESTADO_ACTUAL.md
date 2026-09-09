# SEIS — Estado actual del proyecto

> **Este documento es el índice de estado del proyecto.** Ninguna fase cierra su PR sin
> actualizar la tabla de «Frentes abiertos» de abajo. Nació como auditoría puntual el
> 2026-09-08; se quedó como índice porque en esa auditoría aparecieron **tres líneas de
> trabajo que ninguna sesión sabía que existían**, y la causa no fue mala suerte: no había
> ningún documento que dijera qué ramas y qué PRs estaban vivos.

---

## Frentes abiertos

**Actualizado:** 2026-09-09 · **`main`:** `cc5b782` · **Suite:** 444 passed, 1 skipped
**Última fase cerrada:** 11-A (infraestructura, parte agnóstica del proveedor)

| Rama | PR | Estado | Qué contiene | Siguiente acción |
|---|---|---|---|---|
| `docs/adr-diseno-y-revision-visual` | [#11](https://github.com/christo23ch/seis/pull/11) | 🟡 en revisión | ADR-0010 (UI propia), flujo de capturas repetible, puerta de la deuda | Fusionar |
| `fase-17a-captacion` | [#12](https://github.com/christo23ch/seis/pull/12) | 🟡 en revisión | Fase 17-A: andamiaje de captación (contratos, parser BOE, ingesta, dedupe 0007, vigilancia, ADR-0011) | Fusionar |

**Fusionados desde la última actualización:** #5 (este documento), #8 (plan de fases),
#9 (guion bajo en el PDF), #10 (avisos del README). Las ocho ramas muertas quedaron
borradas desde la web el 2026-09-08; no queda ninguna rama zombi en el remoto.

---

## 1 · Cómo se resolvió la divergencia de ramas

Queda escrito porque es el motivo de que este documento exista.

Había **tres** líneas de trabajo simultáneas y mutuamente desconocidas:

| Línea | Qué era | Desenlace |
|---|---|---|
| `main` | Fases 9, 9.5, 10 y 12 | Base de todo |
| `claude/wizardly-wright-nkscpg` | Una **segunda Fase 10** + una Fase 11 rudimentaria | **Descartada.** Su registro respondía 400 ante email duplicado, convirtiendo `/auth/registro` en un oráculo de enumeración de cuentas; el de `main` responde 201 idéntico |
| `fase-11-infraestructura` (PR #4) | **Fase 11-A completa**, 7.000 líneas, un mes abierta | **Fusionada.** Estaba bloqueada por un solo test rojo |

El test rojo de la 11-A merece recordarse: afirmaba `entorno == "development"` dando por hecho
que la suite corre sin `SEIS_ENV`, cierto en local y falso en la CI, que corre con
`SEIS_ENV=test`. Se corrigió el test —no el workflow—, porque quitar la variable habría
adaptado el entorno real al test y habría dejado sin ejercitar la normalización de entornos que
esa misma fase introducía.

---

## 2 · Inventario por fases

| Fase | Estado | Evidencia |
|---|---|---|
| **1-8** · Motor experto | ✅ | `engine/modules/m01…m14` + `scoring_expres.py`. 30 tests de regresión (`test_golden_caso19` 14, `test_precios` 9, `test_vetos` 7) |
| **9** · Multi-tenancy | ✅ | `Organizacion`, scoping por `organizacion_id`, `require_superadmin`/`require_propietario`. 10 tests + 5 añadidos después (ver §3) |
| **9.5** · Migraciones | ✅ | `0005_esquema_base` + `0006_self_service`, ambas con `downgrade`. 13 tests. CI propia |
| **10** · Alta self-service | ✅ | `registro_service.py`, 6 endpoints públicos, `TokenConsumido`. 45 + 38 tests |
| **11-A** · Infraestructura (agnóstica) | ✅ | Sondas separadas (`salud.py`), staging estricto, `red.py`, purga, beat separado, CI completa. 7 ADRs |
| **11-B** · Despliegue real | ⬜ | Sin `render.yaml` ni runbook en `main`. Semilla en el PR #6 cerrado |
| **12** · Notificaciones + scoring | ✅ | `Alerta`, `Notificacion`, `notificadores/`, matcher, digest. 18 tests |
| **13** · Stripe | 📋 | `FASE_13_PLAN_EJECUCION.md` y su mapa de impacto. Cero código |
| **14** · RGPD | ⬜ | Sin consentimientos, export ni borrado de cuenta |
| **15** · Landing | ⬜ | La raíz `/` sigue bajo `(app)`, protegida |
| **16** · Seguridad | ⬜ | Sin `AUDITORIA_SEGURIDAD.md`; rate limiting solo en auth |
| **17** · Captación real | ⬜ | **No existe `app/ingesta/`.** `api/captacion.py` es un POST manual |
| **18-20** | ⬜ | — |

**Cifras medidas:** 43 endpoints · 19 ficheros de test · `backend/app` 6.719 líneas ·
`backend/tests` 5.564 (ratio 0,83) · frontend 3.292 líneas **con cero tests**.

---

## 3 · Aislamiento multi-tenant

Los **nueve** endpoints que devuelven o crean datos de análisis filtran por
`organizacion_id`. Recurso ajeno = **404**, nunca 403.

| Endpoint | Filtra |
|---|---|
| `POST /analisis` · `/analisis/async` | ✅ sella el tenant |
| `POST /analisis/simular` | ✅ no persiste ni lee |
| `GET /analisis` · `/{id}` · `/informe` · `/informe.pdf` · `/checklist` | ✅ |
| `GET /tareas/{tarea_id}` | ✅ **corregido** — antes no comprobaba nada |

**Lo que estaba mal y ya no:**

- `GET /tareas/{tarea_id}` devolvía el resultado de cualquier tarea a cualquier usuario
  autenticado: quien conociera un `tarea_id` ajeno obtenía el id del análisis y su semáforo.
  Ahora comprueba la organización y responde 404. El texto de la excepción de una tarea
  fallida tampoco se propaga.
- El filtro era ***fail-open***: `if organizacion_id is not None`. Como la columna es nullable,
  un usuario sin organización habría visto los análisis de todas. Ahora el parámetro es
  obligatorio y sin tenant no se devuelve nada.

**Correcto por diseño:** `GET /captacion` no filtra — las subastas son corpus compartido
(CLAUDE.md §4). Alertas y notificaciones son privadas **por usuario**, y lo cumplen.

---

## 4 · Deuda técnica

### Cubierta desde la auditoría
- ~~CVE crítica en `next@15.1.6`~~ → 15.5.25. De 4 vulnerabilidades de producción (1 crítica) a 2.
- ~~La CI ejecutaba 13 de 162 tests~~ → ejecuta la suite completa y el build del frontend.
- ~~`GET /tareas` sin aislamiento~~ y ~~filtro *fail-open*~~ → cerrados, con tests.

### Abierta

**Huecos de cobertura** (documentados por la propia Fase 11-A; ninguno bloqueaba su fusión):

1. **`init_db.main()` no lo ejecuta ningún test.** El más peligroso: sin `create_all` en
   staging y producción, una mutación plausible deja la instalación **sin reglas, sin
   parámetros y sin administrador**, y no se detecta hasta el despliegue.
2. **La CI no levanta PostgreSQL.** Tres caminos exclusivos de ese motor no se ejecutan en
   ninguna parte: `SET LOCAL statement_timeout`, `with_for_update(skip_locked=True)` y un
   rollback silencioso.
3. **La purga en modo `borrar` nunca ha corrido por la ruta de la tarea.** Nace desactivada
   (`informar`); el día que se active, se estrenaría a las 04:30 en producción.
4. **`/health/listo` sin límite de tasa.**

**Otra deuda:**
- Frontend: **cero tests** (3.292 líneas) y **cero linting** (sin configuración de ESLint y con
  `eslint.ignoreDuringBuilds: true`). Lo único que lo protege es el chequeo de tipos de `next build`.
- 2 vulnerabilidades de producción restantes: el `postcss@8.4.31` que Next fija internamente.
  Forzar un `overrides` arriesga el build para un vector nulo en tiempo de compilación.
- `models.py`: `UniqueConstraint` importado y **nunca aplicado** a ninguna tabla. Lo necesitará
  el dedupe de la Fase 17.
- Cero TODO/FIXME en el código. Las dos migraciones tienen `downgrade` y cubren las 22 tablas.

---

## 5 · Discrepancias con las suposiciones de partida

1. **No se usa shadcn/ui.** Toda la UI es artesanal y vive en un único `components/ui.tsx`.
   La decisión de adoptarlo o consolidar el sistema propio se evalúa en `docs/HERRAMIENTAS.md`.
2. **PostGIS está aprovisionado pero no se usa.** `docker-compose` levanta `postgis/postgis`,
   pero el esquema guarda `lat`/`lng` como `Numeric(9,6)`. No hay ninguna columna `geometry`.
3. **El vault de Obsidian existe** y está en la raíz del repositorio: 38 notas, 15 plantillas y
   **9 ADRs** (los 7 de la Fase 11-A más los 2 previos).

---

## 6 · Avance estimado

**~70 % del código · ~55 % del camino hasta el primer cliente de pago.**

Sube desde el 60/50 de la auditoría inicial, que se hizo sin conocer la Fase 11-A.

A favor: el motor está blindado; el aislamiento multi-tenant es correcto en los nueve
endpoints; hay 402 tests con ratio test:código de 0,83 en backend; y la infraestructura
agnóstica del proveedor está resuelta y documentada con ADRs.

En contra, y por este orden:
- **El producto todavía no puede cumplir su promesa.** Sin conector de ingesta (Fase 17), las
  alertas de la Fase 12 vigilan un caudal que no existe: las subastas solo entran tecleadas.
- **No hay nada desplegado.** La 11-A dejó el repositorio listo; falta la 11-B y el hosting.
- **No se puede cobrar** (Fase 13) ni **operar legalmente con datos reales** (Fase 14).
- El frontend sigue siendo la capa menos protegida y la única que ve el cliente.
