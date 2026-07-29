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

> **Nota de vigencia de las cifras.** Todas las referencias a «104 tests» y «102/104» de este
> documento son la **línea base anterior a la fase** y se conservan tal cual porque son mediciones
> históricas. La cifra vigente tras añadir la batería de migraciones es **118 recogidos: 113 pasan,
> 2 fallan (PDF, preexistentes) y 3 se omiten**. `conftest.py:64` sigue usando `create_all` a
> propósito —los tests no pasan por Alembic para no depender de él—; quien ejerce Alembic de verdad
> es `test_migraciones.py`, que es justamente lo que H5 echaba en falta.
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
   `90f725c3ba9f_esquema_base.py`.
6. **Verificar por ejecución antes de aceptar el fichero — no es opcional.** Con el mismo
   `alembic.ini` desechable y la misma base vacía del paso 2, ejecutar
   `alembic -c <ini desechable> upgrade head` y `downgrade base`; ambos deben terminar con
   `returncode == 0`. **Que el comando de generación del paso 3 termine con éxito no basta**:
   autogenerate puede producir un fichero sintácticamente correcto pero **no ejecutable**.
   Trampa conocida y reproducible: al renderizar las columnas con variante JSONB, autogenerate
   emite `astext_type=Text()` pero solo importa `sqlalchemy as sa` y
   `from sqlalchemy.dialects import postgresql` — nunca `Text` a secas —, así que el fichero lanza
   `NameError: name 'Text' is not defined` en cuanto se ejecuta. **Si aparece, es un ajuste manual
   obligatorio, no un fallo del procedimiento**: sustituir cada `Text()` dentro de `astext_type=...`
   por `sa.Text()` (hoy, 19 ocurrencias en las columnas `PortableJSON`) y repetir la verificación.
   La corrección no altera el DDL emitido — `JSONB(astext_type=sa.Text())` y `JSONB()` compilan al
   mismo `CREATE TABLE` en PostgreSQL — así que **no invalida el enfoque ni la corrección de la
   revisión generada**: es un defecto de generación de código de la herramienta, no del diseño.
   **El procedimiento no es garantizadamente «una sola pasada»**: si el `NameError` aparece,
   corregir y volver a ejecutar este mismo paso 6 antes de continuar.
7. Trasladarlo a `backend/alembic/versions/`.

**Descartado: `stamp head`.** Funciona, pero exige escribir un estado falso en `alembic_version`
—declarar la base al día en `0004` cuando no tiene ni una tabla— y genera `down_revision = '0004'`,
añadiendo un paso manual cuyo olvido deja la revisión colgando de una cadena que el Bloque D va a
borrar: fallo silencioso al generar, ruidoso mucho después.

**Riesgos.** Omitir el paso 4 y dejar el identificador hexadecimal, incumpliendo E4 · omitir el
paso 6 y trasladar un fichero nunca ejecutado, arriesgando descubrir el `NameError` (u otro fallo de
generación) en el Bloque C o más tarde, en vez de aquí.

**Criterios de aceptación.** Existe el fichero · 21 tablas · `revision = "0005"` ·
`down_revision = None` · **`upgrade head` y `downgrade base` terminan en éxito contra la base
desechable del paso 2** (paso 6). **El bloque no se cierra aquí**: la corrección semántica de la
DDL —que coincida con `models.py`— es el Bloque C.

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
nadie sabe de dónde viene. El coste de regenerar es reaplicar los pasos manuales mecánicos y
deterministas del Bloque B: fijar el identificador, renombrar el fichero y —si autogenerate vuelve
a reproducirlo— corregir `Text()` a `sa.Text()` en las columnas JSONB (paso 6). **Esto no contradice
«no se parchea a mano»**: son ajustes de generación que se aplican siempre, en cada regeneración,
dentro del propio Bloque B y antes de que el fichero llegue a la auditoría de RC-1 en este Bloque
C — nunca como respuesta a un rechazo de esa auditoría. No es una corrección puntual sobre contenido
ya auditado.

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

**Estado: COMPLETADO.** Retiradas las cuatro revisiones y los `.pyc` obsoletos de `__pycache__`.
`versions/` contiene un único fichero, `0005_esquema_base.py`. Medido tras la retirada:
`alembic heads` → `0005 (head)`, una sola cabeza · `alembic history` → `<base> -> 0005 (head)`,
una sola línea · `alembic current` → vacío sobre base sin sellar y `0005 (head)` tras `upgrade` ·
`alembic upgrade head` y `downgrade base` en éxito (antes de D, `upgrade head` abortaba con
*«Multiple head revisions are present»*, el mismo comando que ejecuta `docker-compose.yml:56`) ·
`alembic check` → *«No new upgrade operations detected»*, que la doble cabeza impedía ejecutar
durante RC-1. Batería de migraciones: de 4 fallos (T1, T2, T4, T6) a 1; T1, T2 y T6 en verde y los
casos parametrizados de T3 omitidos con el motivo previsto. **T4 sigue en rojo por un defecto
propio, no por deriva** (ver Bloque G / P0-1): compara el esquema de `upgrade head` contra el de
`create_all` sin excluir `alembic_version`, tabla que el primero siempre tiene y el segundo nunca,
de modo que la aserción no puede satisfacerse tal como está escrita. Las 21 tablas reales salen
idénticas en esa misma comparación. Suite completa sin regresión: 102 pasan, 2 fallan (PDF/DejaVu,
preexistentes), 14 omitidos — cifras idénticas a las de antes del bloque.

**Agentes ECC.** `refactor-cleaner`.

**Graphify.** No.

---

### Bloque E — Verificación en SQLite

**Objetivo.** T1, T2, T3 y T6 en verde. La batería pasa de roja a verde **por reparación real**.

**Dependencias.** D · paralelizable con F.

**Riesgos.** Ajustar la batería para que pase en lugar de reparar la causa.

**T3 tras el Bloque D — `skipped` es aceptación válida, no un pendiente.** T3 descubre la cadena de
revisiones en tiempo de recolección (no cita `0001`-`0004`). Con la revisión fundacional única, no
hay pares consecutivos que recorrer: los casos parametrizados de T3 se omiten explícitamente con
motivo *«la cadena vigente tiene una sola revisión»*. **Ese `skipped` cuenta como «T3 en verde» a
efectos de este bloque y de RC-2** — no es un hueco de cobertura ni un caso a resolver más tarde: no
hay nada que ejercitar porque no existen saltos entre revisiones. El control del arnés de T3 (sobre
la revisión más antigua de la cadena) sí debe estar en `passed`, no en `skipped`.

**Retirada del gate — criterio de cierre del bloque, no limpieza posterior.** El módulo lleva
`pytestmark = pytest.mark.skipif(...)` sobre `SEIS_CALIBRAR_MIGRACIONES` desde el Bloque A. **No
tiene trinquete propio** (a diferencia de `xfail(strict=True)`, que se descartó precisamente por
esto): nada impide que, reparada la cadena, el gate quede olvidado y la batería siga oculta de la
ejecución por defecto. **Retirar esa línea es parte del criterio de aceptación de este bloque**, no
un paso de limpieza aplazable. El Bloque E no se da por cerrado con la batería en verde y el gate
todavía en su sitio.

**Criterios de aceptación.** `upgrade head` desde vacío y `downgrade base` verdes · idempotencia
verde · **T3: el control del arnés en `passed`; los casos parametrizados en `passed` o `skipped`
según haya o no pares consecutivos que recorrer — nunca en `failed`** · **el gate `pytestmark`
retirado del fichero** · **el texto de las aserciones de toda la batería (T1-T6) es byte-idéntico al
de la versión corregida del Bloque A** (commit `33bb28a`, que ya hizo a T3 agnóstico de
identificadores literales — no a la versión original con `"0001"`-`"0004"` citados a mano); el diff
del fichero entre ambos momentos **no contiene ninguna línea eliminada ni modificada dentro de una
aserción, solo añadidos**. *(Definición operativa única de «no debilitada»: se aplica a los seis
tests, no solo a los que este bloque ejercita, y es la que invocan RC-2 y el DoD.)*

**Estado: COMPLETADO.** Gate retirado del fichero: eliminados el bloque `pytestmark`, la constante
`GATE_ENV_VAR` y los párrafos del docstring que lo describían. La batería corre ya en la invocación
por defecto de `pytest`, sin variable de entorno. Medido en esa invocación: **T1, T2 y T6 en
`passed`**, **el control del arnés de T3 en `passed`** y **los dos casos parametrizados de T3 en
`skipped`** con el motivo previsto («la cadena vigente tiene una sola revisión…») — ninguno en
`failed`. Los seis tests de guarda de aislamiento, en `passed`. T5 en `skipped` (Bloque F).

*Verde por reparación real, verificado de forma objetiva:* `git diff 33bb28a` sobre el fichero
arroja 31 líneas añadidas y 38 eliminadas, y **ninguna de las 38 pertenece a una aserción** — son
docstring, comentario y el propio gate. El texto de las aserciones de T1-T6 permanece byte-idéntico.
Por eso sus mensajes de fallo siguen citando «Bloque A», la `0002` y la `0004`: ese anacronismo es
la evidencia de que no se ablandaron, y corregirlo está **prohibido** por este mismo criterio.

*Efecto sobre la suite por defecto:* de `2 fallan · 102 pasan · 14 omitidos` a
`3 fallan · 112 pasan · 3 omitidos`. Los 14 omitidos anteriores eran la batería entera, oculta por
el gate. El tercer fallo es **T4**, que el gate venía enmascarando y cuya reparación corresponde al
**Bloque G**: no es deriva de esquema —`alembic check` no detecta operación pendiente y las 21
tablas salen idénticas—, sino que T4 compara `upgrade head` contra `create_all` sin excluir
`alembic_version`. Ninguna prueba que pasara antes falla ahora.

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

**Estado: COMPLETADO.** Ejecutado contra `postgis/postgis:16-3.4` —la misma imagen que declara
`docker-compose.yml:5`— en contenedor desechable aparte, sin tocar la composición (eso es el Bloque
H). Motor: **PostgreSQL 16.4**, con las extensiones `postgis`, `postgis_topology`, `fuzzystrmatch` y
`postgis_tiger_geocoder` que trae la imagen.

- **T5 en `passed`** contra PostgreSQL real: `upgrade head` y `downgrade base`, ambos con
  `returncode 0`. `alembic current` → `0005 (head)` tras el upgrade y vacío tras el downgrade.
- **Downgrade sin residuo:** 0 de las 21 tablas de SEIS y 0 columnas `json`/`jsonb` sobreviven al
  `downgrade base`.
- **`skip` de T5 visible** en la invocación por defecto (`pytest -rs`), con motivo legible.
- Suite completa sin regresión: `3 fallan · 112 pasan · 3 omitidos`, idéntico al cierre del Bloque E.

**Volcado de tipos archivado** — `information_schema.columns`, esquema `public`, tras `upgrade head`:

| Columna | `data_type` | `udt_name` |
|---|---|---|
| `activo.atributos` · `alerta.criterios` · `analisis.entrada` · `analisis.hechos` · `analisis.resultado` · `auditoria.delta` · `decision.condiciones` · `decision.vetos` · `fuente_subasta.perfil` · `parametro.valor` · `perfil_inversion.parametros` · `preferencias_notificacion.canales` · `regla.definicion` · `regla_disparada.efecto` · `regla_disparada.evidencias` · `resultado_real.incidencias` · `riesgo_evaluado.condiciones` · `riesgo_evaluado.evidencias` · `subasta.datos_brutos` | `jsonb` | `jsonb` |

Recuento: **`jsonb = 19`, `json = 0`.** Queda elevado a hecho medido lo que hasta ahora solo estaba
demostrado sobre el *código generado*: la **DDL ejecutada** produce `jsonb`, no `json` degradado.
Total de tablas en `public` tras el upgrade: 23 = las 21 de SEIS + `alembic_version` +
`spatial_ref_sys`, esta última propiedad de la extensión PostGIS y creada por la imagen, no por la
migración.

> **Hallazgo registrado, no resuelto — `alembic check` es inservible como barrera de deriva contra
> PostGIS.** Ejecutado sobre la base ya migrada, informa `New upgrade operations detected` con **74
> `remove_table` y 56 `remove_index`**. Verificado uno a uno: las 38 tablas señaladas
> (`loader_lookuptables`, `tiger`, `zip_lookup`, `spatial_ref_sys`, `topology`…) son **todas de las
> extensiones**, y **ninguna es una tabla de SEIS**. No hay ni una sola operación `add_*` ni
> `modify_*`, de modo que **no existe deriva del esquema de SEIS**: lo que falta es un
> `include_object` en `env.py` que excluya los objetos de extensión. Afecta a la barrera
> anti-recurrencia, no a esta fase de verificación. **Alcance: Bloques G / I.** Fuera del alcance del
> Bloque F, cuyos tres criterios no lo mencionan.

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

**Estado: COMPLETADO.**

*Diagnóstico medido.* Replicando la comparación de T4 sobre dos SQLite desechables: la **única**
diferencia entre `upgrade head` y `create_all` era la tabla `alembic_version`, presente solo en el
primer lado. De las 21 tablas comunes, **0 tenían contenido distinto**. T4 no fallaba por deriva:
fallaba porque su aserción era insatisfacible por construcción, y una barrera que no puede ponerse
verde no vigila nada.

*Corrección aplicada.* Una sola exclusión, `alembic_version`, en `_describir_esquema()`, más un
`continue` y una constante `TABLA_VERSION_ALEMBIC` documentada. **No se tocó ninguna línea de
aserción**: el criterio de congelación del Bloque E sigue verificándose con el mismo filtro
(`assert |_afirmar|pytest.fail` sobre las líneas eliminadas del diff contra `33bb28a`) y sigue sin
coincidencias. Excluida esa tabla, la comparación cubre el **100 % del esquema de SEIS**:
**21 tablas · 171 columnas · 22 índices** (medido).

*Determinación sobre `include_object` y los objetos de extensión PostGIS.* **No procede en T4, y no
se ha aplicado.** Ambos lados de T4 son SQLite desechables, donde no existe ninguna extensión:
medido, **cero** objetos con prefijo `spatial_`, `geometry_`, `raster_`, `tiger`, `topology` o
`loader_`. El ruido de PostGIS documentado en el Bloque F afecta a `alembic check` sobre
PostgreSQL —otra barrera, otro mecanismo (`env.py`)— y no a esta prueba. Queda como deuda del
**Bloque I**.

**Prueba de mutación — resultado.** Cinco mutaciones mínimas sobre `0005_esquema_base.py`, una por
dimensión exigida. Para cada una: aplicar → ejecutar T4 → revertir → ejecutar T4.

| Dimensión | Mutación | T4 mutado | T4 revertido |
|---|---|---|---|
| Tabla | `op.create_table('escenario', …)` → `'escenario_mutado'` | **FALLA** ✔ | PASA ✔ |
| Columna | elimina `sa.Column('lote', sa.SmallInteger(), nullable=False)` de `activo` | **FALLA** ✔ | PASA ✔ |
| Tipo | `auditoria.quien`: `String(120)` → `String(80)` | **FALLA** ✔ | PASA ✔ |
| Nulabilidad | `subasta.puja_minima`: `nullable=True` → `nullable=False` | **FALLA** ✔ | PASA ✔ |
| Índice | elimina `op.create_index(op.f('ix_decision_semaforo'), …)` | **FALLA** ✔ | PASA ✔ |

Las cinco fallaron con el mensaje propio de T4 («Deriva detectada entre el esquema de `upgrade head`
y el de `Base.metadata.create_all`»), no con un error accidental. **5/5 dimensiones: PRUEBA DE
MUTACIÓN SUPERADA.** La migración quedó byte-idéntica: SHA-256 `9d5aae5116cc85fc…` antes y después,
y `git diff` sobre el fichero, vacío.

*Efecto sobre la suite.* De `3 fallan · 112 pasan · 3 omitidos` a **`2 fallan · 113 pasan ·
3 omitidos`**. Los dos rojos restantes son los preexistentes de PDF (fuente DejaVu, `docs/PENDIENTES.md`),
ajenos a esta fase. La batería de migraciones queda **sin ningún `failed`**.

> **Deuda registrada, no resuelta.** (a) `_describir_esquema()` compara los índices **por nombre**:
> una mutación que cambiara las columnas de un índice conservando su nombre no se detectaría.
> (b) La prueba de mutación se ejecutó de forma dirigida, no automatizada; convertirla en barrera
> permanente en CI corresponde a los **Bloques I / J** (RC-3 exige «T4 en CI»). (c) Si algún día T4
> se extendiera a PostgreSQL —posibilidad que insinúa el docstring de T5—, habría que reexaminar los
> objetos de extensión; **hipótesis, no hecho medido**: con ambas bases creadas desde la misma
> imagen PostGIS los objetos aparecerían en los dos lados y se cancelarían.

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

**Estado: COMPLETADO.** Motor Docker 29.6.2, Compose v5.3.0.

*Precondición que faltaba.* No existía `.env`, y `docker-compose.yml` declara `POSTGRES_PASSWORD`,
`JWT_SECRET` y `ADMIN_PASSWORD` como `${VAR:?…}` sin respaldo: sin ese fichero la composición ni
siquiera parsea. Se generó uno local —cubierto por `.gitignore:18`, verificado que git no lo ve— con
secretos aleatorios **validados importando `_motivo_inseguro()` de `app/core/config.py`**, la misma
función que ejecuta el backend al arrancar, en vez de darlos por buenos a ojo. `SEIS_ENV` se dejó sin
definir a propósito, de modo que Compose cae en su valor por defecto, `production`: el caso estricto,
con la guarda de secretos activa.

*Protocolo de verificación.* Un solo `down -v` seguido de `up` no distingue «volumen destruido» de
«volumen que nunca existió», y validar contra un volumen antiguo es el riesgo que este bloque nombra.
Se hicieron **dos arranques completos** con destrucción intermedia, usando como testigo el
`system_identifier` del clúster PostgreSQL, que `initdb` genera **solo** sobre un directorio de datos
vacío:

| | Arranque 1 | `down -v` | Arranque 2 |
|---|---|---|---|
| `system_identifier` | `7667641443493126182` | — | **`7667642052658954278`** |
| `seis_pgdata` | creado | `Volume seis_pgdata Removed`, inventario vacío, `inspect` falla | recreado |
| `/api/v1/health` | `HTTP 200` en ~3 s | — | **`HTTP 200` en ~9 s** |
| `alembic_version` | `0005` | — | `0005` |
| Tablas de SEIS | 21 | — | 21 |
| Columnas JSON | `jsonb=19 · json=0` | — | `jsonb=19 · json=0` |

**Los dos identificadores son distintos**: el segundo arranque inicializó un clúster nuevo, luego el
volumen se destruyó de verdad y no se reutilizó. Es la evidencia que cierra el riesgo de verde falso.

*Cadena de arranque, medida en el log del backend del segundo arranque:*
`Running upgrade -> 0005` sobre `PostgresqlImpl` con DDL transaccional → `Usuario administrador
creado` → `esquema creado y conocimiento sembrado` → `Uvicorn running` → `GET /api/v1/health 200 OK`.
Los tres eslabones de `command:` (`alembic upgrade head && python -m scripts.init_db && uvicorn`)
se ejecutan en orden y ninguno aborta. **Esto es exactamente lo que una instalación nueva no podía
hacer antes de esta fase.**

*Comprobación suplementaria, fuera del criterio.* `/api/v1/health` devuelve un diccionario estático y
por sí solo no prueba que el backend alcance la base. Se añadió un `POST /api/v1/auth/login` real con
el `ADMIN_PASSWORD` generado: **HTTP 200 con JWT emitido**, `rol=admin`. Prueba conectividad efectiva
con PostgreSQL y que la siembra funcionó, bajo la guarda estricta de `production`.

*Resto de la pila (sin anomalías).* `db` y `redis` en `healthy`; `worker` conectado a Redis con el
beat programando `seis.telegram_polling` (devuelve `0`, no-op esperado sin token) y **cero errores**
en su log; `frontend` en `HTTP 200`. Los cinco servicios `running`.

> **Observaciones registradas, no resueltas** (ninguna pertenece al Bloque H): (a) `docker-compose.yml`
> conserva `version: "3.9"`, que Compose v5 declara obsoleto y avisa en cada invocación — cosmético;
> (b) `db` y `redis` se publican en `127.0.0.1` con comentario explícito, mientras `backend` (8000) y
> `frontend` (3000) se publican en todas las interfaces: es coherente con que deban ser alcanzables,
> pero conviene confirmarlo en la **auditoría de seguridad de la Fase 16**.

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

**Estado: COMPLETADO, con un residuo explícito en el segundo criterio.**

*Criterio 1 — convenciones en `CLAUDE.md` §6.* Añadidas las reglas **9**, **10** y **11**. No se
redactaron de memoria: cada una cita el defecto real que la motiva, verificado contra el historial de
git antes de escribirla. `git show HEAD:…0001_esquema_inicial.py` confirma
`Base.metadata.create_all` en su línea 18 y `drop_all` en la 22; `git show HEAD:…0002_multitenancy.py`
confirma en su línea 72 el `INSERT INTO organizacion (id, nombre)` que omite `creado_en` —columna
`NOT NULL` cuyo `default=_now` es **de cliente** y por tanto inexistente para el SQL crudo—, que es
la causa medida de `IntegrityError: NOT NULL constraint failed: organizacion.creado_en`.

*Criterio 3 — `render_as_batch`.* El riesgo nombrado de este bloque es documentarlo como el arreglo
que no es, así que **se remidió en esta ejecución** en vez de citar H3. Cuatro cruces sobre SQLite
real (SQLAlchemy 2.0.51 · Alembic 1.18.5):

| Operación | `render_as_batch=False` | `render_as_batch=True` |
|---|---|---|
| `alter_column` | **FALLO** — `OperationalError: near "ALTER": syntax error` | **FALLO** — idéntico |
| `batch_alter_table` | OK | OK |

No repara nada, y `batch_alter_table` no lo necesita. Documentado en `CLAUDE.md` §6.11 y en un
comentario de `backend/alembic/env.py`, en el punto exacto de `run_migrations_online()` donde alguien
sentiría la tentación de activarlo. **Se documenta, no se activa**: el criterio pide precisión, no
habilitación, y encenderlo daría falsa sensación de cobertura.

*Criterio 2 — T4 en el pipeline.* **No existía ninguna CI en el repositorio** (`.github/`, `.gitlab-ci.yml`,
`Jenkinsfile`, `azure-pipelines.yml`, `.circleci`: ninguno). Creado
`.github/workflows/migraciones.yml`, que ejecuta la batería en cada cambio de `backend/**`.
Verificado: el YAML parsea y su estructura es la esperada; el comando del paso principal se ejecutó
en un **entorno virtual limpio**, instalado desde cero con `requirements-dev.txt` y solo con las
variables que el propio workflow declara → **11 pasan · 3 omitidos · 0 fallos**.

*El pipeline no es una prueba vacía — demostrado.* Se mutó `models.py` añadiendo
`activo.columna_de_deriva` **sin migración que la acompañe** (la dirección contraria a la mutación
del Bloque G, y la deriva que de verdad ocurrirá: tocar el modelo y olvidar la revisión). Se ejecutó
el comando literal del workflow y se comprobó el **código de salida**, que es lo que pone la CI en
rojo:

| Estado | `exit` | CI |
|---|---|---|
| Línea base | `0` | verde — 11 pasan |
| `models.py` mutado, sin migración | **`1`** | **roja — 1 falla** |
| Revertido | `0` | verde — 11 pasan |

> **Defecto del método, detectado y corregido en el propio bloque.** El script de mutación
> restauraba `models.py` con `write_text(..., newline="")` y verificaba por SHA-256 del contenido
> **releído**, que Python normaliza: la comprobación daba idéntico mientras los bytes en disco habían
> pasado de CRLF a LF (308 líneas). `git diff --numstat` no listaba el fichero —`core.autocrlf`
> normaliza para comparar— pero `git status` sí lo marcaba modificado. Se detectó por esa
> discrepancia, se caracterizó contando los bytes reales y se restauró con `git checkout --`:
> `models.py` vuelve a tener 308 CRLF y desaparece de `git status`. La evidencia de la mutación no
> queda invalidada —es de comportamiento: `exit 0 → 1 → 0`, y el contenido siempre fue
> semánticamente idéntico—, pero la afirmación «byte-idéntico» solo era cierta en la vista
> normalizada de git. `0005_esquema_base.py` no se vio afectado: ya era LF antes del Bloque G, como
> acredita el aviso que git emitió al añadirlo en el Bloque D.

> **Residuo declarado, sin maquillar.** El workflow está definido y demostrado correcto **en local**;
> **no se ha observado ejecutándose en GitHub Actions**, porque eso exige un push y este entorno no
> tiene `gh` ni `GITHUB_TOKEN`. La primera ejecución remota debe verificarse al publicar la rama. El
> criterio se da por cumplido en lo verificable desde aquí, y este residuo queda explícito.

*Alcance deliberado de la CI.* Solo `tests/test_migraciones.py`, no la suite completa: esta arrastra
dos fallos preexistentes de PDF (falta `fonts-dejavu-core`, que el `Dockerfile` sí instala) que
dejarían el pipeline permanentemente en rojo, y una barrera siempre roja no vigila nada. Ampliarla
queda registrado como deuda.

*Sin regresión, con `env.py` tocado.* Al modificar `env.py` —aunque solo sea un comentario— se
revalidó todo lo que depende de él: `upgrade head` → `0005`, `alembic check` → *No new upgrade
operations detected*, `downgrade base` sin error; suite completa `2 fallan · 113 pasan · 3 omitidos`,
idéntica; y **se repitió el arranque real del Bloque H**: `Running upgrade -> 0005`, `/api/v1/health`
→ `HTTP 200`, `alembic_version=0005`, `jsonb=19 · json=0`, desmontado con `down -v` y cero volúmenes.

> **Corrección de propiedad de deuda.** En los informes de los Bloques F, G y H asigné al Bloque I
> tres deudas —`include_object` para `alembic check` contra PostGIS, la comparación de índices **por
> nombre** en `_describir_esquema()`, y la automatización de la prueba de mutación—. Releído el plan
> canónico, **ninguna de las tres figura en los criterios de aceptación de este bloque**, que son
> exactamente los tres de arriba. Aquellas asignaciones eran mías, no del plan. Se rectifican: quedan
> **sin bloque propietario** dentro de la Fase 9.5 y deben inscribirse en el backlog
> (`docs/PENDIENTES.md`, fichero del **Bloque J**). No se resuelven aquí.

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

**Estado: COMPLETADO.** Cada corrección se verificó contra el repositorio antes de escribirla;
ninguna se dedujo del texto anterior.

| Defecto documental | Evidencia que lo desmiente | Corregido en |
|---|---|---|
| `PENDIENTES.md:29` reservaba la `0005` para la Fase 10 | La `0005` es la fundacional (`down_revision = None`) | → `0006`; Fase 13 → `0007` |
| `PENDIENTES.md:38` nombraba `0005_self_service.py` | Ídem | → `0006_self_service.py` |
| `PENDIENTES.md:134` afirmaba `0003` y `0004` «verificadas en SQLite» | `git show HEAD:…0004…` usa `op.alter_column` (líneas 25 y 30); medido: `OperationalError: near "ALTER": syntax error`. **La `0004` nunca pudo ejecutarse en SQLite** | Corregido, con nota de que ambas fueron retiradas |
| `CLAUDE.md` §2 declaraba «PostgreSQL 16 + PostGIS (geoespacial)» | Sin `geoalchemy2` en `requirements*.txt`; sin columna `Geometry` en `models.py`; `lat`/`lng` son `Numeric(9,6)` | Reescrito: la imagen es PostGIS pero **sus capacidades no se usan** |
| `README.md` decía que `lat/lng` migran a `geometry(Point,4326)` «hasta la Fase 5», marcada ✅ | No ha ocurrido | Reescrito como trabajo futuro, no hecho consumado |
| `README.md` avisaba de que **una instalación nueva no levanta** | Bloque H: `HTTP 200` sobre volumen destruido | Sustituido por el estado real medido |
| `README.md` marcaba la Fase 9.5 «⏳ Siguiente» y la 10 «Bloqueada» | Bloques A-J ejecutados | Actualizado |
| Cifra «104 tests / 102 verdes» en `CLAUDE.md` (×3) y `README.md` (×2) | `--collect-only`: **118 recogidos**; ejecución: 113 pasan · 2 fallan · 3 se omiten | Actualizado en los cinco sitios |
| `CLAUDE.md` §3 describía `0002`, `0003` y `0004` como vigentes | Retiradas en el Bloque D | Anotadas como retiradas, con la causa del fallo de la `0002` |
| `CLAUDE.md` §5 decía «Siguiente tarea: Fase 9.5» | La fase está ejecutada | → Fase 10, tras RC-3 y merge |
| `FASE_13_PLAN_EJECUCION.md` fijaba `0006` para la Fase 13 con `down_revision = "0005"` (§tabla v2.0, §1 y §12-Q1) | Derogado por la renumeración | → `0007` con `down_revision = "0006"`, en los tres sitios |
| `PLAN_REPARACION_MIGRACIONES.md:167` decía «Propagación pendiente» | Ya aplicada en esta ronda | → «Propagación COMPLETADA», enumerando dónde |
| DoD exigía «suite en 102/104» | La batería añadió 14 tests | → 118 recogidos, con la equivalencia explicada |

`CLAUDE.md` §7 se revisó y **no contenía ninguna advertencia pendiente**: no requería cambio.

**Evidencia de P0-2 producida en este bloque** *(no es criterio del Bloque J: es evidencia de RC-2 y
del DoD, sin bloque propietario en el plan; se ejecutó aquí porque era ejecutable y era lo único que
faltaba para cerrar RC-2).* Fabricado a mano el estado imposible de alcanzar por la cadena —escribir
`UPDATE alembic_version SET version_num = …` en una base desechable— y ejecutadas cuatro órdenes de
Alembic con cada sellado, **en los dos motores**:

| Motor | Sellado | `current` | `upgrade head` | `downgrade base` | `check` |
|---|---|---|---|---|---|
| SQLite | `0004` · `0001` | falla | falla | falla | falla |
| PostgreSQL 16.4 | `0004` · `0001` | falla | falla | falla | falla |

Las **16 órdenes** terminan con código distinto de cero y el mensaje
`ERROR [alembic.util.messaging] Can't locate revision identified by '0004'` (resp. `'0001'`).
**Cero aceptaciones en silencio.** Es exactamente el síntoma que anticipa la tabla del §9, y cierra
el riesgo **P0-2**.

> **Deuda sin bloque propietario, trasladada a `docs/PENDIENTES.md`.** El plan no asigna propietario
> a estas cuatro, de modo que no se inventa uno: (a) falta `include_object` en `env.py`, sin el cual
> `alembic check` es inservible contra PostGIS; (b) `_describir_esquema()` compara los índices **por
> nombre**, de modo que un cambio de columnas conservando el nombre no se detectaría; (c) la prueba
> de mutación de T4 se ejecuta a mano, no automatizada; (d) la CI cubre solo la batería, no la suite
> completa, que exigiría `fonts-dejavu-core` en el runner. Ninguna se resuelve aquí.

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
respondiendo · aserciones no debilitadas · **T3 sin ningún caso en `failed`** (el control del arnés
en `passed`; los parametrizados en `passed` o `skipped` — el `skipped` por ausencia de pares
consecutivos es el resultado esperado y no bloquea) · **gate `SEIS_CALIBRAR_MIGRACIONES` ya retirado
del fichero**.
**Bloquea si:** falta evidencia PostgreSQL · Docker no verificado sobre volumen destruido · alguna
BD antigua es aceptada en silencio · el gate sigue presente en el fichero.

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
- [x] `alembic upgrade head` desde base vacía: verde en **SQLite y PostgreSQL** *(E · F)*
- [x] `alembic downgrade base`: verde en ambos motores *(E · F)*
- [x] `alembic history`: **una sola revisión**, `down_revision = None`, identificador `0005` *(D)*
- [x] `alembic heads` devuelve **exactamente una cabeza** *(D)*
- [x] Una BD stampeada en `0001`-`0004` falla **de forma ruidosa** *(P0-2, Bloque J: 16/16 órdenes con `returncode != 0` y `Can't locate revision`, en ambos motores; 0 silencios)*
- [x] `docker compose down -v && up -d --build` sobre volumen limpio: backend en `/api/v1/health` *(H: `HTTP 200`, con `system_identifier` distinto entre arranques)*

**Corrección del esquema**
- [x] Las **19 columnas `PortableJSON` son `jsonb`** en PostgreSQL, con volcado archivado *(F: `jsonb=19 · json=0`)*
- [x] Índices, FKs y tipos verificados contra `create_all` por T4 *(C: 21 tablas · 171 columnas · 15 FK · 22 índices, 0 diferencias)*

**Instrumentación**
- [x] T1-T6 en verde, **sin aserciones debilitadas** respecto de la versión corregida del Bloque A
      (T3 sin ningún caso en `failed`; `skipped` en sus casos parametrizados cuenta como en verde)
- [x] **Gate `SEIS_CALIBRAR_MIGRACIONES` retirado** de `test_migraciones.py` *(E)* — es criterio de cierre
      del Bloque E, no limpieza aplazable: el gate no tiene trinquete propio
- [x] **T4 demostrado capaz de fallar** *(G: 5/5 dimensiones — tabla, columna, tipo, nulabilidad, índice)*
- [x] **Guarda de aislamiento de la batería en su sitio y demostrada capaz de saltar** *(Bloque J: `RuntimeError` en 7/7 escenarios peligrosos — fichero compartido, valor por defecto de `Settings`, sqlite fuera del directorio, postgres con «prod», postgres sin marcador de test, URL vacía y esquema no soportado)*
- [x] T4 en el pipeline de CI — workflow creado, demostrado en local (`exit 0 → 1 → 0` ante deriva
      real) y **ejecutado en GitHub Actions tras el push y la fusión de la rama (PR #1)**
- [x] Suite en **118 recogidos: 113 pasan · 2 fallan · 3 se omiten** — los 2 rojos son de PDF,
      preexistentes y ajenos. *(El criterio se escribió como «102/104» cuando la batería de
      migraciones aún no existía; los 14 tests nuevos elevan el total a 118 sin alterar el
      significado: ninguna prueba que pasara antes falla ahora.)*

**Barreras**
- [x] `CLAUDE.md` §6: prohibido `Base.metadata` en `alembic/versions/` *(I, §6.9)*
- [x] `CLAUDE.md` §6: toda DML de migración especifica cada columna `NOT NULL` *(I, §6.10)*
- [x] Búsquedas de `Base.metadata` y `create_all` en `versions/`: sin resultados *(0 apariciones)*
- [x] `render_as_batch` documentado como preventivo, **nunca como correctivo** *(I: `CLAUDE.md` §6.11 y `env.py`, con los cuatro cruces remedidos)*

**Documentación**
- [x] `PENDIENTES.md` líneas 29, 38 y 134 corregidas *(J)*
- [x] `CLAUDE.md` §§2, 3, 6, 7 corregidos *(J; §7 se revisó y no contenía advertencia pendiente)*
- [x] `README.md` corregido: PostGIS, aviso de estado, tabla de fases y cifras *(J)*
- [x] Renumeración propagada: Fase 10 → `0006`, Fase 13 → `0007` *(J: `PENDIENTES.md` ×2, `FASE_13` ×4, `PLAN_REPARACION`)*
- [x] Plan de Fase 13 anota que su corrección B3 consume la convención de DML *(J)*
- [x] Procedimiento de recreación publicado, **con ambas vías** y `--purge` documentado *(§9)*

**Gobernanza**
- [x] RC-0, RC-1, RC-2, RC-3 superados en orden — **los cuatro superados**: T4 en CI se observó
      tras la fusión de la PR #1, y la contradicción C-2 del informe de cierre quedó corregida
      antes de fusionar
- [x] Revisión humana previa al merge — **PR #1 revisada y fusionada** (`main` en `61039bd`,
      fast-forward, sin commit de merge)
- [x] PRE-1 satisfecha *(Docker Desktop; motor verificado en marcha por medición, no por declaración)*
- [x] **PRE-2 satisfecha** antes de ejecutar el Bloque H *(`.env` con secretos validados contra `_motivo_inseguro()`)*

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
