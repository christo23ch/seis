# PLAN DE REPARACIÓN — Cadena de migraciones Alembic

**Fecha:** 2026-07-26
**Versión:** 2.1 — estrategia cerrada, **procedimiento de generación validado empíricamente**
**Plan de ejecución:** [`FASE_95_PLAN_EJECUCION.md`](FASE_95_PLAN_EJECUCION.md) — documento canónico
de la fase. Este documento es el **diseño**; aquel es el **cómo se ejecuta**. En caso de conflicto
operativo, manda el plan de ejecución.

> **Cambios de la 2.1** (validación empírica de 2026-07-26): §3.3 sustituye el procedimiento de
> generación, que abortaba de forma determinista · paso 2 de §7 actualizado · **R-D1 descartado**
> como riesgo, reclasificado de Alta a Baja y de contención a confirmación.
**Comité:** Migration Architecture Committee
**Estado:** Diseño definitivo. **Sin código, sin parches, sin cambios en el repositorio.**
**Insumo:** verificación experimental del Release Committee (2026-07-26)
**Decisión rectora Q1** *(identificada como **E1** en el plan de ejecución; misma decisión)*:
*«No existe ninguna base de datos que deba preservarse. Se acepta romper
compatibilidad con instalaciones de desarrollo existentes.»* — responsable del proyecto, 2026-07-26
**Bloquea a:** Fase 10 y Fase 13

---

## 1 · Situación verificada

`alembic upgrade head` **no funciona sobre una base de datos limpia**. Comprobado
experimentalmente, no inferido.

| Revisión | Sobre BD nueva | Error |
|---|---|---|
| `0001_esquema_inicial` | ✅ aplica | — |
| `0002_multitenancy` | ❌ **falla** | `IntegrityError: NOT NULL constraint failed: organizacion.creado_en` |
| `0003_notificaciones` | ⚠️ inalcanzable | la cadena se detiene en 0002 |
| `0004_ampliar_auditoria_quien` | ❌ **falla** (aislada) | `OperationalError: near "ALTER": syntax error` |

**Alcance real:** `docker-compose.yml:56` arranca el backend con
`sh -c "alembic upgrade head && python -m scripts.init_db && uvicorn ..."`. El `&&` corta en el
primer fallo, así que **el contenedor no arranca sobre un volumen limpio**, en ningún motor. El
procedimiento de puesta en marcha de `CLAUDE.md` §7 no funciona hoy en una máquina nueva.

**Por qué no se detectó:** `backend/tests/conftest.py:64` construye el esquema con
`Base.metadata.create_all(engine)`. La suite de 104 tests **no invoca Alembic en ningún punto**.
Migraciones y tests son dos caminos disjuntos hacia dos esquemas que nadie ha comparado nunca.

---

## 2 · Causa raíz

### El diseño era deliberado, y está documentado

`0002_multitenancy.py:11-15` declara el contrato:

> *«Idempotente por diseño: la revisión fundacional 0001 crea el esquema con
> `Base.metadata.create_all`, de modo que en una BD nueva las columnas/tablas ya existen cuando
> corre esta migración. Por eso cada paso comprueba el estado real del esquema (inspector) antes
> de actuar.»*

### Dónde se rompe

El contrato cubre la **DDL** pero no la **DML**, y la 0002 tiene ambas:

```
0002:41   if not _tiene_tabla(inspector, "organizacion"):        ← DDL guardada
0002:42-48     op.create_table(... creado_en server_default=now() ...)
0002:71-73   INSERT INTO organizacion (id, nombre) VALUES (...)  ← DML NO guardada
```

Sobre BD nueva la rama de la línea 41 no se toma —la tabla ya existe, creada por la 0001—, de modo
que la **única** declaración de `server_default` nunca se ejecuta. El `INSERT` de la línea 71 omite
entonces `creado_en`, que en el esquema realmente vigente es `NOT NULL` sin default.

**La causa es DDL idempotente combinada con DML que asume la rama no tomada.**

### La exposición es sistémica

| Medición sobre `backend/app/models.py` | Valor |
|---|---|
| Columnas con `default=_now` (lado Python) | **7** |
| Columnas con `default=_uuid` (lado Python) | **9** |
| Columnas con `server_default` | **0** |
| Tablas declaradas | 21 |

`models.py` no usa `server_default` en ninguna parte. **Toda DML cruda futura contra una tabla
materializada por `create_all` reincidirá.** La 0002 es el primer caso, no un caso aislado.

### La 0004 es un problema ortogonal

SQLite no implementa `ALTER TABLE ... ALTER COLUMN`. **`render_as_batch=True` NO lo resuelve** —
verificado en cuatro escenarios:

| Escenario | Resultado |
|---|---|
| `alter_column` directo | FALLO |
| `alter_column` + `render_as_batch=True` | **FALLO** |
| `op.batch_alter_table()` explícito | OK |
| `batch_alter_table` + `render_as_batch=True` | OK |

`render_as_batch` es opción de **autogenerate**: hace que Alembic *escriba* bloques batch al
**generar** ficheros nuevos. No envuelve en ejecución una llamada ya escrita. Valor **preventivo**,
nunca correctivo. *(Se deja constancia porque la intuición contraria ya indujo a error una vez en
este proyecto.)*

### Corolario: toda revisión posterior a la 0001 es un no-op sobre BD nueva

La DDL real de la 0001 ya contiene `quien VARCHAR(120)`, porque `models.py` refleja el estado
post-Fase 12. La 0004 ampliaría de 120 a 120. **Un `upgrade head` en verde no probaría lo que
aparenta probar** — y eso afectaría igual a la migración de la Fase 10 y a la de la Fase 13.

---

## 3 · Estrategia elegida — Alternativa B: revisión fundacional limpia

> **Nota de nomenclatura.** Una versión anterior de este documento enumeraba cuatro opciones (A-D) y
> llamaba **«Alternativa D»** a esta misma estrategia. El Architecture Review Board reformuló después
> la decisión a dos alternativas —A (mantener la historia y reparar) y **B (revisión fundacional
> limpia)**—, y esa es la nomenclatura vigente en todo el proyecto. **«Alternativa D» y «Alternativa
> B» designan la misma decisión.** Los códigos de riesgo `R-D1…R-D8` (§10) conservan el prefijo
> histórico para no romper las referencias existentes.

Con Q1 respondida, la decisión queda cerrada. **Se sustituyen las cuatro revisiones existentes por
una sola revisión fundacional con DDL explícita del esquema actual completo (21 tablas).**

Se descarta la reparación incremental (congelar la 0001, corregir la DML de la 0002, pasar la 0004
a modo batch): resolvía el mismo problema a mayor coste, exigía reconstruir por arqueología de git
el esquema de las Fases 1-2, y su único beneficio —preservar el camino de actualización desde
instalaciones históricas— carece de destinatario.

### 3.1 · Qué se elimina y qué se conserva

| Artefacto | Destino |
|---|---|
| `alembic/versions/0001_esquema_inicial.py` | **Eliminar** |
| `alembic/versions/0002_multitenancy.py` | **Eliminar** |
| `alembic/versions/0003_notificaciones.py` | **Eliminar** |
| `alembic/versions/0004_ampliar_auditoria_quien.py` | **Eliminar** |
| Revisión fundacional nueva | **Crear**, con DDL explícita, `down_revision = None` |
| `scripts/init_db.py` (`create_all`) | **Conservar** — siembra datos, no esquema. Aclarar su papel |
| `tests/conftest.py:64` (`create_all`) | **Conservar** — más el test de deriva de §5 |

El contenido de las cuatro revisiones **no se pierde**: queda en el historial de git. Lo que se
pierde es el **camino de ejecución** desde instalaciones antiguas, que es precisamente lo que Q1
autoriza a sacrificar.

### 3.2 · Numeración: continuar en `0005`, no reutilizar `0001`

**Decisión: la revisión fundacional se numera `0005`, con `down_revision = None`.**

Es contraintuitivo y por eso se justifica. Reutilizar el identificador `0001` introduce un **fallo
silencioso**:

| Estado de una BD de desarrollo | Si la fundacional es `0001` | Si la fundacional es `0005` |
|---|---|---|
| Stampeada en `0002`/`0003`/`0004` | Error ruidoso: *«Can't locate revision»* ✅ | Error ruidoso ✅ |
| **Stampeada en `0001`** | **Alembic la considera al día.** `upgrade head` no hace nada y el esquema antiguo y parcial queda en pie, aparentando estar correcto ⚠️ | Error ruidoso ✅ |

El segundo caso no es hipotético: **cualquier BD que haya fallado al aplicar la 0002 quedó
stampeada exactamente en `0001`** — incluida la que este comité creó al verificar. Numerar desde
`0005` hace que **toda** BD preexistente falle de forma ruidosa, que es el comportamiento correcto
cuando la compatibilidad se rompe a propósito.

**Renumeración resultante de la cadena:**

```
0005_esquema_base   (fundacional, down_revision = None)
  └── 0006          Fase 10 — alta self-service
        └── 0007    Fase 13 — facturación y suscripciones
```

> **Propagación pendiente.** Esto deroga dos decisiones ya tomadas y documentadas:
> `docs/PENDIENTES.md` reserva la `0005` para la Fase 10, y
> `docs/FASE_13_PLAN_EJECUCION.md` §12-Q1 fijó la `0006` para la Fase 13 con
> `down_revision = "0005"`. Ambas pasan a **`0006`** y **`0007`**. Ver §9.

### 3.3 · Cómo se produce la DDL explícita

**No se escribe a mano.** 21 tablas escritas a mano es trabajo mecánico con alta probabilidad de
omisión silenciosa de un índice o una clave foránea.

> **Procedimiento corregido tras validación empírica (2026-07-26).** La redacción anterior
> —«`alembic revision --autogenerate` contra una base de datos vacía»— **aborta de forma
> determinista**: con las revisiones 0001-0004 presentes, Alembic compara la revisión de la base
> contra las cabezas del directorio de scripts y lanza
> `CommandError: Target database is not up to date.` (`alembic/autogenerate/api.py:605-608`).
> Ninguna combinación de `--head=base`, `--splice` ni `--version-path` lo evita: esos flags
> determinan dónde se engancha la revisión nueva, no qué ve Alembic.

**Procedimiento válido:** `alembic revision --autogenerate` con un **`alembic.ini` desechable fuera
del repositorio** cuyo `version_locations` apunte a un **directorio vacío**. Con cabezas `= ∅` y
base vacía, los conjuntos coinciden, la generación procede y **`down_revision = None` sale de forma
nativa**. Las revisiones antiguas permanecen intactas: no se tocan, solo no se miran durante la
generación. **Quedan dos correcciones manuales, no una:** fijar el identificador de revisión a
`0005` —autogenerate asigna un hexadecimal aleatorio— **y renombrar el fichero generado** a
`0005_esquema_base.py`, porque `alembic.ini` no define `file_template` y el fichero nace también con
el hexadecimal en el nombre.

*(Se descarta `stamp head`, que también funciona: exige escribir un estado falso en
`alembic_version` y produce `down_revision = '0004'`, añadiendo un paso manual cuyo olvido deja la
revisión colgando de una cadena que el Bloque D va a borrar. Detalle en
[`FASE_95_PLAN_EJECUCION.md`](FASE_95_PLAN_EJECUCION.md) §4, Bloque B.)*

Sigue siendo obligatoria la **revisión manual** posterior, que debe verificar, como mínimo:

- **`PortableJSON` — riesgo descartado empíricamente, comprobación conservada.** `app/core/db.py:11`
  define `JSON().with_variant(JSONB(), "postgresql")`. Se temía que autogenerate lo aplanara a
  `sa.JSON()`; **la ejecución real demuestra que preserva la variante en las 19 columnas**
  (`sa.JSON().with_variant(postgresql.JSONB(astext_type=Text()), 'postgresql')`, 19 de 19). La
  verificación se mantiene como confirmación, no como contención. Ver R-D1.
- Índices y claves foráneas: presencia y nombre.
- Los 7 `default=_now` y 9 `default=_uuid`: **no** aparecerán como `server_default`, y es correcto
  que no aparezcan — pero debe ser una omisión consciente, no una sorpresa (ver R-D4).
- Tipos con semántica de motor: `DateTime(timezone=True)`, `Numeric(9,6)` de `lat`/`lng`,
  `SmallInteger`.
- El `downgrade` debe eliminar las 21 tablas en orden inverso de dependencias.

La revisión manual no es opcional: es donde se cobra el coste que la Alternativa B ahorra en
arqueología.

### 3.4 · Qué NO resuelve esta estrategia

Conviene decirlo explícitamente para que no se dé por cerrado lo que sigue abierto:

- **RM1 sigue vivo.** Las 7 columnas con default de lado Python siguen ahí. La revisión fundacional
  no hace DML, así que no le afecta — pero **el backfill de la Fase 10 y el de la Fase 13 sí están
  expuestos**. La barrera es la convención de §6, no esta reparación.
- **RM3 sigue vivo.** El primer `ALTER COLUMN` futuro reincidirá en SQLite si no usa modo batch.
  `Auditoria.entidad_id` (`String(36)`, insuficiente para ids de Stripe de ~66-70 caracteres) es el
  próximo caso conocido.

---

## 4 · Procedimiento de recreación de entornos de desarrollo

> **Este procedimiento destruye datos de desarrollo. Es su propósito.** Q1 lo autoriza
> explícitamente. Debe ejecutarlo cada persona con un entorno local, una sola vez, tras fusionar la
> reparación.

### 4.1 · Entorno local con SQLite

La base por defecto es `sqlite:///./seis_dev.db` (`app/core/config.py:12`), relativa al directorio
desde el que se ejecuta. Puede haber más de un fichero `.db` disperso si se han lanzado comandos
desde directorios distintos.

1. Localizar **todos** los ficheros `.db` bajo `backend/` y eliminarlos.
2. Ejecutar `alembic upgrade head`.
3. Verificar con `alembic current` que muestra la revisión fundacional nueva.

**Si por cualquier motivo hay que conservar el fichero:** no basta con re-ejecutar `upgrade`. Hay
que eliminar además la tabla `alembic_version`, o el stamp antiguo hará que Alembic falle al no
localizar la revisión. Recrear es más rápido y más seguro que reparar el stamp.

### 4.2 · Entorno Docker

El backend ejecuta las migraciones al arrancar (`docker-compose.yml:56`), de modo que un volumen
con datos antiguos hará fallar el contenedor de forma ruidosa —comportamiento deseado—.

1. `docker compose down -v` — **la bandera `-v` destruye el volumen de PostgreSQL.** Sin ella el
   volumen sobrevive y el contenedor seguirá fallando.
2. `docker compose up -d --build`.
3. Comprobar que el backend responde en `/api/v1/health`.

### 4.3 · Suite de tests

**No requiere acción.** `conftest.py:64` construye el esquema con `create_all` sobre una base
efímera por módulo; no consulta `alembic_version` ni depende de la cadena. La suite seguía en verde
con las migraciones rotas, y seguirá en verde tras la reparación — motivo por el cual, a partir de
ahora, **deja de ser evidencia suficiente** (§5).

### 4.4 · Síntomas esperados y su lectura

| Síntoma | Significado | Acción |
|---|---|---|
| `Can't locate revision identified by '0004'` | La BD es anterior a la reparación. **Es el fallo ruidoso buscado** | §4.1 o §4.2 |
| El contenedor del backend arranca y muere | Volumen antiguo. `down` sin `-v` | §4.2, con `-v` |
| `alembic current` vacío | BD sin stampear, previa a cualquier migración | `upgrade head` directamente |
| `alembic current` muestra `0001` | BD que falló al aplicar la 0002 | §4.1 |
| Tests verdes, aplicación rota | Esperado con el esquema antiguo: los tests no pasan por Alembic | §4.1 |

---

## 5 · Batería de tests que ejecuta Alembic de verdad

Fichero nuevo `backend/tests/test_migraciones.py`. **No existe hoy**, y su ausencia es la razón de
que este defecto llegara hasta aquí.

| # | Test | Qué demuestra |
|---|---|---|
| **T1** | `upgrade head` desde BD vacía | Que la cadena aplica. **Es el test que hoy fallaría** |
| **T2** | `downgrade base` tras T1 | Que la cadena es reversible |
| **T3** | Ida y vuelta por revisión (`upgrade`/`downgrade` de cada par consecutivo) | Que ninguna revisión intermedia está rota. *Trivial mientras solo haya la fundacional; imprescindible en cuanto entren `0006` y `0007`* |
| **T4** | **Deriva:** comparar el esquema de `upgrade head` con el de `Base.metadata.create_all` — tablas, columnas, tipos, nulabilidad, índices | **El test que impide la recurrencia** |
| **T5** | Marcado `@pytest.mark.postgres`, omitido sin `DATABASE_URL` de PostgreSQL: T1+T2+T4 contra PostgreSQL real | Cubre lo que SQLite no puede ejercitar, **incluida la variante JSONB (R-D1)** |
| **T6** | Idempotencia: aplicar `upgrade` sobre un esquema que ya contiene la revisión no lanza | Que las guardas siguen cumpliendo su función *(aplicable a `0006`/`0007`, no a la fundacional)* |

*(La batería de la v1.0 tenía un T3 de «instalación histórica» que desaparece: bajo la
Alternativa B no existe tal escenario.)*

### T4 es la pieza central

Es el único test que detecta la **causa** y no el síntoma. En el momento en que `Organizacion`
entró en `models.py` sin que la 0001 dejara de crearla, T4 habría fallado. Todos los demás detectan
consecuencias.

**T4 debe demostrarse capaz de fallar.** Un test de deriva que nunca ha fallado no es prueba de
nada: hay que introducir una divergencia deliberada, verla en rojo, y revertirla. Está en los
criterios de aceptación (§7).

**Dependencia ya resuelta:** `pytest-cov>=5.0` figura en `requirements-dev.txt`, de modo que el
umbral de cobertura no requiere herramienta nueva. *(Cierra de paso un punto que el plan de la Fase
13 dejaba por confirmar.)*

---

## 6 · Cómo impedir que vuelva a ocurrir

### Barrera 1 — T4 (deriva) en CI

La única que ataca la causa. Compara el esquema migrado con el de `create_all` y falla si divergen.

### Barrera 2 — Dos convenciones nuevas en `CLAUDE.md` §6

1. **Prohibido `Base.metadata` dentro de `alembic/versions/`.** Una migración describe una
   transición entre dos estados conocidos; no puede depender del modelo vivo, que cambia bajo sus
   pies. Verificable con una búsqueda simple, y por tanto automatizable.
2. **Toda DML de migración especifica explícitamente cada columna `NOT NULL`**, sin apoyarse en
   defaults del servidor ni del ORM. **Es la regla que cubre RM1**, que esta reparación no elimina.

Complemento de bajo coste: añadir `render_as_batch=True` a `env.py`. **No repara nada** (§2); hace
que las migraciones *autogeneradas en el futuro* emitan bloques batch, reduciendo la probabilidad
de reincidir en RM3. **Debe documentarse con esa precisión exacta**, o volverá a leerse como el
arreglo que no es.

### Barrera 3 — Definición de «hecho» para toda migración

Ninguna migración se considera terminada sin `upgrade` y `downgrade` verdes en **SQLite y
PostgreSQL**. La batería de §5 lo convierte en ejecutable en vez de aspiracional.

---

## 7 · Orden de ejecución

Diseñado para que cada paso sea verificable antes del siguiente, y para que la batería exista
**antes** que la reparación que debe validar.

| # | Paso | Verificable por |
|---|---|---|
| **1** | Construir `test_migraciones.py` (T1-T6) **y verla en rojo** | T1 falla con el error exacto del Release Committee. *Si no falla, la batería no prueba lo que dice* |
| **2** | Generar la revisión fundacional por autogenerate **con `version_locations` a directorio vacío** (§3.3); fijar el identificador a `0005` | Existe el fichero, con `down_revision = None`; aún sin revisar |
| **3** | **Revisión manual de la DDL generada** (§3.3), con foco en `PortableJSON` | Inspección humana. Es el paso de mayor valor y el menos automatizable |
| **4** | Eliminar las revisiones 0001-0004 | `alembic history` muestra una sola revisión |
| **5** | T1 y T2 en verde sobre SQLite | Cadena aplicable y reversible |
| **6** | T4 (deriva) en verde | El esquema migrado y el de `create_all` coinciden |
| **7** | **Demostrar que T4 sabe fallar** | Divergencia deliberada → rojo → revertida |
| **8** | T5 contra PostgreSQL real | **Confirma que JSONB sobrevivió** (R-D1) |
| **9** | Suite existente en 102/104 | Sin regresión |
| **10** | `docker compose down -v && up --build` sobre volumen limpio | El backend responde en `/health`. **Cierra el defecto de despliegue** |
| **11** | Convenciones (§6) + T4 en CI | Barreras activas |
| **12** | Corregir documentación (§8) | Los documentos dejan de afirmar lo falso |
| **13** | Propagar la renumeración a Fase 10 y Fase 13 (§9) | Ambos planes consistentes |
| **14** | Desbloquear Fase 10 | — |

**El paso 1 va primero deliberadamente.** Escribir la batería contra el código roto y verla fallar
con el error exacto es lo que demuestra que sirve. Escrita después de reparar, produciría tests que
pasan sin haber demostrado nunca su capacidad de detectar el fallo.

---

## 8 · Cambios en documentación

| Documento | Corrección |
|---|---|
| `docs/PENDIENTES.md:134` | *«migraciones 0003 y 0004 con upgrade/downgrade verificados en SQLite»* — **falso para la 0004**, que no puede ejecutarse en SQLite |
| `docs/PENDIENTES.md:29,38` | Reservan la `0005` para la Fase 10. Pasa a `0006` (§3.2) |
| `CLAUDE.md` §3 (Fase 12) | Arrastra la misma afirmación sobre la 0004 |
| `CLAUDE.md` §3 (Fase 9) | *«Verificada upgrade/downgrade sobre BD real»*: cierto solo para el camino histórico, que deja de existir |
| `CLAUDE.md` §3 (migraciones) | La cadena «0001→0002→0003→0004» se sustituye por la fundacional única |
| `CLAUDE.md` §7 (puesta en marcha) | El `docker compose up` documentado no funciona sobre volumen limpio hasta el paso 10 |
| `CLAUDE.md` §6 (convenciones) | Añadir las dos reglas de §6 |
| `CLAUDE.md` §2 (stack) | Declara «PostgreSQL 16 + PostGIS (geoespacial)», pero **no hay ninguna columna geométrica ni dependencia de `geoalchemy2`**: `lat`/`lng` son `Numeric(9,6)` y `models.py:3-4` sitúa la migración a `geometry(Point,4326)` en una fase futura. La imagen es PostGIS; el esquema no lo usa |
| **`CLAUDE.md` §5 (hoja de ruta)** | Ruta crítica sin la Fase 9.5 y numeración derogada (`0005` asignada a la Fase 10). **Ya propagado en la rama de planificación**, antes de abrir el PR: era la contradicción más directa y `CLAUDE.md` se carga como contexto en cada sesión |
| **`README.md` (tabla de fases)** | Roadmap sin la Fase 9.5 y Fase 10 marcada como «Siguiente». **Ya propagado en la rama de planificación** |
| **`README.md` (PostGIS)** | Repite la inexactitud de `CLAUDE.md` §2, y además sitúa la migración a `geometry` «hasta la Fase 5», que figura como completada. **Pendiente** |
| `docs/FASE_13_PLAN_EJECUCION.md` | §12-Q1 (migración `0006`) y el criterio de «hecho» del Bloque A (§9) |

---

## 9 · Impacto sobre el plan maestro

- **Fase 10 y Fase 13 están bloqueadas** hasta el paso 14: ninguna puede validar su migración sobre
  una cadena rota.
- Esta reparación **no pertenece a ninguna de las dos**: es deuda de las Fases 9 y 12.
  **Decisión Q5, cerrada por el ARB:** se ejecuta como **fase propia — Fase 9.5**, no absorbida por
  la Fase 10. Ruta crítica resultante: 9 → 9.5 → 10 → 11 → 13 → 20.
- **Renumeración a propagar:** Fase 10 `0005 → 0006`; Fase 13 `0006 → 0007`, con
  `down_revision = "0006"`. Deroga `PENDIENTES.md:29,38` y `FASE_13_PLAN_EJECUCION.md` §12-Q1.
- **La dependencia de orden se mantiene y se refuerza:** la `0007` no aplica sin la `0006`, luego la
  Fase 13 sigue sin ser desplegable antes que la Fase 10.
- **La corrección B3 del plan de Fase 13** (backfill de suscripciones) es **exactamente el patrón
  que rompió la 0002** (RM1). Esta reparación **no lo previene**; lo previene la convención 2 de
  §6. Debe quedar explícito en el plan de la Fase 13.

---

## 10 · Riesgos de la Alternativa B

| # | Riesgo | Severidad | Mitigación |
|---|---|---|---|
| **R-D1** | ~~**Pérdida de la variante JSONB** en las 19 columnas `PortableJSON`~~ → **RIESGO DESCARTADO (2026-07-26).** El mecanismo temido —que autogenerate aplanara `JSON().with_variant(JSONB(), "postgresql")` a `sa.JSON()`— **no se produce**: la ejecución real rinde las 19 columnas con la variante intacta. **Matiz que debe preservarse:** lo demostrado es que el *código generado* es correcto, no que la *DDL ejecutada* en PostgreSQL produzca `jsonb`. La verificación del paso 8 **se mantiene**, reclasificada de contención a **confirmación** | ~~Alta~~ → **Baja** | Revisión manual del paso 3 + T5 contra PostgreSQL real (paso 8), ahora como comprobación de resultado esperado |
| **R-D2** | **Stamp obsoleto silencioso** si se reutilizara el identificador `0001` | Alta | Neutralizado por diseño: numerar desde `0005` (§3.2) |
| **R-D3** | **Pérdida definitiva del camino de actualización.** Ninguna BD anterior podrá migrarse jamás; solo recrearse | Aceptada | Autorizada explícitamente por Q1. §4 documenta la recreación |
| **R-D4** | **RM1 persiste.** Los 7 `default=_now` siguen sin `server_default`; el backfill de la Fase 10 y el de la Fase 13 siguen expuestos | Media | Convención 2 de §6. **No la resuelve esta reparación** |
| **R-D5** | **Autogenerate omite lo que no sabe detectar**: restricciones CHECK, índices parciales, comentarios, restricciones con nombre | Media | Revisión manual (paso 3) + T4, que compara contra `create_all` y detecta divergencias de esquema |
| **R-D6** | **Recreación destructiva mal ejecutada.** `docker compose down -v` destruye el volumen; alguien puede perder datos de desarrollo que creía descartables | Baja | §4 lo advierte en primera línea. Q1 lo autoriza |
| **R-D7** | **RM3 persiste.** El primer `ALTER COLUMN` futuro reincidirá en SQLite. `Auditoria.entidad_id` es el próximo caso conocido | Media | Convención + `render_as_batch` como paliativo de autogenerate |
| **R-D8** | **Divergencia futura si alguien añade geometría real.** Sin `geoalchemy2`, autogenerate no sabría rendir `geometry(Point,4326)` | Baja | Fuera de alcance. Anotado para la fase del módulo de mapa |

---

## 11 · Criterios de aceptación

- [ ] `alembic upgrade head` desde BD vacía en **SQLite**: verde.
- [ ] `alembic upgrade head` desde BD vacía en **PostgreSQL**: verde.
- [ ] `alembic downgrade base` tras el anterior: verde en ambos motores.
- [ ] `alembic history` muestra **una sola revisión**, con `down_revision = None`.
- [ ] Ningún fichero bajo `alembic/versions/` referencia `Base.metadata` ni `create_all`.
- [ ] **T4 (deriva) en verde**, y **demostrado capaz de fallar** ante una divergencia deliberada.
- [ ] **En PostgreSQL, las 19 columnas `PortableJSON` son `jsonb`, no `json`** (R-D1).
- [ ] La suite existente sigue en **102/104** (los 2 rojos de PDF son preexistentes y ajenos).
- [ ] `docker compose down -v && docker compose up -d --build` sobre volumen limpio: el backend
      responde en `/api/v1/health`.
- [ ] Una BD stampeada en `0001`, `0002`, `0003` o `0004` **falla de forma ruidosa**, no silenciosa.
- [ ] Documentación de §8 corregida, incluida la renumeración de Fase 10 y Fase 13.
- [ ] Convenciones de §6 incorporadas a `CLAUDE.md` §6.

---

## 12 · Plan de rollback

### Reversibilidad

La reparación produce **solo código, tests y documentación**, y el rollback del PR es
`git revert`.

> **Corrección (2026-07-26).** La redacción anterior afirmaba que la fase «no ejecuta ninguna
> operación sobre datos». **No es estrictamente cierto.** El Bloque A ejecuta T2
> (`alembic downgrade base`), y el `downgrade` de la 0001 antigua es `Base.metadata.drop_all`: si el
> aislamiento de la URL no está bien resuelto, **borra las tablas de la base que resuelva
> `DATABASE_URL`**. El riesgo es real y silencioso, y ocurre **antes** de cualquier paso destructivo
> por diseño de la fase.
>
> **Mitigación definida** (`FASE_95_PLAN_EJECUCION.md`, Bloque A): guarda de aislamiento que
> comprueba la URL efectiva antes de ejecutar ninguna migración y aborta si no coincide con la ruta
> desechable, más demostración de que la guarda salta. Con esa guarda en su sitio, la afirmación
> original vuelve a ser cierta; **sin ella, no lo es.**
>
> E1 hace tolerable la pérdida en caso de accidente, pero eso es una circunstancia del proyecto, no
> una propiedad del procedimiento.

**Asimetría que hay que entender antes de fusionar:** revertir el código es trivial, pero **no
resucita las bases de datos de desarrollo ya recreadas**. Quien haya ejecutado §4 tendrá que volver
a recrear con las migraciones antiguas — que están rotas. En la práctica, **una vez fusionado y
recreados los entornos, el rollback deja de ser útil**: lo procedente ante un fallo es corregir
hacia adelante.

### Puntos de no retorno

| Operación | Reversibilidad |
|---|---|
| Crear la revisión fundacional | Reversible |
| Eliminar las revisiones 0001-0004 | Reversible por git; **su ejecución sobre BDs antiguas, no** |
| Recrear un entorno de desarrollo (§4) | **NO reversible.** Los datos se destruyen |
| `docker compose down -v` | **NO reversible.** El volumen se destruye |

### Ante un fallo tras la fusión

1. **No** intentar restaurar la cadena antigua: estaba rota, no es un estado seguro al que volver.
2. Corregir hacia adelante sobre la revisión fundacional.
3. Registrar la revisión y el motor donde falló, y **añadirlo a la batería como test nuevo antes de
   reintentar**.

---

## 13 · Checklist del Release Committee

Para el pase de verificación independiente, una vez implementada la reparación.

### Evidencia exigible

- [ ] Salida literal de `alembic upgrade head` desde vacío, **en ambos motores**.
- [ ] Salida literal de `alembic downgrade base`, en ambos motores.
- [ ] Salida de `alembic history`: una sola revisión.
- [ ] **Volcado de tipos de PostgreSQL demostrando `jsonb` en las 19 columnas `PortableJSON`.**
      *Confirma el resultado esperado: el código generado ya se verificó correcto (R-D1 descartado).
      La evidencia se sigue exigiendo, pero su ausencia ya no denota un riesgo abierto.*
- [ ] Demostración de que **T4 falla** ante una divergencia introducida a propósito.
- [ ] `docker compose up` sobre volumen limpio, con el backend respondiendo en `/health`.
- [ ] Prueba de que una BD stampeada en una revisión antigua falla de forma **ruidosa**.
- [ ] Recuento de la suite: 102/104, con los 2 rojos identificados como los de PDF.

### Verificación de que no se ha reintroducido la causa

- [ ] Búsqueda de `Base.metadata` en `alembic/versions/`: sin resultados.
- [ ] Búsqueda de `create_all` en `alembic/versions/`: sin resultados.
- [ ] T4 está en el pipeline de CI, no solo en el repositorio.
- [ ] `CLAUDE.md` §6 contiene las dos convenciones.

### Verificación documental

- [ ] `docs/PENDIENTES.md` líneas 29, 38 y 134 corregidas.
- [ ] `CLAUDE.md` §§2, 3, 6 y 7 corregidos *(§5 ya propagada antes del PR)*.
- [ ] `README.md` corregido: PostGIS *(la tabla de fases ya se propagó antes del PR)*.
- [ ] `docs/FASE_13_PLAN_EJECUCION.md` renumerado a `0007`.

### Criterio de bloqueo

**Se bloquea el pase si:** no hay evidencia de `jsonb` en PostgreSQL · no se ha demostrado que T4
sabe fallar · T4 no está en CI · `docker compose` sobre volumen limpio no levanta · alguna BD
antigua es aceptada en silencio.

---

**Documento de diseño. No contiene código ni parches.**
Estrategia cerrada sobre la Alternativa B. **Q5 resuelta:** la reparación se ejecuta como fase
propia, la **Fase 9.5**, cuyo plan de ejecución canónico es
[`FASE_95_PLAN_EJECUCION.md`](FASE_95_PLAN_EJECUCION.md). **No queda ninguna decisión abierta en
este documento.**
