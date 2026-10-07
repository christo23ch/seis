# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

Este proyecto **no versiona por SemVer**: versiona por **fases del Plan Maestro**
(`docs/SEIS_Plan_Maestro_Fases_920.md`). Cada entrada corresponde a una fase
cerrada, con la fecha en que se dio por terminada, salvo entradas de
infraestructura transversal (como la de Obsidian) que no pertenecen a ninguna
fase concreta.

Las fases 1-8 construyeron el motor experto y el producto de un solo tenant.
Este registro arranca en la Fase 9, que es cuando el proyecto empieza a
convertirse en un SaaS. Lo anterior está en el historial de git.

> **Dos numeraciones distintas.** Las entradas «Línea de producto · Fase 1-4» y
> «Fase 5C-5F.7» de abajo **no son** las fases 1-8 del Plan Maestro: son una
> línea de trabajo posterior (trazabilidad del análisis y simulaciones) que se
> numeró por su cuenta. Así aparecen en el código (`Fase 3:`, `Fase 5D —`…).

---

## [Fase 5J-3] — Aviso de la franja del letrado; reglas sincronizadas al sembrar — 2026-10-08

Rama `fase/5j-3-avisos`, apilada sobre la 5J-2b, sin PR ([[ADR-0027]]). **Cambia el semáforo, no
los números**, con la tabla antes/después aprobada por el responsable. Suite: 1183 passed,
18 skipped, 0 failed (+34). Vitest: 144 (+1). Revisión de código: 0 críticos, 0 altos; 2 medios y
4 bajos corregidos. Sin migración.

### Añadido
- **Aviso de la franja del letrado** (`procedimiento.aviso_aprobacion`, en el motor): en un
  procedimiento judicial con la puja máxima por debajo de la aprobación segura (70 %), bloque
  destacado bajo el semáforo con el riesgo y los umbrales T3 (cada uno con su estado), condición en
  la decisión e ítem en el checklist. Franjas: **por debajo del suelo** de la vivienda habitual y
  **a decisión del letrado** ⇒ techo naranja e ítem bloqueante; **sujeta a mejora** ⇒ sin techo e
  ítem no bloqueante. Nunca veto; ningún número cambia. Vivienda habitual «no consta» ⇒ se asume
  que sí, con aviso. El panel del procedimiento lo destaca.
- **Las reglas T2 se sincronizan al sembrar** (`scripts/sembrar.py::sincronizar_reglas`): una
  versión nueva del catálogo sustituye a la sembrada; nunca pisa una creada por la API.

### Cambiado
- **§19: amarillo → naranja** (por debajo del suelo de la vivienda habitual supuesta, 91.200 €).
  Guarda invariante regenerada: 13 hojas por caso, ninguna numérica.
- **SEM-EJEC-01 2026.10.07** y riesgo de ejecución de M13: la cesión de remate es del ejecutante
  y, con la LO 1/2025, también de los acreedores posteriores (LEC 647.3).

### Despliegue
- El siguiente `init_db` lleva SEM-EJEC-01 2026.10.07 a las bases ya sembradas (salvo que alguien
  la haya editado por la API, que manda).

---

## [Fase 5J-2b] — Depósito, táctica de puja y plazo reales — 2026-10-07

Rama `fase/5j-2b-deposito-y-plazo`, sin PR ([[ADR-0024]], [[ADR-0025]], [[ADR-0026]]). **Cambia
cifras**, con la tabla antes/después aprobada por el responsable. Suite: 1149 passed, 18 skipped,
0 failed (+49). Vitest: 143 (+2). E2E: 168 comprobaciones (+5), 0 fallos. Sin migración.

### Cambiado (cifras)
- **Plazo de la operación** = ocupación + obra + comercialización + **meses de inmovilización**
  entre el cierre y la posesión (T3 por régimen, al plazo legal máximo). Régimen judicial sin
  fecha de inicio ⇒ el plazo más largo (2,5 meses); sin plazo en la norma o venta no reglada ⇒
  2,5 meses, «estimación prudente, sin base legal».
- **§19:** plazo 13 → 15,5 meses (P80 18,2 → 21,7); escalera 51.317 / 60.011 / 68.731 / 80.022 →
  50.753 / 59.447 / 67.941 / 78.529 €; coste de capital 3.659,05 → 4.362,72 €; RVC 1,077 → 1,064
  (alcanzable); TIR 33,87 → 26,41 %; VAN 33.230,42 → 32.721,46 €; colchón a P_max 60,9 → 61,5
  meses; semáforo, ICO, RA, ROI y capital para pujar sin cambio.
- El aviso del catálogo para el coste de capital pasa del 6 % al 5 %: el umbral medido en el
  §19 a partir del cual la escalera degenera baja de 6,13 % a 5,14 %.

### Cambiado (textos)
- **Depósito** del plan de puja, del §2 y del checklist: el del régimen (20 % con la LO 1/2025,
  supuesto desfavorable si no consta la fecha de inicio), no el 5 % del alta.
- **Táctica de puja por forma de puja** (nuevo dato T3, contrastado con la API del BOE): pujas
  secretas sin prórroga, visibles con prórroga, visibles sin prórroga fijada, presencial o «no
  consta». La forma de puja figura en la base legal del informe y del panel.
- **SEM-EJEC-01 2026.10:** «depósito según el régimen del procedimiento (20 %…; 5 %…)». Salda el
  único «%» pegado que quedaba en el informe.
- El aviso orientativo del procedimiento ya no dice que nada de él mueve las cifras.
- El informe escribe el plazo con un decimal cuando no es entero («15,5 m»), en el §5 y en los
  escenarios del §7.

### Despliegue
- La siembra copia el catálogo de reglas a la tabla `regla` solo si está vacía, y desde entonces el
  motor ignora el YAML: **las bases ya inicializadas conservan SEM-EJEC-01 2026.07**. La versión
  2026.10 solo llega a las bases nuevas (ADR-0024). Los parámetros T3 sí llegan.

### Pruebas y referencias
- `tests/datos/invariante_5h1.json` **regenerada** con aprobación expresa; vigila también los
  campos añadidos desde la 5H.1. Diff hoja a hoja en el ADR-0026 y en la entrega de la fase.
- `tests/test_deposito_plazo_5j2b.py` (48). «Ver cálculo» del plazo sustituye la inmovilización;
  datos de prueba del frontend y `docs/SEIS_informe_ejemplo_caso19.md` regenerados.

---

## [Fase 5J-2a] — Textos legibles en el informe y el PDF; operandos de «Ver cálculo» — 2026-10-07

Rama `fase/5j-2a-textos-y-datos`, sin PR ([[ADR-0023]]). Ninguna cifra cambia: la guarda del §19
(510 hojas) pasa sin tocarla. Suite: 1100 passed, 18 skipped, 0 failed (+39). Vitest: 141 (+8).
E2E: 163 comprobaciones, 0 fallos. Sin migración.

- **Textos (a):** `app/engine/textos.py`; M14 redacta con nombres legibles (costes fijos, descuento de
  prudencia, jurídico, una dimensión alta…). Los códigos del resultado no cambian.
- **Datos (b):** campos nuevos y opcionales con los operandos de «Ver cálculo» (escalera y tramos
  fiscales, rentista, RA, P_adj, TIR/VAN, colchón, plazo, ICI y evidencias).
- **Frontend:** «Ver cálculo» completa esas fórmulas; los tests las recalculan contra el motor.
- Revisión de código: 0 críticos, 0 altos; 2 medios y 3 bajos corregidos.

---

## [Fase 5K] — Presentación: informe maquetado, datos legibles, fórmulas y «Ver cálculo» — 2026-10-07

Fase de solo frontend sobre `docs/INVENTARIO_PRESENTACION.md`. Rama `fase/5k-presentacion`, sin
PR. **Sin dependencias nuevas** (decisión del responsable: renderizador de Markdown propio).
No toca `backend/` ni `app/engine/`: ninguna cifra cambia y la guarda del §19 y la suite del
backend pasan igual (1061 passed, 18 skipped, 0 failed). Vitest: 133 tests (+69). E2E nueva `frontend/e2e/presentacion.mjs` (1440 y
390 px) en `e2e/correr_simulaciones.sh`; la batería completa da 157 comprobaciones, 0 fallos.

### Añadido
- **A · Informe maquetado.** La vista previa y los informes oficiales pintan el Markdown de M14
  (títulos desde h2, listas, casillas del checklist, negritas, cursivas y tablas con
  desplazamiento propio y enfocable) en lugar de mostrarlo en crudo. `lib/markdown.ts` devuelve
  nodos, nunca HTML. El texto congelado de los informes oficiales no cambia.
- **B · Datos legibles.** «Datos de entrada» por los pasos del asistente, con nombres, unidades
  y valores en español; «Árbol completo vigente» en secciones plegables con los nombres y
  unidades del catálogo de las Simulaciones (los datos legales de la 5J-1, con artículo y
  estado). «Ver JSON» conserva la vista anterior. El editor libre muestra el valor vigente.
- **C · Fórmulas e identificadores.** `P_max`, `C_F`, `c_v`, `δ_v`… con subíndice, y las claves
  internas (`ocupacion_desalojo`, `judicial_boe`, `una_alta`…) con su nombre, solo al mostrar.
- **D · «Ver cálculo»** con fórmula, valores sustituidos y resultado del motor en ICI, C_F, c_v,
  reforma, valoración por comparables, escalera (P_objetivo, P_max, P_límite y coste de
  capital), RVC, ROI, inversión total, margen de seguridad y riesgo por dimensión. El frontend no
  recalcula. Cada fórmula se verificó recalculándola en los tests con el resultado real del §19.
  Lo que no viaja en el resultado dice «Cálculo no disponible aún» y el dato que falta.

### Corregido
- **E · Los pesos del desglose del ICO estaban escritos en el frontend** (`resultado.tsx:196`).
  Ahora salen del catálogo y son los de los parámetros que produjeron el resultado mostrado.
- Cabecera: RVC con coma decimal; perfil y dimensiones de riesgo con su nombre y tildes.
- **Revisión de código (`code-reviewer`: 0 críticos, 2 altos, 3 medios), corregida antes del
  commit final:** la reforma sumaba dos veces los extras conocidos (en M05 la obra ya los
  incluye); con la capitalización vinculante del perfil rentista se mostraba «VS = VS_m2 × m²»,
  que no era el VS usado; la inversión total se sustituía con P_objetivo en vez del P_eval del
  motor; el margen de seguridad no decía que está acotado a 0; una fila de «-» en una tabla
  desaparecía; el respaldo de identificadores reescribía nombres de fichero, correos y rutas; y el
  aviso de pesos del ICO no distinguía «cargando» de «sin snapshot». Cada caso tiene su test.

### Deuda (para la 5J-2)
- `docs/DEUDA_PRESENTACION_MOTOR.md`: 14 datos que el resultado no trae, textos del motor con
  claves internas (que siguen llegando así al PDF oficial), el endpoint global del catálogo y
  pantallas de frontend fuera del alcance (reglas, simulaciones).

---

## [Fase 5J-1] — Datos del procedimiento de subasta, informativos (diseño A) — 2026-10-07

Primera capa del diseño elegido en la 5J-0 (C, construido A → B → C). Rama
`fase/5j-1-datos-procedimiento`, sin PR. Autorización expresa para tocar `app/engine/` solo para
añadir campos y cálculos informativos ([[ADR-0022]]). **Ninguna cifra existente cambia:** la guarda
`tests/datos/invariante_5h1.json` (510 hojas del §19) pasa sin tocarla. Suite al cerrar:
1061 passed, 18 skipped, 0 failed (+45 tests de backend); 64 tests de vitest (+10); e2e nueva
`frontend/e2e/procedimiento.mjs` en `e2e/correr_simulaciones.sh` (la batería completa: 105
comprobaciones de navegador, 0 fallos).

### Corregido
- **El procedimiento dejaba de seguir a la fuente** tras su primer cambio automático
  (react-hook-form lo daba por modificado). Lo destapó la e2e nueva antes del commit.
- **Revisión de código (`code-reviewer`, 0 críticos, 0 altos):** en el régimen de 2015 y en la TGSS
  la norma exige *superar* el umbral (`estricto: true` en el parámetro y aviso en el resultado); el
  aviso de vivienda habitual ya no muestra el código interno «P4»; un cambio de fuente antes de
  cargar `/opciones` ya no se pierde.

### Añadido
- **Preguntas del procedimiento en el alta:** tipo (judicial, AEAT, TGSS, notarial, extrajudicial,
  concursal, no aplica), preseleccionado con el de la fuente; si el judicial se inició antes o
  después del 3-4-2025, con «No sé»; vivienda habitual del ejecutado sí / no / no consta (sustituye
  a la casilla); cantidad reclamada opcional. Cada una solo donde cuenta, con errores en español.
- **Parámetros T3 `procedimiento.regimenes`**: depósito, depósito mínimo, plazo de pago, umbrales de
  aprobación (segura, general, por cubrir la deuda, vivienda habitual), puja mínima y meses de
  inmovilización por procedimiento y régimen, cada uno con su artículo y marcado confirmado o sin
  confirmar según `docs/INVESTIGACION_PROCEDIMIENTOS_SUBASTA.md`.
- **`app/engine/procedimiento.py`**, puro y fuera del DAG: régimen aplicable, depósito exigido y
  capital necesario para pujar, plazo de pago, meses de inmovilización, puja mínima aprobable sin
  depender de la autoridad, puja de aprobación segura y suelo absoluto, con base legal y avisos.
  Supuestos declarados: régimen «No sé» ⇒ LO 1/2025; vivienda habitual «No consta» en una vivienda
  ⇒ sí. Un dato sin valor fiable queda en «no consta» (P4).
- **`AnalisisResult.procedimiento`**, subapartado al final del §8 del informe con aviso estándar de
  cálculo orientativo, y panel «Procedimiento y umbrales legales» en el resultado del asistente y en
  la pestaña Estrategia de puja.
- **`/opciones`**: etiquetas de los procedimientos, procedimiento por fuente y fecha de la LO 1/2025.

### Migraciones
- **`0016_datos_procedimiento`**: `subasta.procedimiento`, `subasta.regimen_judicial`,
  `subasta.cantidad_reclamada` y `activo.vivienda_habitual_ejecutado`, anulables y sin relleno.
  Verificada con T1-T6 y sobre una copia de la base de desarrollo.

### Cambios incompatibles
- **Una base de desarrollo creada con `create_all` debe migrarse a mano** (`alembic stamp 0015` y
  `alembic upgrade head`; `MANUAL_DE_PRUEBAS.md` §1 bis): `create_all` no añade columnas a tablas
  existentes y el alta fallaría al guardar.

### Deuda que queda (a propósito)
- El depósito del alta sigue en el 5 % por defecto y alimenta el plan de puja de M13; el resultado
  muestra el legal y avisa de la diferencia. Corregirlo mueve cifras (5J-2/5J-3).
- La táctica de puja de M13 («la extensión automática del cierre…») sigue sin distinguir el régimen.
- Los parámetros del procedimiento no son simulables; `defaults.yaml` sigue en la versión `2026.07`.

---

## [Fase 5J-0] — Investigación de las reglas legales de puja e inventario de presentación — 2026-10-07

Solo documentos, sin cambios de código (PR #31). `docs/INVESTIGACION_PROCEDIMIENTOS_SUBASTA.md`
(umbrales, depósitos y plazos por procedimiento, leídos en el BOE), `docs/IMPACTO_MOTOR_UMBRALES_LEGALES.md`
(diseños A, B y C) y `docs/INVENTARIO_PRESENTACION.md` (formato pobre, fórmulas con barra baja y
métricas sin cálculo consultable).

---

## [Fase 5I] — Formulario de alta: errores, validación guiada y datos que faltan — 2026-10-06

Fase de producto motivada por una prueba manual del asistente de alta («Nueva inversión»).
Rama `fase/5i-formulario-alta`, sin PR. Cada bloque pasó por `code-reviewer` y por el revisor de
su lenguaje (`react-reviewer`, `python-reviewer`), con 0 críticos al cerrar; CI en verde tras
cada commit. Suite al cerrar: 1002 passed, 18 skipped, 0 failed (+37 tests de backend); 54 tests
unitarios nuevos de frontend (vitest); dos e2e nuevas (`nueva-inversion.mjs`,
`validacion-alta.mjs`) que corren en `e2e/correr_simulaciones.sh`.

### Corregido
- **El alta daba 422 con cualquier opcional vacío** (`f97f620` ya lo tenía; viene del commit
  inicial). El asistente enviaba `aPayload(form.getValues())`: el texto crudo de los campos, y
  cada opcional vacío viajaba como `""`. Ahora el envío pasa por `handleSubmit` (valores ya
  validados) y un normalizador único, `limpiarVacios`, que omite los vacíos (5I-A).
- **La antigüedad de un comparable podía ser negativa.** No hay ningún cálculo de antigüedad:
  era el control, `type="number"` sin mínimo, que bajaba a −1, −2… con la flecha ↓ o la rueda.
  Los campos numéricos son ahora texto con teclado decimal y el esquema exige ≥ 0. El backend
  sigue aceptando negativos (ver Deuda).
- **Los campos condicionales perdían lo tecleado al cambiar de paso** (defecto introducido en
  5I-A y corregido en 5I-C): `shouldUnregister` los daba de baja al desmontarse el paso.
  `rutasOcultas` es ahora la única fuente de qué está oculto.

### Añadido
- **Conversor numérico único** `aNumero`: coma decimal, punto de miles en importes, punto
  decimal en tasas/coeficientes/coordenadas; rechaza mezclas ambiguas en vez de adivinar.
- **Valores por defecto visibles**: valor inicial cuando es el del contrato; marcador o ayuda
  cuando vacío significa «el motor estima» (atrasos, tenencia, ITP, costes fijos, baremos).
  `GET /opciones` expone `valores_defecto` del catálogo T3 vigente.
- **Validación guiada** (5I-B): obligatorios con «*»; mensaje en rojo bajo cada campo, foco y
  desplazamiento al primero, y salto al paso que lo contiene; los 422 del backend traducidos
  campo a campo al español (`traducir422`); `aria-invalid`/`aria-describedby` en `Campo`.
- **Depósito como importe o porcentaje** (5I-C): conversión en un solo sitio
  (`depositoFraccion`) con su equivalente visible; `SubastaInput.deposito_importe` opcional e
  informativo, que el motor no lee.
- **Estado de conservación «No consta»** (5I-D, [[ADR-0020]]): el motor asume el estado del
  parámetro T3 `conservacion.desconocido_usa` («malo»), sin cambiar pesos ni fórmulas; aviso en
  el informe e ítem de checklist. Es el valor por defecto del formulario (antes «regular»).
  El parámetro se valida al escribirlo (400 con los valores admitidos).
- **Coordenadas aproximadas desde la provincia** (5I-E): las 52 provincias con la coordenada
  de su capital (CartoCiudad/IGN), autocompletado que no pisa lo escrito y marca «aproximada
  (provincia)». El motor no usa lat/lng.
- **Tests unitarios de frontend** con vitest (`npm test`, paso nuevo en la CI) y las e2e
  `nueva-inversion.mjs` y `validacion-alta.mjs`, que corren en `e2e/correr_simulaciones.sh`.

### Cambio de comportamiento
- Un alta en la que nadie toca el estado de conservación sale ahora con «No consta» (reforma
  media, k = 0,72), no con «regular»: precios recomendados más bajos. Intencionado (P4).
- El caso dorado §19 no cambia ni un valor (guarda `test_invariante_5h1`). Sin migraciones.

---

## [Fase 5H.1] — Motor: VAN, coste de capital sobre el capital propio, colchón de plazo y especificación coherente — 2026-10-04

Puntos de la auditoría 5G.4 que **no cambian el caso dorado** (`docs/AUDITORIA_MOTOR_ESPECIFICACION.md`,
E1, E5, E6 y el punto 5 del orden E7), con autorización expresa para tocar `app/engine/`.
**Guarda invariante de toda la fase:** `tests/datos/invariante_5h1.json` es la foto del
resultado completo del §19 y del §19 con hipoteca tomada antes de empezar; el §19 no cambió ni
una de sus 510 hojas, y el caso con hipoteca solo las cuatro que justifica D5. Cada bloque pasó
por el agente `code-reviewer` (0 críticos, 0 altos en B y C). Suite al cerrar: 965 passed,
18 skipped, 0 failed; CI en verde en cada bloque.

### 5H.1-A · VAN y diferencial TIR frente al coste de capital (`31dd511`, ADR-0017)

#### Añadido
- M11 calcula, con los mismos flujos que la TIR (escenario base, P_objetivo),
  `van_coste_capital` y `diferencial_tir_coste_capital` (puntos). Tasa efectiva anual llevada a
  mensual con `(1+cc)^(1/12) − 1`, la misma equivalencia que la TIR: VAN = 0 cuando cc = TIR.
  Informativos. §19: **33.230 € y +32,37 puntos**.
- Informe (§7), «Métricas de decisión» y comparación de simulaciones.
- `tests/test_golden_caso19.py`: la entrada pasa a la función `entrada_caso_19()` (mismos 52
  assert y 14 tests) para que la guarda y sus scripts la reutilicen.

### 5H.1-B · Coste de capital solo sobre el capital propio (`5cb0634`, `1386faa`, ADR-0018)

#### Corregido
- **Con hipoteca, el precio límite cobraba dos veces la parte financiada** (intereses en `c_v`
  y coste de oportunidad sobre toda la inversión). Ahora
  `coste_capital = cc · max(0, I(P_max, C_F^P80) − LTV·P_max) · plazo_P80/12`. Sin hipoteca,
  idéntico. Caso con hipoteca (LTV 70 %, 3,5 %): coste de capital 3.659,05 → 2.603,76 € y
  **P_límite 77.100 → 78.156 €**. `detalle["capital_propio"]` guarda la base.
- `1386faa`: correcciones de la revisión de código (el test del `max(0, …)` no saturaba con
  LTV 1,2; test de compra al contado con LTV informado; test del rentista con la fórmula).

### 5H.1-C · Colchón de plazo (`f2bc04a`, ADR-0019)

#### Añadido
- §9.5: meses extra hasta beneficio base cero por tenencia, intereses del préstamo y coste de
  oportunidad del capital propio, a P_objetivo y a P_max. Informativo. §19: **84,8 meses
  (60,9 a P_max)**. `None` con escalera degenerada o sin coste mensual.
- Informe, «Métricas de decisión» y comparación de simulaciones.

### 5H.1-D · Especificación coherente con el motor

#### Cambiado
- Especificación: §9.1 define `coste_capital` (con D5); §7.7 añade VAN_cc y Δ_cc; §9.5 concreta
  el colchón; **§19 regenerado con las cifras reales del motor** y un recuadro de qué cambió y
  por qué (C_F^P80 85.060/86.800 → 87.708 €, coste de capital 3.659 €, P_límite 82.500 →
  80.022 €, «TIR ≈ 23 %» era el ROI anualizado: ROI anualizado 22,9 % y TIR 33,9 %).
- `docs/SEIS_informe_ejemplo_caso19.md` regenerado: era anterior a la corrección del ITP y a la
  5G.2. Lo leen los tests del PDF (en verde).
- `ESTADO_ACTUAL` §4: cerrada Backend 16 y la 18 en parte; nuevas Backend 19-21 y Pruebas 5.
- Auditoría: estado punto a punto tras la 5H.1. Vault: notas `40-Fases/Fase-5G-4`,
  `40-Fases/Fase-5H-1` y `02-Diario/2026-10-04`.

---

## [Fase 5G.4] — Coste de capital, decimales en formato español y e2e en CI — 2026-10-01

Decisiones del responsable D1–D5 sobre `capital.coste_capital_anual`, registradas en
[ADR-0016](30-Decisiones/ADR/ADR-0016-coste-de-capital-como-coste-de-oportunidad.md).
**Ningún cálculo del motor cambia**: los tests de la fase fijan los valores de M11, M12 y M13
del caso §19 capturados antes de empezar. Commits `3ecc9c8` (A), `729efd5` (B), `e2284da` y
`b74abd0` (C). **CI en verde con los cuatro jobs, incluido el nuevo `e2e`:**
[ejecución 36921942152](https://github.com/christo23ch/seis/actions/runs/36921942152).

### 5G.4-A · Coste de capital como coste de oportunidad, rango y aviso

#### Añadido
- **Catálogo:** `capital.coste_capital_anual` se describe como coste de oportunidad del capital
  propio (D1), con unidad «fracción anual (0–1)», **rango 0–0,15** (D2) y dos campos nuevos
  opcionales, `umbral_aviso` (0,06) y `texto_aviso` (D3). Advertencia e impacto dicen que solo
  afecta al precio límite (§9.1), no al ROI ni a la TIR. El nivel de riesgo sigue
  `pendiente_de_definir`: el catálogo no tiene escala para él.
- **`GET /analisis/{id}/parametros-simulables`** devuelve `umbral_aviso` y `texto_aviso` en cada
  editable (`null` si no tiene aviso). Cambio aditivo.
- **Editor de simulaciones:** aviso en el campo si el valor supera el umbral o sale del rango.
  No bloquea crear; el backend decide.
- **Informe (M14) e interfaz (escalera de precios):** «El coste de capital (X % anual, coste de
  oportunidad del capital propio) solo se descuenta del precio límite (§9.1); ROI y TIR no lo
  incluyen. Importe aplicado: Y €.» Sin tasa o sin importe no se muestra.
- **M12** añade la tasa aplicada a `precios.detalle["coste_capital_anual"]` (trazabilidad).

#### Cambiado
- **Validación de rango vinculante** con una sola función, `simulacion_service.validar_rangos`,
  para las simulaciones y para la edición global (`PUT /parametros`). Fuera del rango concreto
  del catálogo: **422** con el rango en español, sin escribir filas ni auditoría. Las **11
  cotas técnicas** que ya existían (dominancias de RA, umbral ICI del ICO, `ico_min`, `ici_min`
  y `ms_valor_min` del semáforo) pasan a ser vinculantes; ningún valor guardado ni por defecto
  quedaba fuera. Publicar una sección entera no salta el rango de sus hojas.
- **Incompatible:** `PUT /parametros` responde 422 (antes 200) a un valor fuera de rango, y una
  simulación con coste de capital > 0,15 ya no se puede crear. Las ya guardadas se siguen
  leyendo.

### 5G.4-B · Decimales en formato español en el informe

#### Corregido
- El informe usaba el formato de Python: «25.0%», «6.40%», «RVC 1.08», «CV 5.3%». Pasa a coma
  decimal y «25,0 %» con `app/engine/formato.py` (`decimal`, `pct`) en M14, M13 (depósito del
  plan de puja) y M12 (razones con MS y RVC). Mismo redondeo; solo cambian los separadores. En
  el §19 cambian 15 fragmentos, enumerados en `tests/test_informe_coherencia.py::FORMATO_5G4B`.
- Los informes oficiales ya emitidos conservan su texto (Markdown congelado).

### 5G.4-C · E2E en CI, lanzadores unificados y desbordamiento de /app

#### Añadido
- **Job `e2e` en la CI** (`ubuntu-latest`, `CHROMIUM_PATH=/usr/bin/google-chrome`, sin descargar
  navegadores): ejecuta `e2e/correr.sh` y `e2e/correr_simulaciones.sh`.
- `frontend/scripts/navegador.mjs`: **una sola variable para el navegador** en los seis guiones
  de Playwright (`CHROMIUM_PATH`, y `PLAYWRIGHT_CHROMIUM` por compatibilidad).

#### Corregido
- **`e2e/correr.sh` (alta)** funciona en Windows: sonda `/api/v1/health` (esperaba a
  `/health/vivo`, que no existe), Python del venv, rutas nativas en un temporal fuera del repo,
  puertos 8020/3020, compila contra su propio backend y cierra sus procesos por PID de Windows.
  `comprobar_alta.py` imprime en UTF-8.
- **`/app` desbordaba a 482 px con datos** (tabla de 447 px a 390 px), defecto previo a 5G.4. La
  tabla del panel y la de la comparativa van dentro de un contenedor con desplazamiento propio.
- «No utilizable» en la comparación ya no usa la fuente de las cifras.
- El aviso del editor usa el estilo informativo del proyecto, no un color del semáforo.
- **La Escalera de precios desbordaba 8 px a 390 px en Linux y macOS** (`b74abd0`), defecto
  previo a 5G.4 que destapó la primera ejecución del job `e2e` (398/390 en la pestaña
  Resumen). `.cifra` usa la monoespaciada del sistema, ~0,6 em en DejaVu Sans Mono y Menlo
  frente a ~0,55 em de Consolas, y los escalones `flex-1` no encogían por debajo de su cifra.
  Ahora encogen (`min-w-0`) y, por debajo de `sm`, la cifra va a 12 px. El paso 10 de
  `simulaciones.mjs` mide además con la monoespaciada ancha forzada, para verlo en Windows.
- **«1, % anual» en la nota de la escalera** (defecto de 5G.4-A, `b74abd0`): la expresión
  regular de `lib/format.ts::tasa` perdió una barra al escribirse. Reescrita sin expresión
  regular; la e2e comprueba el texto «1,5 % anual».

### 5G.4-D · Decisión y documentación

- **ADR-0016** (aceptado): D1–D4 con su justificación, D5 aceptada y pendiente para la 5H, y la
  tabla de sensibilidad del §19 (coste de capital 0–0,20) con el umbral de degeneración 6,13 %.
- `MANUAL_DE_PRUEBAS.md`: cómo probar el rango y el aviso, y las dos e2e con `CHROMIUM_PATH`.
- `docs/ESTADO_ACTUAL.md` §4: cerradas Backend 12, 13 y 15 (y la 4 en parte), Pruebas 1 y
  Entorno 1-2; deudas nuevas Backend 16-18, Frontend 11-14 y Entorno 7.
- `CLAUDE.md`: reglas de entorno 3 y 5 actualizadas (las dos e2e compilan; puertos 8020/3020
  del alta) y regla 6 nueva (`CHROMIUM_PATH`).

### 5G.4-E · Auditoría del motor frente a la especificación

- `docs/AUDITORIA_MOTOR_ESPECIFICACION.md` (solo lectura de código): doble cuenta con hipoteca,
  `coste_capital()` sin definir, TIR del §19, perfil rentista, colchón de plazo y depósito,
  diseño del VAN y orden propuesto para la 5H.

---

## [Fase 5G.3] — Escalera degenerada en la interfaz y formato de 4 cifras — 2026-10-01

Lo mismo que 5G.2 hizo en el informe, ahora en la interfaz. La interfaz no decide si una
escalera es degenerada: usa la marca `decision.precios.degenerada` de M12.

### Corregido

- **Escalera de precios** (`components/resultado.tsx`): con la escalera degenerada, el escalón
  «Límite» deja de dibujarse como el más alto y sin su cifra: muestra «No utilizable» y
  «escalera degenerada (§9.3)», con borde discontinuo y la altura del escalón «Objetivo». La
  **línea de adjudicación se oculta**: no hay ningún escalón válido contra el que situarla, y
  el precio de adjudicación esperado sigue en la cabecera de la tarjeta. La nota al pie se
  mantiene. Sin escalera degenerada, el marcado es el de antes.
- **Métricas clave:** «Precio límite: No utilizable (escalera degenerada)».
- **Comparación original / simulación:** la celda del precio límite dice «No utilizable» en el
  lado cuya escalera es degenerada; si el dato es antiguo y no trae la marca, la cifra como
  antes.
- **Importes de 4 cifras:** `lib/format.ts::eur` agrupa siempre (`useGrouping: "always"`):
  «7.600 €» en vez de «7600 €», igual que el informe. es-ES no agrupa 4 cifras por defecto
  (`minimumGroupingDigits` = 2 en CLDR). `num`, `pct` y `fecha` no cambian.

### Añadido

- `GET /analisis/{id}/simulaciones/{sid}/comparacion`: campo `escalera_degenerada`
  (`bool | null`) en `resultado.original` y `resultado.simulacion`, leído tal cual de
  `decision.precios.degenerada`; `null` si el resultado no trae la marca. Sin cálculos.

### Pruebas

`test_comparacion_simulacion_api.py`: `true` con `capital.coste_capital_anual = 0.31`, `false` en
el original y `null` sin la marca. Suite: 865 passed, 18 skipped, 0 failed. `tsc` sin errores.
Verificación visual en copia aislada a 1440 y 390 px (análisis normal, 4 cifras, simulación
degenerada en uso y su comparación), sin desbordamiento horizontal. La e2e no se ejecutó: el
puerto 3000 estaba ocupado por el entorno de desarrollo.

## [Fase 5G.2] — Coherencia del texto del informe y overrides en el PDF oficial — 2026-10-01

Tres hallazgos en un PDF oficial real (simulación con `capital.coste_capital_anual` alto).

### Corregido

- **El informe presentaba como accionable un precio límite inutilizable.** Con la escalera
  degenerada (§9.3, la marca `decision.precios.degenerada` que ya pone M12 y que hace el
  semáforo rojo), la tabla decía «Precio límite absoluto -13.894 € — infranqueable» y el plan
  de puja instruía a «cargar límites». Ahora:
  - tabla: «No utilizable: escalera de precios degenerada (§9.3)», sin la cifra;
  - plan de puja (M13): «No cargar límites ni pujar: la escalera de precios es degenerada
    (§9.3); la estructura de costes consume el valor y no hay precio límite utilizable», sin
    las dos tácticas de cómo pujar; se mantienen el depósito y el re-análisis;
  - checklist: «Escalera de precios cargada en la interfaz de puja» pasa a **pendiente**
    («Escalera de precios degenerada (§9.3): no hay escalera utilizable para pujar.») y sale
    entre los bloqueantes, con el mismo patrón que «sin comparables».

  El valor calculado sigue en `decision.precios.p_limite`. **Ningún cálculo cambia**: un test
  fija los números de M13 y de la escalera capturados antes del cambio (caso §19, §19 con
  coste de capital 0,31 y un caso inviable).
- **Separador de miles inglés.** El plan de puja de M13 escribía «60,011 €» y «7,600 €»
  (`:,.0f`) mientras el resto del informe escribe «60.011 €». Un único helper,
  `app/engine/formato.py::eur`, para M13, M14 y el correo de alertas
  (`notificaciones_service`, «Valor de subasta: 152.000 €»). El informe del caso dorado §19
  es idéntico al anterior salvo esas cuatro cifras (comparado con su texto previo,
  `tests/datos/informe_caso19_antes_5g2.md`).

### Añadido

- **PDF oficial:** el bloque de identificación lista los overrides del informe, uno por línea
  y por clave (`· capital.coste_capital_anual = 0.31`), leídos solo de `Informe.overrides`;
  valor técnico tal cual y estructuras en JSON recortado a 60 caracteres.

### Sin cambios

Los informes oficiales ya emitidos conservan su texto exacto (Markdown congelado; hay test).
Los análisis y simulaciones ya guardados conservan el texto anterior hasta que se reanalicen.
Sin migración. Ni M01-M12, ni la parte numérica de M13/M14, ni modelos ni frontend.

### Pruebas

`test_formato.py`, `test_informe_coherencia.py`, tres casos nuevos en
`test_pdf_identificacion.py` y uno en `test_notificaciones.py`. Suite: 863 passed,
18 skipped, 0 failed.

## [Fase 5G.1] — Identificación del informe oficial en el PDF — 2026-09-30

Resuelve la deuda D5: impreso, un informe oficial no decía qué informe era.

### Añadido

- **PDF oficial identificado** (`GET /analisis/{id}/informes/{iid}/pdf`): cabecera en
  cada página («Informe oficial · {id corto} · emitido … UTC»), un bloque inicial en la
  primera (id, fecha y hora de emisión en UTC, procedencia —«Configuración original» o
  «Simulación {id corto}» con el id completo—, versión de parámetros, versión de reglas,
  overrides aplicados y, si falta, «Sin snapshot de parámetros») y un pie con el id
  completo y la procedencia en cada página.
- Todo sale **solo de la fila `Informe`** (`id`, `generado_en`, `simulacion_id`,
  `overrides`, `parametros_aplicados`, `resultado.decision.version_*`); lo que no consta se
  imprime como «no consta». La fecha de creación del PDF es la de emisión: **dos descargas
  del mismo informe son idénticas byte a byte**.
- **Vista previa marcada** (`GET /analisis/{id}/informe.pdf`): «VISTA PREVIA — NO OFICIAL»
  en la cabecera de cada página y en un bloque inicial.
- `pdf_service`: `Identificacion`, `identificacion_oficial`, `identificacion_vista_previa` y
  el parámetro `identificacion=` de `informe_a_pdf`. Sin él, el PDF sale como antes. El pie
  reduce el cuerpo (8 → 6 pt) si no cupiera en una línea; con los ids reales cabe a 8 pt en
  Helvetica y en DejaVu.

### Sin cambios

El Markdown congelado (base y `GET /informes/{iid}`), M14, `informe_service`, los modelos y
las migraciones. Sin migración nueva.

### Pruebas

`tests/test_pdf_identificacion.py`: 9 casos, cada uno con Helvetica y con DejaVu (la
variante DejaVu se omite fuera de CI si la fuente no está instalada y falla en CI si falta).
El texto se lee con `pypdf==6.19.0`, nueva dependencia **solo de tests** en
`requirements-dev.txt`. `test_informe_api.py` comprueba además que la identificación que
recibe el PDF es la de ese informe. Suite: 837 passed, 17 skipped, 0 failed.

## [Fase 5F.7] — Simulaciones e informes oficiales en la interfaz — 2026-09-24 a 2026-09-30

Rama `checkpoint/5f6-simulaciones-informes`. Una subfase, un commit (fechas de
`git log`).

### Añadido

- **5F.7.1** (`9db8e70`) — `_validar_overrides` comprueba también la **forma**
  del valor contra el de referencia del mismo árbol (número con número, `bool`
  no cuenta como número, listas y diccionarios recursivos). Un valor de tipo
  incorrecto da **422** en vez de 500. `SimulacionNueva` lleva
  `extra="forbid"`: un campo desconocido da 422 en vez de crear una simulación
  vacía.
- **5F.7.2** (`a517299`) — `GET /analisis/{id}/parametros-simulables`:
  editables, no editables y derivados, con `coincide_con_analisis`.
  `app/services/parametros_simulables_service.py`.
- **5F.7.3** (`a6835e8`) — `GET /analisis/{id}/simulaciones/{sid}/comparacion`:
  qué parámetros cambian (causa `override` o `conocimiento_vigente`) y 12
  campos del resultado a cada lado. No ejecuta el motor ni audita.
- **5F.7.4** (`c957fc0`) — base del frontend: tipos, cliente de API
  (`simulaciones.*`, `informes.*`, `guardarBlob`), `lib/permisos.ts`. **La UI
  deja de ofrecer el PDF de `/informe.pdf`**; la pestaña «Informe» pasa a ser
  «Vista previa (no oficial)».
- **5F.7.5** (`b435688`) — pestaña **Simulaciones**: lista, validar,
  descartar, usar esta configuración, y el aviso de qué configuración se
  muestra (`aviso-configuracion.tsx`).
- **5F.7.6** (`f244d6c`) — editor de parámetros por grupos y creación de
  simulaciones (`editor.tsx`).
- **5F.7.7** (`8b03870`) — comparación original / simulación en la interfaz
  (`comparacion.tsx`), con «Mostrar todos».
- **5F.7.8** (`9d6e411`) — pestaña **Informes oficiales**: emitir con
  confirmación, histórico, detalle y descarga del PDF oficial
  (`informes-oficiales.tsx`).
- **5F.7.9** (`a589fbd`) — e2e versionada del flujo:
  `e2e/correr_simulaciones.sh` + `frontend/e2e/simulaciones.mjs` +
  `e2e/comprobar_simulaciones.py`. Puertos propios (8010/3010), base en un
  temporal fuera del repo, compila su propio frontend.
  `frontend/scripts/medir-desborde.mjs` acepta `CHROMIUM_PATH`.
- **5F.7.10 A** (`4df5de8`) — `Confirmacion` compartida en
  `components/ui.tsx` (antes duplicada en `lista.tsx` e
  `informes-oficiales.tsx`); todas las escrituras de simulaciones comparten
  `mutationKey` y el botón «Volver a la configuración original» se desactiva
  mientras hay otra en curso.

### Corregido

- `de3498f` — la hoja `version` del árbol de parámetros ya no aparece como
  parámetro no editable cambiado en la comparación (`_HOJA_VERSION`).

### Verificado al cierre

`pytest`: **828 passed, 9 skipped, 0 failed**. `tsc --noEmit`: sin errores.
`correr_simulaciones.sh`: EXIT=0.

## [Pruebas] — La suite deja de usar la base de desarrollo — 2026-09-28

Commit `9db44b3`. No es una fase.

### Corregido

- **`pytest` borraba `seis_dev.db`.** `conftest.py` no fijaba `DATABASE_URL`,
  así que la suite usaba la base por defecto (`sqlite:///./seis_dev.db`), la
  misma del `uvicorn` de desarrollo, y la fixture `api` hacía `drop_all` y
  `os.remove("seis_dev.db")` al terminar cada módulo. Ahora `conftest.py` fija
  `DATABASE_URL` a una base en un directorio temporal (`SEIS_PYTEST_DIR_BD`)
  **antes** de importar la aplicación, y aborta la sesión (`pytest.exit`) si
  detecta que apunta a otra (`problema_de_aislamiento`).
  `tests/test_aislamiento_bd.py`.

## [Fases 5C-5F.6] — Catálogo, simulaciones, configuración validada, informes oficiales y API — 2026-09-23

Todo en **un solo commit**, `4a6f61d` («feat: simulaciones, configuracion
validada e informes oficiales»). Las subfases se reconstruyen por las marcas
`Fase 5X` del código, no por commits propios. La fecha es la del commit.

[VERIFICAR: las subfases **5B**, **5F.2** y **5F.5** no dejan marca en el código ni commit
propio; no se documentan aquí. Tampoco consta la fecha de cierre de cada subfase, solo la
del commit.]

### Añadido

- **5C / 5C.1** — `app/parametros/catalogo.py`: catálogo técnico de metadatos
  de los parámetros T3 de M12/M13, con disciplina «no inventar». 5C.1 cierra
  las tres claves físicas de `perfiles.rentista` y las de M12/M13 que faltaban.
  `tests/test_catalogo_parametros.py`.
- **5D** — tabla `simulacion` (migración `0012`) y
  `app/services/simulacion_service.py`: una configuración alternativa de
  parámetros sobre un análisis existente. Estados `pendiente` → `validada` o
  `descartada`. `tests/test_simulacion.py`.
- **5E / 5E.1** — `Analisis.simulacion_validada_id` (migración `0013`): qué
  configuración se muestra hoy (NULL = la original). 5E.1 permite volver a
  seleccionar una simulación ya validada. `tests/test_configuracion_validada.py`.
- **5F.1 / 5F.1A** — `Analisis.parametros_aplicados` (migración `0014`): el
  árbol T3 efectivo congelado en el análisis.
  `tests/test_analisis_parametros_aplicados.py`.
- **5F.3 / 5F.3.1** — tabla `informe` (migración `0015`): informe **oficial**,
  snapshot histórico e inmutable. 5F.3.1: el informe y su evento de auditoría
  van en la misma transacción (defecto B-1). `app/services/informe_service.py`,
  `tests/test_informe.py`.
- **5F.4** — API de informes oficiales: `POST/GET /analisis/{id}/informes`,
  `GET …/informes/{iid}` y `GET …/informes/{iid}/pdf`. Recurso de otra
  organización = 404. `tests/test_informe_api.py`.
- **5F.6** — API de simulaciones: crear, listar, obtener, validar, descartar,
  seleccionar y `POST /analisis/{id}/configuracion/original`. Cada escritura
  audita en la **misma transacción**, con `rollback` si algo falla.
  `tests/test_simulacion_api.py`.

### Migraciones

`0012_simulacion`, `0013_simulacion_validada`,
`0014_analisis_parametros_aplicados`, `0015_informe`.

## [Línea de producto · Fases 1-4] — Puente captación → análisis y trazabilidad de la valoración — 2026-09-23

También dentro de `4a6f61d`; sin commits propios.

### Añadido

- **Fase 1 · Puente captación → análisis.** `POST /analisis?subasta_id=…`
  reutiliza la `Subasta` captada en vez de crear otra
  (`analisis_service.crear_analisis`, fail-closed si no existe o no es
  visible). En la interfaz: botón «Analizar» en `/subastas` y
  `nueva?subasta=`. Cierra el frente 🔴 «el puente captación → análisis no
  existe».
- **Fase 2 · Corte sin ancla.** Sin comparables (`metodo="sin_comparables"`
  en M03), M12 decide **rojo** con «Sin ancla de mercado independiente…» y M14
  añade al checklist «**NO DETERMINABLE: sin comparables de mercado.**».
- **Fase 3 · Comparables usados.** `ComparableUsado` (migración `0010`):
  snapshot inmutable de cada comparable tal y como lo recibió M03.
  `tests/test_comparables_usados.py`.
- **Fase 4 · Detalle de la valoración.** `ComparableValorado` y
  `ValoracionAjustes` (migración `0011`): intermedios de M03 por comparable y
  agregados; `detalle_comparables` y `k_estado_activo` en `contracts.py`.
  `tests/test_valoracion_detalle.py`.

### Migraciones

`0010_comparable_usado`, `0011_valoracion_detalle`.

---

## [Corrección del motor] — La base imponible del ITP y la puja inviable — 2026-09-11

No es una fase. Van aquí porque **cambian el número que lee el cliente en el
informe** y se descubrieron los dos el mismo día, recorriendo una subasta real de
la AEAT de punta a punta —no con una fixture—.

### Corregido

- **El ITP se liquidaba sobre la puja y no sobre el mayor valor.** La base
  imponible es el mayor de (valor de referencia del Catastro, valor declarado,
  precio pagado) — art. 10 TRLITPAJD, Ley 11/2021. En una subasta, donde todo el
  atractivo consiste en rematar por debajo del valor, el error iba **siempre** en
  la misma dirección —infraestimar— y era **mayor cuanto mejor parecía la
  operación**: 700 € frente a 2.800 € reales sobre un remate de 10.000 € con
  valor de referencia de 40.000 €. Resuelto en `app/engine/fiscal.py`; `c_v` se
  queda igual y aparece un sobrecoste que solo actúa en el tramo `P < B`, de modo
  que la función de inversión y **su inversa —la escalera de precios de M12— pasan
  a tener dos tramos**. Alcance y límites en [[ADR-0015]]. `tests/test_base_fiscal.py`
  (16 tests); nueve mutaciones aplicadas, nueve detectadas.
- **M13 dejaba caer el análisis justo en las operaciones que debe rechazar.**
  `next()` sin valor por defecto lanzaba `StopIteration` —HTTP 500— cuando el RVC
  salía negativo, que es lo que ocurre siempre que la puja máxima sensata cae por
  debajo de cero: tasación baja sin comparables, ICI hundido, contingencia alta.
  El caso dorado §19 no lo cubría porque es una operación buena.
  `tests/test_puja_inviable.py` (5 tests).

### Añadido

- Campos opcionales `costes.valor_referencia_catastral` y `costes.valor_declarado`
  en el motor, en la API y en el alta. Sin ellos la corrección no sería alcanzable
  desde el producto.

### Cambiado

- **Comportamiento visible:** un análisis sin valor de referencia declara en el
  informe que el impuesto es un **MÍNIMO**, y su ítem fiscal del checklist —que es
  bloqueante— pasa de `ok` a `pendiente`. No se estima un valor de referencia a
  partir de nada. Los análisis ya emitidos **no se recalculan**: son inmutables
  por P1 y llevan el impuesto infraestimado.

---

## [Fase 16] — Auditoría de seguridad y correcciones — 2026-09-10

Auditoría completa del proyecto con informe entregado antes de tocar nada
(`docs/AUDITORIA_SEGURIDAD.md`, 497 líneas). Tres hallazgos altos y siete medios,
todos corregidos **con demostración por mutación**.

### Añadido

- `app/core/cabeceras.py`: cinco cabeceras de seguridad por middleware, aplicadas
  con `setdefault` para no pisar las que ya vengan. CSP de API cerrada.
- `app/core/datos_personales.py` y una barrera `before_insert` sobre `Auditoria`:
  **vetar datos personales en el `delta`**, recorriendo cadenas, listas, diccionarios
  y también las **claves** de los diccionarios.
- Contadores y motivos de resolución de IP en `app/core/red.py`, expuestos en
  `/health/detalle` (`red.resolucion_ip`: política activa, sin resolver, por motivo).
- `tests/test_fase16.py`: 34 tests, uno por hallazgo.
- [[ADR-0014]]: **todo mecanismo de verificación declara qué NO cubre, y falla antes
  que pasar en vacío.** Tres reglas operativas y una sección entera sobre dónde NO
  llega la regla, que es la parte que importa.

### Cambiado

- **CORS: el arranque aborta** si la política es peligrosa, con un centinela
  explícito (`ninguno`) para decir «sin CORS» a propósito. Antes una configuración
  vacía se leía como permisiva.
- **Las dos degradaciones silenciosas dejan de serlo**, tratadas como la misma
  clase de defecto —un mecanismo de seguridad que deja de funcionar sin emitir
  síntoma—: `red.py` cayendo al cupo global sin un solo registro, y la red de
  guardia del esquema pasando en verde con la metadata sin poblar. Ahora **o lo
  dicen en voz alta o fallan**.
- Normalización del correo en el alta (`strip().lower()`), vida del enlace de baja
  fijada en una constante (7 días) en vez de un literal, y caché de sondas de salud
  con caducidad comprobada.

---

## [Fase 14] — RGPD: consentimientos, exportación y borrado — 2026-09-10

Poder operar legalmente con datos de personas reales en la UE. **Decisión previa,
escrita en la ficha antes de codificar:** la fase extiende el borrado existente,
no escribe un borrador paralelo ([[ADR-0012]]).

### Añadido

- `app/services/borrado_service.py`: **un solo camino de borrado de personas**, en
  orden de claves foráneas —ninguna de las seis tiene `ondelete`—, anonimizando la
  auditoría **antes** de borrar la fila del titular.
- `app/services/cuenta_service.py` y `app/api/cuenta.py`: `GET /cuenta/exportar`,
  `DELETE /cuenta` con **gracia de 14 días**, `POST /cuenta/borrado/cancelar` y
  `GET /cuenta/consentimientos`. Ninguno acepta un `{usuario_id}`: se actúa sobre
  la sesión, deliberadamente.
- Modelo `Consentimiento` con **versión y fecha**, guardados por el registro en la
  misma transacción que la cuenta. Textos legales en `app/legal/textos.py` con un
  marcador explícito de pendiente de redacción, servidos sin exigir sesión.
- Casillas de consentimiento en la pantalla de alta: términos obligatorio, el resto
  opcional y **desmarcado por defecto**.
- `tests/test_rgpd.py` (20 tests) y `tests/escenario_rgpd.py`, con la comprobación
  de filas huérfanas corriendo **también contra PostgreSQL**: es justo el caso en
  el que SQLite miente, porque sin claves foráneas un borrado incompleto pasa en
  verde.
- `e2e/correr.sh` + `frontend/e2e/alta-real.mjs`: alta real de punta a punta con
  navegador, contra el backend levantado.
- `tests/test_esquemas.py`: recorre los 51 esquemas Pydantic y comprueba que **cada
  valor por defecto pasa la validación de su propio campo**.

### Corregido

- **`acepta_terminos` tenía un valor por defecto y su validador nunca se
  ejecutaba:** Pydantic v2 no valida los valores por defecto. El alta aceptaba un
  registro sin consentimiento y la suite seguía verde. Se quitaron los defectos y
  se auditaron los 51 esquemas del proyecto en busca del mismo patrón (0 casos más).
- `auditoria.entidad_id` es `String(36)` y la marca de anonimización ocupaba 48
  caracteres: **PostgreSQL aborta, SQLite lo habría guardado en silencio**.

### Cambiado

- La purga de cuentas nunca verificadas pasa a anonimizar la auditoría, por usar
  ahora el camino único. Cambio de comportamiento documentado aparte en [[ADR-0013]].

---

## [Fase 0 · Deuda de cobertura] — La puerta — 2026-09-09

Condición escrita en `docs/PLAN_FASES.md`: **nada que toque producción se despliega
antes de cerrar esta deuda.** Ambas filas cerradas con el mismo criterio: no basta
con que el test pase, hay que **verlo en rojo con la mutación aplicada**.

### Añadido

- `tests/test_siembra.py`: cubre la orquestación de `init_db.main()` y `sembrar.main()`,
  que nunca se habían ejecutado en ninguna prueba. El test decisivo corre en
  `staging` y **comprueba su propia premisa** antes de afirmar nada.
- **PostgreSQL en la CI** (`.github/workflows/ci.yml`, servicio `postgres:16`), con
  una guarda que **hace fallar el job si algún test se omite**. Los tres caminos
  exclusivos de PostgreSQL —que no se habían ejecutado nunca, ni en local ni en la
  CI— se demostraron por mutación uno a uno.

### Corregido

- Un test de `SET LOCAL` pasaba con y sin el camino puesto: resultó que **un `SET`
  normal dentro de una transacción también se revierte**, y la diferencia solo
  aparece al hacer COMMIT. Reescrito para que el COMMIT ocurra, y documentado que
  el camino real no puede distinguirlos.

---

## [Fase 17-A] — Conector de captación, andamiaje — 2026-09-09

Primera mitad de la captación automática: todo lo que no depende de tener HTML real
del BOE delante. La 17-B queda abierta con los selectores reales y dos condiciones
de cierre heredadas de aquí.

### Añadido

- `app/ingesta/contratos.py`: contratos de captación y el tipo `OrigenCaptacion`,
  que hace **imposible el `None` ambiguo** entre alta manual y alta de plataforma.
- `app/ingesta/boe.py`: parser defensivo — un HTML corrupto devuelve lista vacía,
  no una excepción.
- Unicidad de subasta por `(fuente, identificador_externo)`: ejecutar dos veces el
  mismo lote no duplica filas.
- `app/services/vigilancia_service.py`: **avisar cuando una fuente lleva demasiado
  tiempo en silencio**. Una fuente muda tiene el mismo aspecto que una fuente sin
  novedades, y ese es el modo de fallo que importa.
- `evaluar_subasta(db, subasta, origen)`: el alcance del matcher lo decide el
  **origen** de la captación, no un parámetro implícito ([[ADR-0011]]). Con test
  negativo explícito de que una notificación de plataforma **nunca** contiene datos
  de otra organización.
- `docs/VOLUMEN_MATCHER.md`: análisis de coste del matcher, medido.

### Cambiado

- Dos puntos de volumen quedan registrados como **decisiones de diseño, no de
  escala**, y son condición de cierre de la 17-B: el modo `instantaneo` por defecto
  de fábrica (50 correos por noche con diez usuarios), y el envío síncrono dentro
  de la ingesta (cuando el correo se rompe, la captación **parece** rota).

## [Fase 11-A] — Infraestructura de producción, parte agnóstica del proveedor — 2026-08-05

La Fase 11 se parte en dos por decisión del responsable: **11-A** es de repositorio
y no depende del proveedor; **11-B** (IaC, jobs de despliegue, RUNBOOK) queda
bloqueada hasta elegir hosting, dominio y proveedor de correo.

> **La Fase 11 NO se cierra con esta entrada.** Sus criterios de salida son
> operativos —HTTPS sirviendo, staging desplegado, backup restaurado con tiempo
> medido, alarma recibida, email de verificación llegado a una bandeja real— y
> ninguno es alcanzable sin la 11-B y sin ejecución humana.

### Añadido

- **Salud por componente** (Bloque A): `GET /health` intacto como liveness,
  `/health/listo` como readiness pública que responde 503, y `/health/detalle`
  autenticado con revisión de Alembic, versiones T2/T3, latencias y diagnóstico
  de red. Tres audiencias con necesidades opuestas, no una.
- **`staging` como cuarto entorno, y estricto** (Bloque D): entra en
  `ENTORNOS_SOPORTADOS` **y** en `ENTORNOS_ESTRICTOS`.
- **Higiene de despliegue portable** (Bloque C′): `backend/.dockerignore`,
  ancla YAML de entorno compartida, servicio `beat` propio, `healthcheck` del
  backend, puertos con loopback por defecto y `.env.produccion.example`.
- **Mantenimiento periódico** (Bloque I): tarea `seis.purgar` con horario
  `crontab`, purga de `token_consumido` y purga de cuentas nunca verificadas
  **con el borrado desactivado de fábrica**.
- **IP real tras proxy** (Bloque H): `app/core/red.py`, tres variables de
  política, guardia de arranque y `--no-proxy-headers` explícito.
- **CI con la suite completa** (Bloque F′): `.github/workflows/ci.yml` con el
  backend entero y `npm run build`.

### Corregido

- **`create_all` fuera de la ruta de producción** (Bloque E). El antipatrón que
  `CLAUDE.md` §6.9 prohíbe en `alembic/versions/` vivía en el arranque, y el
  compose lo encadenaba **después** de `alembic upgrade head`: un modelo con una
  tabla que ninguna migración creara se creaba en silencio en producción.
- **Puerta de despliegue de la Fase 10**: el límite por origen dejaba de ser un
  cupo global para todo el sitio.
- **P1 de la Fase 12**: las siete variables de SES/SMTP no llegaban al
  contenedor y el correo fallaba en silencio. La causa raíz eran dos bloques
  `environment` duplicados que derivaron, no un olvido.
- **El limitador anti-abuso no reintentaba Redis** tras el primer fallo, ni
  soltaba un cliente muerto, ni conservaba los bloqueos vigentes al recuperarse.
- **`.gitignore` no protegía `.env.produccion`**, que es el nombre que la
  plantilla nueva invita a crear.
- **`smtp.starttls()` sin contexto TLS** usaba `CERT_NONE`. Rama inalcanzable
  bajo Docker hasta que este mismo trabajo la activó al propagar las credenciales.
- **`VERSION_REGLAS` y `VERSION_PARAMETROS` no llegaban a ningún contenedor**,
  de modo que ajustarlas en `.env` no tenía efecto (principio P1).
- **El informe PDF reventaba sin la fuente DejaVu** *(corregido con autorización
  expresa; queda fuera del alcance original de la fase)*. Una viñeta `•` se
  concatenaba **fuera** del saneador, y Helvetica —el respaldo— solo admite
  latin-1, así que `fpdf2` lanzaba `FPDFUnicodeEncodingException` y **el informe
  entero se perdía** en cualquier máquina sin la fuente: todo Windows de
  desarrollo y cualquier imagen que no sea `backend/Dockerfile`. El backlog
  llevaba dos fases diagnosticándolo mal («tabla de transliteración incompleta»).
  Se corrigió la causa raíz y se añadió una tabla de equivalencias tipográficas
  para que el respaldo produzca texto legible en vez de «?».
  **Con esto la suite queda en 0 fallos por primera vez desde que hay registro.**

### Desviaciones del plan, registradas

- La siembra **sigue corriendo en todos los entornos**, en contra de lo que el
  plan proponía: es idempotente, y sacarla del arranque haría que
  `docker compose up` no baste para tener un sistema en pie — el defecto que
  originó la Fase 9.5.
- Se tocó **la publicación de puertos**, que el plan difería a la Fase 16: la
  premisa del diferimiento caducó cuando este trabajo convirtió el compose en
  base de un despliegue portable.
- **`--no-proxy-headers`** en lugar del `--proxy-headers` con `--forwarded-allow-ips`
  que pedían el plan y el backlog de la Fase 10. Razonado en `ADR-0005`.
- **La corrección de `pdf_service.py`**, fuera del alcance original y autorizada
  expresamente por el responsable.

### Deuda que queda abierta

- **Sentry queda fuera de la fase** por decisión del responsable. Incumple
  deliberadamente el requisito 2 del prompt del Plan Maestro y **no tiene fase
  propietaria**. Mientras siga así, **un error 500 en producción no avisa a nadie**.
- **La purga de cuentas nace desactivada**: la deuda no está cerrada en
  producción hasta que alguien mire un informe real y active el modo `borrar`.
- **Seis requisitos que bloquean el despliegue**, inventariados en `docs/PENDIENTES.md`
  con propietario Fase 11-B: `/docs` y `/openapi.json` abiertos · `/health/listo` sin
  límite de tasa y revelando el estado por componente · dependencias sin fijar ni
  auditar bajo una CI que ahora es puerta de despliegue · la purga en modo informe no
  deja rastro cuando no hay candidatas.
- Toda la **Fase 11-B**.

### ⚠️ Cambio incompatible al actualizar una instalación existente

**Un `.env` anterior a esta fase impide arrancar toda la pila.** Medido sobre una
instalación real: `SEIS_ENV` sin declarar vale `production` por el defecto del compose,
que es entorno estricto, y ahí la guardia del Bloque H **aborta** si
`PROXIES_DE_CONFIANZA` no está. No solo el backend: `worker` y `beat` también, porque
`celery_app` valida al importarse.

El mensaje es accionable y la guardia está haciendo su trabajo —forzar una decisión que,
tomada mal en silencio, deja el límite por origen como cupo global para todo el sitio—,
pero exige **una línea nueva** en cada `.env` existente:

```
PROXIES_DE_CONFIANZA=ninguno        # si no hay proxy delante
PROXIES_DE_CONFIANZA=10.0.0.5/32    # o la IP/CIDR de su proxy, con CABECERA_IP_CLIENTE
```

### Evidencia

Cifras **medidas** al cerrar, no citadas:

```
suite      393 recogidos · 391 pasan · 0 fallan · 2 omitidos
build      npm run build → exit 0
compose    docker compose config → exit 0, 6 servicios
```

Las 2 omisiones son condicionales y no son fallos: T5 exige `SEIS_TEST_POSTGRES_URL`, y
el test de la rama con la fuente DejaVu se omite si no está instalada — **en CI esa
omisión es un fallo deliberado**, para que un `apt-get` roto no deje de probar esa rama
en silencio.

**Verificación de arranque en frío: EJECUTADA y satisfactoria**, sobre volumen
destruido (`docker compose down -v && up -d --build`):

```
servicios          6/6 arriba; backend healthy
/health            200  {"status":"ok"}
/health/listo      200  {"estado":"ok","componentes":{"bd":"ok","redis":"ok"}}
/health/detalle    401 sin token
alembic_version    0006 · 26 tablas
create_all         NO ejecutado: «entorno production: el esquema lo gobierna Alembic»
siembra            1 usuario · 7 fuentes · 6 perfiles · 17 reglas
idempotencia       tras reiniciar el backend: cifras idénticas, 26 tablas
login del admin    200 con la contraseña sembrada, sin intervención manual
frontend           200
imagen             824 K, sin `.env`, sin `*.db`, sin `.venv`
```

Los 824 K contrastan con los **147 MB** de contexto de build que se medían antes del
`.dockerignore`, y son la prueba directa de la tesis del Bloque C′.

### Sin cambios de esquema

Ninguna migración Alembic. La siguiente libre sigue siendo la **`0007`** (Fase 13).

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

---

## [Fase 10] — Alta self-service — 2026-07-29

Registro público, verificación de correo y recuperación de cuenta. Objetivo
contratado: *«que cualquier persona pueda registrarse sola, verificar su email y
recuperar su contraseña, sin intervención tuya»*.

### Añadido
- `POST /auth/registro`: crea una organización propia y su usuario propietario,
  inactivo y sin verificar. Responde **201 exista o no la cuenta**; si ya existe,
  no crea nada y avisa por correo al titular.
- `POST /auth/verificar`: activa la cuenta. Un solo uso, caducidad 24 h.
- `POST /auth/reenviar-verificacion`: reenvía el correo de activación. Sin él, un
  enlace caducado dejaba la cuenta sin salida.
- `POST /auth/recuperar`: solicita el restablecimiento. Responde 200 siempre.
- `POST /auth/resetear`: fija una contraseña nueva. Un solo uso, caducidad 1 h.
- `POST /auth/cambiar-password`: cambio de contraseña con sesión iniciada.
  **Disponible en la API; sin interfaz de usuario en esta fase.**
- Páginas públicas `/registro`, `/verificar`, `/recuperar` y `/resetear`, fuera
  del grupo `(app)/` y por tanto fuera del guardia de sesión.
- `app/core/rate_limit.py`: limitador de ventana deslizante sobre Redis con
  respaldo en memoria. Cubre login y recuperación por email; registro y reenvío
  por origen; reenvío también por destinatario.
- Tabla `token_consumido`: registro de `jti` gastados que impone el uso único
  real de los tokens de propósito.
- Columna `usuario.email_verificado`.
- Variables de entorno `LOGIN_MAX_INTENTOS` (5) y `LOGIN_VENTANA_MIN` (15),
  propagadas en `docker-compose.yml`.
- `tests/test_registro.py`: 42 funciones de test, 45 casos con parametrización.

### Cambiado
- El login devuelve **403 accionable** cuando la contraseña es correcta pero el
  correo no está verificado, con reenvío de la verificación a mano. Una cuenta
  desactivada por su propietario sigue devolviendo el **401 genérico** que fijó
  la Fase 9.
- `crear_usuario` acepta `activo` y `email_verificado`, ambos `True` por defecto:
  las altas administrativas son confiadas y no reciben correo de verificación.
  Solo el registro público pasa `False`.
- Los correos transaccionales viajan **sin enlace de baja**: nadie debe poder
  darse de baja del mensaje que le permite activar su cuenta.
- `obtener_por_email` recorta espacios además de pasar a minúsculas.

### Corregido
- **Confusión de audiencia entre tokens.** Un enlace de verificación o de reseteo
  enviado por correo valía como Bearer de sesión completo, heredando el rol real
  de la cuenta, y seguía valiendo **después de consumirse**. Defecto nacido en la
  Fase 12. Ver la sección de cambios incompatibles.
- **Denegación de servicio dirigida en el login.** Con la clave del limitador
  solo por email, cualquiera bloqueaba la cuenta de un tercero de forma
  indefinida con cinco contraseñas erróneas, sin que la cuenta tuviera siquiera
  que existir. La clave pasa a componerse de **email y origen**.
- **Condición de carrera en el alta duplicada.** Dos registros simultáneos del
  mismo email producían un 500 y dejaban una organización huérfana.
- `/verificar` consumía el token al cargar la página, de modo que los escáneres
  corporativos de enlaces lo gastaban antes que su destinatario. Ahora exige un
  clic explícito.
- `admin@seis.local` no podía usar `/recuperar`: `EmailStr` rechaza `.local` por
  ser un dominio de uso especial (RFC 6762) y devolvía un 422 que rompía la
  promesa de «200 siempre».

### Retirado
- `test_t3_revision_aislada_via_stamp`, barrera de la Fase 9.5. Era insostenible
  por construcción: `Base.metadata.create_all` produce siempre el esquema de
  HEAD, nunca el de la revisión predecesora, de modo que toda migración aditiva
  lo rompía. Nunca había llegado a ejecutarse. Lo que cubría lo cubre
  `test_t3_par_consecutivo_por_la_cadena_natural`.

### Migraciones
- **`0006_self_service`** (`down_revision = "0005"`). Añade
  `usuario.email_verificado` con `server_default`, aplica un backfill que da por
  verificados a los usuarios preexistentes, y crea `token_consumido`.
  Reversible; verificada en SQLite y en PostgreSQL 16.4 real.

### ⚠️ Cambios incompatibles
- **Los tokens de sesión emitidos antes de esta fase dejan de ser válidos.**
  `crear_token` marca `tipo="sesion"` y `decodificar_token` lo exige como lista
  blanca. Al desplegar se produce un **cierre de sesión único** para todos los
  usuarios conectados. No hay pérdida de datos ni migración de credenciales.

### Pendiente
- OAuth con Google: paso 6 del contrato, clasificado como **opcional y
  diferible** por el propio Plan Maestro.
- Interfaz para `/auth/cambiar-password`.

### Evidencia
- Suite: **162 recogidos · 159 pasan · 2 fallan · 1 omitido**. Los 2 rojos son de
  PDF y preexisten a la fase.
- Cobertura de los módulos de la fase: **90 %** con la suite completa.
- Deriva de esquema (T4): sin divergencia — 22 tablas, 175 columnas, 22 índices.
- `npm run build` limpio, 21 rutas.

---

## [Fase 9.5] — Saneamiento del sistema de migraciones — 2026-07-28

Fase intercalada, no prevista en el Plan Maestro. Se demostró experimentalmente
que `alembic upgrade head` fallaba sobre una base limpia y que, como
`docker-compose.yml` encadena las migraciones al arranque, **una instalación
nueva no podía levantar el backend**.

### Cambiado
- Las revisiones `0001`-`0004` se sustituyen por una **revisión fundacional
  única, `0005_esquema_base`**, con `down_revision = None`. Su contenido
  permanece en el historial de git.

### Corregido
- La revisión `0002` hacía un `INSERT` que omitía `creado_en`, columna
  `NOT NULL`. Era la causa medida del fallo de arranque.
- La revisión `0004` usaba `op.alter_column`, que SQLite no implementa: **nunca
  pudo ejecutarse en SQLite**.

### Añadido
- Batería T1-T6 en `tests/test_migraciones.py`, que ejerce Alembic de verdad.
- Barrera anti-recurrencia en CI: `.github/workflows/migraciones.yml`.
- Endurecimiento del arranque: `app/core/config.py` valida en producción que
  `JWT_SECRET` y `ADMIN_PASSWORD` sean propios y fuertes, y rechaza cualquier
  `SEIS_ENV` no reconocido.

---

## [Fase 12] — Notificaciones multicanal y scoring exprés — 2026-07-24

### Añadido
- `app/notificadores/`: interfaz común con implementaciones de email
  (Postmark/SES/SMTP) y Telegram. Sin credenciales no rompe: registra en log y
  bufferiza.
- Telegram por polling, no webhook: el webhook exige URL pública HTTPS, que es
  Fase 11.
- Preferencias por usuario: canales, modo instantáneo o digest, hora y franja de
  silencio. Tarea beat `seis.digest`.
- Baja sin login mediante enlace firmado, con página pública `/baja`.
- `app/engine/scoring_expres.py`, **fuera de `modules/` y del DAG**: el caso
  dorado §19 queda intacto.
- Modelos `Alerta`, `Notificacion`, `PreferenciasNotificacion`,
  `CodigoTelegram`; router `captacion.py`; páginas `/alertas` y `/subastas`.

### Corregido
- `docker-compose.yml` era **YAML inválido** desde el commit inicial: contenía un
  bloque duplicado tras `volumes:`. `docker compose up` nunca pudo funcionar pese
  a estar documentado como vía principal de arranque.
- El worker no llevaba `--beat`, sin el cual el digest y el polling nunca se
  ejecutan.

---

## [Fase 9] — Multi-tenancy por organización — 2026-07-14

### Añadido
- Entidad `Organizacion`. `Usuario` gana `organizacion_id`, `rol_org` y
  `es_superadmin`; `Analisis` gana `organizacion_id`.
- Modelo de roles en dos ejes: `rol` (capacidad dentro de la organización) y
  `rol_org` (gestión de miembros), más `es_superadmin` para el gobierno del
  conocimiento global.
- Router `organizacion.py` y página `/equipo`.

### Cambiado
- Aislamiento por `organizacion_id` en todos los endpoints de análisis. **El
  acceso a un recurso ajeno devuelve 404, no 403**: no se revela su existencia.
