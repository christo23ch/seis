# SEIS — Plan de fases hasta el lanzamiento

**Fecha:** 2026-09-08 · **Base:** `main` tras fusionar la Fase 11-A y las correcciones de seguridad (402 tests)
**Sustituye, en el orden y la clasificación, a lo que dice `docs/SEIS_Plan_Maestro_Fases_920.md`.** Aquel sigue
siendo válido como descripción de *qué* hace cada fase; este manda en *cuándo* y *cómo*.

---

## 0 · Por qué este plan reordena el Plan Maestro

Dos motivos, y conviene entenderlos antes de mirar la tabla.

**El primero: sin captación no hay producto.** SEIS promete «te avisamos de las subastas que
encajan contigo». Hoy la única forma de que entre una subasta es que alguien la teclee: no
existe conector de ingesta. Las alertas, el scoring y los canales de la Fase 12 están
construidos y probados, pero **vigilan un caudal que no existe**. Mientras eso siga así, todo
lo demás —cobrar, landing, beta— construye sobre una promesa que el producto no puede cumplir.
Por eso la captación sube al segundo puesto, por delante de la monetización, aunque el Plan
Maestro la pusiera en la posición 17.

**El segundo: no hay portátil.** Las fases se clasifican por dónde pueden ejecutarse, y el
orden maximiza el trabajo 🟢 sin romper la ruta crítica.

| | Significado |
|---|---|
| 🟢 | **Ejecutable ahora.** Código puro, entero en el sandbox web. |
| 🟡 | **Código ahora, activación después.** Se escribe y se prueba ya; queda inerte hasta que configures un panel externo. |
| 🔴 | **Requiere máquina local.** Depuración iterativa contra red, QA multinavegador, carga, restauración real de backups. |

---

## 1 · Trámites humanos que deberías arrancar HOY desde el móvil

No dependen del portátil y son el camino crítico real: sus plazos los marca un tercero, no tú.

| Trámite | Por qué ya | Plazo típico |
|---|---|---|
| **Figura fiscal** (autónomo o SL) con tu gestor | Sin ella no puedes facturar. Bloquea la Fase 13 entera y, por dependencia, la 18 | Semanas |
| **Dominio + Cloudflare** | Bloquea el despliegue (11-B) y el calentamiento del dominio de correo | Horas + propagación |
| **Alta en Render** (o el hosting elegido) | Bloquea 11-B | Minutos |
| **Alta en Postmark o SES + SPF/DKIM** | Sin dominio verificado, los correos de verificación van a spam. Ya hay código que los envía | Días (verificación DNS) |
| **Bot de Telegram** con @BotFather | 10 minutos. Desbloquea el canal ya construido en la Fase 12 | Minutos |
| **Abogado** para textos legales | Bloquea la Fase 14 y el lanzamiento | Semanas |
| **Sentry + UptimeRobot** | Observabilidad de 11-B | Minutos |

---

## 2 · Mecanismo contra un cuarto hallazgo perdido

En esta sesión aparecieron **tres** líneas de trabajo que ninguna sesión conocía: una rama
divergente con una Fase 10 duplicada, una Fase 11 huérfana, y un PR #4 con 7.000 líneas y 236
tests que llevaba un mes abierto. Eso no es mala suerte: **no existe un índice fiable del
estado**. `CLAUDE.md` y `docs/PENDIENTES.md` describen el contenido, pero ninguno lista *qué
ramas y qué PRs están vivos*, que es justo lo que se perdió.

### La regla

**`docs/ESTADO_ACTUAL.md` es el índice, y ninguna fase cierra su PR sin actualizarlo.**
Se le añade una sección de cabecera, obligatoria y corta:

> Lo de abajo es **la forma de la tabla, no su contenido**: los valores son de relleno a
> propósito. La versión anterior de este ejemplo traía un «PR #12» inventado que con el tiempo
> pasó a existir de verdad (Fase 17-A), y un ejemplo que se puede leer como estado real es peor
> que no tener ejemplo. **El estado vivo está en `docs/ESTADO_ACTUAL.md`, y solo ahí.**

```markdown
## Frentes abiertos  (actualizado: AAAA-MM-DD · commit de main: XXXXXXX)

| Rama | PR | Estado | Qué contiene | Siguiente acción |
|---|---|---|---|---|
| <rama> | #<n> | 🟡 en revisión | <una línea> | <qué falta> |

**Suite:** <n> passed, <n> skipped · **Última fase cerrada:** <fase>
```

### Cómo se mantiene sin depender de que te acuerdes

Tres capas, de menos a más fiable:

1. **En el prompt de cada fase** (`docs/PROMPTS_FASES.md`): el último requisito de todos los
   prompts es actualizar esa tabla antes de abrir el PR. Depende de que el modelo obedezca.
2. **En la CI, como test.** Es lo que lo hace fiable: no depende de memoria humana ni de la
   buena voluntad del modelo, sino de la misma puerta que ya bloquea los merges. Pero un test
   así **solo sirve si nadie lo acaba desactivando**, de modo que está diseñado para fallar
   poco y bien.

   **Qué comprueba exactamente:** que **todo PR abierto aparezca en la tabla**. Nada más.
   Se ejecuta en `pull_request`, pide a la API los PRs abiertos y falla si encuentra alguno
   que la tabla no menciona.

   **La comprobación es deliberadamente unidireccional.** El fallo que perseguimos es
   *trabajo que existe y nadie sabe que existe* — un PR #4 abierto un mes. El caso contrario,
   que la tabla mencione un PR ya fusionado, es contabilidad atrasada: molesta, pero no pierde
   nada, y se corrige sola en la siguiente actualización. Hacerla bidireccional convertiría
   cada fusión en un `main` rojo hasta que alguien borrase una fila, que es precisamente la
   clase de ruido que termina con el test desactivado.

   **Qué NO comprueba, y por qué:**

   | No comprueba | Motivo |
   |---|---|
   | Nombres de ramas | Se crean y borran constantemente. Una rama sin PR no es un frente perdido: es ruido |
   | Las columnas «Estado» y «Siguiente acción» | Texto libre. Compararlo haría fallar el test por una palabra distinta |
   | El orden de las filas | Irrelevante |
   | El SHA y el recuento de tests de la cabecera | Quedan obsoletos en el commit siguiente. Son informativos, no verificables |
   | PRs de bots (Dependabot) | Cada actualización automática rompería la CI |
   | PRs ya cerrados o fusionados que sigan en la tabla | Contabilidad atrasada, no pérdida de trabajo (ver arriba) |

   **Coste:** una llamada a la API con el `GITHUB_TOKEN` que Actions ya inyecta; sin secretos
   nuevos. **Efecto secundario buscado:** un PR nuevo falla hasta que se añade a sí mismo a la
   tabla. Eso no es un falso positivo — es la disciplina que se quiere imponer.
3. **En el vault.** `999-Meta/Estado-de-Implantacion.md` ya existe y cumple un papel parecido
   para el propio vault; se enlaza desde `01-Home/Home.md` para que sea lo primero que se ve al
   abrirlo.

### ADRs: aprovechar lo que ya hay

El vault trae `900-Plantillas/Plantilla-ADR.md` y la Fase 11-A ya escribió **siete ADRs**
(0003-0009) siguiendo esa plantilla. No hay que inventar nada: **la regla es que toda decisión
discutible de una fase termine en un ADR numerado antes de cerrar su PR**, y que el PR lo
enlace. Los siete de la Fase 11-A son la prueba de que el hábito funciona — fueron lo que me
permitió entender 7.000 líneas ajenas en minutos en vez de leerlas enteras.

---

## 2-bis · Deuda de cobertura: lo primero, antes de cualquier fase

Cuatro asuntos que no son una fase pero van por delante de todas. Tres los documentó la propia
Fase 11-A al cerrarse; el cuarto es un defecto en el entregable que ve el cliente.

> **Por qué existía la puerta:** (a) y (b) se cerraban **antes de la Fase 11-B**, es decir, antes
> de que nada tocara producción. No después. Ambos protegen justo el camino que 11-B estrena:
> (a) cubre el arranque de una instalación nueva —donde ya no hay `create_all` de red— y (b)
> ejecuta por primera vez los tres caminos que solo existen en PostgreSQL, que es el motor que
> 11-B pone en producción. Cerrarlos después habría sido estrenarlos con datos reales.
>
> **Estado: ABIERTA** (2026-09-09). Las dos filas están hechas y demostradas por mutación. (c) no
> es una tarea sino una regla de activación, y (d) ya se cerró. Con PostgreSQL disponible la
> suite no deja ninguna omisión escondiendo nada.

### a) Test de `init_db.main()` — ✅ **hecho** (`tests/test_siembra.py`)

**El hueco más peligroso de los cuatro.** Los tests prueban las tres piezas de la siembra por
separado (conocimiento, administrador, sesión), pero **nunca la orquestación**. La mutación que
sobrevive es envolver la siembra en un `if creado:`: en `development` y `test` no cambia nada y
la suite queda verde; en `staging` y `production`, donde la Fase 11-A retiró el `create_all` de
red (ADR-0004), **la instalación arranca sin reglas, sin parámetros y sin administrador**.

Y no se detecta hasta el despliegue, que es justo cuando más caro es. Es el defecto de la Fase
9.5 entrando por otra puerta.

- **Qué hacer:** un test que ejecute `init_db.main()` de extremo a extremo contra una base
  vacía y afirme que después existen reglas, parámetros y administrador. Y otro que cubra la
  duplicación de esa orquestación en `sembrar.py`.
- **Salida verificable:** con la mutación `if creado:` aplicada a mano, el test falla. ✅
  Demostrado: `test_init_db_siembra_aunque_el_esquema_no_lo_cree_el` falla con «sin reglas T2 el
  motor no evalúa nada», y quitar `sembrar_conocimiento` de `sembrar.main()` tumba el suyo. Lo
  que no se veía al plantearlo: **un test en el entorno de desarrollo no habría servido**, porque
  ahí `creado` es True y la mutación no cambia nada. El test tiene que correr en un entorno donde
  `create_all` NO corra, que es el único parecido a un despliegue.

### b) PostgreSQL en la CI — ✅ **hecho** (job `postgres` + `tests/test_postgres.py`)

Hoy la CI solo corre SQLite, así que **tres caminos exclusivos de PostgreSQL no se ejecutan en
ninguna parte**: `SET LOCAL statement_timeout` en la sonda de salud,
`with_for_update(skip_locked=True)` en la purga y el motivo de `_rollback_silencioso`. Además
T5 queda omitido de forma permanente.

- **Qué hacer:** añadir `services: postgres:16` al job de backend y definir
  `SEIS_TEST_POSTGRES_URL`.
- **Salida verificable:** la CI deja de reportar la omisión de T5, y los tres caminos aparecen
  ejecutados. ✅ Con PostgreSQL disponible: **455 passed, 0 skipped**. Y no basta con que
  aparezcan ejecutados: los tres están demostrados por mutación, porque un test que pasa con el
  camino puesto y sin él no prueba nada. El job además **falla si algún test se omite**, que era
  la forma exacta en que este hueco podía volver sin que nadie se enterara.

### c) La purga en modo `borrar` no se activa todavía — 🟡 regla, no tarea

`PURGA_CUENTAS_MODO` nace en `informar` y **así se queda**. Todos los tests de borrado pasan el
modo explícito y la sesión de la fixture, de modo que la combinación real —tarea + `SessionLocal`
+ ajustes de producción— **se estrenaría a las 04:30 borrando cuentas reales**.

**Condición de activación, no negociable:**

1. Un test que ejercite la ruta completa de la tarea, sin doblar la sesión.
2. Un ensayo en staging con datos de prueba, verificando qué se borró y qué sobrevivió.
3. Solo entonces, y con el modo `informar` habiendo reportado antes lo que habría borrado.

### d) `pdf_service._limpiar` partía los identificadores — ✅ hecho

`C_F` salía como «C F» en el informe. Corregido en el PR #9, con tests derivados del informe
dorado. Se deja anotado aquí porque el hallazgo salió de esta revisión.

---

## 3 · Las fases

### Fase 11-B · Despliegue real 🟡
**Objetivo.** Que SEIS esté en internet, con dominio, HTTPS, backups y alarmas.
**Por qué aquí.** Todo lo demás se valida contra algo desplegado; sin esto, cada fase siguiente
acumula riesgo no medido. Y la 11-A ya dejó el repositorio listo, así que es lo más barato.

- **Modelo:** `render.yaml` con la sintaxis correcta de blueprint, workflows de despliegue,
  runbook. Semilla ya escrita en el **PR #6 cerrado** — reutilizarla corrigiendo dos cosas:
  `healthCheckPath` debe ser `/health/listo` (no la sonda de liveness) y las variables deben
  alinearse con `.env.produccion.example` de la 11-A.
- **Tú:** dominio, Cloudflare, alta en Render, secretos, *Required reviewers* del entorno
  `produccion`, y el **simulacro de restauración de backup** (🔴, exige portátil).
- **Bloqueantes:** dominio y hosting.
- **Salida verificable:** `curl https://<dominio>/health/listo` responde 200 desde fuera; un push
  a `main` despliega staging solo; un despliegue a producción exige aprobación; restauración de
  backup documentada con tiempos medidos.
- **Riesgo específico:** el `.env` es un **cambio incompatible** — un `.env` anterior a la 11-A
  impide arrancar la pila entera (`SEIS_ENV` sin declarar vale `production` en el compose, que
  es estricto, y exige `PROXIES_DE_CONFIANZA`). Te morderá al recuperar el portátil.
- **Modelo recomendado:** **Opus 5.** El diseño operativo ya está decidido en la 11-A y sus ADRs.

### Fase 17-A · Conector de captación 🟡 (con una parte 🔴) — ✅ **hecha** (rama `fase-17a-captacion`)
> Lo 🟢 de esta ficha está construido y probado. Queda la 17-B: los selectores reales,
> que necesitan el HTML del portal. Dos hallazgos que la ficha no preveía: el alcance
> del matcher tuvo que decidirse de nuevo ([[ADR-0011]]) porque `organizacion_id=None`
> no significaba «todas» sino «nadie»; y el coste del despacho con ingesta diaria
> impone dos condiciones a la 17-B (`docs/VOLUMEN_MATCHER.md` §5).

**Objetivo.** Que entren subastas solas, que es la promesa del producto.
**Por qué aquí, y no en la posición 17.** Es el riesgo número uno del proyecto: sin caudal, las
alertas de la Fase 12 vigilan el vacío y no hay nada que monetizar en la 13.

- **Modelo (🟢, ahora):** `app/ingesta/` con parser defensivo (nunca lanza, cuenta lo no
  parseado), parámetros T3 `ingesta.boe.*` para que selectores y cadencia se cambien sin
  desplegar, dedupe por `UniqueConstraint(fuente_codigo, identificador_externo)` —estaba
  importado en `models.py` y **sin aplicar a ninguna tabla**; lo aplica la migración `0007`,
  que aborta listando los duplicados en vez de borrar filas por su cuenta—,
  transaccionalidad por lote, y vigilancia de fuentes (aviso al superadmin si una fuente lleva
  24 h a cero) reutilizando `Notificacion`, que ya existe.
- **Condición de cierre (🟢, sin dependencias externas): el puente captación → análisis.**
  Hoy `crear_analisis` crea su propia `Subasta` y no reutiliza las captadas, de modo que una
  subasta traída por el conector **no se puede analizar sin re-teclear todo**. El caudal que
  abre la 17-A desembocaría en un formulario de diez pasos. Descubierto con un caso real de la
  AEAT (ver `ESTADO_ACTUAL.md`). Esta ficha no cierra su PR sin resolverlo.
- **Decisión de producto con dueño (🟢, sin dependencias externas): cuál es el modo de
  notificación por defecto.** No es una optimización y no puede heredarse: con ingesta diaria,
  el `instantaneo` de fábrica manda **50 correos por cabeza y noche con diez usuarios**
  (`docs/VOLUMEN_MATCHER.md` §3, medido). La ficha de la 17-B es su propietaria y **no cierra su
  PR sin haberla resuelto**, con las tres opciones de esa nota decididas explícitamente, no por
  omisión. Es la primera tarea de la 17-B porque no depende del HTML.
- **Tú (🔴 o desde el móvil):** pegar el HTML real de `subastas.boe.es` (listado + una ficha).
  **Comprobado: el sandbox no puede descargarlo** — el proxy de egreso deniega ese dominio, así
  que el ajuste de selectores no se puede hacer sin que tú aportes el HTML.
- **Salida verificable:** con las fixtures reales, el parser extrae ≥ 90 % de los campos
  críticos; un HTML corrupto devuelve lista vacía sin excepción; ejecutar dos veces el mismo
  lote no duplica filas; una fuente en silencio 24 h genera notificación.
- **Riesgo específico:** el scraping tiene cara legal y de cortesía (robots, términos, cadencia
  ≤ 1 req/s, User-Agent identificado). No es solo técnico.
- **Modelo recomendado:** **Opus 5** para el andamiaje; **Sonnet 5** para el ajuste de selectores
  cuando tengas el HTML (tarea acotada de parsing, con fixtures como red).

### Fase 17-C · Fuente automática de comparables de mercado 🟡 — **nueva, sin empezar**

**Objetivo.** Que el motor pueda valorar un inmueble **sin depender de que alguien teclee
comparables a mano**, y que cuando no pueda lo diga en vez de compararse consigo mismo.

---

#### Dónde encaja en el plan, y por qué es fase propia

**Decisión: fase nueva, 17-C, inmediatamente después de la 17-B.** No es una ampliación de la
17-A/B ni una condición de cierre de la 17-B. Las tres razones, en orden de peso:

1. **Es otro problema.** La Fase 17 (A y B) trata de **encontrar** subastas: descubrir anuncios,
   parsearlos, no duplicarlos, avisar. Esto trata de **valorarlas**: traer un ancla de precio
   independiente del tasador. Comparten fontanería, no objetivo. Metido dentro de la 17-B,
   ampliaría su alcance justo cuando lo que le falta es un HTML real y acabaría retrasando ambas.
2. **Pero depende de ella, no al revés.** Reutiliza tres piezas que la 17-A ya construyó
   —parser defensivo, parámetros de fuente en T3, `vigilancia_service` para fuentes en
   silencio— y su urgencia **la crea** la 17-B: mientras el alta sea manual, el usuario puede
   teclear comparables; en cuanto entren doscientas subastas al mes, nadie lo hará. De ahí
   *después* y no *antes*.
3. **Tiene tamaño de fase, no de condición.** El puente captación→análisis sí es una condición
   de cierre de la 17-B (`docs/ESTADO_ACTUAL.md`): son horas y no tiene decisiones abiertas.
   Esto son semanas y arranca con **una investigación cuyo resultado puede cambiar el alcance**
   (si el valor de referencia no tiene servicio web libre, la fuente recomendada cambia).

**Qué la desbloquea:** nada externo para empezar la fuente 1 (dato público y gratuito). La
opción 2 (idealista/data) sí exige una negociación comercial previa, así que **no se estima en
euros** hasta tenerla.

---

#### El caso que la motiva (2026-09-10, real, no una fixture)

Se recorrió el flujo completo con una subasta real de la AEAT: **vivienda de 44 m² de 1940 en
Calle Feria 15, Santiponce (Sevilla), tasada en 23.391,72 €**, sin comparables de mercado
porque el anuncio no los trae y nadie los tenía.

Lo que hizo el motor, medido:

```
VM = 23.391,72 €    método = sin_comparables    confianza = 0,0
```

**El valor de mercado cayó al valor del propio tasador de la AEAT.** Es decir: el análisis
comparó la subasta consigo misma. El motor fue honesto —`confianza=0,0`, la carencia
«Comparables insuficientes (n≥6, CV≤20%)» en el ICI, que se hundió a 20— pero **no tenía nada
con lo que contrastar**.

Y esto no es un caso raro: **es el caso por defecto de todo lo que entre por la 17-B.** Nadie va
a teclear seis comparables por subasta cuando el conector traiga doscientas al mes. Si el
producto depende de que el usuario los aporte, no escala — y el análisis, que es lo único que
SEIS vende, queda sin ancla independiente.

> Se registra aquí, en la ficha, y no como nota al pie, por la misma razón que el trade-off del
> matcher acabó en el [[ADR-0011]]: para que quien lo implemente entienda **por qué existe** en
> vez de reconstruirlo.

---

#### Fuentes candidatas, con lo que se pudo verificar de cada una

Investigado antes de proponer. **Lo que no se pudo confirmar está marcado como tal.**

**1 · Valor de referencia del Catastro — RECOMENDADA, y es la que más resuelve**

- **Qué es:** valor oficial que la Dirección General del Catastro fija **cada año y por
  inmueble**. Consulta **gratuita y pública** —a diferencia del valor catastral, que solo puede
  consultar el titular—. Publicado para 2026 en el BOE (`BOE-B-2025-46480`).
- **Por qué encaja mejor que cualquier portal:** es **por inmueble**, oficial, sin condiciones de
  uso que prohíban la reutilización, y **ya está ligado a la referencia catastral que la subasta
  trae en el anuncio** (en el caso real: `1282034TG3418S0001UL`).
- **Y resuelve un segundo problema, mayor de lo que parece.** La base imponible del ITP es **el
  mayor** de: valor de referencia, valor declarado, o precio pagado. SEIS calcula el ITP sobre la
  puja (`m11_rentabilidad.py:41`, `p * (1 + c_v)`). En una subasta —donde el atractivo es pujar
  por debajo del valor— **eso subestima sistemáticamente el impuesto**. Con el valor de
  referencia disponible, la base pasa a ser la correcta.
  **Es un hallazgo aparte de esta ficha y hay que decidir si se corrige antes** (ver §Riesgos).
- **Coste:** gratuito.
- **Viabilidad legal:** la más limpia de todas. Dato público de una administración.
- **⚠️ Lo que NO se pudo confirmar:** que exista un **servicio web libre y documentado para el
  valor de referencia concretamente**. Los servicios libres de la Sede Electrónica que sí están
  documentados (`Webservices_Libres.pdf`, v2.6) son callejero, conversor de coordenadas y
  consulta por referencia catastral, y son **SOAP** (algunos accesibles por REST sobre HTTP). La
  consulta del valor de referencia está descrita como *interactiva* en la Sede. **Primera tarea
  de la fase: comprobarlo, y si no hay API, decidir entre el acceso autenticado con certificado
  o descartarla.** No se da por hecho.

**2 · idealista/data (API comercial) — VIABLE PERO DE PAGO Y A NEGOCIAR**

- **Qué ofrece:** API de **comparables y métricas** de zona hasta nivel de barrio.
- **Coste:** **no hay plan gratuito ni autoservicio.** Todo acceso pasa por solicitud y
  aprobación del proyecto por parte de Idealista, y el precio **se negocia caso por caso**: no
  hay tarifa publicada. **Imposible presupuestar esta fase sin hablar con ellos.**
- **Restricción de uso relevante:** está orientada a análisis de mercado y métricas, **no a
  extraer anuncios individuales con fines comerciales**. Habría que confirmar con ellos que el
  uso de SEIS —valorar un inmueble concreto para un cliente— encaja en su licencia.
- **Viabilidad legal:** limpia si se licencia. Es la vía correcta si se quiere dato de portal.

**3 · Scraping de portales (Idealista, Fotocasa) — NO RECOMENDADA**

Tres razones, en orden de peso:

- **El dato es peor de lo que parece.** Un portal publica **precios de oferta**, no de
  transacción. El propio motor ya lo sabe: `ComparableInput.origen` distingue `portal_oferta`
  de `testigo` y de `notarial` precisamente porque no valen lo mismo. Alimentarlo con ofertas
  sesgaría la valoración al alza justo en el lado que hace perder dinero.
- **Exposición legal real, no teórica.** La técnica en sí es legal, pero: el TJUE (sentencia de
  15-01-2021) confirmó que el titular de una base de datos **puede prohibir contractualmente la
  reutilización**, y los términos de estos portales lo hacen; a eso se suma la vía de competencia
  desleal por aprovechamiento del esfuerzo ajeno. Y en 2025 la AEPD sancionó por scraping
  **299 veces, 40 M€** —principalmente por datos personales, que en un anuncio inmobiliario
  aparecen con facilidad (teléfono del anunciante, nombre de la agencia)—.
- **Fragilidad operativa.** Es exactamente la deuda que la 17-A ya asumió con el BOE
  (selectores en T3, vigilancia de fuentes en silencio), multiplicada por un portal que **sí
  tiene interés en romperlo**.

**Recomendación: descartarla.** Si se quiere dato de portal, se licencia (opción 2).

**4 · Estadística oficial agregada — COMPLEMENTO BARATO Y LIMPIO**

- INE (Estadística de Transmisiones de Derechos de la Propiedad), Ministerio de Vivienda (valor
  tasado de vivienda), Consejo General del Notariado.
- **Gratuitas y sin restricción de reutilización.** Precio real de transacción, no de oferta.
- **Limitación:** son **agregadas** por municipio o provincia, no por inmueble. No sirven como
  «comparable» en el sentido de M03, pero **sí para construir una banda de €/m² de zona**, que es
  lo que M03/M04 necesitan para dar un rango en vez de un punto.
- Encaja como **red de seguridad**: cuando no haya comparables por inmueble, una banda de zona
  con confianza declarada es mucho mejor que VM = el valor del tasador.

**5 · Registradores / notariado (precio real por operación) — DESCARTADA POR AHORA**

Es el dato ideal —transacción real, por inmueble— pero el acceso es restringido y de pago, y no
hay indicio de una vía de autoservicio. Se anota y no se explora hasta que haya ingresos.

---

#### Reglas de diseño, no negociables

1. **Nunca inventar un comparable para rellenar el hueco.** Si la fuente no cubre la zona o el
   tipo de inmueble, el motor debe seguir marcando `confianza` baja y la carencia en el ICI,
   exactamente como hace hoy. **Un comparable falso es peor que ninguno**: convierte un «no lo
   sé» honesto en un número que alguien va a creerse. Esta regla es la razón de ser de la fase,
   no un detalle de implementación.
2. **Trazabilidad por comparable, no caja negra.** Cada comparable que use el motor guarda
   **de dónde salió**: fuente, identificador en origen, fecha de obtención, y URL o referencia
   cuando exista. `ComparableInput` ya tiene `origen` y `meses_antiguedad`; hay que ampliarlo y
   **persistirlo en el snapshot del análisis** (P1: el análisis es inmutable, así que el
   comparable que se usó tiene que quedar congelado con él, no releerse después).
   Criterio de salida: **desde el informe se puede llegar a cada comparable**.
3. **La fuente se declara en T3**, como los selectores del BOE: cambiar de proveedor no debe
   exigir un despliegue.
4. **Vigilancia de silencio**, reutilizando `vigilancia_service` de la 17-A: una fuente de
   comparables que deja de devolver nada tiene el mismo modo de fallo mudo que un conector roto.
5. **Declaración de alcance (ADR-0014)** en cada mecanismo nuevo: qué zonas cubre, qué
   tipologías, y qué NO.

---

#### Riesgos específicos

- **La base del ITP.** El hallazgo de §1 —SEIS calcula el impuesto sobre la puja y no sobre
  `max(puja, valor de referencia)`— es **independiente de esta fase y probablemente más urgente**,
  porque afecta a todo análisis que ya se haga hoy. Decidir si se corrige antes, por separado.
- **Sesgo de oferta.** Si acaba entrando dato de portal, el motor debe seguir ponderándolo por
  `origen`. No mezclar ofertas y testigos en el mismo saco.
- **Coste no presupuestable hoy.** La opción 2 exige negociación previa. La fase **no se puede
  estimar en euros** hasta tener esa respuesta.
- **Dependencia externa nueva** justo en el camino crítico del producto: si la fuente cae, la
  valoración se degrada. De ahí la regla 4.

---

#### Modelo recomendado

**Opus 5** para el diseño y la capa de trazabilidad —es donde está la decisión difícil, y P1
obliga a congelar el comparable en el snapshot—. **Sonnet 5** para el cliente de cada fuente una
vez decidida, que es trabajo acotado de parsing con fixtures como red.

### Fase 14 · RGPD 🟢 — ✅ **hecha** (rama `fase-14-rgpd`; falta el texto del abogado)
**Objetivo.** Poder operar legalmente con datos de personas reales en la UE.
**Por qué aquí.** Es 🟢 casi entera, y **bloquea el lanzamiento**: hoy no hay consentimientos,
ni exportación, ni borrado de cuenta. Además el registro self-service ya está vivo.

> **DECISIÓN PREVIA, tomada antes de escribir una línea (2026-09-09).** La Fase 14
> **extiende `purga_service`; no escribe un borrador paralelo.** Un segundo camino de borrado
> reproduciría las filas huérfanas que resolvió el [[ADR-0009]], y en SQLite volvería **en
> verde**, con datos personales sobreviviendo a un borrado que el sistema da por completo.
>
> Si al implementarlo resulta que extender `purga_service` no encaja, **se para y se consulta
> antes de bifurcar**: se prefiere replantear a tener dos borradores. Esto no es una
> preferencia de estilo, es la condición bajo la que se aprobó la fase.

- **Modelo:** consentimientos granulares con versión y fecha en el registro; `GET
  /cuenta/exportar`; `DELETE /cuenta` con gracia de 14 días y anonimización de auditoría.
  **Un solo camino de borrado**, el de `purga_service.py`, que ya resolvió el problema difícil:
  **no hay `ondelete` en ninguna de las seis claves foráneas**, así que un borrado desordenado
  aborta la transacción en PostgreSQL y —peor— deja huérfanos en SQLite.
- **Tú:** abogado para los textos. El hueco está preparado de punta a punta: `app/legal/textos.py`
  tiene la estructura y las versiones, `GET /legal/{tipo}` los sirve sin exigir sesión —hay que
  poder leerlos antes de registrarse— y `/legal/[tipo]` los muestra avisando de que aún son
  provisionales. Un test vigila el marcador «PENDIENTE DE REDACCIÓN LEGAL»: cuando lleguen los
  textos, se pone rojo y obliga a subir `VERSION_VIGENTE` a mano.
- **Deuda que abre esta fase (dueña: Fase 16):** `usuario_service` sigue escribiendo la DIRECCIÓN
  en `auditoria.quien`/`entidad_id` en el alta, la verificación y el cambio de contraseña. El
  borrado la limpia después ([[ADR-0013]]), pero el origen no está arreglado, y `auditoria` no
  tiene clave foránea a `usuario`, así que ningún test derivado del esquema puede vigilarlo.
- **Salida verificable:** un usuario exporta sus datos y borra su cuenta sin intervención; los
  consentimientos quedan con versión y fecha; la auditoría del borrado queda anonimizada. Y,
  como condiciones explícitas de la aprobación:
  1. **Cero filas huérfanas tras `DELETE /cuenta`, demostrado también contra PostgreSQL** en el
     job `postgres` de la CI. SQLite miente justo aquí: con las claves foráneas apagadas, un
     borrado incompleto pasa en verde.
  2. **Demostración por mutación:** romper el borrado en cascada o la anonimización de auditoría
     debe verse en rojo.
  3. **La exportación no cruza organizaciones**, con test negativo explícito.
  4. **Consentimientos con versión y fecha, guardados ya por el registro**, con el hueco de los
     textos legales preparado para cuando lleguen.
- **Riesgo específico:** el borrado toca datos irrecuperables. Los tests deben cubrir el ciclo
  completo con cancelación dentro de la gracia.
- **Modelo recomendado:** **Opus 5.** El borrado en cascada manual es delicado, pero es
  verificable con tests, que es el criterio.

### Fase 13 · Monetización con Stripe 🟡
**Objetivo.** Cobrar.
**Por qué aquí.** Ya tiene plan escrito (`docs/FASE_13_PLAN_EJECUCION.md` y su mapa de impacto),
pero depende del trámite más lento de todos —la figura fiscal— y no tiene sentido cobrar por un
producto que aún no capta.

- **Modelo:** tabla `Suscripcion`, Checkout, Customer Portal, webhooks **idempotentes**,
  dependencia `exigir_limite`. Sin claves configuradas, el módulo queda desactivado y el
  producto funciona como hoy.
- **Tú:** figura fiscal, alta en Stripe, Stripe Tax, productos y precios, endpoint de webhook.
- **Salida verificable:** con tarjeta de prueba, un usuario gratis choca con su límite, mejora,
  se le amplía al instante, cancela y vuelve a gratis; un webhook repetido no duplica efectos.
- **Riesgo específico:** el enforcement de «alertas» necesita enganchar en el CRUD de alertas de
  la Fase 12 — existe, pero conviene revisarlo antes de dar el límite por aplicado.
- **Modelo recomendado:** **Opus 5.** Los ciclos de suscripción y la idempotencia son terreno de
  errores sutiles, pero son exactamente lo que un test de transiciones cubre bien.

### Fase 16 · Endurecimiento de seguridad 🟢
**Objetivo.** Cerrar vectores antes de exponer el producto a tráfico y dinero.
**Por qué aquí.** Tiene que ir después de que existan Stripe y la ingesta, porque son dos de sus
objetivos de auditoría (SSRF en el conector, firma de webhooks) — auditar antes sería auditar
la mitad.

- **Modelo, Parte 1 (solo informe):** auditoría OWASP contra el repositorio →
  `docs/AUDITORIA_SEGURIDAD.md`, y **parar ahí**.
- **Modelo, Parte 2 (tras tu aprobación):** correcciones, rate limiting global —extendiendo
  `core/rate_limit.py`, que la 11-A ya reescribió con ventana deslizante y degradación
  controlada—, cabeceras de seguridad.
- **Tú:** Dependabot, WAF de Cloudflare, y (recomendado) que alguien externo intente romperlo.
- **Salida verificable:** cero hallazgos altos o críticos abiertos; test que verifica el rate
  limiting global; cabeceras comprobadas en la respuesta real.
- **Modelo recomendado:** **Fable 5.1 solo para la Parte 1** (el informe), y **Opus 5 para la
  Parte 2**. Es el único uso de Fable que propongo en todo el plan, y esta es la justificación:
  la auditoría es razonamiento adversarial puro, y su modo de fallo es **el hallazgo que nadie
  encuentra**. No hay test que falle por un vector que no se te ocurrió, así que el coste del
  error es alto y, por definición, invisible para la suite — que es exactamente tu criterio.
  Aplicar tu regla al pie de la letra: Fable produce el documento, Opus 5 implementa.

### Fase 15 · Landing, onboarding y ayuda 🟢
**Objetivo.** Que un desconocido entienda SEIS en 10 segundos y llegue solo a su primer análisis.
**Por qué aquí.** Es la primera fase con trabajo visual serio, y **no debe empezar sin
`docs/DESIGN_SYSTEM.md`** (ver §4). Además su onboarding mide «primera alerta», que solo
significa algo cuando hay captación real.

- **Modelo:** landing pública en la raíz (hoy `/` está bajo `(app)` y protegida), onboarding con
  checklist persistida, `/ayuda`, correos de ciclo de vida.
- **Tú:** decidir si la app se mueve a `/app` o a un subdominio; escribir el contenido real y el
  `MANUAL_DE_USUARIO.md`, que **no existe** (solo hay `MANUAL_DE_PRUEBAS.md`, que es de
  instalación).
- **Salida verificable:** Lighthouse ≥ 90 en rendimiento y accesibilidad; un usuario nuevo llega
  al primer análisis sin ayuda; la landing no rompe el guard de sesión de la app.
- **Riesgo específico:** mover el guard de sesión es el cambio con más superficie de regresión de
  toda la fase. Tests de que las rutas privadas siguen exigiendo sesión.
- **Modelo recomendado:** **Opus 5**, referenciando siempre `docs/DESIGN_SYSTEM.md`.

### Fase 19 · Analítica y panel de negocio 🟡
**Objetivo.** Medir el embudo, sin lo cual la beta no enseña nada.
- **Modelo:** Plausible sin cookies (evita el banner y simplifica el RGPD), eventos del embudo,
  panel de superadmin, widget de feedback.
- **Tú:** alta en Plausible.
- **Salida verificable:** los seis eventos del embudo se disparan en los puntos exactos; el panel
  cuadra con la base de datos.
- **Modelo recomendado:** **Sonnet 5.** Integración documentada y acotada.

### Fase 18 · WhatsApp 🔴 (condicional)
**Objetivo.** Canal chat de alto contacto.
**Puerta:** solo si la Fase 12 demuestra demanda (p. ej. > 30 % de usuarios activos vinculan
Telegram). Depende además de la figura fiscal (Meta Business) y de plantillas aprobadas por Meta,
cuyos plazos no controlas.
- **Modelo recomendado:** **Sonnet 5**, reutilizando el patrón del canal Telegram ya construido.

### Fase 20 · Beta cerrada y lanzamiento 🔴
**Objetivo.** Validar con humanos reales antes de abrir.
Exige QA guionizado multinavegador, prueba de carga y usuarios reales: **es la fase que más
necesita el portátil**. El guion de QA sí puede redactarlo el modelo por adelantado (🟢).
- **Salida verificable:** primeros clientes de pago; embudo midiendo; una semana estable sin
  intervención manual.
- **Modelo recomendado:** **Opus 5** para el guion; la ejecución es humana.

---

## 4 · Fase 0 transversal · Sistema de diseño 🟢

**No es una fase del Plan Maestro: es un prerrequisito que este plan añade.** El motivo está en
`docs/ESTADO_ACTUAL.md`: el frontend son 3.292 líneas **sin un solo test y sin ESLint**, con toda
la UI en un único `components/ui.tsx` artesanal. Sin tokens ni reglas escritas, cada sesión
improvisa y el resultado sale genérico — que es exactamente la queja.

Debe producirse **antes que la Fase 15**, y a partir de entonces **ningún prompt de frontend se
ejecuta sin referenciar `docs/DESIGN_SYSTEM.md`**.

Su contenido, la decisión abierta sobre shadcn/ui y las herramientas (skills, MCPs, Obsidian) van
en `docs/HERRAMIENTAS.md` (Paso 4), no aquí.

---

## 5 · Resumen del orden y por qué

| # | Fase | Clase | Depende de |
|---|---|---|---|
| **0** | **Deuda de cobertura (§2-bis a y b)** | 🟢 | — · **PUERTA: nada que toque producción se despliega antes** |
| 1 | 11-B · Despliegue | 🟡 | Dominio, hosting · **la puerta 0** |
| 2 | 17-A · Captación | 🟡 + 🔴 | HTML real del BOE |
| 2-bis | 17-C · Comparables de mercado | 🟡 | La 17-B · investigar si el valor de referencia tiene servicio web libre |
| 3 | 14 · RGPD | 🟢 | Abogado (textos) |
| 4 | 13 · Stripe | 🟡 | **Figura fiscal** (empieza hoy) |
| 5 | 16 · Seguridad | 🟢 | Que existan 13 y 17 |
| 0' | Sistema de diseño | 🟢 | — (antes de la 15) |
| 6 | 15 · Landing | 🟢 | Sistema de diseño |
| 7 | 19 · Analítica | 🟡 | Alta en Plausible |
| 8 | 18 · WhatsApp | 🔴 | Puerta de demanda + fiscal |
| 9 | 20 · Beta | 🔴 | Todo lo anterior |

**Mientras no haya portátil**, el trabajo 🟢 disponible es: el andamiaje de la 17-A, la Fase 14
casi entera, la Fase 16 completa, y el sistema de diseño. Es varias semanas de trabajo sin tocar
un panel externo.
