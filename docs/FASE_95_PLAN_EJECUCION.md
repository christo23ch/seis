# FASE 9.5 — Saneamiento del sistema de migraciones
## Plan de ejecución canónico

**Fecha:** 2026-07-26 · **Versión:** 1.0 — documento canónico de la fase
**Rama:** `fase-95-saneamiento-migraciones`
**Ruta crítica:** 9 → **9.5** → 10 → 11 → 13 → 20
**Estado:** aprobado y **ejecutable**. Único bloqueante de ejecutabilidad cerrado con validación
empírica (2026-07-26).

**Documentos relacionados**
- [`PLAN_REPARACION_MIGRACIONES.md`](PLAN_REPARACION_MIGRACIONES.md) — estrategia y diseño de la
  reparación. **Este documento es el plan de ejecución**; aquel es el porqué.
- [`FASE_13_PLAN_EJECUCION.md`](FASE_13_PLAN_EJECUCION.md) — fase bloqueada por esta.
- [`PENDIENTES.md`](PENDIENTES.md) — Fase 10, bloqueada por esta.

> **Arquitectura cerrada.** La elección de la Alternativa B (revisión fundacional limpia) y la
> creación de la Fase 9.5 son decisiones aprobadas y no se reabren en la ejecución.
>
> *Nomenclatura: una versión previa del documento de diseño llamaba «Alternativa D» a esta misma
> estrategia, antes de que el ARB reformulara la decisión a dos opciones. Son la misma. De ahí el
> prefijo histórico de los códigos de riesgo `R-D*`.*

---

## 1 · Objeto y encuadre

Fase de saneamiento, no de producto. No añade capacidad al usuario final: retira un bloqueo que
impide arrancar el sistema en instalación nueva y que bloquea a las Fases 10 y 13.

**Sustituye las cuatro revisiones existentes por una sola revisión fundacional con DDL explícita
del esquema actual completo (21 tablas).**

---

## 2 · Base probatoria

Clasificación explícita. No se opera sobre suposiciones sin marcarlas.

### Hechos demostrados

| # | Hecho | Evidencia |
|---|---|---|
| H1 | `alembic upgrade head` falla sobre base limpia, en la revisión **0002** | `IntegrityError: NOT NULL constraint failed: organizacion.creado_en`, en `0002_multitenancy.py:71` |
| H2 | La **0004** falla independientemente en SQLite | `OperationalError: near "ALTER": syntax error` |
| H3 | `render_as_batch=True` **no repara** `alter_column`; solo `op.batch_alter_table()` ejecuta | Cuatro escenarios contrastados |
| H4 | La causa raíz es `Base.metadata.create_all()` en `0001:18` | DDL volcada + guarda de `0002:41` verificada |
| H5 | La suite de 104 tests **no ejerce Alembic** | `conftest.py:64` usa `create_all` |
| H6 | `models.py`: 7 `default=_now`, 9 `default=_uuid`, **0 `server_default`**, 21 tablas | Recuento |
| H7 | `autogenerate` contra base vacía con 0001-0004 presentes **aborta siempre** | `CommandError: Target database is not up to date.` — `alembic/autogenerate/api.py:605-608` |
| H8 | `version_locations` a directorio vacío **genera `down_revision = None` de forma nativa** | Ejecutado; 21 tablas, 19 columnas JSONB |
| H9 | `autogenerate` **preserva la variante JSONB** en las 19 columnas `PortableJSON` | `sa.JSON().with_variant(postgresql.JSONB(...), 'postgresql')` — 19 de 19 |
| H10 | `autogenerate` asigna un **identificador hexadecimal aleatorio**, nunca `0005` | Fichero generado: `revision = '90f725c3ba9f'` |
| H11 | Una BD que falló al aplicar la 0002 **queda stampeada en `0001`** — *en SQLite* | `alembic current` sobre la base de la verificación |

### Inferencias (no medidas)

| # | Inferencia | Fundamento | Se eleva a hecho en |
|---|---|---|---|
| I1 | El backend **no arranca sobre volumen limpio** | `docker-compose.yml:56` encadena con `&&` (medido) + fallo de la 0002 en PostgreSQL (deducido: el `INSERT` textual crudo no recibe defaults de lado Python en ningún motor) | **Bloque H** |
| I2 | En **PostgreSQL** el fallo de la 0002 revertiría también el stamp de la 0001, dejando la base sin stampear | `env.py:30-33` no fija `transaction_per_migration`; la cadena corre en una transacción única. Lectura de código, no medición | No se eleva; no es necesario |

### Decisiones estratégicas cerradas

| # | Decisión | Origen |
|---|---|---|
| E1 | **No existe base de datos que preservar.** Se acepta romper compatibilidad con instalaciones de desarrollo | Responsable del proyecto |
| E2 | Alternativa B — revisión fundacional limpia | ARB |
| E3 | Fase propia 9.5, no absorbida por la Fase 10 | ARB |
| E4 | Numeración: fundacional `0005`; Fase 10 → `0006`; Fase 13 → `0007` | ARB |

---

## 3 · Precondición de fase

**PRE-1 · Entorno de verificación resuelto.** Antes de abrir el Bloque A debe existir y estar
documentado un entorno capaz de ejecutar **PostgreSQL real** y **Docker Compose**.

| Opción | Cubre |
|---|---|
| Docker Desktop local | PRE-1 completa, incluido el Bloque H |
| Runner de CI con servicio PostgreSQL | Evidencia JSONB y RC-2; el Bloque H depende de si el runner levanta la composición |
| PostgreSQL gestionado accesible en local | Evidencia JSONB; **deja el Bloque H sin cubrir** |

**Regla de honestidad:** si no se dispuso de Docker, **el Bloque H no se marca como superado ni se
declara cerrada I1**. Se consigna como pendiente explícito. No se admite darlo por bueno por
inferencia — es el error que esta fase corrige.

**PRE-2 · Secretos de `.env` generados.** Prerequisito **del Bloque H**, no de la fase completa:
puede satisfacerse en cualquier momento anterior a ese bloque.

`.env.example` entrega `JWT_SECRET`, `ADMIN_PASSWORD` y `POSTGRES_PASSWORD` **vacíos a propósito**,
y `docker-compose.yml` los declara obligatorios sin respaldo embebido
(`${POSTGRES_PASSWORD:?Defina POSTGRES_PASSWORD en .env antes de arrancar}`). Sin generarlos, la
composición no levanta y el Bloque H no puede ejecutarse. Con `SEIS_ENV=production` el arranque
además aborta si los secretos son cortos, poco variados o contienen marcadores de plantilla
(`app/core/config.py`, `_validar_seguridad_produccion`).

**Verificable:** existe un `.env` con los tres secretos no vacíos y la composición levanta. No es
condición para abrir el Bloque A.

---

## 4 · Bloques de trabajo

### Bloque A — Batería de tests de migraciones, en rojo

**Objetivo.** Construir `test_migraciones.py` (T1-T6) y **verla fallar** con el error exacto de H1.
Es el instrumento de medida de la fase: se calibra antes de usarse.

**Archivos.** `backend/tests/test_migraciones.py` (nuevo) · posible fixture de base desechable, sin
tocar la fixture `api` existente.

**Dependencias.** Ninguna.

**Riesgos.** Que la batería nazca en verde. Contaminar la fixture `api` y romper los 104 tests.

**Aislamiento de la base — riesgo destructivo, no solo de corrección.** `env.py:14` sobrescribe
`sqlalchemy.url` con `get_settings().database_url`, y `get_settings()` está cacheada: **una URL
pasada por objeto `Config` será ignorada sin aviso**. Y **T2 ejecuta `downgrade base`, cuyo
`downgrade` en la 0001 antigua es `Base.metadata.drop_all`** — con el aislamiento mal resuelto, el
Bloque A borra las tablas de la base que resuelva `DATABASE_URL`. E1 hace tolerable la pérdida,
pero el fallo es silencioso y ocurre antes de cualquier paso destructivo *por diseño* de la fase.

El aislamiento debe lograrse fijando `DATABASE_URL` en el entorno **antes** de que se importe
`app.core.config`, o ejecutando Alembic en subproceso.

> **Nota:** `alembic.ini:4` (`sqlalchemy.url = sqlite:///./seis_dev.db`) es **línea muerta** —
> `env.py:14` la sobrescribe siempre. Editarla no redirige nada. Es el primer sitio donde alguien
> intentará resolver el aislamiento, y no funciona.

**Criterios de aceptación.**
- T1 falla con `IntegrityError: NOT NULL constraint failed: organizacion.creado_en` — no con error
  de importación ni de fixture.
- La suite existente sigue en **102/104**.
- **Guarda de aislamiento verificable:** la batería comprueba, **antes de ejecutar ninguna
  migración**, que la URL efectiva que Alembic va a usar coincide con la ruta desechable esperada, y
  **aborta sin ejecutar nada** si no coincide.
- **La guarda está demostrada:** se comprueba que salta apuntando deliberadamente a otra ruta, y se
  revierte. *(Misma disciplina que la prueba de mutación de T4: una guarda que nunca ha saltado no
  prueba nada.)*

**Pruebas.** Ejecución mostrando rojo con el error esperado.

**Agentes ECC.** `tdd-guide` · `python-reviewer` al cierre.

**Graphify.** No.

---

### Bloque B — Generación de la revisión fundacional

**Objetivo.** Producir por autogenerate la DDL explícita de las 21 tablas.

**Archivos.** `backend/alembic/versions/0005_esquema_base.py` (nuevo).

**Dependencias.** A.

#### Procedimiento validado — obligatorio

> El procedimiento «autogenerate contra base vacía» **aborta de forma determinista** (H7). Alembic
> compara la revisión de la base contra las cabezas del directorio de scripts, y ninguna
> combinación de `--head=base`, `--splice` ni `--version-path` lo evita: esos flags determinan
> dónde se engancha la revisión nueva, no qué ve Alembic.

1. Crear un **`alembic.ini` desechable** fuera del repositorio, copia del real, con
   `version_locations` apuntando a un **directorio vacío**. El `alembic.ini` del repositorio **no
   se modifica en ningún momento**, de modo que no queda configuración que revertir.
2. Base de datos vacía; `DATABASE_URL` fijada en el entorno hacia ella.
3. `alembic -c <ini desechable> revision --autogenerate`.
   Con cabezas `= ∅` y base en `base`, los conjuntos coinciden y la generación procede.
4. **Fijar el identificador manualmente a `0005`.** Autogenerate asigna un hexadecimal aleatorio
   (H10). `down_revision` ya sale `None` de forma nativa (H8) y **no requiere edición**.
5. **Renombrar el fichero a `0005_esquema_base.py`.** `alembic.ini` no define `file_template`, de
   modo que el fichero nace con el hexadecimal en el nombre —observado:
   `90f725c3ba9f_esquema_base.py`—. Son **dos** correcciones manuales, no una: el identificador
   *dentro* del fichero y el nombre *del* fichero.
6. Trasladarlo a `backend/alembic/versions/`.

**Descartado: `stamp head`.** Funciona, pero exige escribir un estado falso en `alembic_version`
—declarar la base al día en `0004` cuando no tiene ni una tabla— y genera `down_revision = '0004'`,
añadiendo un paso manual cuyo olvido deja la revisión colgando de una cadena que el Bloque D va a
borrar: fallo silencioso al generar, ruidoso mucho después.

**Riesgos.** Omitir el paso 4 y dejar el identificador hexadecimal, incumpliendo E4.

**Criterios de aceptación.** Existe el fichero · 21 tablas · `revision = "0005"` ·
`down_revision = None`. **El bloque no se cierra aquí**: su validación es el Bloque C.

**Agentes ECC.** Ninguno. Paso mecánico.

**Graphify.** No.

---

### Bloque C — Auditoría humana de la DDL generada

**Objetivo.** Revisar línea a línea lo generado. **Es el bloque de mayor valor de la fase y el
menos automatizable.**

**Archivos.** `0005_esquema_base.py` (revisión).

**Dependencias.** B.

**Riesgos.** Revisión superficial que da por bueno el autogenerate. **R-D5**: autogenerate omite lo
que no sabe detectar —CHECK, índices parciales, restricciones con nombre—, y **T4 no puede
cubrirlo** (§6): esta revisión humana es la única barrera.

**Criterios de aceptación** *(todos contables)*
- **Inventario de las 19 columnas `PortableJSON`**: tabla, columna y tipo renderizado. Las 19
  presentes, todas con la variante JSONB.
- **Recuento de índices y claves foráneas** igual al derivado de `models.py`.
- **Recuento de tablas = 21**; orden de `drop` del `downgrade` igual al inverso de
  `metadata.sorted_tables`.
- **El docstring enumera las 7 columnas con default de lado Python** y declara que toda migración
  con DML debe suministrarlas.

**Si RC-1 rechaza la DDL — procedimiento único.** **Se regenera desde el Bloque B. No se parchea a
mano el artefacto generado.** Sin excepciones, y sea cual sea el defecto detectado:

- si el defecto está en `models.py`, se corrige `models.py` y **luego** se regenera;
- si el defecto está en el renderizado, se regenera y se ajusta lo que proceda en la generación.

**Motivo:** el fichero es un artefacto generado y su valor entero descansa en corresponderse con
`models.py`. Parches manuales acumulados rompen esa correspondencia, la vuelven inauditable y
degradan T4 —que compara DDL ejecutada contra `create_all`— a un test que valida un fichero que ya
nadie sabe de dónde viene. El coste de regenerar es reaplicar los dos pasos manuales del Bloque B
(identificador y nombre de fichero).

**No se admite «corregir solo esta línea».** Es la decisión que evita improvisar bajo presión en el
checkpoint más crítico de la fase.

**Agentes ECC.** `database-reviewer` · `python-reviewer` en segunda pasada.

**Graphify.** Marginal, no recomendado: `metadata.sorted_tables` es autoritativo y más barato.

---

### Bloque D — Retirada de la historia antigua

**Objetivo.** Eliminar 0001-0004. Su contenido persiste en git; se retira el camino de ejecución.

**Archivos.** Las cuatro revisiones, eliminadas.

**Dependencias.** C. **No se retira lo viejo hasta que lo nuevo está auditado.**

**Riesgos.** Retirar antes de tiempo y quedarse sin ninguna cadena aplicable. Residuos
`__pycache__` que Alembic siga descubriendo.

**Nota operativa.** Entre C y D el directorio tiene **dos raíces** —`0001` y `0005`— y por tanto
dos cabezas: cualquier `alembic upgrade head` fallará con *«multiple heads»*. Es transitorio,
esperado, y se resuelve al completar D. No es una regresión.

**Punto de retorno de la ventana D→E.** Es el único tramo de la fase en que la cadena antigua ya no
está en el árbol de trabajo y la nueva todavía no se ha verificado. El retorno está definido y es
determinista:

| Situación | Retorno |
|---|---|
| La retirada aún **no se ha confirmado** en git | `git restore` de las cuatro revisiones. Recuperación completa, coste nulo |
| La retirada **ya está confirmada** en la rama | `git revert` del cambio que las retiró. Las cuatro vuelven al árbol de trabajo |
| Base de datos desechable en cualquier estado | Se descarta y se recrea. **Nunca se repara** |

**El retorno no requiere ninguna operación sobre datos**: las cuatro revisiones viven en git desde
el primer commit de la fase, y las bases implicadas son desechables por construcción. Esto es lo
que hace que RC-1 sea «el último punto de marcha atrás barata»: a partir de D el retorno sigue
siendo posible, pero deja de ser gratuito porque obliga a repetir la auditoría.

**Criterios de aceptación.** `alembic history` muestra una sola revisión · ningún fichero bajo
`versions/` referencia `Base.metadata` ni `create_all`.

**Agentes ECC.** `refactor-cleaner`.

**Graphify.** No.

---

### Bloque E — Verificación en SQLite

**Objetivo.** T1, T2, T3 y T6 en verde. La batería pasa de roja a verde **por reparación real**.

**Dependencias.** D · paralelizable con F.

**Riesgos.** Ajustar la batería para que pase en lugar de reparar la causa.

**Criterios de aceptación.** `upgrade head` desde vacío y `downgrade base` verdes · idempotencia
verde · **el texto de las aserciones de toda la batería (T1-T6) es byte-idéntico al del Bloque A**;
el diff del fichero entre ambos momentos **no contiene ninguna línea eliminada ni modificada dentro
de una aserción, solo añadidos**. *(Definición operativa única de «no debilitada»: se aplica a los
seis tests, no solo a los que este bloque ejercita, y es la que invocan RC-2 y el DoD.)*

**Agentes ECC.** `tdd-guide` · `silent-failure-hunter`.

**Graphify.** No.

---

### Bloque F — Verificación en PostgreSQL y confirmación JSONB

**Objetivo.** T5 en verde contra PostgreSQL real y volcado de tipos.

**Dependencias.** D · paralelizable con E.

**Riesgos.** Omitir el bloque por no tener PostgreSQL a mano — **el patrón exacto que produjo el
defecto original**. Que el *skip* de T5 sin PostgreSQL pase inadvertido en CI.

**Naturaleza de la comprobación.** Tras H9, esto **confirma un resultado esperado**; ya no contiene
un riesgo abierto. El criterio se mantiene: lo demostrado es que el **código generado** conserva la
variante, no que la **DDL ejecutada** produzca `jsonb`.

**Criterios de aceptación.** `upgrade head` y `downgrade base` verdes en PostgreSQL · **las 19
columnas son `jsonb`**, verificado por consulta de tipos con salida archivada · el *skip* de T5 es
visible.

**Agentes ECC.** `database-reviewer`.

**Graphify.** No.

---

### Bloque G — Test de deriva y prueba de mutación

**Objetivo.** Consolidar T4 y **demostrar que sabe fallar**.

**Archivos.** `test_migraciones.py` (T4 — creado en el Bloque A junto con el resto de la batería;
aquí se consolida y se somete a prueba de mutación).

**Dependencias.** E · paralelizable con F.

**Riesgos.** **Un T4 vacuo.** Una comparación que ignore tipos, nulabilidad o índices pasa siempre
y da falsa seguridad permanente.

**Alcance de T4, delimitado**

| T4 **sí** cubre | T4 **no** cubre |
|---|---|
| Divergencias de renderizado sobre metadata común — incluida la degradación de variantes | Elementos ausentes de `models.py`: CHECK, índices parciales, restricciones con nombre → **RC-1** |
| Deriva futura entre `models.py` y las migraciones | Que `models.py` represente el esquema pretendido |

**Criterios de aceptación.** T4 verde · **T4 demostrado en rojo** ante una divergencia introducida
a propósito y revertida · la comparación cubre tablas, columnas, tipos, nulabilidad e índices.

**Agentes ECC.** `tdd-guide` · `pr-test-analyzer`.

**Graphify.** No.

---

### Bloque H — Verificación de arranque en Docker

**Objetivo.** Elevar I1 a hecho: `docker compose down -v && up --build` sobre volumen limpio
levanta el backend.

**Dependencias.** F.

**Riesgos.** Ejecutar `down` sin `-v` y validar contra un volumen antiguo → verde falso.

**Criterios de aceptación.** Backend respondiendo en `/api/v1/health` tras arranque sobre volumen
destruido · evidencia de que el volumen se destruyó.

**Agentes ECC.** `build-error-resolver` solo si el arranque falla.

**Graphify.** No.

---

### Bloque I — Barreras anti-recurrencia

**Objetivo.** Que el defecto no pueda reintroducirse.

**Archivos.** `CLAUDE.md` §6 · configuración de CI · `backend/alembic/env.py`.

**Dependencias.** G. No se cablea a CI un test no demostrado.

**Riesgos.** Documentar `render_as_batch` como el arreglo que no es (H3) — reintroduce una creencia
ya desmentida en este proyecto.

**Criterios de aceptación.**
- `CLAUDE.md` §6 contiene: **(1)** prohibido `Base.metadata` en `alembic/versions/`;
  **(2) toda DML de migración especifica explícitamente cada columna `NOT NULL`**.
- T4 en el pipeline, no solo en el repositorio.
- `render_as_batch` documentado con precisión: **preventivo de autogenerate, jamás correctivo**.

**Agentes ECC.** `doc-updater` · `code-reviewer` al cierre.

**Graphify.** No.

---

### Bloque J — Saneamiento documental y renumeración

**Objetivo.** Que ningún documento siga afirmando lo que la verificación desmiente.

**Archivos.** `docs/PENDIENTES.md` (líneas 29, 38, 134) · `CLAUDE.md` **§§2, 3, 5, 6, 7** ·
`README.md` · `docs/FASE_13_PLAN_EJECUCION.md` · `docs/PLAN_REPARACION_MIGRACIONES.md` ·
procedimiento de recreación.

> **Propagación mínima ya adelantada** (rama de planificación, antes de abrir el PR):
> **`CLAUDE.md` §5** (ruta crítica y renumeración) y la **tabla de fases de `README.md`** ya se
> corrigieron, para que el contexto maestro del proyecto —que se carga en cada sesión de trabajo—
> no siguiera apuntando a una ruta crítica y una numeración derogadas. **El resto sigue pendiente
> en este bloque.**
>
> `CLAUDE.md` §5 no figuraba en el alcance original de este bloque, que se limitaba a §§2, 3, 6 y 7.
> Era un defecto: la contradicción más directa con la renumeración vivía precisamente en §5, de modo
> que cumplir el DoD al pie de la letra habría cerrado la fase dejando en pie el error que la
> motiva.

**Dependencias.** H e I. La documentación describe hechos verificados.

**Criterios de aceptación.**
- Renumeración propagada: **Fase 10 → `0006`; Fase 13 → `0007`** con `down_revision = "0006"`.
- `PENDIENTES.md:134` corregido — la 0004 **no** puede ejecutarse en SQLite.
- `CLAUDE.md` §2 **y `README.md`**: retirar la declaración de PostGIS geoespacial — **no hay columna
  geométrica ni dependencia de `geoalchemy2`**; `lat`/`lng` son `Numeric(9,6)`. `README.md` contiene
  además la afirmación de que la migración a `geometry(Point,4326)` ocurre «hasta la Fase 5», que
  figura como completada: no ha ocurrido.
- `CLAUDE.md` §7 sin advertencia pendiente.
- Procedimiento de recreación (§9) publicado y comunicado.
- `FASE_13_PLAN_EJECUCION.md` anota que su corrección **B3 es consumidora** de la convención de DML.

**Agentes ECC.** `doc-updater` · `comment-analyzer`.

**Graphify.** Marginal.

---

### Nota sobre Graphify

**No aporta valor en ninguno de los diez bloques.** Rinde cuando hay que comprender una superficie
amplia o desconocida; aquí ocurre lo contrario: el área está exhaustivamente caracterizada por
cuatro dictámenes previos, con ficheros, líneas y causas identificados, sobre ~12 ficheros.

---

## 5 · Paralelismo

```
A ──► B ──► C ──► D ──┬──► E ──┬──► G ──► I ──┐
                      │        │             ├──► J
                      └──► F ──┴──► H ────────┘
```

**En paralelo:** E ‖ F (motores y bases distintos) · F ‖ G (G necesita E, no F).

**Secuenciales obligados:** A→B (calibración antes de medición) · B→C · **C→D** (no se retira lo
antiguo sin auditar lo nuevo) · E→G · F→H · H,I→J.

**Cadena crítica:** A → B → C → D → E → G → I → J.

---

## 6 · Checkpoints del Release Committee

### RC-0 · Calibración — tras A
**Evidencia:** salida mostrando el error de H1; confirmación de que no es error de importación ni
de fixture; suite en 102/104.
**Bloquea si:** la batería nace en verde · falla por otro motivo · contamina la fixture `api`.

### RC-1 · Auditoría de la DDL — tras C
**El checkpoint más importante.** Último punto de marcha atrás barata, previo a la retirada de la
historia antigua — el retorno posterior está definido en el Bloque D.
**Evidencia:** los cuatro inventarios contables del Bloque C · constancia de revisión de R-D5,
que T4 no cubre.
**Bloquea si:** falta cualquiera de los inventarios · **cualquier duda no resuelta**.
**Si rechaza:** se regenera desde el Bloque B. **No se parchea a mano el artefacto generado**
(procedimiento único, Bloque C).

### RC-2 · Evidencia de ejecución — tras H
**Evidencia:** `upgrade head` y `downgrade base` literales en **ambos motores** · `alembic history`
con una sola revisión · volcado de tipos con `jsonb` en las 19 columnas · prueba de que una BD
stampeada en revisión antigua falla ruidosamente · Docker sobre volumen limpio con `/health`
respondiendo · aserciones no debilitadas.
**Bloquea si:** falta evidencia PostgreSQL · Docker no verificado sobre volumen destruido · alguna
BD antigua es aceptada en silencio.

> **Cómo producir la evidencia del stamp obsoleto** *(guía de validación, no requisito adicional).*
> Tras el Bloque D las revisiones antiguas ya no existen, de modo que **ese estado no puede
> generarse ejecutando la cadena**: hay que fabricarlo escribiendo a mano el valor `0004` en la
> tabla `alembic_version` de una base desechable, y comprobar después que cualquier orden de Alembic
> falla al no poder localizar la revisión. En PostgreSQL tampoco surge de forma natural (I2), así
> que la fabricación manual es el único camino en ambos motores. Esta nota no añade exigencia: el
> criterio ya figuraba en la evidencia de RC-2; solo elimina la ambigüedad sobre cómo satisfacerlo.

### RC-3 · Pase final — tras J
**Evidencia:** T4 demostrado en rojo · T4 en CI · convenciones en `CLAUDE.md` §6 · búsquedas de
`Base.metadata` y `create_all` sin resultados · renumeración propagada · procedimiento de
recreación comunicado.
**Bloquea si:** T4 no ha demostrado saber fallar · T4 no está en CI · algún documento contradice a
otro · `render_as_batch` documentado como correctivo.

---

## 7 · Órdenes

### Implementación
`A → B → C → D → (E ‖ F) → G → H → I → J`

con hitos: **RC-0** tras A · **RC-1** tras C ⛔ · **RC-2** tras H · **RC-3** tras J.

*El paso 1 va primero por método: una batería escrita después de reparar produce tests que pasan
sin haber demostrado nunca que saben detectar el fallo.*

### Revisión — sigue el riesgo, no la implementación

| # | Qué | Quién | Cuándo |
|---|---|---|---|
| 1 | DDL fundacional — las 19 columnas primero | `database-reviewer` → `python-reviewer` | C, antes de RC-1 |
| 2 | ¿La batería mide lo que dice medir? | `pr-test-analyzer` | Tras G |
| 3 | Retirada de la historia: residuos, referencias colgantes | `refactor-cleaner` | Tras D |
| 4 | Rutas de fallo silencioso | `silent-failure-hunter` | Tras E |
| 5 | Convenciones y CI | `code-reviewer` | I |
| 6 | Coherencia documental | `doc-updater` → `comment-analyzer` | J, antes de RC-3 |
| 7 | Revisión humana final | Responsable | Antes del merge |

### Merge

**PR único.** Ficheros afectados: **≥12**. La justificación no es el recuento sino la coherencia
temática —un solo asunto, indivisible sin dejar la cadena en estado inaplicable— y un volumen muy
inferior al que hizo inrevisable el PR de la Fase 13.

**Secuencia entre ramas:**

| # | Rama | Condición |
|---|---|---|
| 1 | `fase-95-saneamiento-migraciones` → `main` | RC-0…RC-3 + revisión humana |
| 2 | *(bloqueo)* | Ninguna rama que toque `alembic/versions/` se fusiona antes |
| 3 | Fase 10 (`0006`) | Parte de `main` posterior al merge de 9.5 |
| 4 | Fase 13 (`0007`) | Parte de `main` posterior al merge de Fase 10 |

**Regla de congelación, con síntoma.** Desde el inicio del Bloque D hasta el merge,
`alembic/versions/` queda congelado para toda otra rama. **Síntoma del incumplimiento:**
`alembic upgrade head` falla con *«The script directory has multiple heads»*. Fase 10 y Fase 13 no
pueden colgar ambas de la fundacional: `0007` cuelga de `0006`, nunca de `0005`.

---

## 8 · Matriz de riesgos

> **Aviso de nomenclatura.** `P0`, `P1` y `P2` designan aquí **niveles de severidad de riesgo** de
> esta fase. **No confundir con los principios `P1`-`P10` de la especificación del proyecto**
> (`P1` determinismo, `P4` la ausencia de datos penaliza, `P6` vetos antes que promedios…), que son
> otra cosa y conviven en `CLAUDE.md` y `README.md`. Cuando este documento cita un principio, lo
> nombra («principio P1 del proyecto»); cuando cita una severidad, usa el código con guion
> (`P0-1`, `P1-3`).

### P0 — bloquean la fase

| # | Riesgo | Bloque | Contención |
|---|---|---|---|
| **P0-1** | **T4 vacuo** — la barrera anti-recurrencia nace rota y da falsa seguridad permanente | G | Prueba de mutación obligatoria en RC-3 |
| **P0-2** | **Reutilizar el identificador `0001`** → una BD stampeada en `0001` se considera al día conservando un esquema parcial. **Alcance del fundamento: SQLite** (H11 medido). En PostgreSQL el fallo revertiría también ese stamp (I2, inferido). **La restricción se mantiene**: SQLite es el caso local habitual y el seguro cuesta cero | B | Identificador `0005`; prueba de stamp obsoleto en RC-2 |
| **P0-3** | **Batería nacida en verde** — todo lo verde posterior carece de valor probatorio | A | RC-0 |
| **P0-4** | **Retirar 0001-0004 antes de auditar la fundacional** → sin ninguna cadena aplicable | D | Dependencia dura C→D; RC-1 como puerta |

> **Retirado de P0:** la degradación de la variante JSONB en autogenerate. El mecanismo temido
> quedó **refutado empíricamente** (H9): 19 de 19 columnas conservan la variante. La comprobación
> del Bloque F se mantiene, reclasificada como **confirmación**, no como contención.

### P1 — antes de cerrar

| # | Riesgo | Bloque |
|---|---|---|
| **P1-1** | **RM1 sobrevive**: 7 columnas con default de lado Python, 0 `server_default`. El backfill de Fase 10 y el de Fase 13 siguen expuestos al patrón que rompió la 0002. **La Alternativa B lo esconde en vez de forzar a corregirlo** | I, J |
| **P1-2** | Omisiones de autogenerate (CHECK, índices parciales, restricciones con nombre). **T4 no las cubre** | C / RC-1 |
| **P1-3** | Verificación solo en SQLite — el patrón que produjo el defecto original | F |
| **P1-4** | `render_as_batch` documentado como correctivo | I |
| **P1-5** | Documentación contradictoria entre `CLAUDE.md`, `PENDIENTES.md` y los planes de Fase 10 y 13 | J |
| **P1-6** | Verde falso en Docker por `down` sin `-v` | H |

### P2 — se documentan

| # | Riesgo | Destino |
|---|---|---|
| **P2-1** | **RM3**: el primer `ALTER COLUMN` futuro reincidirá en SQLite sin modo batch | Convención |
| **P2-2** | `Auditoria.entidad_id` es `String(36)`; los ids de Checkout Session rondan 66-70 caracteres | Precondición de Fase 13 |
| **P2-3** | `CLAUDE.md` §2 **y `README.md`** declaran PostGIS sin columna geométrica ni `geoalchemy2` | Corrección en J |
| **P2-4** | Divergencia tests ↔ migraciones persiste mientras `conftest` use `create_all` | T4 la hace detectable |
| **P2-5** | **RM7**: el arranque del servicio está acoplado a las migraciones por el `&&` | Fase 11 |

---

## 9 · Procedimiento de recreación de entornos

> Aplicable **tras** el merge. Autorizado por E1.

**La vía de stamp cubre más entornos de lo que se suponía:** la 0001 antigua ejecutaba `create_all`
con el `models.py` actual, y las guardas de la 0002 impidieron aplicar nada antes del `INSERT` que
falló. **Una BD stampeada en `0001` tiene ya el esquema actual completo.**

**Vía 1 — Stamp (no destructiva).** Para entornos cuyo esquema coincide con el actual: los creados
por `scripts/init_db.py` y los stampeados en `0001`. Exige **verificación previa del esquema**; si
coincide, `alembic stamp --purge` a la revisión fundacional. **`--purge` es obligatorio**: sin él
Alembic intenta resolver la revisión actual, que ya no existirá, y falla.

**Vía 2 — Recreación (destructiva).** Vía por defecto, y única recomendada para quien no verifique
el esquema o cuyo entorno preceda a la Fase 12.
- SQLite: eliminar **todos** los `.db` bajo `backend/` y `alembic upgrade head`.
- Docker: `docker compose down -v` —**la bandera destruye el volumen**— y `up -d --build`.

**Regla:** ante cualquier duda sobre la correspondencia del esquema, **vía 2**. Un stamp incorrecto
produce una base que Alembic considera al día con un esquema que no lo está: exactamente la
corrupción silenciosa que esta fase erradica.

**Síntomas esperados**

| Síntoma | Significado | Acción |
|---|---|---|
| `Can't locate revision identified by '0004'` | BD anterior a la reparación. **Fallo ruidoso buscado** | Vía 1 o 2 |
| El contenedor arranca y muere | Volumen antiguo; `down` sin `-v` | Vía 2 con `-v` |
| `alembic current` vacío | BD sin stampear | `upgrade head` |
| `alembic current` muestra `0001` | BD que falló al aplicar la 0002 | Vía 1 tras verificar, o vía 2 |
| Tests verdes, aplicación rota | Esperado: los tests no pasan por Alembic | Vía 2 |

---

## 10 · Definition of Done

**Ejecución**
- [ ] `alembic upgrade head` desde base vacía: verde en **SQLite y PostgreSQL**
- [ ] `alembic downgrade base`: verde en ambos motores
- [ ] `alembic history`: **una sola revisión**, `down_revision = None`, identificador `0005`
- [ ] `alembic heads` devuelve **exactamente una cabeza**
- [ ] Una BD stampeada en `0001`-`0004` falla **de forma ruidosa**
- [ ] `docker compose down -v && up -d --build` sobre volumen limpio: backend en `/api/v1/health`

**Corrección del esquema**
- [ ] Las **19 columnas `PortableJSON` son `jsonb`** en PostgreSQL, con volcado archivado
- [ ] Índices, FKs y tipos verificados contra `create_all` por T4

**Instrumentación**
- [ ] T1-T6 en verde, **sin aserciones debilitadas** respecto del Bloque A
- [ ] **T4 demostrado capaz de fallar**
- [ ] **Guarda de aislamiento de la batería en su sitio y demostrada capaz de saltar**
- [ ] T4 en el pipeline de CI
- [ ] Suite existente en **102/104** (los 2 rojos de PDF, preexistentes y ajenos)

**Barreras**
- [ ] `CLAUDE.md` §6: prohibido `Base.metadata` en `alembic/versions/`
- [ ] `CLAUDE.md` §6: toda DML de migración especifica cada columna `NOT NULL`
- [ ] Búsquedas de `Base.metadata` y `create_all` en `versions/`: sin resultados
- [ ] `render_as_batch` documentado como preventivo, **nunca como correctivo**

**Documentación**
- [ ] `PENDIENTES.md` líneas 29, 38 y 134 corregidas
- [ ] `CLAUDE.md` §§2, 3, 6, 7 corregidos *(§5 ya propagada en la rama de planificación)*
- [ ] `README.md` corregido: PostGIS *(la tabla de fases ya se propagó en la rama de planificación)*
- [ ] Renumeración propagada: Fase 10 → `0006`, Fase 13 → `0007`
- [ ] Plan de Fase 13 anota que su corrección B3 consume la convención de DML
- [ ] Procedimiento de recreación publicado, **con ambas vías** y `--purge` documentado

**Gobernanza**
- [ ] RC-0, RC-1, RC-2, RC-3 superados en orden
- [ ] Revisión humana previa al merge
- [ ] PRE-1 satisfecha, o Bloque H consignado como no superado con I1 sin cerrar
- [ ] **PRE-2 satisfecha** antes de ejecutar el Bloque H

---

## 11 · Desbloqueo de la Fase 10

| # | Condición |
|---|---|
| 1 | DoD de la Fase 9.5 completo, sin excepciones |
| 2 | Fase 9.5 **fusionada a `main`** |
| 3 | **Convención de DML explícita escrita en `CLAUDE.md` §6** |
| 4 | Renumeración propagada: `PENDIENTES.md` refleja `0006` |
| 5 | `alembic/versions/` descongelado |

**La condición 3 no es formalismo.** El backfill de la Fase 10 —`usuario.email_verificado` a `True`
para usuarios existentes, más la tabla `TokenConsumido`— es **el primer consumidor de la convención
y el primer candidato a repetir el fallo de la 0002**. La Alternativa B no elimina RM1; solo la
convención escrita lo contiene.

**Condición de parada.** Si durante la ejecución apareciera cualquier base de datos cuyos datos
importen, **E1 queda invalidada, la fase se detiene y vuelve al ARB**.

---

**Documento canónico de la Fase 9.5.** La ejecución se rige por este documento; en caso de
conflicto con cualquier otro, manda este.
