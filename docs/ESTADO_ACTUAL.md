# SEIS — Estado actual del proyecto

> **Este documento es el índice de estado del proyecto.** Ninguna fase cierra su PR sin
> actualizar la tabla de «Frentes abiertos» de abajo. Nació como auditoría puntual el
> 2026-09-08; se quedó como índice porque en esa auditoría aparecieron **tres líneas de
> trabajo que ninguna sesión sabía que existían**, y la causa no fue mala suerte: no había
> ningún documento que dijera qué ramas y qué PRs estaban vivos.

---

## Frentes abiertos

**Actualizado:** 2026-09-10 · **`main`:** `5f14119` · **Suite:** 518 con PostgreSQL, 0 omitidos (en SQLite: 510 + 8 omitidos, los exclusivos de PG) · **E2E:** alta real verde (`e2e/correr.sh`)
**Última fase cerrada:** 16 (seguridad) · **Puerta: ABIERTA**

| Rama | PR | Estado | Qué contiene | Siguiente acción |
|---|---|---|---|---|
| `docs/fase-17c-comparables` | *(pendiente de abrir)* | 🟢 lista | Ficha de la Fase 17-C (comparables de mercado): solo planificación, sin código | Abrir PR |

Sin frentes abiertos de código.

### 🔴 Frente abierto de PRODUCTO, con dueño: el puente captación → análisis

**No existe.** `analisis_service.crear_analisis` **crea su propia fila `Subasta`**
a partir del `AnalisisInput`; no reutiliza ninguna captada. `POST /subastas`
(captación, con su scoring exprés) y `POST /analisis` (motor M01-M14) son dos
caminos que no se hablan.

**Consecuencia, y por eso es prioritario: BLOQUEA LA 17-B.** En cuanto la ingesta
automática del BOE empiece a producir subastas, serán subastas **que nadie podrá
analizar sin volver a teclear todos los datos a mano**. El caudal que la 17-A
existe para abrir desembocaría en un formulario de diez pasos.

**Dueña: la ficha de la Fase 17-B** (`PLAN_FASES.md`), que no cierra su PR sin
resolverlo — igual que ya no cierra sin decidir el modo de notificación por
defecto. No es una nota al pie: es condición de la fase.

Descubierto el 2026-09-10 recorriendo el flujo completo con un caso real de la
AEAT, no con una fixture.

### 🟡 Frente abierto de PRODUCTO, planificado: sin comparables, el motor se compara consigo mismo

En el mismo recorrido real (Santiponce, 44 m², tasada en 23.391,72 €) el motor devolvió
`VM = 23.391,72 € · método = sin_comparables · confianza = 0,0`: **el valor de mercado cayó al
valor del propio tasador de la AEAT.** El motor fue honesto —confianza 0, carencia en el ICI,
que se hundió a 20— pero no tenía ancla independiente.

**Es el caso por defecto de todo lo que entre por la 17-B**, porque nadie teclea seis
comparables por subasta cuando el conector traiga doscientas al mes.

**Registrado como fase propia: [Fase 17-C](PLAN_FASES.md) — «Fuente automática de comparables
de mercado»**, ordenada justo después de la 17-B. No se implementa todavía. La ficha lleva el
caso real como contexto motivador, cinco fuentes candidatas con coste y viabilidad legal
investigados, y las reglas no negociables (nunca inventar un comparable; trazabilidad por
comparable congelada en el snapshot, P1).

**Hallazgo colateral, INDEPENDIENTE y más urgente que la fase:** la base imponible del ITP es el
**mayor** de (valor de referencia, valor declarado, precio pagado), y SEIS lo calcula sobre la
puja (`m11_rentabilidad.py:41`). En una subasta —donde el atractivo es pujar por debajo del
valor— **eso subestima el impuesto en todo análisis que se haga hoy**. Sin dueño: pendiente de
decidir si se corrige por separado y antes.

**Fusionados:** [#12](https://github.com/christo23ch/seis/pull/12) Fase 17-A ·
[#13](https://github.com/christo23ch/seis/pull/13) puerta (a) ·
[#14](https://github.com/christo23ch/seis/pull/14) puerta (b) ·
[#15](https://github.com/christo23ch/seis/pull/15) Fase 14 ·
[#11](https://github.com/christo23ch/seis/pull/11) ADR-0010 y revisión visual ·
[#16](https://github.com/christo23ch/seis/pull/16) Fase 16 (auditoría, correcciones, ADR-0014) ·
[#17](https://github.com/christo23ch/seis/pull/17) M13 en operaciones inviables.

**La puerta está abierta:** (a) test de `init_db.main()` ✅ · (b) PostgreSQL en la CI ✅ ·
(c) regla de activación de la purga, no una tarea · (d) cerrada.

**Siguiente:** con la 16 cerrada, quedan 🟢 la Fase 0' (sistema de diseño) y la 15.

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
