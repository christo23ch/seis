# Investigación — Reglas legales de puja por procedimiento de subasta

**Fase:** 5J-0 (solo investigación; no cambia código ni base de datos)
**Fecha de consulta de las fuentes:** 2026-10-06
**Motivo:** una prueba manual produjo un informe cuya puja recomendada no se puede aprobar
legalmente en una subasta judicial.

> **Aviso.** Esto es investigación técnica para diseñar el motor, no asesoramiento jurídico.
> Antes de convertir cualquier umbral en un bloqueo del software, debe validarlo un profesional
> (CLAUDE.md §4, aviso de gobernanza de `defaults.yaml`).

---

## 0 · Resumen para decidir

1. **La premisa de partida necesita una corrección.** La LEC **no fija una puja mínima** para
   que una postura se admita en una subasta judicial: se admiten pujas de cualquier importe. Lo
   que fija son **umbrales de aprobación del remate**, y a partir de ellos cambia lo que ocurre.
   En **inmuebles** (art. 670) los umbrales son **70 %, 60 %, 50 % y 40 %**; en **muebles**
   (art. 650), **50 % y 30 %**. Por debajo del último umbral, el remate **no es imposible**:
   lo decide el letrado de la Administración de Justicia (LAJ), que puede aprobarlo o
   denegarlo. La única prohibición absoluta es la de la **vivienda habitual del deudor**:
   **nunca por debajo del 60 %**.
2. **Hay dos regímenes judiciales a la vez.** La Ley Orgánica 1/2025 reescribió los arts. 647 a
   671 con efectos desde el **3 de abril de 2025**, pero solo se aplica a los **procedimientos
   incoados después** de esa fecha (DT 9.ª.1). Las ejecuciones anteriores siguen con las reglas
   de 2015. Cambian el depósito (del **5 % al 20 %** en inmuebles), el plazo de pago (de **40 a
   20 días**), el carácter de las pujas (**visibles → secretas**) y el cierre (**prorrogable →
   improrrogable**).
3. **El motor incumple hoy cuatro cosas**, documentadas en §2.13: depósito judicial por defecto
   del 5 %, táctica de puja basada en la prórroga del cierre (que el régimen nuevo suprime),
   ratio de adjudicación esperada por debajo del 50 % sin advertir de su efecto legal, y ningún
   tratamiento de la vivienda habitual del deudor.
4. **AEAT** (§3): depósito del 5 % en inmuebles, puja mínima del 10 % del tipo, adjudicación
   automática desde el 50 % y, por debajo, decisión de la Mesa **sin precio mínimo**. Ya no
   existe la «segunda licitación» dentro de la misma subasta: hoy es una subasta nueva con el
   tipo reducido por un coeficiente (0,8 y luego 0,6).

---

## 1 · Método

- **Fuente única:** el texto consolidado del BOE, leído desde su API de datos abiertos
  (`https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{ID}/texto/bloque/{art}`).
  La API devuelve **todas las redacciones** de cada artículo con su norma modificadora y su
  fecha de vigencia. Así se ha podido comparar la versión de 2015 con la de 2025.
- **Normas consultadas:**

  | Norma | ID BOE | Enlace |
  |---|---|---|
  | Ley 1/2000, de Enjuiciamiento Civil (LEC) | BOE-A-2000-323 | <https://www.boe.es/buscar/act.php?id=BOE-A-2000-323> |
  | Ley Orgánica 1/2025, de 2 de enero (eficiencia del Servicio Público de Justicia) | BOE-A-2025-76 | <https://www.boe.es/buscar/act.php?id=BOE-A-2025-76> |
  | RD 939/2005, Reglamento General de Recaudación (RGR, AEAT) | BOE-A-2005-14803 | <https://www.boe.es/buscar/act.php?id=BOE-A-2005-14803> |
  | RD 1415/2004, Reglamento General de Recaudación de la Seguridad Social (RGRSS) | BOE-A-2004-11836 | <https://www.boe.es/buscar/act.php?id=BOE-A-2004-11836> |
  | Ley del Notariado de 1862 (arts. 72-77, redacción de la Ley 15/2015) | BOE-A-1862-4073 | <https://www.boe.es/buscar/act.php?id=BOE-A-1862-4073> |
  | Ley Hipotecaria (Decreto de 8-2-1946) | BOE-A-1946-2453 | <https://www.boe.es/buscar/act.php?id=BOE-A-1946-2453> |
  | RDLeg 1/2020, Texto Refundido de la Ley Concursal (TRLC) | BOE-A-2020-4859 | <https://www.boe.es/buscar/act.php?id=BOE-A-2020-4859> |

- **Convención de este documento:**
  - ✅ **Confirmado:** leído literalmente en el texto consolidado vigente del BOE; se cita el
    artículo y el enlace.
  - ⚠️ **No confirmado:** interpretación, práctica forense, dato de un portal o afirmación que
    no aparece literalmente en la norma. **No debe convertirse en regla del motor sin validarlo.**
- Los enlaces llevan el ancla del artículo (`#a670`). Los artículos «bis» del RGR tienen anclas
  internas del BOE (`#a1-2` = art. 103 bis, `#a1-4` = art. 104 bis).

---

## 2 · Subasta judicial (LEC)

### 2.1 Qué régimen se aplica: dos a la vez

| | Dato | Estado | Fuente |
|---|---|---|---|
| Entrada en vigor de la LO 1/2025 | 3 meses tras su publicación (BOE de 3‑1‑2025): **3‑4‑2025**. Las notas de vigencia de la LEC dicen «con efectos de 3 de abril de 2025» | ✅ | [LO 1/2025, DF 38.ª](https://www.boe.es/buscar/act.php?id=BOE-A-2025-76#df-38); [LEC art. 670, nota](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a670) |
| A qué procedimientos | «Las previsiones recogidas por la presente ley serán aplicables **exclusivamente a los procedimientos incoados con posterioridad** a su entrada en vigor» | ✅ | [LO 1/2025, DT 9.ª.1](https://www.boe.es/buscar/act.php?id=BOE-A-2025-76#dt-9) |
| Si «procedimiento» es la ejecución o el pleito declarativo previo | La DT no lo dice. En una ejecución de título judicial pueden ser dos procedimientos distintos | ⚠️ No confirmado | — |
| Qué ve el licitador para saberlo | Fecha de incoación o número de autos del edicto. No he comprobado si el Portal de Subastas muestra la fecha de incoación | ⚠️ No confirmado | — |

**Consecuencia para el motor:** el régimen no se deduce de la fecha de la subasta. Una subasta
celebrada hoy puede seguir las reglas de 2015 si la ejecución empezó antes del 3‑4‑2025.

### 2.2 Valor de subasta (la base de todos los porcentajes)

| Regla | Estado | Fuente |
|---|---|---|
| Inmuebles: avalúo **menos** el importe de las cargas anteriores preferentes que conste en la certificación de dominio y cargas | ✅ | [LEC 666.1](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a666) |
| Si las cargas igualan o superan el valor, se suspende la ejecución sobre ese bien | ✅ | [LEC 666.2](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a666) |
| Ejecución hipotecaria: el tipo es el pactado en la escritura y **no puede ser inferior al 75 %** de la tasación oficial | ✅ | [LEC 682.2.1.º](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a682) |
| La subasta hipotecaria de muebles o inmuebles sigue las reglas de los inmuebles | ✅ | [LEC 691.4](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a691) |

> **Dato para el motor:** los umbrales se calculan sobre el **valor de subasta**, que ya resta las
> cargas anteriores. El campo `subasta.valor_subasta` del motor (VT) coincide con él si el
> usuario lo copia del edicto; el formulario lo rotula «Valor de subasta / tasación», lo que
> admite confundirlo con la tasación sin descontar las cargas.

### 2.3 Depósito para pujar

| Régimen | Muebles | Inmuebles | Estado | Fuente |
|---|---|---|---|---|
| **Nuevo** (incoados desde 3‑4‑2025) | **10 %** del valor, mínimo **1.000 €** | **20 %** del valor de subasta (art. 666), mínimo **1.000 €** | ✅ | [LEC 647.1.3.º](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a647); [LEC 669.1](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a669) |
| **Anterior** (Ley 19/2015) | 5 % | 5 % | ✅ (redacción anterior en la API) | mismos artículos, versión BOE-A-2015-7851 |
| El LAJ puede **elevar o reducir** el porcentaje según las circunstancias | ✅ (régimen nuevo) | | | LEC 647.1.3.º y 669.1 |
| El ejecutante puja sin depósito | ✅ | | | [LEC 647.2](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a647) |
| La consignación se hace por el Portal de Subastas a través de entidades colaboradoras de la AEAT | ✅ | | | LEC 647.1.3.º |

**Devolución y reserva** ([LEC 652](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a652)) ✅:
al terminar, el Portal devuelve «inmediatamente» los depósitos salvo el del mejor postor. Quien
pidió **reserva de postura** mantiene el depósito retenido hasta que el rematante pague. Si el
mejor postor no paga, **pierde el depósito** y se adjudica al siguiente con reserva
([LEC 653](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a653)).

### 2.4 Desarrollo de la puja

| Regla | Régimen nuevo | Régimen anterior | Estado | Fuente |
|---|---|---|---|---|
| Duración | 20 días naturales, **«improrrogable»** | 20 días; no se cierra hasta 1 h después de la última puja, con un máximo de 24 h de prórroga | ✅ | [LEC 649.1](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a649) (y su versión de 2015) |
| Visibilidad | Pujas **secretas**; al final solo se publica el mejor precio | El portal publicaba cada puja al recibirla | ✅ | [LEC 648.6.ª](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a648) |
| Modificar la puja | El postor puede pujar por importe **superior o inferior** al suyo; cuenta la **última** antes del cierre | Se admitían pujas iguales o inferiores a la más alta, que valían como reserva | ✅ | LEC 648.6.ª |
| Empates | Gana la anterior en el tiempo | Igual | ✅ | LEC 648.6.ª |
| Días de cierre | No puede terminar en sábado, domingo, festivo nacional, del 24‑dic al 6‑ene ni en agosto | — | ✅ | LEC 649.1 |
| Puja mínima | La LEC **no la fija** | Igual | ✅ (ausencia comprobada en 647-650 y 668-671) | — |
| Puja mínima o tramos fijados por la autoridad gestora | La ayuda del Portal dice que, si la autoridad gestora no la indicó, se puede pujar por cualquier importe | | ⚠️ No confirmado en la norma; consta en la [ayuda del Portal](https://subastas.boe.es/ayuda.php) | — |

> **Consecuencia directa:** la táctica que M13 recomienda hoy, «Entrar tarde con límites
> precargados: la extensión automática del cierre neutraliza el sniping», **solo vale en el
> régimen anterior y en la AEAT**. En el régimen judicial nuevo no hay prórroga ni se ven las
> pujas ajenas: es una puja sellada a sobre cerrado.

### 2.5 Aprobación del remate — inmuebles (art. 670)

Todos los porcentajes son sobre el **valor de subasta**. ✅ Literal de
[LEC 670](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a670), redacción LO 1/2025.

| Mejor postura | Qué ocurre | Apartado |
|---|---|---|
| **≥ 70 %** | El LAJ aprueba el remate **el día siguiente** al cierre. Pago del resto en **20 días desde el cierre** | 670.1 |
| **< 70 %** | Se abre un plazo de **10 días** desde el cierre en el que el **ejecutado** puede presentar a un tercero que mejore la postura: **≥ 60 %**, o menos si basta para pagar entera la deuda del ejecutante. El tercero consigna antes el mismo depósito y paga en 10 días | 670.3, párr. 1-2 |
| Sin mejora, **≥ 50 %** | Se aprueba al mejor postor | 670.3, párr. 4 |
| Sin mejora, < 50 % pero **cubre entera la deuda del ejecutante y ≥ 40 %** | Se aprueba; la ejecución termina y se liberan los demás bienes | 670.3, párr. 4 |
| Sin mejora y **por debajo de lo anterior** | **El LAJ decide**, oídas las partes, según la conducta del deudor, si hay otros bienes con que cobrar, el sacrificio patrimonial y el beneficio del acreedor. Cabe recurso de revisión. Si lo deniega, a instancia del ejecutado, se alza el embargo | 670.3, párr. 4-5 |
| **Vivienda habitual del deudor** | **Nunca por debajo del 70 %**, salvo que la postura iguale lo debido al ejecutante por todos los conceptos; e incluso entonces, **nunca por debajo del 60 %**. Si el mejor postor es el ejecutante con una puja menor, se le aprueba por el 70 % o por lo debido, con un mínimo del 60 % | 670.3, último párrafo |

**Régimen anterior (2015)** ✅ ([versión BOE-A-2015-8167](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a670)):
≥ 70 % aprobación (el mismo día o el siguiente) y pago en **40 días**. Por debajo, el ejecutado
podía presentar un tercero que ofreciera **más del 70 %**; si no, el **ejecutante** podía pedir
la adjudicación por el 70 % o por lo debido si superaba el 60 % y la mejor postura. Sin eso, se
aprobaba si la postura superaba el 50 % o cubría la cantidad reclamada, y si no, decidía el LAJ.
**No había suelo del 40 %.** Las reglas de vivienda habitual del 70 %/60 % ya existían
(RDL 8/2011 y Ley 1/2013).

**Otros datos del art. 670** ✅:
- **Financiación hipotecaria del remate (670.6):** el LAJ expide testimonio del decreto de
  aprobación para constituir la hipoteca del art. 107.12.º LH, y **la solicitud suspende el
  plazo de pago** hasta que se entrega. Matiza la condición actual del motor «pago sin condición
  suspensiva de financiación».
- **Liberación por el deudor (670.7):** hasta la aprobación del remate el ejecutado puede pagar
  lo debido y la subasta queda sin efecto.
- **Cargas anteriores (670.5):** el adjudicatario las asume y se subroga.

**Lo que no está confirmado** ⚠️:
- Con qué frecuencia aprueban los LAJ remates por debajo del 50 % o del 40 % (tesis del «precio
  vil»). La norma lo permite y no he contrastado jurisprudencia ni estadística.
- Si la cantidad reclamada (principal, intereses y costas) aparece en el edicto o en el Portal.
  Sin ese dato no se puede saber si una postura «cubre la deuda» (ruta del 40 %).

### 2.6 Aprobación del remate — muebles (art. 650)

✅ [LEC 650](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a650), redacción LO 1/2025:
- **≥ 50 %:** aprobación el día siguiente al cierre y pago del resto en **10 días**.
- **< 50 %:** 10 días para que el ejecutado presente un tercero (≥ 50 % o pago completo de la
  deuda). Sin mejora, se aprueba si la postura es **≥ 30 %** o cubre la deuda; si no, decide el
  LAJ.

> SEIS trabaja con inmuebles; los muebles se citan porque son el origen de la idea «50 %», que
> **no** es el umbral de los inmuebles.

### 2.7 Subasta sin postores (art. 671)

✅ [LEC 671](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a671): a instancia del ejecutado
se alza el embargo. Desde el cierre, el ejecutado (o el ejecutante a propuesta suya) puede
designar a alguien que se adjudique el bien por **≥ 50 %**, o por lo debido con un mínimo del
**40 %**; por debajo decide el LAJ. Las partes pueden pedir de común acuerdo una nueva subasta.

> **Nota sobre `subastas_desiertas_previas`:** en el régimen nuevo, una subasta judicial
> desierta **no** baja el tipo de la siguiente. El ajuste de M13 (−8 pp de ratio esperado por
> cada desierta) es una estimación de mercado, no una regla legal.

### 2.8 Mejora por tercero, ejecutante y cesión del remate

| Regla | Estado | Fuente |
|---|---|---|
| El ejecutante puede pujar aunque no haya otros postores, sin depósito. Si quiere el bien **debe pujar**: tras la subasta **no puede mejorar** el precio del mejor postor ni pedir la adjudicación | ✅ | [LEC 647.2](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a647) |
| Cesión del remate: la tienen **el ejecutante y los acreedores posteriores**, sin manifestarlo. Antes era solo el ejecutante | ✅ | [LEC 647.3](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a647) |
| Si el tercero presentado por el ejecutado mejora, se devuelve el depósito al mejor postor | ✅ | LEC 670.4 |

> **Riesgo para el inversor:** una puja entre el 50 % y el 70 % puede ganar la subasta y
> perderla diez días después ante un tercero presentado por el deudor. No pierde el depósito,
> pero lo tiene inmovilizado ese tiempo. Es un riesgo real y **no figura hoy en el informe**.

### 2.9 Plazos de pago y consecuencias del impago

| Supuesto | Plazo | Estado | Fuente |
|---|---|---|---|
| Inmuebles, postura ≥ 70 % | 20 días **desde el cierre** | ✅ | LEC 670.1 |
| Inmuebles, postura < 70 % aprobada | 20 días **desde el requerimiento** tras el plazo de mejora | ✅ | LEC 670.4 |
| Muebles | 10 días | ✅ | LEC 650.1 y 650.4 |
| Anterior a la LO 1/2025, inmuebles | 40 días | ✅ | LEC 670.1 (versión 2015) |
| Impago | Pérdida del depósito («quiebra de la subasta») y nueva subasta | ✅ | [LEC 653](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a653) |
| Representación no acreditada en 3 días | Pérdida del depósito | ✅ | LEC 647.1.1.º |

### 2.10 Cargas y título

| Regla | Estado | Fuente |
|---|---|---|
| El licitador acepta la titulación existente y se subroga en las cargas anteriores al crédito del actor | ✅ | [LEC 668.2](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a668), [669.2](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a669) |
| El edicto debe incluir certificación de dominio y cargas, avalúo, situación posesoria y, si procede, la posibilidad de visitar el inmueble | ✅ | LEC 668.2 |
| Se cancelan las cargas posteriores (mandamiento de cancelación) | ✅ | [LEC 674](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a674) |
| Título inscribible: testimonio del decreto de adjudicación | ✅ | [LEC 673](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a673) |
| Remanente: primero para acreedores posteriores; después, al ejecutado | ✅ | [LEC 672](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a672) |
| Si el poseedor permite la visita, el deudor puede pedir una reducción de deuda de hasta el 2 % | ✅ | LEC 669.3 |

### 2.11 Ocupantes

| Regla | Estado | Fuente |
|---|---|---|
| Antes de la subasta, el ejecutante puede pedir que se declare que los ocupantes no tienen derecho a permanecer; se publica en el anuncio | ✅ | [LEC 661](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a661) |
| El adquirente puede pedir el lanzamiento de ocupantes de mero hecho en el plazo de **1 año**; después, juicio declarativo | ✅ | [LEC 675](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a675) |

### 2.12 Concurso y vivienda habitual (deuda remanente)

- **Concurso del deudor:** suspende la ejecución y deja sin efecto la subasta aunque esté en
  curso ✅ ([LEC 649.1](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a649),
  [691.5](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a691)). El depósito vuelve, pero
  el capital queda inmovilizado mientras tanto.
- **Art. 579.2** ✅ ([enlace](https://www.boe.es/buscar/act.php?id=BOE-A-2000-323#a579)):
  liberación de la deuda remanente del deudor de vivienda habitual. **No afecta al comprador**
  salvo en un caso: si el adjudicatario es el ejecutante o su cesionario y revende en 10 años, la
  deuda del deudor se reduce en el 50 % de la plusvalía. Para un tercero no tiene efecto.

### 2.13 Dónde choca el motor con lo anterior (resumen; detalle en el documento de impacto)

| # | Hoy en SEIS | Lo que dice la norma | Fichero |
|---|---|---|---|
| 1 | Depósito por defecto del **5 %** (contrato, modelo, ingesta) | 20 % en inmuebles del régimen nuevo; 5 % solo en el anterior (y en la AEAT) | `engine/contracts.py:49`, `models.py:60`, `ingesta/contratos.py:29`, `ingesta/boe.py:164` |
| 2 | Condición T2: «Judicial: depósito del 5 %… cesión de remate solo por el ejecutante» | Depósito 20 % (nuevo); cesión también para acreedores posteriores | `engine/rules/catalogo.yaml:224` |
| 3 | Táctica: «Entrar tarde… la extensión automática del cierre neutraliza el sniping» | En el régimen nuevo no hay prórroga y las pujas son secretas | `engine/modules/m13_puja.py:67` |
| 4 | Ratio esperado judicial: vivienda ocupada **0,42**, desconocida 0,45, por defecto 0,50 | Por debajo del 50 % el remate no es automático; por debajo del 40 % no hay ninguna vía automática; en vivienda habitual, imposible por debajo del 60 % | `engine/params/defaults.yaml:219-221` |
| 5 | `es_vivienda_habitual` se captura pero **ninguna regla lo usa**, y por defecto es `False` (lo optimista, contra P4) | Suelo absoluto del 60 % | `contracts.py:38`, `m01_captura.py:23` |
| 6 | Ningún peldaño de la escalera se compara con los umbrales | — | `m12_decision.py:65-148` |
| 7 | «Pago del remate sin condición suspensiva de financiación» | La solicitud del testimonio para hipotecar suspende el plazo | `m13_puja.py:81` |

---

## 3 · AEAT (Reglamento General de Recaudación)

Todo ✅, literal de la redacción vigente salvo donde se indica.

| Tema | Regla | Fuente |
|---|---|---|
| Valoración | A precios de mercado; el deudor puede aportar una valoración contradictoria | [RGR 97.1-4](https://www.boe.es/buscar/act.php?id=BOE-A-2005-14803#a97) |
| **Tipo de subasta** | Sin cargas: la valoración. Con cargas anteriores: valoración − cargas (si las cargas la superan, el tipo es la deuda y las costas, con el valor del bien como tope). Las cargas anteriores **subsisten** | [RGR 97.6](https://www.boe.es/buscar/act.php?id=BOE-A-2005-14803#a97) |
| **Nuevas convocatorias** | Si el bien quedó sin adjudicar, el tipo se multiplica por **0,8** en la segunda subasta y por **0,6** en la tercera y siguientes | [RGR 97.7](https://www.boe.es/buscar/act.php?id=BOE-A-2005-14803#a97) |
| **Segunda licitación** | **Ya no existe.** La redacción de 2005 permitía a la Mesa una segunda licitación inmediata al **75 %** del tipo; la vigente no la contiene. Hoy el equivalente es una subasta nueva con el coeficiente del 97.7 | RGR 104, versiones 2005 y vigente |
| Norma que la suprimió | La modificación con ID BOE-A-2017-15839, vigente desde el 1‑1‑2018. **No he verificado su título** (con probabilidad, el RD 1071/2017) | ⚠️ |
| **Depósito** | **5 %** del tipo si el lote contiene algún inmueble; **10 %** si son solo muebles | [RGR 103 bis.1](https://www.boe.es/buscar/act.php?id=BOE-A-2005-14803#a1-2) |
| Reserva de depósito | Opcional al pujar; **obligatoria** si la puja es igual o inferior a la más alta | RGR 103 bis.2-3 |
| Plataforma | Portal de Subastas del BOE; 20 días naturales | [RGR 104.1-2](https://www.boe.es/buscar/act.php?id=BOE-A-2005-14803#a104) |
| **Puja mínima** | **10 % del tipo**, salvo que el bien tenga cargas ≥ 25 % de su valoración | RGR 104.3 |
| Visibilidad y cierre | Las pujas **se publican** al recibirse; el cierre se prorroga **1 h** tras la última puja, con un máximo de **24 h** | RGR 104.2-3 |
| **Adjudicación** | Mesa en ≤ 15 días naturales. **≥ 50 % del tipo:** adjudica. **< 50 %:** la Mesa decide «atendiendo al interés público y **sin que exista precio mínimo** de adjudicación» | [RGR 104 bis.1](https://www.boe.es/buscar/act.php?id=BOE-A-2005-14803#a1-4) |
| Pago | Resto en **15 días** desde la notificación; si no, pierde el depósito | RGR 104 bis.3.b |
| Escritura pública | Opcional; exige un ingreso adicional del **5 %** del remate en 5 días | [RGR 111.1](https://www.boe.es/buscar/act.php?id=BOE-A-2005-14803#a111) |
| Tanteo o adquisición preferente | La adjudicación queda en suspenso mientras dure el plazo legal de ejercicio | RGR 104 bis.3.a |
| **Adjudicación directa** | Tras un concurso desierto, por urgencia o cuando no convenga la concurrencia. Precio mínimo: el tipo del concurso o el valor de mercado; **si no se alcanza, sin precio mínimo**. Plazo de gestión: 1 mes | [RGR 107](https://www.boe.es/buscar/act.php?id=BOE-A-2005-14803#a107) |
| Liberación por el deudor | Hasta la certificación del acta de adjudicación o la escritura | RGR 104.4 |
| Subasta por entidad especializada | Sin depósito previo; reglas habituales de esa entidad | [RGR 105](https://www.boe.es/buscar/act.php?id=BOE-A-2005-14803#a105) |

> **Para el motor:** en la AEAT no hay un umbral que impida la adjudicación. El 50 % separa «la
> adjudica» de «la Mesa decide», y el único suelo duro es la puja mínima del 10 %. El depósito
> del 5 % actual **es correcto para la AEAT**.

---

## 4 · Otros procedimientos (resumen)

### 4.1 Seguridad Social (TGSS)

✅ [RGRSS arts. 111-123 bis](https://www.boe.es/buscar/act.php?id=BOE-A-2004-11836#a120):

- **Tipo:** la valoración; con cargas preferentes, valoración − cargas (art. 111).
- **Formato:** sobre cerrado presentado en la Dirección Provincial y puja **presencial** a viva
  voz (arts. 117, 118, 120). Depósito del **25 %** del tipo con el sobre, o del **30 %** para
  pujar en el acto. Las pujas verbales deben ser **≥ 75 %** del tipo, con tramos de al menos el
  2 %.
- **Primera subasta:** remate si la postura **supera el 60 %**, o cubre la deuda (en inmuebles,
  nunca por debajo del **25 %**). El deudor puede presentar un tercero que mejore hasta el 75 %
  en 3 días hábiles.
- **Segunda subasta:** remate si supera el **50 %** o cubre la deuda (mínimo 25 % en inmuebles);
  el director provincial puede aprobar entre el 25 % y el 50 % con resolución motivada.
- **Pago:** 5 días hábiles.
- ⚠️ **No confirmado:** si la TGSS ya celebra sus subastas en el Portal del BOE. El reglamento
  vigente describe un acto presencial, y el art. 120 se modificó en 2024 (BOE-A-2024-6086) sin
  que yo haya revisado ese cambio en detalle.

### 4.2 Notarial

- **Subasta notarial (Ley del Notariado, arts. 72-77)** ✅
  ([art. 75](https://www.boe.es/buscar/act.php?id=BOE-A-1862-4073#a75)): en el Portal de
  Subastas, ≥ 20 días, consignación del **5 %**, pago del resto en **10 días hábiles**, reserva
  de postura y adjudicación al siguiente si el primero no paga. En lo no previsto, se aplica la
  LEC ([art. 72.2](https://www.boe.es/buscar/act.php?id=BOE-A-1862-4073#a72)). **A diferencia
  de la LEC, el portal informa de las pujas durante la subasta** (75.1.3.ª).
- **Venta extrajudicial hipotecaria** ✅
  ([LH art. 129.2](https://www.boe.es/buscar/act.php?id=BOE-A-1946-2453#a129)): una sola subasta
  electrónica en el Portal del BOE. «Los tipos en la subasta y sus condiciones serán, **en todo
  caso, los determinados por la Ley de Enjuiciamiento Civil**» (129.2.d). Por tanto, **le
  aplican los umbrales del art. 670**, incluida la vivienda habitual (129.2.b presume que lo es
  si así consta en la escritura). El tipo no puede ser inferior a la tasación del mercado
  hipotecario (129.2.a).
- ⚠️ **No confirmado:** el detalle del Reglamento Hipotecario (art. 236 y siguientes) sobre la
  consignación en la venta extrajudicial. No lo he leído; la LH remite a él (129.2.e).

### 4.3 Concursal

✅ [TRLC](https://www.boe.es/buscar/act.php?id=BOE-A-2020-4859):
- Liquidación: los bienes de más del 5 % del inventario se venden en **subasta electrónica**, en
  el Portal del BOE **o en cualquier otro portal especializado**, salvo que el juez fije otras
  reglas ([art. 423](https://www.boe.es/buscar/act.php?id=BOE-A-2020-4859#a4-35)).
- Bienes con privilegio especial: subasta electrónica salvo autorización de otro modo
  ([art. 209](https://www.boe.es/buscar/act.php?id=BOE-A-2020-4859#a2-21)); venta directa si el
  precio supera el mínimo pactado en la garantía, o menos con conformidad y a valor de mercado
  ([art. 210](https://www.boe.es/buscar/act.php?id=BOE-A-2020-4859#a2-22)).
- Sin postores en la subasta de un bien hipotecado: el acreedor puede adjudicárselo en los
  términos de la LEC; si no lo hace y el bien vale menos que la deuda, el juez se lo adjudica;
  si vale más, **nueva subasta sin postura mínima**
  ([art. 423 bis](https://www.boe.es/buscar/act.php?id=BOE-A-2020-4859#a4-115)).
- ⚠️ **No confirmado:** los umbrales y depósitos dependen de las **reglas de liquidación de cada
  concurso** y del portal elegido. No hay una regla única que el motor pueda parametrizar sin
  leer el edicto concreto.

### 4.4 Ejecución administrativa de otras administraciones

⚠️ **No confirmado en esta fase.** Comunidades autónomas y ayuntamientos aplican el RGR por
remisión de su normativa de recaudación o tienen normas propias. Sin una lista cerrada de
órganos, el motor debería tratarlas como «AEAT por defecto» y marcar el dato como supuesto.

### 4.5 Bancaria y privada

No son subastas públicas regladas: las condiciones las fija el vendedor. **No existe un umbral
legal** que comprobar.

---

## 5 · Tabla resumen para parametrizar (inmuebles)

| Procedimiento | Depósito | Puja mínima | Aprobación automática | Zona discrecional | Suelo duro | Pago del resto | Pujas |
|---|---|---|---|---|---|---|---|
| Judicial LEC, **nuevo** | 20 % (mín. 1.000 €; el LAJ puede variarlo) | No | ≥ 70 % al día siguiente; ≥ 50 % (o ≥ 40 % si cubre la deuda) tras 10 días sin mejora | < 50 % (< 40 % aunque cubra la deuda) | **Vivienda habitual: 60 %** | 20 días | Secretas, sin prórroga |
| Judicial LEC, **anterior** | 5 % | No | ≥ 70 %; > 50 % o si cubre lo reclamado tras el trámite de mejora | Por debajo | Vivienda habitual: 60 % | 40 días | Visibles, prórroga de 1 h (máx. 24 h) |
| Venta extrajudicial notarial (LH 129) | ⚠️ Reglamento Hipotecario | No | Como la LEC (art. 670) | Como la LEC | Vivienda habitual: 60 % | ⚠️ | ⚠️ |
| Subasta notarial (Notariado) | 5 % | No | ⚠️ Supletoria de la LEC | ⚠️ | ⚠️ | 10 días hábiles | Visibles |
| AEAT | 5 % | 10 % del tipo | ≥ 50 % | < 50 % (sin precio mínimo) | 10 % (puja mínima) | 15 días | Visibles, prórroga de 1 h (máx. 24 h) |
| TGSS | 25 % (sobre) / 30 % (en el acto) | 75 % (pujas verbales) | > 60 % (1.ª) / > 50 % (2.ª) o si cubre la deuda | 2.ª subasta: 25-50 % | 25 % | 5 días hábiles | ⚠️ Presencial |
| Concursal | ⚠️ Según las reglas de liquidación | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| Bancaria / privada | Contractual | Contractual | — | — | — | Contractual | — |

---

## 6 · Pendiente de confirmar (no usar sin validar)

1. Interpretación de «procedimientos incoados» de la DT 9.ª (ejecución o pleito previo).
2. Si el Portal de Subastas o el edicto publican la **fecha de incoación** y la **cantidad
   reclamada**.
3. Frecuencia real de aprobación de remates por debajo del 50 % y del 40 % (jurisprudencia o
   estadística del CGPJ).
4. Título de la norma BOE-A-2017-15839 y contenido de la modificación de 2024 del RGR
   (BOE-A-2024-1771).
5. Consignación y plazos de la venta extrajudicial (Reglamento Hipotecario, art. 236 y ss.).
6. Formato actual de las subastas de la TGSS (presencial o portal) tras la modificación de 2024.
7. Si el LAJ fija en la práctica una puja mínima o tramos en el Portal para subastas judiciales.
