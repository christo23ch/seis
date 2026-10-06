# Inventario de presentación — formato, fórmulas y cálculos no consultables

**Fase:** 5J-0 (solo inventario; no cambia código ni base de datos)
**Fecha:** 2026-10-06 · **Rama:** `fase/5j-0-investigacion`
**Relación con los otros dos documentos de la fase:** el informe que motivó la 5J-0 era
ilegible además de erróneo. `INVESTIGACION_PROCEDIMIENTOS_SUBASTA.md` e
`IMPACTO_MOTOR_UMBRALES_LEGALES.md` tratan lo erróneo; este documento trata lo ilegible y lo
que el usuario no puede comprobar. Cualquier diseño (A, B o C) añade cifras y avisos a estas
mismas pantallas, así que conviene arreglar antes dónde y cómo se muestran.

---

## 0 · Resumen

1. **Cuatro pantallas vuelcan texto o JSON sin maquetar:** la vista previa y los informes
   oficiales enseñan el Markdown en crudo (`**`, `|---|`, `#`, `_…_`), «Datos de entrada»
   enseña el JSON de la entrada y «Árbol completo vigente» enseña JSON en un `Textarea` por
   sección. Otras cuatro muestran estructuras en JSON plegado.
2. **Los nombres internos llegan al usuario.** El informe del caso dorado §19 contiene 15
   identificadores distintos con barra baja: fórmulas (`C_F`, `c_v`, `δ_v`, y en otros casos `P_max` y
   `P_ideal`) y claves de código (`ocupacion_desalojo`, `judicial_boe`, `posesion_verificada`,
   `una_alta`, `comparables_ajustados`…). Casi todos nacen en el **motor** (`app/engine/`), no en
   la interfaz.
3. **Ninguna métrica principal enseña cómo se ha calculado.** El resultado ya trae buena parte
   del desglose (ICI, costes, reforma, ICU, comparables, `precios.detalle`), pero la interfaz no
   lo muestra; otras piezas (la fórmula del RVC con sus ajustes, los flujos de la TIR, la
   composición del plazo) **no existen en el resultado** y habría que emitirlas desde el motor.
4. **Un riesgo de coherencia:** los pesos del desglose del ICO están **escritos a mano en el
   frontend** (`resultado.tsx:196`) y copian los de `defaults.yaml:144`. Si alguien cambia esos
   pesos en el catálogo T3, las barras se dibujan con el máximo equivocado sin que nada avise.

---

## 1 · Método

- Lectura de todas las páginas de `frontend/app/app/` y de los componentes de
  `frontend/components/` que pintan resultados, parámetros o reglas.
- Generación del informe del caso dorado §19 con el motor real (`ejecutar_analisis` sobre
  `entrada_caso_19()`, sin base de datos) y búsqueda en la salida de todo token con barra
  baja. Así la lista de §3 refleja **lo que el usuario ve**, no lo que el código podría emitir.
  Los casos que el §19 no dispara (veto competitivo, RVC entre 0,80 y 0,90, banda
  `muy_alto`) se localizaron leyendo el código.
- Contraste con las deudas ya registradas en `docs/ESTADO_ACTUAL.md` (§4, deudas de interfaz
  3, 4 y 6), que se citan en vez de repetirlas.
- Rutas: `F/` = `frontend/`, `E/` = `backend/app/engine/`.

---

## 2 · Pantallas con formato pobre

### 2.1 Las cuatro pedidas

| # | Pantalla | Archivo · componente | Qué se ve hoy | Por qué es pobre |
|---|---|---|---|---|
| P1 | **Vista previa (no oficial)** — pestaña del detalle de inversión | `F/app/app/inversiones/[id]/page.tsx:138-148` · `TabPanel valor="informe"` | `res.informe_markdown` dentro de un `<pre>` con fuente monoespaciada | El Markdown no se interpreta: el usuario lee `**ICO**`, filas `\| Métrica \| Valor \|`, separadores `\|---\|---\|`, títulos con `#` y cursivas `_…_`. Las 8 tablas del informe (decisión, costes, riesgos, escenarios…) se ven como texto con barras verticales. Es la pantalla del informe denunciado |
| P2 | **Datos de entrada** — pestaña del detalle | `F/app/app/inversiones/[id]/page.tsx:152-158` · `TabPanel valor="datos"` | `JSON.stringify(data.entrada, null, 2)` en un `<pre>` | Claves internas (`deposito_pct`, `fotos_interior_o_visita`, `horas_hasta_cierre`), decimales con punto y en tanto por uno (`0.05` en vez de «5 %»), `true`/`false`, `null`, importes sin formato. **Sin `whitespace-pre-wrap`**: las líneas largas obligan a desplazar en horizontal, también en móvil. Sin agrupar por los pasos del asistente con que se introdujeron. El tipo es `any` (deuda 6 de `ESTADO_ACTUAL.md`) |
| P3 | **Árbol completo vigente** — página Parámetros (T3) | `F/app/app/parametros/page.tsx:103-116` · tarjeta «Árbol completo vigente» | Un `<details>` por sección con un `Textarea readOnly` que contiene `JSON.stringify(data[k], null, 2)`, recortado a 16 filas | JSON sin nombres legibles, unidades, fuente legal ni vigencia. Los porcentajes en tanto por uno. Recortar a 16 filas obliga a desplazar dentro de un `Textarea`. El nombre de sección es la clave cruda (`adjudicacion`, `scoring_expres`). **Ya existe** un catálogo con `nombre_legible`, `unidad`, `descripcion` y `rango` (`parametros_simulables_service.py`, usado en Simulaciones) que esta página no aprovecha |
| P4 | **Parámetros** — resto de la página | `F/app/app/parametros/page.tsx:81-101` · «Editor libre de parámetro» | Tres campos de texto: clave con puntos, valor en JSON y fuente | El administrador escribe a mano la ruta (`reforma.baremos_m2.media`) y el valor en JSON, sin ver el valor actual, la unidad ni la cota. Un porcentaje mal escrito (`5` en vez de `0.05`) se publica y entra en vigor «de inmediato» para todos. La sección ITP sí está maquetada (`:52-79`), pero transforma la clave con `ccaa.replace(/_/g, " ")` |

### 2.2 Las que han aparecido al revisar

| # | Pantalla | Archivo · componente | Qué se ve | Nota |
|---|---|---|---|---|
| P5 | **Informes oficiales** — Markdown congelado | `F/components/informes/informes-oficiales.tsx:267-270` · `DetalleInforme` | Igual que P1: `<pre data-markdown>` | El mismo problema en el documento que sí es oficial. El texto congelado no cambia (P1 de la especificación), pero su **presentación** sí se puede mejorar sin tocar lo congelado |
| P6 | Informes oficiales — «Cambios aplicados» | `informes-oficiales.tsx:248-257` y `Valor` (`:280-290`) | Clave cruda (`adjudicacion.ratios.judicial_boe…`) → valor; las estructuras como «objeto de N claves» y JSON plegado | Sin `nombre_legible` ni unidad, que el catálogo sí tiene |
| P7 | **Motor de reglas** | `F/app/app/reglas/page.tsx:12-19` (`Condicion`), `:52-56` y `:75` (editor) | Cada condición como código: `hecho op valor` (p. ej. `ocupacion.estado in [renta_antigua]`); el editor, el JSON completo de la regla | Aceptable para un superadministrador; ilegible para explicar a un usuario por qué saltó un veto |
| P8 | Simulaciones — parámetros de estructura | `F/components/simulaciones/editor.tsx:270-289` (`Estructura`) y `mostrar` (`:217-218`) | JSON plegado y valores en bruto (`0.015`) | Ya registrado: deuda 3 de `ESTADO_ACTUAL.md` |
| P9 | Simulaciones — comparación | `F/components/simulaciones/comparacion.tsx:236-248` (`Valor`) | JSON plegado de 280 px de ancho | Ídem; las etiquetas de `CAMPOS` (`:146`) están escritas en el frontend (deuda 4) |
| P10 | PDF oficial | `backend/app/services/pdf_service.py:164-172` (`_limpiar`) | Quita `**` y acentos graves, pero conserva los nombres internos de §3 | El PDF hereda todo lo de §3 |

---

## 3 · Fórmulas y claves con barra baja en texto plano

Las celdas «Origen» señalan dónde nace el texto; «Se ve en» dónde lo lee el usuario. **Ninguno
se escribe con notación matemática** (subíndices): `C_F` se lee literalmente «C barra baja F».

### 3.1 Fórmulas (símbolos de la especificación)

| Texto que ve el usuario | Origen | Se ve en |
|---|---|---|
| `C_F (P50 / P80)` | `F/app/app/inversiones/[id]/page.tsx:86` | Tarjeta «Costes» del resumen |
| `c_v` | `[id]/page.tsx:87` | Tarjeta «Costes» |
| `δ_v aplicado` | `F/components/resultado.tsx:246` (`MetricasClave`) | «Métricas de decisión» |
| `Partida C_F (P50)` · `Total C_F P50 / P80` · `c_v = 6,40 %` · `δ_v aplicado` | `E/modules/m14_informe.py:191, 267, 269, 272` | Vista previa, informe oficial, PDF |
| Checklist: «…incorporadas a **C_F**», «…aplicada en **c_v**», «Capital para **C_F**…» | `m14_informe.py:55, 72, 104` | Pestaña Checklist (`ChecklistLista`) e informe §9 |
| Veto: «Rojo competitivo: **P_max** queda tan por debajo…» | `E/rules/catalogo.yaml:149` (VETO-COMP-01) | `CondicionesVetos` (`resultado.tsx:224-229`) e informe §1. **Cambiarlo exige una versión nueva de la regla** |
| Plan: «RVC 0,80–0,90: pujar solo **P_ideal** 'por si acaso'…» | `E/modules/m13_puja.py:77` | Pestaña «Estrategia de puja» e informe §8 |
| `P×I` | `resultado.tsx:132`, `m14_informe.py:155` | Correcto como notación, pero sin explicar qué es P ni I |

### 3.2 Claves de código mostradas como texto

| Texto que ve el usuario (§19) | Origen | Se ve en |
|---|---|---|
| `ocupacion_desalojo`, `atrasos_comunidad_ibi`, `adquisicion_fija`, `cargas_subsistentes`, `plusvalia_municipal` (y `reforma`, `tenencia`…) | Claves del desglose de costes: `E/modules/m06_costes.py:104-111`; se pintan tal cual en `m14_informe.py:161` | Tabla de costes del informe |
| «Subasta **judicial_boe**» | `m14_informe.py:258` (`inp.subasta.fuente`) | Informe §2 |
| «Ocupación declarada: precario» (y `arrendado_posterior`, `renta_antigua`…) | `m14_informe.py:258` (`inp.ocupacion.estado`) | Informe §2 |
| «Método **comparables_ajustados**» (o `sin_comparables`) | `m14_informe.py:188`; valores de `E/modules/m03_valoracion.py:73, 125` | Informe §3 |
| «Subsanar: **posesion_verificada**; Subsanar: **fotos_interior_o_visita**; … **cert_comunidad**; … **ite_cee**» | `E/modules/m07_riesgo_juridico.py:52` (carencias del ICI) | Pestaña Riesgos (`RiesgosPanel`, `resultado.tsx:153-157`) e informe §6 |
| «dominancia: **una_alta**» (o `dos_altas`, `critica_mitigable`…) | `defaults.yaml:104`; se pinta en `m14_informe.py:279` y `resultado.tsx:135` | Informe §6 y cabecera de Riesgos |
| Banda `muy_alto` (cuando se da) | `defaults.yaml:106` | Mismos sitios |
| Dimensiones sin tilde: `juridico`, `urbanistico`, `tecnico`, `ocupacion` | `E/contracts.py:20` (`Dimension`) | Eje del gráfico de Riesgos (`resultado.tsx:144`), lista de condiciones (`:155`), informe §6 |
| Componentes del ICO: `juridico`, `urbanistico`, `ubicacion`, `revalorizacion`, `informacion` (con `capitalize`, sin tildes) | Claves de `ico_desglose`; se pintan en `resultado.tsx:205` | Tarjeta «ICO — desglose» |
| Evidencias `ICI=63`, `estado=precario`, `nivel_reforma=media`, `DOM=75d` | `m07_riesgo_juridico.py:53, 61`, `m10_riesgo_comercial.py` | Hoy **no se muestran** (están en el resultado); si se muestran, habrá que traducirlas |

> **Dónde arreglarlo.** Los textos del motor viven en `app/engine/` y cambian el informe del
> caso dorado §19 (texto, no cifras): necesitan la misma autorización de CLAUDE.md §6.8 que los
> diseños A-C. Los de la interfaz (`[id]/page.tsx:86-87`, `resultado.tsx:135, 144, 155, 205,
> 246`) se pueden corregir sin tocar el motor, con un diccionario de etiquetas. Lo deseable es
> que ese diccionario lo sirva el backend, como ya hace el catálogo de parámetros, para que
> interfaz, informe y PDF digan lo mismo.

---

## 4 · Métricas sin cálculo consultable

«En el resultado» = el dato ya viaja en `Resultado` (`F/lib/types.ts` o el JSON real del §19).
«Falta en el motor» = habría que emitirlo desde `app/engine/`.

| Métrica | Dónde se muestra | Qué se puede consultar hoy | Qué hay en el resultado y no se muestra | Falta en el motor |
|---|---|---|---|---|
| **Semáforo** | `SemaforoHero` (`resultado.tsx:15-32`) | Solo la primera razón (`razones[0]`) | `razones` completas, `techos_aplicados`, `reglas_disparadas` (estas solo salen en el informe §10) | Qué regla fijó el color y con qué hechos |
| **ICO** | `SemaforoHero`, `IcoDesglose` (`:194-216`) | Barra por componente | — | Cómo se puntúa cada componente. **Pesos duplicados en el frontend** (`:196`) |
| **RA** | `RiesgosPanel` (`:127-162`) | P×I por dimensión | `ra_base` (25,36 en el §19, frente a RA 40), `probabilidad`/`impacto` por separado, `evidencias` | Pesos de agregación (`defaults.yaml:101`) y cómo la dominancia sube el RA |
| **ICI** | `SemaforoHero` (solo el número) | Nada | `ici.desglose` (puntos por documento), `carencias`, `penalizaciones`, `efecto_delta_v_pp`, `efecto_contingencia_pp`, `techo_semaforo` | — (todo está en el resultado) |
| **ICU** | `SemaforoHero` (solo el número) | Nada (macro y micro solo en el informe) | `macro_score`, `micro_score`, `icu.desglose` (15 entradas) | — |
| **P_ideal · P_objetivo · P_max · P_límite** | `EscaleraPrecios`, `MetricasClave` | Cifras y nota del coste de capital | `precios.detalle`: `m_objetivo_ajustado`, `m_minimo_ajustado`, `vs_pesimista`, `p_por_margen_min`, `p_por_pesimista`, `capital_propio` (solo se usa `coste_capital`) | La fórmula de cada peldaño con sus operandos (§9 de la especificación) |
| **P_adj esperado · RVC** | Escalera, «Plan de puja», `SemaforoHero` | `ratio_base` y la banda | — | `RVC = P_max / P_adj` no se enseña; los ajustes del ratio (−8 pp por desierta, +6 pp por «chollo», acotado) **no se emiten** (`m13_puja.py:8-36`) |
| **Margen de seguridad** | `MetricasClave` | El porcentaje | — | Fórmula y operandos (`m12_decision.py:295`) |
| **ROI · ROI anualizado** | `MetricasClave`, escenarios | `inversion_total` | `precio_evaluado`, `beneficio`, `costes.desglose_p50` (las 9 partidas solo en el informe) | — |
| **TIR anual · VAN · TIR − coste de capital** | `MetricasClave` | El valor | — | Los flujos y fechas con que se calculan |
| **Valor esperado** | `EscenariosPanel` (`:164-192`) | Beneficio y probabilidad por escenario | `vs`, `coste_total` y `plazo_meses` de cada escenario (solo en el informe §7) | — |
| **Colchón de plazo** | `MetricasClave` | Meses | `colchon_plazo_meses_p_max` (solo en el informe) | Beneficio de partida y coste mensual con que se divide |
| **VS prudente · δ_v** | `MetricasClave`, tarjeta «Valoración» | Las cifras | `ici.efecto_delta_v_pp` (de dónde sale δ_v) | — |
| **VM · VS · €/m² · CV** | Tarjeta «Valoración» (`[id]/page.tsx:73-82`) | Nº de comparables y CV | `detalle_comparables` (precio ajustado, normalizado y peso de cada testigo), `vm_rango`, `vs_rango`, `confianza`, `k_estado_activo`, `ratio_sanidad`, `metodo` | — (la trazabilidad de comparables de la 5x existe y no se pinta) |
| **C_F · c_v · contingencia** | Tarjeta «Costes» (`[id]/page.tsx:83-92`) | Totales | `desglose_p50`, `desglose_p80`, `c_v_desglose`, `tipo_impositivo`, `base_fiscal_origen`, `tenencia_mensual` | — |
| **Reforma** | Tarjeta «Costes» | Nivel y total P50 | `obra_p50/p80`, `tecnicos_licencia_p50/p80`, `partidas` | — |
| **Plazo P50 / P80** | Tarjeta «Costes» | Meses | — | Composición (ocupación + obra + comercialización, `m06_costes.py:72`) |
| **Depósito** | Plan de puja (texto) | Importe y % | — | De dónde sale el porcentaje (hoy el 0,05 fijo; ver documento de impacto §1.3) |
| **Y neta · DSCR · cash-on-cash** | En ningún sitio | — | En `rentabilidad` (`null` en el §19, perfil flip) | — |
| Listados, panel y comparativa | `F/app/app/page.tsx:51, 109-110`, `inversiones/page.tsx:66-68`, `comparativa/page.tsx:41-50` | Cifras sueltas | — | Enlace al desglose del detalle |

---

## 5 · Propuesta de orden (para decidir, no implementada)

1. **Sin tocar el motor:** renderizar el Markdown en P1 y P5 (una biblioteca de Markdown con
   tablas, sin HTML incrustado); maquetar P2 por pasos del asistente con etiquetas y formato
   español; P3 con el catálogo de parámetros que ya existe; diccionario de etiquetas para las
   claves de §3.2 que pinta la interfaz; mostrar los desgloses de §4 que **ya están en el
   resultado**; leer los pesos del ICO del backend.
2. **Con autorización para el motor** (junto a la 5J-1): sustituir en M14, M13 y M07 los
   símbolos y claves de §3 por texto legible o por notación con subíndices; emitir los
   operandos que faltan (ajustes del RVC, fórmula de cada peldaño, composición del plazo,
   flujos de la TIR). Cambia el texto del caso dorado §19 y `invariante_5h1.json`, no sus cifras.
3. **Con una versión nueva de regla T2:** el motivo de VETO-COMP-01 (`catalogo.yaml:149`), que
   la 5J-1 ya tendrá que tocar por el texto judicial del depósito (`SEM-EJEC-01`).
