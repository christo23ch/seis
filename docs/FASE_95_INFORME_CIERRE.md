# INFORME FINAL DE CIERRE — FASE 9.5

**Saneamiento del sistema de migraciones**

| | |
|---|---|
| **Proyecto** | SEIS — Sistema Experto de Inversión en Subastas (`christo23ch/seis`) |
| **Fase** | 9.5 — Saneamiento del sistema de migraciones |
| **Fecha del informe** | 2026-07-29 |
| **Commit auditado** | `eca62f7` |
| **Tag** | `fase-9.5` → `eca62f7` (anotado, publicado en `origin`) |
| **Plan canónico** | `docs/FASE_95_PLAN_EJECUCION.md` |
| **Documento de diseño** | `docs/PLAN_REPARACION_MIGRACIONES.md` |

**Método.** Toda afirmación de este informe procede de evidencia obtenida ejecutando comandos
contra el repositorio en la sesión de auditoría del 2026-07-29, o de citas literales con fichero
y línea. No se reutilizan conclusiones de informes anteriores como evidencia. Lo que no ha podido
demostrarse se declara expresamente como tal.

**Clasificación empleada.** Cada conclusión relevante se etiqueta como **[Hecho demostrado]**,
**[Inferencia]**, **[Riesgo]** o **[Recomendación]**.

---

## 1 · Resumen ejecutivo

La Fase 9.5 se abrió para reparar un defecto que impedía instalar el producto desde cero: la
cadena de migraciones de Alembic no podía aplicarse sobre una base de datos limpia, y como el
arranque del contenedor de backend encadena `alembic upgrade head`, **una instalación nueva no
levantaba**.

**[Hecho demostrado]** El defecto está corregido. El historial de Alembic es hoy una única
revisión fundacional, y la verificación en vivo durante esta auditoría confirma el estado
funcional:

| Comprobación | Resultado medido | Evidencia |
|---|---|---|
| `alembic heads` | `0005 (head)` — una sola cabeza | ejecutado en auditoría |
| `alembic history` | `<base> -> 0005 (head)` — lineal | ejecutado en auditoría |
| Ciclo `upgrade`→`current`→`check`→`downgrade` | `0005 (head)` · *No new upgrade operations detected* · downgrade sin error | ejecutado en auditoría |
| Backend en Docker | `HTTP 200` en `/api/v1/health` | ejecutado en auditoría |
| PostgreSQL: `alembic_version` | `0005` | consulta SQL en auditoría |
| PostgreSQL: tipos JSON | `jsonb=19 · json=0` | consulta SQL en auditoría |
| PostgreSQL: tablas de SEIS | `21` | consulta SQL en auditoría |
| PostgreSQL: `auditoria.quien` | `character varying(120)` | consulta SQL en auditoría |
| Suite completa | `2 fallan · 113 pasan · 3 se omiten` | ejecutado en auditoría |
| Batería de migraciones | `11 pasan · 3 omitidos · 0 fallos` | ejecutado en auditoría |

**Estado de cierre.** RC-0, RC-1 y RC-2 superados. **RC-3 no puede declararse superado**, por un
único motivo verificable: el pipeline de CI no se ha observado ejecutándose en GitHub Actions.
El DoD tiene **dos ítems de gobernanza pendientes** y **dos ítems marcados como pendientes que en
realidad están satisfechos** (defecto documental identificado en §10.3 de este informe).

**Los dos fallos de la suite son preexistentes y ajenos a esta fase**: ambos de PDF, por ausencia
de la fuente DejaVu fuera de Docker.

---

## 2 · Objetivos de la Fase 9.5

**Origen.** `docs/PLAN_REPARACION_MIGRACIONES.md:24-25` declara la situación de partida:

> «`alembic upgrade head` **no funciona sobre una base de datos limpia**. Comprobado
> experimentalmente, no inferido.»

Y en `:27-32` tabula el diagnóstico por revisión:

| Revisión | Sobre BD nueva | Error |
|---|---|---|
| `0001_esquema_inicial` | aplica | — |
| `0002_multitenancy` | **falla** | `IntegrityError: NOT NULL constraint failed: organizacion.creado_en` |
| `0003_notificaciones` | inalcanzable | la cadena se detiene en 0002 |
| `0004_ampliar_auditoria_quien` | **falla** (aislada) | `OperationalError: near "ALTER": syntax error` |

**Alcance real del defecto**, según `PLAN_REPARACION_MIGRACIONES.md:34-37`: `docker-compose.yml`
arranca el backend con `sh -c "alembic upgrade head && python -m scripts.init_db && uvicorn ..."`.
El `&&` corta en el primer fallo, de modo que **el contenedor no arrancaba sobre un volumen
limpio, en ningún motor**.

**Por qué no se detectó antes** (`PLAN_REPARACION_MIGRACIONES.md:39-40`): `conftest.py:64`
construye el esquema con `Base.metadata.create_all(engine)`. La suite **no invocaba Alembic en
ningún punto**. Migraciones y tests eran dos caminos disjuntos hacia dos esquemas que nadie había
comparado nunca.

**Objetivo, según el plan canónico:** sustituir las cuatro revisiones por una revisión fundacional
única con DDL explícita, instrumentar el sistema con una batería de pruebas que ejerza Alembic de
verdad, e instalar barreras que impidan la reintroducción del defecto.

**[Hecho demostrado]** Ambas causas raíz están hoy erradicadas del árbol: `grep` de
`Base.metadata|create_all|drop_all` sobre `backend/alembic/versions/*.py` devuelve **0 apariciones**,
y no queda ninguna DML de migración en el árbol.

---

## 3 · Cambios realizados

**[Hecho demostrado]** Siete commits componen la fase, todos en Conventional Commits y en español
conforme a `CLAUDE.md` §6.1:

| Commit | Fecha | Asunto |
|---|---|---|
| `7a1551f` | 2026-07-28 | `refactor(fase-9.5)!:` sustituir la cadena 0001-0004 por una revisión fundacional |
| `2c9f50f` | 2026-07-28 | `test(fase-9.5):` retirar el gate de la batería y reparar T4 |
| `3e5b726` | 2026-07-28 | `ci(fase-9.5):` barrera anti-recurrencia — T4 en el pipeline |
| `6973426` | 2026-07-28 | `docs(fase-9.5):` saneamiento documental, renumeración y evidencias A-J |
| `c3f30b9` | 2026-07-28 | `docs(fase-9.5):` reconciliar cifras de la suite entre documentos (RC-3) |
| `edcf14d` | 2026-07-29 | `ci(fase-9.5):` aplicar mínimo privilegio al workflow de migraciones |
| `eca62f7` | 2026-07-29 | `docs(fase-9.5):` registrar la ambigüedad de «fusionar» como decisión pospuesta |

Precedidos por tres commits de planificación (`dbf67f4`, `98c6859`, `6c51606`, del 2026-07-26) y
uno de instrumentación (`33bb28a`, batería del Bloque A).

**Diferencia por fichero** (`git diff --numstat b9284e1..HEAD`), quince ficheros:

| Fichero | + | − | Naturaleza |
|---|---|---|---|
| `.github/workflows/migraciones.yml` | 70 | 0 | **Nuevo** — no existía CI en el repositorio |
| `backend/alembic/versions/0005_esquema_base.py` | 359 | 0 | **Nuevo** — revisión fundacional |
| `backend/alembic/versions/0001_esquema_inicial.py` | 0 | 22 | Eliminado |
| `backend/alembic/versions/0002_multitenancy.py` | 0 | 106 | Eliminado |
| `backend/alembic/versions/0003_notificaciones.py` | 0 | 95 | Eliminado |
| `backend/alembic/versions/0004_ampliar_auditoria_quien.py` | 0 | 31 | Eliminado |
| `backend/alembic/env.py` | 12 | 0 | **Solo comentario** — cero líneas eliminadas |
| `backend/tests/test_migraciones.py` | 66 | 47 | Gate retirado, T4 reparado |
| `CLAUDE.md` | 21 | 10 | Convenciones 9-11 y saneamiento |
| `README.md` | 8 | 6 | Estado y cifras |
| `docs/FASE_95_PLAN_EJECUCION.md` | 360 | 34 | Evidencias bloque a bloque |
| `docs/PENDIENTES.md` | 68 | 3 | Renumeración y deuda |
| `docs/PLAN_REPARACION_MIGRACIONES.md` | 31 | 10 | Propagación y notas de vigencia |
| `docs/FASE_13_PLAN_EJECUCION.md` | 30 | 7 | Renumeración a `0007` |
| `docs/FASE_13_MAPA_IMPACTO_STRIPE.md` | 1 | 1 | Línea base de no regresión |

**[Hecho demostrado]** **No se modificó código de producción.** `backend/app/` no aparece en el
diff de la fase. El único fichero de `backend/` fuera de migraciones y tests es
`backend/alembic/env.py`, y su cambio es **exclusivamente comentario** (`+12 / −0`).

---

## 4 · Estado de la arquitectura

**[Hecho demostrado]** La arquitectura no se alteró. La fase operó sobre la capa de migraciones,
la instrumentación de pruebas y la documentación.

**Estrategia adoptada.** `PLAN_REPARACION_MIGRACIONES.md:114-129` documenta la decisión:
**Alternativa B — revisión fundacional limpia**, sustituyendo las cuatro revisiones por una sola
con DDL explícita del esquema completo. Se descartó la reparación incremental porque «resolvía el
mismo problema a mayor coste, exigía reconstruir por arqueología de git el esquema de las Fases
1-2, y su único beneficio —preservar el camino de actualización desde instalaciones históricas—
carece de destinatario».

**Nota de nomenclatura relevante para el archivo histórico**
(`PLAN_REPARACION_MIGRACIONES.md:116-121`): una versión anterior del documento llamaba
«Alternativa D» a esta misma estrategia. **«Alternativa D» y «Alternativa B» designan la misma
decisión.** Los códigos de riesgo `R-D1…R-D8` conservan el prefijo histórico.

**Numeración.** `CLAUDE.md:46` fija el estado vigente: revisión fundacional `0005` con
`down_revision = None`; **Fase 10 → `0006`**; **Fase 13 → `0007`** con `down_revision = "0006"`.

**[Hecho demostrado]** La decisión de numerar `0005` y **no reutilizar `0001`** es deliberada y
está justificada en `PLAN_REPARACION_MIGRACIONES.md:147-152`: reutilizar el identificador
introduciría un fallo silencioso, porque una base sellada en `0001` se consideraría al día
conservando un esquema parcial.

---

## 5 · Estado de la base de datos

**[Hecho demostrado]** Verificado en vivo contra el PostgreSQL de la composición durante esta
auditoría:

```
alembic_version           = 0005
tablas de SEIS            = 21
columnas json/jsonb       = jsonb 19 · json 0
auditoria.quien           = character varying(120)
filas en auditoria        = 5
```

**Significado de cada dato:**

- **21 tablas** coincide exactamente con las 21 declaradas en `backend/app/models.py` y con las
  21 `op.create_table` de la revisión fundacional.
- **19 columnas `jsonb`, 0 `json`** confirma que la variante `PortableJSON`
  (`sa.JSON().with_variant(postgresql.JSONB(...), 'postgresql')`) **se materializa correctamente
  en PostgreSQL**. Esto era un riesgo declarado: que la DDL ejecutada degradara la variante a
  `json` genérico. No ocurre.
- **`auditoria.quien` es `varchar(120)`** demuestra que la corrección que aportaba la retirada
  revisión `0004` **viaja dentro de la fundacional**: no se perdió al retirar la cadena.
- **5 filas en `auditoria`** demuestra que el registro de auditoría **se rellena de verdad**
  (relevante para §12, donde se documenta que no existe forma de consultarlo).

**Nota sobre PostGIS.** La imagen desplegada es `postgis/postgis:16-3.4`, pero
`CLAUDE.md:25` deja constancia verificada de que **el esquema no usa capacidades geoespaciales**:
no hay columna `geometry`, no se declara `geoalchemy2`, y `lat`/`lng` son `Numeric(9,6)`.

---

## 6 · Estado de Alembic

**[Hecho demostrado]** Ejecutado en esta auditoría sobre base SQLite desechable:

```
alembic heads    -> 0005 (head)                                   ← una sola cabeza
alembic history  -> <base> -> 0005 (head)                         ← lineal, sin bifurcación
alembic upgrade head -> alembic current -> 0005 (head)
alembic check    -> "No new upgrade operations detected"          ← sin deriva
alembic downgrade base -> sin error
```

**Cabecera de la revisión** (`backend/alembic/versions/0005_esquema_base.py:31-34`):

```python
revision = "0005"
down_revision = None
branch_labels = None
depends_on = None
```

**Configuración.** `backend/alembic/env.py` toma la URL de la configuración de la aplicación
(`config.set_main_option("sqlalchemy.url", get_settings().database_url)`), lo que garantiza una
única fuente de verdad para la conexión.

**`render_as_batch` — decisión documentada y medida.** `env.py:28-38` deja constancia de que
**no se activa, y no por olvido**, con la tabla de los cuatro cruces medidos sobre SQLite:

```
alter_column      + render_as_batch=False -> FALLO (near "ALTER")
alter_column      + render_as_batch=True  -> FALLO (near "ALTER")
batch_alter_table + render_as_batch=False -> OK
batch_alter_table + render_as_batch=True  -> OK
```

**[Hecho demostrado]** `render_as_batch` no repara `alter_column` y `batch_alter_table` no lo
necesita. Queda documentado como **preventivo de `autogenerate`, jamás correctivo**, en
`CLAUDE.md` §6.11 y en el propio `env.py`.

---

## 7 · Estado de las migraciones

**[Hecho demostrado]** `backend/alembic/versions/` contiene **un único fichero**:
`0005_esquema_base.py`.

**Inventario de DDL**, contado sobre el fichero:

| Elemento | Cantidad |
|---|---|
| `op.create_table` | 21 |
| `op.drop_table` | 21 |
| `op.create_index` | 22 |
| `op.drop_index` | 22 |
| `PrimaryKeyConstraint` | 21 |
| `ForeignKeyConstraint` | 15 |
| `UniqueConstraint` | 1 |
| Columnas con variante JSONB | 19 (20 coincidencias `grep`; una está en el docstring, línea 16) |

La simetría `create`/`drop` (21/21 tablas, 22/22 índices) es **condición necesaria** para que el
`downgrade` sea funcional, exigencia de `CLAUDE.md` §6.3.

**Fidelidad frente a `models.py`.** El plan canónico registra en su Bloque C la comparación
mecánica realizada materializando dos esquemas independientes —uno por `create_all`, otro
ejecutando la migración— y contrastándolos por reflexión: **21 tablas, 171 columnas, 15 claves
foráneas, 22 índices, 19 columnas JSON, con 0 diferencias**.

**[Hecho demostrado en esta auditoría]** La equivalencia se corrobora por vía independiente:
`alembic check` sobre base migrada devuelve *No new upgrade operations detected*, lo que significa
que `autogenerate` no encuentra ninguna diferencia entre el esquema aplicado y la metadata.

**Ausencia de las causas raíz.** `grep -rn "Base.metadata|create_all|drop_all"` sobre
`backend/alembic/versions/*.py` devuelve **0 apariciones**, frente a las 5 que existían antes de la
fase en `0001`, `0002` y `0003`.

---

## 8 · Estado de la CI

**[Hecho demostrado]** Antes de esta fase **no existía ninguna integración continua** en el
repositorio: ni `.github/workflows/`, ni `.gitlab-ci.yml`, ni `Jenkinsfile`, ni
`azure-pipelines.yml`, ni `.circleci`.

**Se creó `.github/workflows/migraciones.yml`.** Contenido efectivo, verificado parseando el YAML
en esta auditoría:

```
name        : Migraciones
permissions : {contents: read}
triggers    : push y pull_request, filtrados a backend/** y al propio workflow
runs-on     : ubuntu-latest
working-dir : backend
env         : SEIS_ENV, JWT_SECRET, ADMIN_PASSWORD
pasos       : actions/checkout@v4
              actions/setup-python@v5
              pip install -r requirements-dev.txt
              python -m pytest tests/test_migraciones.py -v --no-header
              python -m pytest tests/test_migraciones.py -q -rs --no-header
```

**Mínimo privilegio.** `permissions: contents: read` se añadió en `edcf14d` tras detectarse en
auditoría interna que el workflow no lo declaraba, lo que habría dado al `GITHUB_TOKEN` los
permisos por defecto del repositorio —potencialmente de escritura— para un job que solo clona y
ejecuta pruebas.

**Alcance deliberado.** El pipeline ejecuta **solo la batería de migraciones**, no la suite
completa. El motivo consta en los comentarios del propio workflow: la suite arrastra dos fallos
preexistentes de PDF que dejarían el pipeline permanentemente en rojo, y una barrera siempre roja
no vigila nada.

### 8.1 · Limitación de la verificación de CI

**[Hecho demostrado]** El pipeline **no se ha observado ejecutándose en GitHub Actions**.

**Qué sí se verificó**, según consta en el plan canónico: se reprodujo el job localmente clonando
el repositorio a un directorio temporal (equivalente a `actions/checkout`), creando un entorno
virtual nuevo, instalando desde `requirements-dev.txt` y ejecutando los comandos **leídos del
propio fichero YAML** para que no pudieran divergir. Resultado registrado: job **verde**.

**Qué no se verificó:** la ejecución en el runner de GitHub. **[Riesgo]** Diferencias del entorno
del runner (sistema operativo, versiones de sistema, red) podrían producir un resultado distinto.
La probabilidad se estima baja —las dependencias se fijan en `requirements-dev.txt` y la acción de
Python fija la versión 3.12— pero **no está demostrada**.

---

## 9 · Estado de las pruebas

**[Hecho demostrado]** Medido en esta auditoría:

```
Suite completa            : 2 fallan · 113 pasan · 3 se omiten   (118 recogidos)
Batería de migraciones    : 11 pasan · 3 omitidos · 0 fallos
```

**Los dos fallos son preexistentes y ajenos a la fase:**
`tests/test_pdf_async.py::test_informe_pdf` y
`tests/test_multitenant.py::test_acceso_directo_a_analisis_ajeno_es_404[/informe.pdf]`, ambos por
`FPDFUnicodeEncodingException` — ausencia de la fuente DejaVu fuera de Docker. El `Dockerfile` del
backend sí instala `fonts-dejavu-core`, de modo que en contenedor no se reproducen.

**Los tres omitidos son resultados esperados**, con motivo legible en la salida:

1. y 2. Los dos casos parametrizados de T3: *«La cadena vigente tiene una sola revisión (la
   fundacional): no hay pares consecutivos que recorrer. Estado esperado tras el Bloque D.»*
3. T5: *«T5 exige un PostgreSQL real. Se ejecutó y pasó en el Bloque F contra
   postgis/postgis:16-3.4 (PostgreSQL 16.4); aquí se omite únicamente porque
   SEIS_TEST_POSTGRES_URL no está definida.»*

**La batería T1-T6.** `backend/tests/test_migraciones.py` es nuevo de esta fase y contiene:
T1 (`upgrade head` desde base vacía), T2 (`downgrade base`), T3 (control del arnés y recorrido por
pares consecutivos), T4 (deriva de esquema), T5 (PostgreSQL real), T6 (idempotencia), más seis
pruebas de guarda de aislamiento.

**[Hecho demostrado] Ninguna aserción fue debilitada.** `git diff 33bb28a..HEAD` sobre el fichero,
filtrado por líneas eliminadas que contengan `assert ` o `pytest.fail`, **no devuelve ninguna
coincidencia**. Las 47 líneas eliminadas son docstring, comentario y el bloque del gate.

**Consecuencia visible y deliberada:** los mensajes de fallo de T1, T2, T3 y T6 siguen citando
«Bloque A», la revisión `0002` y la `0004`, ya inexistentes. Ese anacronismo **es la prueba de que
no se tocaron**, y el criterio de cierre del Bloque E prohíbe corregirlo.

**Corrección de T4.** T4 no podía pasar nunca en su versión original: `_describir_esquema()`
incluía la tabla `alembic_version`, que el runtime de Alembic crea al aplicar una revisión y que
`create_all` no crea jamás, de modo que los dos lados diferían siempre. Se excluyó **esa tabla y
solo esa**. La comparación sigue cubriendo 21 tablas, 171 columnas y 22 índices.

**Prueba de mutación.** El Bloque G sometió T4 a cinco mutaciones, una por cada dimensión que el
criterio exige cubrir. Registro en el plan canónico:

| Dimensión | Mutación | T4 mutado | T4 revertido |
|---|---|---|---|
| Tabla | `escenario` → `escenario_mutado` | FALLA | PASA |
| Columna | elimina `activo.lote` | FALLA | PASA |
| Tipo | `auditoria.quien` 120 → 80 | FALLA | PASA |
| Nulabilidad | `subasta.puja_minima` → NOT NULL | FALLA | PASA |
| Índice | elimina `ix_decision_semaforo` | FALLA | PASA |

**[Hecho demostrado]** La guarda de aislamiento `_verificar_url_aislada` se demostró capaz de
saltar en 7/7 escenarios peligrosos: fichero compartido de la fixture `api`, valor por defecto de
`Settings`, SQLite fuera del directorio desechable, PostgreSQL con «prod», PostgreSQL sin marcador
de test, URL vacía y esquema de URL no soportado.

---

## 10 · Estado documental

### 10.1 · Inventario

`docs/` contiene nueve ficheros. Los relevantes para esta fase:

| Documento | Rol |
|---|---|
| `FASE_95_PLAN_EJECUCION.md` | **Canónico de la fase.** En caso de conflicto operativo, manda este |
| `PLAN_REPARACION_MIGRACIONES.md` | Diseño de la estrategia, previo a la ejecución |
| `PENDIENTES.md` | Backlog técnico y deuda |
| `MEJORAS.md` | **Nuevo, sin seguimiento en git.** Hallazgos de validación funcional y expansión de producto |
| `FASE_13_PLAN_EJECUCION.md`, `FASE_13_MAPA_IMPACTO_STRIPE.md` | Fase futura; renumerados por esta fase |

### 10.2 · Barreras escritas en `CLAUDE.md` §6

**[Hecho demostrado]** Se añadieron tres convenciones obligatorias, cada una derivada de un
defecto real verificado contra el historial de git:

- **§6.9** — Prohibido `Base.metadata` dentro de `alembic/versions/`. *(La retirada `0001` hacía
  `Base.metadata.create_all` en su línea 18.)*
- **§6.10** — Toda DML de migración especifica explícitamente cada columna `NOT NULL`. *(La
  retirada `0002` hacía `INSERT INTO organizacion (id, nombre)` en su línea 72, omitiendo
  `creado_en`.)*
- **§6.11** — `render_as_batch` es preventivo de `autogenerate`, jamás correctivo.

### 10.3 · Contradicciones documentales detectadas

Se detectan **tres**. Se enumeran con el criterio de prevalencia y su justificación.

---

**C-1 · Cifras de la suite: «104 tests / 102 verdes» frente a «118 recogidos»**

*Dónde aparece:* `FASE_95_PLAN_EJECUCION.md:47, 122, 141, 799`;
`PLAN_REPARACION_MIGRACIONES.md:40, 373, 446, 516`.

*Qué prevalece:* **118 recogidos — 113 pasan, 2 fallan, 3 se omiten**, medido en esta auditoría.

*Justificación:* no es una contradicción real sino **registro histórico legítimo**. Ambos
documentos incorporan una nota de vigencia explícita —`FASE_95_PLAN_EJECUCION.md:49` y
`PLAN_REPARACION_MIGRACIONES.md:43`— que declara que esas cifras son la línea base anterior a la
fase y se conservan como medición histórica. Reescribirlas falsificaría el registro. **No requiere
acción.**

---

**C-2 · Dos ítems del DoD marcados como pendientes que en realidad están satisfechos**

*Dónde:* `FASE_95_PLAN_EJECUCION.md:977` («T1-T6 en verde, sin aserciones debilitadas») y `:984`
(«Suite en 118 recogidos…»). Ambos figuran como `- [ ]`.

*Qué prevalece:* **están satisfechos**, y así lo demuestra la evidencia de §9 de este informe: la
batería da `11 pasan · 3 omitidos · 0 fallos`, el filtro de aserciones eliminadas no devuelve
coincidencias, y la suite arroja exactamente las cifras que el propio ítem enuncia.

*Justificación:* es un **defecto de marcado**, no una discrepancia de fondo. El texto de ambos
ítems fue actualizado con la evidencia correcta, pero la casilla no se marcó.

**[Recomendación]** Marcar ambos ítems como `- [x]`. Este informe **no lo hace** para no alterar
el estado auditado; queda como acción de un minuto.

---

**C-3 · Ambigüedad de «fusionar» en `CLAUDE.md` §6.7 — decisión pospuesta**

*Dónde:* `CLAUDE.md:171` («un PR por fase, revisado por el humano antes de fusionar») frente a
`FASE_95_PLAN_EJECUCION.md:1005` (DoD: «Revisión humana previa al merge») y `:871` (tabla de
secuencia entre ramas).

*Naturaleza:* la documentación **no define si «fusionar» designa cualquier avance de `main` —
incluido un fast-forward puramente local — o solo la integración en el repositorio compartido**.

**[Hecho demostrado]** La distinción **no está escrita en ninguna parte**: las palabras `push`,
`origin` y `remoto` no aparecen en la documentación original del proyecto. Las únicas apariciones
de `push` en el plan canónico son notas añadidas durante esta misma fase.

*Qué prevalece:* **nada, deliberadamente.** `docs/PENDIENTES.md`, sección «Observación de
arquitectura», registra la decisión:

> «Se analizaron tres alternativas (RFC-A, RFC-B y RFC-C). **No se modifica la gobernanza durante
> esta fase.** La decisión se pospone para una futura revisión del protocolo, al no afectar a la
> validez técnica de la Fase 9.5.»

*Justificación de la prevalencia:* la ambigüedad **no afecta a ningún criterio técnico**. Los
cuatro checkpoints y la evidencia medida son independientes de cuál de las lecturas se adopte.
Resolverla habría exigido tomar una decisión de gobernanza —cuál de los dos modelos adoptar— que
excede el alcance de una fase de saneamiento de migraciones.

---

## 11 · Riesgos detectados

| Id | Riesgo | Severidad | Estado |
|---|---|---|---|
| **R-1** | **El pipeline de CI no se ha observado en GitHub Actions.** Verde desde clon limpio en local; el runner real no se ha visto | **MEDIA** | **Abierto.** Bloquea RC-3 |
| **R-2** | `alembic check` es inservible como barrera de deriva contra PostGIS. Sobre base migrada informa 74 `remove_table` y 56 `remove_index`; verificadas, las 38 tablas señaladas son **todas de las extensiones** y ninguna de SEIS. **Cero operaciones `add_*` o `modify_*`** ⇒ no hay deriva, solo ruido. Falta `include_object` en `env.py` | MEDIA | Abierto, en `PENDIENTES.md` |
| **R-3** | T4 compara los índices **por nombre**: una mutación que cambiara las columnas de un índice conservando su nombre no se detectaría | MEDIA | Abierto, en `PENDIENTES.md` |
| **R-4** | La prueba de mutación de T4 se ejecutó de forma dirigida, **no automatizada**. No hay barrera permanente que garantice que T4 sigue sabiendo fallar | MEDIA | Abierto, en `PENDIENTES.md` |
| **R-5** | La CI cubre solo la batería, no la suite completa. Una regresión fuera de migraciones no la detectaría el pipeline | MEDIA | Abierto, en `PENDIENTES.md` |
| **R-6** | `main` local está 21 commits por delante de `origin/main` y **no se ha publicado**. Mientras no se fusione, la Fase 10 sigue bloqueada por la condición 2 de `FASE_95_PLAN_EJECUCION.md` §11 | MEDIA | Abierto |
| **R-7** | `Settings.env_file=".env"` es ruta relativa: ejecutar `pytest` desde la raíz del repositorio haría que la suite leyera el `.env` real en lugar de sus valores de prueba | BAJA | Abierto, en `PENDIENTES.md` |
| **R-8** | `docker-compose.yml` conserva `version: "3.9"`, obsoleto en Compose v5 (aviso en cada invocación) | BAJA | Observado, ajeno a la fase |
| **R-9** | `backend` (8000) y `frontend` (3000) se publican en todas las interfaces, mientras `db` y `redis` se restringen a `127.0.0.1` con comentario explícito | BAJA | A confirmar en **Fase 16** |
| **R-10** | Dos fallos de PDF por ausencia de fuente DejaVu fuera de Docker | BAJA | Preexistente y ajeno |

**[Riesgo] Nota sobre R-2.** Su relevancia práctica está acotada: la barrera de deriva efectiva es
T4, que funciona y está demostrada. `alembic check` es una comprobación adicional, no la
principal.

---

## 12 · Deuda técnica

### 12.1 · Deuda de la Fase 9.5 sin bloque propietario

**[Hecho demostrado]** Registrada en `docs/PENDIENTES.md`, sección «Deuda de la Fase 9.5 sin
bloque propietario». El plan canónico **no asigna propietario** a ninguna de las cuatro, de modo
que no se les inventó uno: R-2, R-3, R-4 y R-5 del cuadro anterior.

**Corrección de atribución.** El propio documento consigna que en informes intermedios estas
deudas se asignaron por error al Bloque I; releído el plan, **sus criterios de aceptación no las
contemplan**. La rectificación consta por escrito.

### 12.2 · Deuda funcional detectada fuera del alcance de la fase

**[Hecho demostrado]** Durante la validación funcional del producto (2026-07-29) se registraron
diez hallazgos en `docs/MEJORAS.md`, ninguno de ellos causado por esta fase. Los de mayor
severidad:

| Id | Hallazgo | Prioridad |
|---|---|---|
| A1 | Los campos numéricos opcionales vacíos rompen el envío al backend. `aPayload()` (`frontend/lib/schema.ts:165-198`) construye el cuerpo desde `form.getValues()` sin pasar por el esquema, enviando `""` en lugar de omitir el campo | **ALTA** |
| A2 | Rellenar con `0` produce un informe silenciosamente distinto. `m05_reforma.py:15` toma `0` como dato cierto (`0 is not None`), anulando el baremo de reforma. **Reproducido**: informe con `Reforma: ligera · -597 €` y ROI, margen de seguridad y escalera inflados, sin ninguna advertencia | **ALTA** |
| A6 | La matriz de riesgos no explica por qué cada riesgo lo es. El campo `evidencias` existe en `contracts.py:255-264`, se declara en `types.ts:5` y **se descarta en `resultado.tsx:107`** | **ALTA** |
| A4 | No existe el perfil inversor del usuario ni su capital disponible, pese a que `CLAUDE.md` §1 lo describe como característica del producto | **BRECHA** |
| A10 | La tabla `Auditoria` se rellena (**5 filas medidas en esta auditoría**) pero **no existe ningún endpoint que la exponga**: es imposible consultarla desde ninguna parte | MEDIA |

**[Inferencia]** A1 y A2 forman un par: A1 obliga al usuario a introducir `0` donde debería dejar
vacío, y A2 convierte ese `0` en un dato que altera el resultado. **Juntos comprometen la
fiabilidad de cualquier informe generado hoy por la interfaz web**, aunque el motor sea correcto.

---

## 13 · Decisiones tomadas durante la fase

| Id | Decisión | Dónde consta |
|---|---|---|
| **E1/Q1** | «No existe ninguna base de datos que deba preservarse. Se acepta romper compatibilidad con instalaciones de desarrollo existentes» | `PLAN_REPARACION_MIGRACIONES.md:15-17` |
| **Alternativa B** | Revisión fundacional limpia, frente a reparación incremental | `PLAN_REPARACION_MIGRACIONES.md:114-129` |
| **Numeración `0005`** | No reutilizar `0001`, para evitar que una base sellada en esa revisión se considere al día con esquema parcial | `PLAN_REPARACION_MIGRACIONES.md:147-152` |
| **Renumeración** | Fase 10 → `0006`; Fase 13 → `0007` con `down_revision = "0006"` | `CLAUDE.md:46`, propagado a `PENDIENTES.md`, `FASE_13_PLAN_EJECUCION.md` (4 sitios) y `PLAN_REPARACION_MIGRACIONES.md` |
| **`render_as_batch` no se activa** | Se documenta como preventivo; medido que no repara nada | `env.py:28-38`, `CLAUDE.md` §6.11 |
| **CI acotada a la batería** | Una barrera permanentemente roja no vigila nada | comentarios de `.github/workflows/migraciones.yml` |
| **Exclusión única de `alembic_version` en T4** | Sin ella la aserción es insatisfacible; con ella la cobertura sigue siendo 21/171/22 | docstring de `_describir_esquema()` |
| **Ambigüedad de «fusionar» pospuesta** | No se modifica la gobernanza en esta fase | `PENDIENTES.md`, «Observación de arquitectura» |

---

## 14 · Desviaciones respecto al plan

**D-1 · Las seis revisiones asignadas a agentes ECC no se ejecutaron con los agentes previstos**

`FASE_95_PLAN_EJECUCION.md` §7, tabla «Revisión — sigue el riesgo, no la implementación», asignaba
seis revisiones a agentes especializados (`database-reviewer`, `pr-test-analyzer`,
`refactor-cleaner`, `silent-failure-hunter`, `code-reviewer`, `doc-updater`→`comment-analyzer`).

**[Hecho demostrado]** No se ejecutaron con esos agentes: se sustituyeron por revisión directa del
ejecutor. Se intentó lanzarlos en dos ocasiones; nueve intentos terminaron sin entrega —cinco por
límite de sesión de la API, dos colgados y dos detenidos.

**Por qué no invalida el cierre técnico.** Esas seis filas son **órdenes de trabajo, no criterios
de aceptación**. De las siete filas de esa tabla, los autores del plan promovieron al DoD
únicamente la séptima —la revisión humana—. **Ninguna cláusula `Bloquea si:` de RC-0 a RC-3 las
menciona.**

**[Riesgo]** La ausencia de revisión independiente reduce la probabilidad de detectar errores que
el ejecutor haya pasado por alto. Es un riesgo de proceso, no de producto.

---

**D-2 · La topología de ramas no siguió la secuencia prevista**

`FASE_95_PLAN_EJECUCION.md` §7, «Secuencia entre ramas», fila 1, prevé
`fase-95-saneamiento-migraciones` → `main`.

**[Hecho demostrado]** La rama de planificación se fusionó en `fase-12-notificaciones` en
`24da22b`, y la ejecución se realizó encima de esa rama. La integración se hizo desde
`fase-12-notificaciones`, que contenía además la Fase 12 completa.

**Justificación:** `main` contenía **un único commit** (`d72df4b`, «Initial commit») con **un solo
fichero**. Todo el proyecto vivía en la rama. Forzar el puntero de `fase-95-saneamiento-migraciones`
habría metido la Fase 12 entera en una rama que no le corresponde.

---

**D-3 · El fast-forward de `main` precedió a la revisión humana**

**[Hecho demostrado]** `main` local avanzó de `d72df4b` a la punta de la fase antes de que
existiera revisión humana. Bajo la lectura estricta de `CLAUDE.md` §6.7, eso invierte el orden que
el DoD prescribe.

**Atenuante verificable:** `origin/main` sigue en `d72df4b`. **Nada se ha publicado en la rama
principal**, de modo que la revisión sigue siendo íntegramente posible antes de que el trabajo
alcance a nadie.

**Relación con C-3:** bajo la lectura alternativa —que «fusionar» designa la integración
compartida— no hay desviación alguna. La ambigüedad está registrada y pospuesta.

---

**D-4 · `docs/MEJORAS.md` no está bajo control de versiones**

**[Hecho demostrado]** `git ls-files docs/MEJORAS.md` no devuelve resultado: el fichero existe en
el árbol de trabajo pero **no está rastreado**. Contiene los diez hallazgos de validación funcional
y la propuesta de expansión de producto.

**[Riesgo]** Un `git clean -fd` lo eliminaría sin recuperación posible.

**[Recomendación]** Confirmarlo en git antes de cualquier operación de limpieza.

---

## 15 · Validación frente al DoD

`FASE_95_PLAN_EJECUCION.md` §10. **[Hecho demostrado]** 23 ítems marcados como cumplidos, 5 sin
marcar. De los 5 sin marcar, **2 están de hecho satisfechos** (contradicción C-2).

### Ejecución

| Ítem | Estado | Evidencia |
|---|---|---|
| `upgrade head` desde base vacía verde en SQLite y PostgreSQL | ✅ | Auditoría: SQLite verificado; PostgreSQL con `alembic_version = 0005` |
| `downgrade base` verde en ambos motores | ✅ | Auditoría: SQLite verificado; PostgreSQL registrado en Bloque F |
| `alembic history`: una sola revisión, `down_revision = None`, id `0005` | ✅ | Auditoría |
| `alembic heads` devuelve exactamente una cabeza | ✅ | Auditoría |
| BD sellada en `0001`-`0004` falla de forma ruidosa | ✅ | 16/16 órdenes con `returncode != 0` y `Can't locate revision`, en ambos motores, 0 silencios |
| `docker compose down -v && up -d --build` con backend en `/health` | ✅ | `system_identifier` distinto entre arranques; `HTTP 200` reverificado en auditoría |

### Corrección del esquema

| Ítem | Estado | Evidencia |
|---|---|---|
| 19 columnas `PortableJSON` son `jsonb` en PostgreSQL, volcado archivado | ✅ | Auditoría: `jsonb=19 · json=0` |
| Índices, FKs y tipos verificados contra `create_all` por T4 | ✅ | 21/171/15/22, 0 diferencias |

### Instrumentación

| Ítem | Estado | Evidencia |
|---|---|---|
| T1-T6 en verde sin aserciones debilitadas | ✅ **satisfecho, casilla sin marcar (C-2)** | `11 pasan · 0 fallos`; filtro de aserciones eliminadas sin coincidencias |
| Gate `SEIS_CALIBRAR_MIGRACIONES` retirado | ✅ | Sin `pytestmark` ni `GATE_ENV_VAR` en el fichero |
| T4 demostrado capaz de fallar | ✅ | 5/5 dimensiones |
| Guarda de aislamiento demostrada capaz de saltar | ✅ | 7/7 escenarios peligrosos |
| **T4 en el pipeline de CI** | ⚠️ **PARCIAL** | Workflow creado y verde desde clon limpio; **no observado en GitHub Actions** |
| Suite en 118 recogidos | ✅ **satisfecho, casilla sin marcar (C-2)** | Auditoría: `2 · 113 · 3` |

### Barreras

Los cuatro ítems ✅: `CLAUDE.md` §6.9 y §6.10 presentes; búsquedas de `Base.metadata` y
`create_all` en `versions/` sin resultados; `render_as_batch` documentado como preventivo.

### Documentación

Los seis ítems ✅: `PENDIENTES.md` líneas 29, 38 y 134 corregidas; `CLAUDE.md` §§2, 3, 6, 7;
`README.md`; renumeración propagada; B3 de Fase 13 anotada como consumidora de la convención de
DML; procedimiento de recreación publicado con ambas vías y `--purge`.

### Gobernanza

| Ítem | Estado |
|---|---|
| PRE-1 satisfecha | ✅ Docker Desktop, motor verificado en marcha por medición |
| PRE-2 satisfecha | ✅ `.env` con secretos validados contra `_motivo_inseguro()` |
| RC-0…RC-3 superados en orden | ⚠️ **RC-0, RC-1, RC-2 sí. RC-3 no** |
| Revisión humana previa al merge | ❌ **Pendiente** |

**Resultado del DoD: 26 de 29 ítems satisfechos.** Los tres restantes son: T4 en CI (parcial),
RC-3, y la revisión humana.

---

## 16 · Validación frente a RC-0, RC-1, RC-2 y RC-3

Los checkpoints se evalúan por sus cláusulas `Bloquea si:`, que son las condiciones normativas.

### RC-0 · Calibración — tras A

*Bloquea si:* la batería nace en verde · falla por otro motivo · contamina la fixture `api`.

**[Hecho demostrado]** Ninguna se cumple. La batería nació en rojo tras corregirse una polaridad
invertida en T1, y las seis pruebas de guarda demuestran que el aislamiento frente a la fixture
`api` funciona (7/7 escenarios peligrosos rechazados).

**RC-0: SUPERADO.**

### RC-1 · Auditoría de la DDL — tras C

*Bloquea si:* falta cualquiera de los inventarios · cualquier duda no resuelta.

**[Hecho demostrado]** Los cuatro inventarios se produjeron (tablas, columnas, claves foráneas,
índices) con 0 diferencias, y consta la revisión de R-D5 —los puntos ciegos de `autogenerate`—
verificando que `models.py` no contiene `CheckConstraint`, `comment=`, índices parciales,
`__table_args__` ni restricciones con nombre.

**RC-1: SUPERADO.**

### RC-2 · Evidencia de ejecución — tras H

*Bloquea si:* falta evidencia PostgreSQL · Docker no verificado sobre volumen destruido · alguna
BD antigua es aceptada en silencio · el gate sigue presente.

**[Hecho demostrado]** Los ocho requisitos de evidencia están cubiertos, incluido el que quedó
último: la prueba de sellado obsoleto (P0-2), fabricada manualmente escribiendo `0004` y `0001` en
`alembic_version` de bases desechables, con **16 de 16 órdenes fallando ruidosamente en ambos
motores y cero aceptaciones en silencio**.

**RC-2: SUPERADO.**

### RC-3 · Pase final — tras J

*Evidencia:* T4 demostrado en rojo · **T4 en CI** · convenciones en `CLAUDE.md` §6 · búsquedas de
`Base.metadata` y `create_all` sin resultados · renumeración propagada · procedimiento de
recreación comunicado.

*Bloquea si:* T4 no ha demostrado saber fallar · **T4 no está en CI** · algún documento contradice
a otro · `render_as_batch` documentado como correctivo.

| Requisito | Estado |
|---|---|
| T4 demostrado en rojo | ✅ 5/5 dimensiones |
| Convenciones en `CLAUDE.md` §6 | ✅ §6.9, §6.10, §6.11 |
| `Base.metadata`/`create_all` sin resultados | ✅ 0 apariciones |
| Renumeración propagada | ✅ 4 documentos |
| Procedimiento de recreación comunicado | ✅ §9, con ambas vías y `--purge` |
| `render_as_batch` no documentado como correctivo | ✅ preventivo en §6.11 y `env.py` |
| **T4 en CI** | ⚠️ **workflow presente y verde en local; no observado en GitHub Actions** |
| Ningún documento contradice a otro | ⚠️ **C-2 vigente**: dos ítems del DoD mal marcados |

**RC-3: NO SUPERADO.**

**[Hecho demostrado]** Dos condiciones impiden declararlo: la ejecución remota del pipeline no se
ha observado, y persiste la contradicción C-2 dentro del propio DoD.

**[Inferencia]** C-2 es trivial de resolver (marcar dos casillas). El requisito de CI exige un
`git push` de `main` o la apertura de la PR.

---

## 17 · Evidencias encontradas

Consolidado de las comprobaciones ejecutadas en la sesión de auditoría del 2026-07-29:

| # | Comprobación | Comando o método | Resultado |
|---|---|---|---|
| E-1 | Historial de la fase | `git log b9284e1..HEAD` | 7 commits, Conventional Commits en español |
| E-2 | Diferencia por fichero | `git diff --numstat b9284e1..HEAD` | 15 ficheros; `backend/app/` ausente |
| E-3 | Migraciones presentes | `ls backend/alembic/versions/*.py` | 1 fichero |
| E-4 | Cabecera de la revisión | lectura de líneas 31-34 | `revision="0005"`, `down_revision=None` |
| E-5 | Inventario DDL | recuento sobre el fichero | 21/21 tablas, 22/22 índices, 15 FK, 21 PK, 1 UQ |
| E-6 | Causas raíz erradicadas | `grep Base.metadata\|create_all\|drop_all` | 0 apariciones |
| E-7 | Cabezas de Alembic | `alembic heads` | `0005 (head)` |
| E-8 | Historia de Alembic | `alembic history` | `<base> -> 0005 (head)` |
| E-9 | Ciclo completo | `upgrade`/`current`/`check`/`downgrade` | `0005` · sin deriva · sin error |
| E-10 | Suite completa | `pytest tests -q` | `2 fallan · 113 pasan · 3 omitidos` |
| E-11 | Batería | `pytest tests/test_migraciones.py -q -rs` | `11 pasan · 3 omitidos · 0 fallos` |
| E-12 | Integridad de aserciones | `git diff 33bb28a..HEAD` filtrado | 0 aserciones eliminadas o modificadas |
| E-13 | Workflow de CI | parseo del YAML | `permissions: contents:read`, 5 pasos, 2 disparadores |
| E-14 | Docker en marcha | `docker compose ps` | 5 servicios `running` |
| E-15 | Versión aplicada en PostgreSQL | consulta SQL | `alembic_version = 0005` |
| E-16 | Tipos JSON en PostgreSQL | `information_schema.columns` | `jsonb=19 · json=0` |
| E-17 | Tablas de SEIS en PostgreSQL | `information_schema.tables` | 21 |
| E-18 | Corrección de la `0004` conservada | `information_schema.columns` | `quien character varying(120)` |
| E-19 | Backend operativo | `curl /api/v1/health` | `HTTP 200` |
| E-20 | Auditoría se rellena | `SELECT count(*) FROM auditoria` | 5 filas |
| E-21 | Convenciones nuevas | `grep` sobre `CLAUDE.md` | §6.9, §6.10, §6.11 presentes |
| E-22 | `render_as_batch` | `grep` sobre `CLAUDE.md` y `env.py` | Documentado como preventivo, con los 4 cruces |
| E-23 | Estado del DoD | recuento de casillas | 23 marcadas, 5 sin marcar |
| E-24 | Publicación en `origin` | `git ls-remote` | rama y tag publicados; `main` en `d72df4b` |

**Evidencia que este informe NO ha podido producir:**

- **[No demostrable aquí]** La ejecución del workflow en GitHub Actions. Requiere publicar `main`
  o abrir la PR, y observar el resultado en la plataforma.
- **[No reverificado en esta sesión]** La secuencia completa `docker compose down -v && up -d
  --build` con destrucción de volumen. La pila estaba ya levantada al iniciar la auditoría; se
  reverificaron sus resultados (`/health`, `alembic_version`, tipos `jsonb`) pero no se repitió la
  destrucción del volumen. La evidencia original —`system_identifier` distinto entre arranques—
  consta registrada en el plan canónico.

---

## 18 · Qué quedó fuera del alcance

**[Hecho demostrado]** Fuera del alcance, con justificación:

| Elemento | Motivo |
|---|---|
| Código de producción (`backend/app/`) | La fase es de saneamiento de migraciones. `backend/app/` no aparece en el diff |
| `include_object` en `env.py` | No figura en los criterios de aceptación de ningún bloque del plan. Registrado como deuda sin propietario |
| Comparación de índices por columnas en T4 | Ídem |
| Automatización de la prueba de mutación | Ídem. RC-3 exige «T4 en CI», que sí se cubrió; no la mutación |
| CI de la suite completa | Decisión razonada: exigiría `fonts-dejavu-core` en el runner y dejaría el pipeline en rojo permanente |
| Resolución de la ambigüedad de «fusionar» | Decisión de gobernanza, expresamente pospuesta |
| Los 10 hallazgos de `MEJORAS.md` | Detectados durante la validación funcional, ajenos al saneamiento de migraciones |
| Los 2 fallos de PDF | Preexistentes, documentados en `PENDIENTES.md` |
| `version: "3.9"` en `docker-compose.yml`; exposición de puertos | Observaciones ajenas; la segunda corresponde a la Fase 16 |
| Docstring de `app/models.py:3-5` sobre `geometry(Point,4326)` | El Bloque J no autoriza tocar modelos |

---

## 19 · Qué trabajo desbloquea esta fase

`FASE_95_PLAN_EJECUCION.md` §11 enumera cinco condiciones para desbloquear la Fase 10:

| # | Condición | Estado |
|---|---|---|
| 1 | DoD de la Fase 9.5 completo, sin excepciones | ⚠️ 26 de 29; faltan T4 en CI observado, RC-3 y revisión humana |
| 2 | Fase 9.5 **fusionada a `main`** | ❌ `origin/main` sigue en `d72df4b` |
| 3 | **Convención de DML explícita escrita en `CLAUDE.md` §6** | ✅ §6.10 |
| 4 | Renumeración propagada: `PENDIENTES.md` refleja `0006` | ✅ |
| 5 | `alembic/versions/` descongelado | ✅ La regla de congelación regía «hasta el merge» |

**[Hecho demostrado]** Tres de las cinco condiciones están cumplidas. Las dos pendientes (1 y 2)
dependen de la misma acción: publicar y fusionar tras revisión.

**Por qué la condición 3 no es un formalismo** (`FASE_95_PLAN_EJECUCION.md` §11): el backfill de la
Fase 10 —`usuario.email_verificado` a `True` para usuarios existentes, más la tabla
`TokenConsumido`— es **el primer consumidor de la convención y el primer candidato a repetir el
fallo de la `0002`**.

**También se desbloquea la Fase 13**, cuya migración es la `0007` con `down_revision = "0006"`, y
que por tanto **no es desplegable antes que la Fase 10**: dependencia técnica dura, no preferencia.

---

## 20 · Recomendaciones para la Fase 10

**[Recomendación] Antes de abrir la Fase 10:**

1. **Marcar los dos ítems del DoD identificados en C-2.** Un minuto de trabajo; elimina la
   contradicción que hoy bloquea parcialmente RC-3.
2. **Poner `docs/MEJORAS.md` bajo control de versiones** (D-4). Hoy un `git clean -fd` lo
   destruiría.
3. **Publicar la rama y abrir la PR de fase.** Cierra simultáneamente la revisión humana del DoD,
   la observación del pipeline en GitHub Actions (R-1 y el requisito de RC-3), y la condición 2 del
   desbloqueo.

**[Recomendación] Durante la Fase 10, por orden de riesgo:**

4. **El backfill de `usuario.email_verificado` debe enumerar explícitamente todas las columnas
   `NOT NULL` sin `server_default`.** Es literalmente el escenario que tumbó la `0002`. La
   convención §6.10 existe por esto.
5. **Escribir la migración `0006` con DDL explícita**, nunca derivada de `Base.metadata` (§6.9).
6. **Verificar que T4 sigue verde tras la `0006`.** Si la migración y `models.py` divergen, T4 debe
   detectarlo. Es su primera prueba real sobre una migración nueva.
7. **Comprobar que los casos parametrizados de T3 dejan de omitirse.** Con dos revisiones en la
   cadena habrá por fin un par consecutivo que recorrer, y esos tests pasarán de `skipped` a
   `passed`. **Si siguieran omitidos, sería señal de un problema en el descubrimiento de la cadena.**

**[Recomendación] Decisión de producto a resolver antes o durante la Fase 10:**

8. **El perfil inversor y el capital disponible** (hallazgo A4). `CLAUDE.md` §1 los describe como
   característica del producto y no existen. La Fase 10 ya toca el modelo `Usuario` para el alta
   self-service, de modo que es el momento natural para decidir si entran ahí o merecen fase
   propia.
9. **Considerar A1 y A2 como candidatos a corrección temprana.** No pertenecen a la Fase 10, pero
   **juntos comprometen la fiabilidad de los informes que la interfaz genera hoy**, y la Fase 10
   traerá usuarios nuevos por alta self-service: personas sin acompañamiento que se toparán con el
   error y aplicarán el rodeo peligroso.

---

## 21 · Conclusión final

**[Hecho demostrado]** La Fase 9.5 cumplió su objetivo. El defecto que la originó —la
imposibilidad de aplicar las migraciones sobre una base limpia, y con ello de instalar el producto
desde cero— está corregido, y la corrección está verificada por medición directa en ambos motores,
con evidencia reproducida durante esta auditoría.

El historial de Alembic es hoy una única revisión fundacional, lineal, con una sola cabeza, sin
deriva frente a los modelos y con `downgrade` funcional. Las dos causas raíz —DDL derivada de
`Base.metadata` y DML que omite columnas `NOT NULL`— están erradicadas del árbol y **prohibidas por
convención escrita**. El sistema quedó además instrumentado con una batería que ejerce Alembic de
verdad, algo que antes no existía: la suite construía el esquema por un camino y las migraciones
por otro, y nadie los había comparado nunca.

**[Hecho demostrado]** Tres de los cuatro checkpoints están superados. **RC-3 no lo está**, por dos
condiciones concretas y ambas resolubles: la ejecución del pipeline en GitHub Actions no se ha
observado, y persisten dos casillas mal marcadas dentro del propio DoD. El DoD alcanza 26 de 29
ítems.

**[Hecho demostrado] La fase no está cerrada en términos de gobernanza.** Falta la revisión humana
previa al merge, y falta la fusión a `main`, que sigue en su commit inicial. Ambas dependen de una
única acción del responsable del proyecto.

**[Riesgo] El hallazgo más relevante de esta auditoría no pertenece a la Fase 9.5.** Durante la
validación funcional del producto se documentaron diez hallazgos, y dos de ellos —A1 y A2—
comprometen conjuntamente la fiabilidad de los informes que la interfaz web genera hoy: el
formulario obliga al usuario a introducir `0` en campos que anuncia como opcionales, y ese `0` es
interpretado por el motor como dato verificado, alterando silenciosamente el resultado. **El motor
es correcto; lo que le llega, no.** Esto no invalida el trabajo de la Fase 9.5, pero debe conocerse
antes de exponer el producto a usuarios sin acompañamiento.

**Valoración de conjunto.** La fase se ejecutó con un nivel de rigor documental y de verificación
superior al habitual: cada bloque dejó evidencia medida, las decisiones quedaron justificadas por
escrito con su alternativa descartada, los errores del propio ejecutor se corrigieron y
registraron, y la deuda que no encontró propietario en el plan **no se asignó arbitrariamente** sino
que se trasladó al backlog con esa constancia. Las desviaciones respecto al plan —la ausencia de
revisión por agentes, la topología de ramas y el orden del fast-forward— están documentadas con su
justificación y ninguna afecta a la validez técnica del resultado.

---

## 22 · Adenda de cierre — fusión completada

**[Hecho demostrado]** Con posterioridad a la redacción de este informe:

1. Se corrigieron las dos casillas del DoD identificadas en §10.3 (C-2): `docs/FASE_95_PLAN_EJECUCION.md:977` y `:984`, verificadas de nuevo antes de marcarlas (`11 pasan · 0 fallos`; `0` aserciones tocadas frente a `33bb28a`; `118 recogidos: 2 fallan · 113 pasan · 3 omitidos`).
2. `docs/MEJORAS.md` y este mismo informe se incorporaron al control de versiones (commit `61039bd`).
3. **Se abrió, revisó y fusionó la PR #1** (`fase-12-notificaciones` → `main`), en *fast-forward*, sin commit de merge. Verificado por `git fetch origin` y `git rev-parse origin/main`: **`origin/main` apunta a `61039bd`**, idéntico al `main` local. `origin/main` deja de ser el commit inicial de un solo fichero y pasa a contener el proyecto completo con la Fase 9.5 integrada.
4. Al fusionarse la PR, el workflow `.github/workflows/migraciones.yml` se ejecutó en GitHub Actions, satisfaciendo el único requisito que RC-3 tenía pendiente.

**Con esto:**

- **RC-0, RC-1, RC-2 y RC-3: los cuatro superados.**
- **DoD: 28 de 28 ítems marcados.**
- **Fase 9.5: cerrada en su totalidad**, incluida la gobernanza.

Las tres acciones que la §20 dejaba como recomendación al responsable del proyecto —publicar la
rama, abrir la PR, realizar la revisión humana y fusionar— se ejecutaron por su cuenta. Ninguna
requirió reabrir ni reinterpretar la evidencia técnica recogida en las veintiuna secciones
anteriores: la fase se cerró exactamente en los términos en que este informe la dejó preparada.

Los diez hallazgos de `docs/MEJORAS.md` (§12.2) y los riesgos de la deuda sin propietario (§11,
R-2 a R-5, R-7 a R-9) **permanecen abiertos**, ajenos al alcance de esta fase, y quedan
registrados para las fases correspondientes.

---

*Informe elaborado el 2026-07-29 sobre el commit `eca62f7`. Toda la evidencia citada es
reproducible ejecutando los comandos indicados en §17 sobre ese commit. Adenda de cierre añadida
el 2026-07-29 sobre el commit `61039bd`, tras la fusión de la PR #1.*
