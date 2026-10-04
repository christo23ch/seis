# Auditoría del motor frente a la especificación (Fase 5G.4-E)

**Fecha:** 2026-10-03 · **Rama:** `checkpoint/5f6-simulaciones-informes` · **Código auditado:** `e1dd01f`
**Alcance:** solo lectura. No se ha cambiado una línea del motor. Prepara la **5H**.
**Decisión de partida:** [ADR-0016](../30-Decisiones/ADR/ADR-0016-coste-de-capital-como-coste-de-oportunidad.md)
(coste de capital = coste de oportunidad del capital propio; D5 aceptada y pendiente).

## Cómo se ha medido

Todas las cifras salen del **motor real ejecutado en memoria** (`app.engine.pipeline.ejecutar_analisis`),
sin base de datos, con scripts fuera del repositorio. Dos casos:

- **Caso §19** — la entrada de `tests/test_golden_caso19.py` (flip integral, cash, VT 152.000 €).
- **Caso §19 con hipoteca** — la misma entrada con `financiacion = hipoteca, preaprobada, LTV 70 %,
  interés 3,5 %`.

Cuando hace falta otro caso (perfil rentista, otra banda de riesgo) se dice en el punto. Los
importes van redondeados al euro salvo que se indique. «Cambia el caso dorado» significa que
cambiaría algún valor que hoy fija un test (`test_golden_caso19.py`, `test_informe_coherencia.py`,
`test_coste_capital_5g4.py`).

## Estado tras la Fase 5H.1 (2026-10-04)

| Punto | Estado | Commits | Decisión |
|---|---|---|---|
| E6 · VAN y diferencial TIR − coste de capital | ✅ Resuelto | `31dd511` | [ADR-0017](../30-Decisiones/ADR/ADR-0017-van-y-diferencial-tir-frente-al-coste-de-capital.md) |
| E1 · D5, coste de capital solo sobre el capital propio | ✅ Resuelto (la parte del plazo de los intereses, no: ESTADO_ACTUAL, Backend 19) | `5cb0634`, `1386faa` | [ADR-0018](../30-Decisiones/ADR/ADR-0018-coste-de-capital-solo-sobre-el-capital-propio.md) |
| E5 · Colchón de plazo | ✅ Resuelto (el coste del depósito, no) | `f2bc04a` | [ADR-0019](../30-Decisiones/ADR/ADR-0019-colchon-de-plazo.md) |
| E7 punto 5 · §9.1 definido y §19 regenerado (E2 a, H3) | ✅ Resuelto | 5H.1-D | especificación §7.7, §9.1, §9.5 y §19 |
| E3, E2 b, E5 depósito, E4, E8 | Pendientes (5H.2) | — | — |

Medidas tras la 5H.1, caso §19: VAN al coste de capital 33.230,42 €, TIR − coste de capital
+32,37 puntos, colchón de plazo 84,8 meses a P_objetivo y 60,9 a P_max; ningún valor existente
cambió (guarda `tests/test_invariante_5h1.py`). Caso con hipoteca: P_límite 77.100 → 78.156 €.

## Resumen

| Punto | Qué pasa | ¿Cambia el caso dorado al corregirlo? | Tamaño |
|---|---|---|---|
| E1 | Con hipoteca, el precio límite cobra dos veces el coste de la parte financiada, y los intereses van a plazo P50 dentro de un límite estresado a P80 | **No** (el §19 es cash) | Pequeño |
| E2 | La especificación usa `coste_capital(plazo)` y nunca lo define | No, si se documenta la fórmula actual; −36 € en P_límite con la definición alternativa | Pequeño |
| E3 | TIR 33,87 % (motor) frente a ≈23 % (§19): el calendario de flujos es una decisión del código | Sí, si se cambia el calendario (TIR 33,87 → 34,73 %) | Pequeño-medio |
| E4 | El perfil rentista resta coste de capital y §9.2 no; degenera desde un 7,21 % | No (el §19 es flip) | Pequeño |
| E5 | «Colchón de plazo» (§9.5) y coste del depósito (§6.6, P7) sin implementar | Colchón: no. Depósito: sí, −9 € por mes inmovilizado | Pequeño / medio |
| E6 | VAN al coste de capital y diferencial TIR − coste de capital (opción «D») | **No** | Medio-pequeño |
| E8 | La utilidad de rentabilidad del ICO no depende de la operación y premia el riesgo | Sí, si se corrige | Medio, decisión de producto |

E7 es el orden propuesto para la 5H (al final).

---

## Tres hechos estructurales que condicionan todo lo demás

### H1 · I(P_max, C_F^P80) no depende de la financiación

`P_max = min(P_por_margen_mínimo, P_pesimista)` (`m12_decision.py:85`). Las dos ramas se
definen **despejando P de una ecuación sobre I(P)**, así que la inversión a P_max queda fijada
por la ecuación y no por el precio:

- **Si manda la rama pesimista**, `P_pes` resuelve `I(P, C_F^P80) = VS_pes / (1 + piso)` con
  piso 0 en todos los perfiles de venta (`m12_decision.py:79-83`). Por tanto
  **`I(P_max, C_F^P80) = VS_pes` exactamente.** Medido en el §19: 160.837,44 € en los dos lados.
- **Si manda el margen mínimo**, `I(P_max, C_F^P50) = VS_p / (1 + m_min)` y
  `I(P_max, C_F^P80) = VS_p/(1 + m_min) + (C_F^P80 − C_F^P50)`. Medido con el perfil oportunista:
  151.559,25 €, también idéntico con cash y con hipoteca.

| Perfil | Financiación | Rama que manda | I(P_max, C_F^P80) | VS_pes | Coste de capital |
|---|---|---|---|---|---|
| flip_integral (§19) | cash | pesimista | 160.837 € | 160.837 € | 3.659 € |
| flip_integral (§19) | hipoteca | pesimista | 160.837 € | 160.837 € | 3.659 € |
| flip_ligero | cash / hipoteca | pesimista | 160.837 € | 160.837 € | 3.378 € |
| oportunista | cash / hipoteca | margen mínimo | 151.559 € | 160.837 € | 3.448 € |

**Implicación para D5.** Hoy el coste de capital (`cc · I(P_max, C_F^P80) · plazo_p80/12`,
`m12_decision.py:126-127`) es **idéntico con cash y con hipoteca**: la hipoteca sube `c_v`, baja
P_max y deja I(P_max) donde estaba. La financiación solo puede entrar en el coste de capital a
través de D5, restando la parte financiada: `E = I(P_max, C_F^P80) − LTV · P_max`. Y como I está
fijada, **D5 se reduce a restar `cc · LTV · P_max · plazo_p80/12`**, que es exactamente la doble
cuenta de E1.

### H2 · El ROI a precio objetivo es siempre el margen exigido

M11 se evalúa a **P_objetivo** (`pipeline.py:90-91`) y P_objetivo es, por definición,
`P(m*, VS_p, C_F^P50)`: el precio que deja **exactamente** el margen objetivo ajustado a riesgo
(§9.1, `m12_decision.py:76`). El ROI resultante es ese margen, por construcción:

| Perfil | Margen objetivo ajustado | ROI a P_objetivo (cash · hipoteca · con base fiscal mínima) |
|---|---|---|
| flip_ligero | 0,16 | 0,16 · 0,16 · 0,16 |
| flip_integral (§19) | 0,25 | 0,25 · 0,25 · 0,25 |
| cambio_uso | 0,30 | 0,30 · 0,30 · 0,30 |
| division_horizontal | 0,28 | 0,28 · 0,28 · 0,28 |
| oportunista | 0,35 | 0,35 · 0,35 · 0,35 |

**¿Es intencionado según la especificación?** Sí en su letra. §9.1 define P_objetivo como el
precio que «cumple exactamente el margen objetivo del perfil», y §19 presenta la «Rentabilidad a
P_objetivo» (ROI 25 %) como resultado. Nada en la especificación dice que el ROI deba evaluarse a
otro precio. La consecuencia, que la especificación no comenta, es que **el ROI, el ROI
anualizado y la línea de escenario base del informe no informan de la operación**: repiten el
margen exigido. Lo que sí varía de una operación a otra son P_objetivo, los escenarios pesimista
y optimista, la TIR (por el calendario) y el margen de seguridad. Ver E8 para el efecto sobre el
ICO.

### H3 · El §19 de la especificación no es reproducible con sus propias cifras

El ejemplo del §19 no cuadra ni siquiera consigo mismo, y el motor aplica estreses que el ejemplo
no aplica. Desglose de C_F^P80:

| Partida | §19 (texto) | Motor |
|---|---|---|
| Reforma P80 | 60.500 € | 61.064 € |
| Desalojo P80 | 9.500 € | 9.500 € |
| Atrasos comunidad/IBI | 2.400 € (P50) | 3.235 € (P50 × 1,33, `atrasos.stress_p80`) |
| Adquisición fija | 2.700 € | 2.700 € |
| Tenencia | 3.120 € (13 m, P50) | 4.368 € (18,2 m, plazo P80) |
| Comercialización | 6.840 € | 6.841 € |
| Contingencia | consumida | consumida |
| **Suma de las partidas** | **85.060 €** | **87.708 €** |
| **C_F^P80 declarado** | **86.800 €** | **87.708 €** |

- Las partidas del §19 suman 85.060 €, pero el texto declara 86.800 €. Faltan 1.740 € que
  ninguna partida explica.
- El motor estresa en P80 los atrasos y la tenencia (P5: la ausencia de datos penaliza). El
  ejemplo usa los valores P50.
- Con las cifras del documento, el P_límite bruto es (176.700 − 86.800)/1,064 = 84.492 €. Con las
  del motor, 83.681 €.
- El «82.500 €» del §19 implicaría un coste de capital de 1.992 € sobre el bruto del documento, y
  de 1.181 € sobre el del motor. Ninguna definición razonable da las dos cosas (ver E2).
- El «TIR ≈ 23 %» del §19 coincide con el ROI anualizado (22,87 %), no con una TIR de flujos
  mensuales (ver E3).

**Conclusión:** el §19 es un ejemplo ilustrativo redondeado, no una especificación numérica. El
test dorado lo trata así (rangos: P_límite 78.000–84.500 €, TIR 0,15–0,35). Propuesta para la 5H:
**regenerar el §19 con las cifras del motor**, como ya se hace con
`docs/SEIS_informe_ejemplo_caso19.md`, y quitar los valores que no salen de ninguna fórmula.

---

## E1 · Doble cuenta de los intereses con hipoteca en el precio límite

**Qué dice la especificación.** §6.6 (tabla de costes de M06): «Financiación: apertura + interés
`i × LTV × P × plazo` + tasación banco — entra parcialmente en `c_v`». §9.1: P_límite =
`P(0, VS_p, C_F^P80) − coste_capital(plazo)`. No dice si el coste de capital se aplica a toda la
inversión o solo al capital propio. P7 (§1): «el capital tiene coste».

**Qué hace el código.**
- `m06_costes.py:77-78`: con hipoteca, `c_v += apertura_pct · LTV + LTV · i · plazo_p50/12`.
- `m12_decision.py:124-128`: `p_lim_bruto` se resuelve con ese `c_v`, que ya incluye los
  intereses de la parte financiada; luego se resta `cc · I(P_max, C_F^P80) · plazo_p80/12` sobre
  **toda** la inversión.
- Dos incoherencias:
  1. **Doble cuenta:** la parte financiada (LTV · P) paga su coste real como intereses en `c_v`
     y, además, el coste de oportunidad.
  2. **Plazos distintos:** los intereses se calculan a plazo P50 (13 meses) dentro de un límite
     que todo lo demás estresa a P80 (18,2 meses).

**Impacto medido** (hipoteca LTV 70 %, 3,5 %, coste de capital 1,5 %):

| Magnitud | Valor |
|---|---|
| Intereses en `c_v` (a P50) | 0,02654 · P ≈ 2.143 € a P_límite bruto |
| Coste de capital cobrado a la parte financiada (`cc · LTV · P_max · plazo_p80/12`) | **1.055 €** |
| P_límite actual | **77.100 €** |
| P_límite con D5 (coste de capital solo sobre E = I − LTV·P_max) | **78.156 €** (+1.056) |
| Efecto de calcular los intereses a plazo P80 en el límite | −774 € en el P_límite bruto |
| D5 + intereses a P80 | ≈ 77.382 € (+282 frente a hoy) |
| Caso §19 (cash) | 80.022 € con cualquiera de las variantes: LTV = 0 ⇒ E = I |

**Propuesta (D5).** En `m12_decision.calcular_escalera`, con `f.tipo == "hipoteca"`:
`coste_capital = cc · max(0, I(P_max, C_F^P80) − LTV · P_max) · plazo_p80/12`. Además, para que el
límite estresado sea coherente, calcular los intereses de la parte financiada a plazo P80 en el
`c_v` que usa `p_lim_bruto`. Son dos cambios separables, y el segundo necesita decisión: hoy
`c_v` es uno solo para toda la escalera.

**¿Cambia el caso dorado?** No: el §19 es cash. Cambian los análisis con hipoteca, en la cuantía
de la tabla.

**Tamaño:** pequeño (M12 y sus tests; el segundo cambio, M06 y M12).

---

## E2 · `coste_capital()` no está definido en la especificación

**Qué dice la especificación.** §9.1 (tabla de la escalera) y §9.3 (pseudocódigo,
`p_lim = P(0.0, VS_p, CF80) - coste_capital(h.plazo_p80, h)`) usan la función sin definirla.
§9.5 habla de «coste de tenencia + capital mensual» para el colchón de plazo, sin fórmula. §19
da «≈ 82.500 €» sin el cálculo.

**Qué hace el código** (`m12_decision.py:123-128`): interés simple sobre la inversión a P_max con
costes P80 y plazo P80, `cc · I(P_max, C_F^P80) · plazo_p80/12`.

**Impacto medido de las alternativas** (caso §19, coste de capital 1,5 %, P_límite bruto 83.681 €):

| Definición | Importe | P_límite |
|---|---|---|
| **Código actual:** cc · I(P_max, C_F^P80) · plazo_P80/12 | 3.659 € | **80.022 €** |
| cc · I(P_max, C_F^P80) · plazo_P50/12 | 2.614 € | 81.067 € |
| cc · I(P_obj, C_F^P50) · plazo_P50/12 | 2.298 € | 81.383 € |
| cc · P_límite bruto · plazo_P80/12 | 1.904 € | 81.777 € |
| cc · P_max · plazo_P80/12 | 1.564 € | 82.117 € |
| Compuesto: ((1+cc)^(plazo_P80/12) − 1) · I(P_max, C_F^P80) | 3.673 € | 80.008 € |
| **Alternativa propuesta:** B(P) = k · E(P), con k = cc · plazo_P80/12 | — | **79.986 €** |

**Por qué el §19 no se puede reproducir:** ver H3. Ninguna fila da los 1.992 € implícitos sobre el
bruto del documento, y el bruto del documento no es el del motor porque su C_F^P80 no cuadra.

**Propuesta para la especificación** (§9.1, nueva definición explícita):

> **P_límite es el precio al que el beneficio en estrés iguala el coste de oportunidad del capital
> propio durante el plazo estresado:** `B(P) = k · E(P)`, con `B(P) = VS_p − I(P, C_F^P80)`,
> `E(P) = I(P, C_F^P80) − LTV·P` (capital propio; `LTV = 0` en cash) y
> `k = cc · plazo_P80 / 12` (interés simple).

- **Por qué esta forma.** Es la misma familia que el resto de la escalera (§9.1: P_límite =
  P(m, VS_p, C_F^P80) con `m = k` cuando no hay deuda). Tiene solución cerrada y lineal:
  `P = (VS_p − (1+k)·C_F^P80) / ((1+k)(1+c_v) − k·LTV)`, y el tramo fiscal se resuelve con
  `fiscal.resolver_por_tramos` como hoy. Incorpora D5 sin un caso aparte. Además deja de
  depender de P_max, que es otro peldaño.
- **Interés simple y no compuesto:** la diferencia es de 14 € en el §19 (80.022 frente a
  80.008), y el simple mantiene la fórmula lineal y es el mismo criterio con el que M06 calcula
  los intereses del préstamo.
- **Plazo P80:** el límite es el punto de indiferencia **estresado**; mezclar plazos es justo lo
  que se critica en E1.

| Caso | Hoy | Definición propuesta | Umbral de degeneración hoy → propuesto |
|---|---|---|---|
| §19 (cash) | 80.022 € | 79.986 € (−36) | 6,13 % → 6,52 % |
| §19 con hipoteca | 77.100 € | 78.288 € (+1.188) | — → 9,16 % |

**¿Cambia el caso dorado?** Hay dos caminos:
- **(a) Documentar la fórmula actual** y aplicar D5 aparte: **no** cambia.
- **(b) Adoptar la definición propuesta:** P_límite del §19 **−36 €** (80.022 → 79.986). El test
  dorado (rango 78.000–84.500) sigue pasando, pero hay que actualizar los valores fijados en
  `test_informe_coherencia.py`, `test_coste_capital_5g4.py`, el plan de puja y el texto de
  referencia del informe.

**Tamaño:** pequeño en ambos caminos. El (b) toca M12, cuatro tests y §9.1 y §19 de la
especificación, y merece ADR propio.

---

## E3 · TIR: 33,87 % en el motor frente a ≈23 % en el §19

**Qué dice la especificación.** §7.7: `TIR = tir(flujos mensuales del calendario M06)`, por
bisección. §6.6 dice que M06 produce el «calendario de desembolsos» y el «desglose por fase
(adquisición → posesión → transformación → tenencia → salida)», pero **no define cómo se
reparten los pagos en el tiempo**. §19: «ROI anualizado ≈ 23 % · TIR ≈ 23 %».

**Qué hace el código** (`m11_rentabilidad.py:40-66`). M06 **no** produce ningún calendario: lo
construye M11 con fracciones fijas del plazo.
- Mes 0: precio·(1+c_v), adquisición, atrasos, contingencia, cargas y plusvalía.
- Cada mes: tenencia.
- Desalojo en el mes `round(0,45·n)` (`:53`).
- Reforma repartida en los `round(0,30·n)` meses siguientes (`:54`).
- Mes n: VS menos comercialización.

Las fracciones 0,45 y 0,30 son **decisión del código**, sin respaldo en la especificación, y no
salen de los plazos que el propio motor conoce: en el §19, ocupación P50 = 7 meses y obra =
3 meses, frente a los 6 y 4 meses que salen de las fracciones.

**De dónde sale la diferencia** (caso §19, escenario base, 13 meses):

| Calendario | TIR |
|---|---|
| **Motor** (desalojo mes 6, reforma meses 7-10) | **33,87 %** |
| Reforma pagada en el mes 0 | 24,93 % |
| Reforma y desalojo en el mes 0 | 24,34 % |
| Todo el gasto en el mes 0 | 24,03 % |
| ROI anualizado, (1,25)^(12/13) − 1 | 22,87 % |
| Calendario con los plazos reales de M06 (ocupación 7 m, obra 3 m) | 34,73 % |

- **Casi toda la diferencia es la reforma:** 50.053 € que el calendario paga entre los meses 7 y
  10 en vez del 0. Eso solo explica 9 de los 11 puntos.
- **Por qué «todo en el mes 0» da 24,03 % y no 22,87 %:** la comercialización (6.841 €) se resta
  del cobro final en vez de pagarse al principio.
- **El §19 con «TIR ≈ 23 %»** es, en la práctica, el ROI anualizado: trata todo el gasto como si
  se pagara el día 0. Con hipoteca la TIR es la misma (33,87 %): M11 calcula sobre la inversión
  total, sin apalancamiento (H1, H2).

**¿Qué cifra es más defendible ante un inversor?** **El ≈23 % (ROI anualizado), como cifra
principal.** Tres razones:
1. La TIR de 33,87 % supone que el capital de la reforma queda libre hasta que se gasta. El propio
   checklist exige lo contrario («Capital para C_F comprometido por calendario», §13 ítem 19): ese
   dinero está reservado y no rinde. Por P7, ese tiempo cuesta.
2. El calendario que produce el 33,87 % es inventado (fracciones fijas), no medido.
3. La diferencia es demasiado grande (11 puntos) para presentarla sin explicación.

La TIR tiene sentido como cifra secundaria si: (a) el calendario sale de las fases reales de M06,
(b) se etiqueta («supone pagos de reforma escalonados») y (c) se acompaña del VAN al coste de
capital (E6), que mide el efecto del tiempo con la tasa del inversor.

**Propuesta.** Calendario de M11 con los plazos reales que ya calcula M06 (meses de ocupación de
la tabla §7.2 y `reforma.plazo_obra_meses`), y documentarlo en §6.6/§7.7. En el informe y la
interfaz, ROI anualizado como cifra principal y TIR con su supuesto.

**¿Cambia el caso dorado?** Sí: la TIR del §19 pasa de 33,87 % a 34,73 %. El test dorado
(0,15–0,35) sigue pasando, pero hay que actualizar la guarda de 5G.4 (`tir_anual = 0,3387`).
Ningún precio ni el semáforo cambian: la TIR no entra en el ICO ni en la escalera.

**Tamaño:** pequeño-medio (M11, guardas, §6.6/§7.7, texto del informe).

---

## E4 · Perfil rentista: el código resta coste de capital y §9.2 no

**Qué dice la especificación.** §9.2: `P_límite = P(y_suelo)`, con
`y_suelo = referencia libre de riesgo a 10 años + 250 pb`. Para el rentista, el coste de
oportunidad **ya está dentro de y_suelo** y no hay término de coste de capital.

**Qué hace el código** (`m12_decision.py:119-130`). Calcula para todos los perfiles el límite de
la rama de venta (`p_lim_bruto − coste_capital`, sobre VS_p y plazo P80 de un flip) y, en el
rentista, se queda con el menor: `p_lim = min(p_lim, p_lim_rent)`. Además del coste de capital
que §9.2 no prevé, aplica un horizonte de flip (18,2 meses) a una estrategia de ≥ 60 meses (§9.6).

**Impacto medido** (caso §19 con perfil rentista, renta 950 €/mes, IBI 350 €, comunidad
60 €/mes; P_max = 66.375 €; P(y_suelo 5,7 %) = 73.704 €):

| Coste de capital | P_límite | Escalera degenerada | Semáforo |
|---|---|---|---|
| 0 – 0,015 | 73.704 € (manda y_suelo) | no | amarillo |
| 0,05 | 71.674 € (manda el coste de capital) | no | amarillo |
| 0,10 | 59.668 € | **sí** | **rojo** |
| 0,15 | 47.661 € | sí | rojo |

- **El coste de capital empieza a mandar desde 4,16 %:** por encima, el límite deja de ser el de
  §9.2.
- **La escalera degenera desde 7,21 %.** Con §9.2 al pie de la letra, el rentista **no
  degeneraría nunca por el coste de capital**.
- El aviso de ADR-0016 (6 %) avisa a tiempo para el §19 de venta, pero en este rentista la
  degeneración llega al 7,21 %, dentro del rango admitido (≤ 15 %).

**Propuesta.** Aplicar §9.2: en el rentista, `p_lim = p_lim_rent`, sin la rama de venta. Si se
quiere conservar el límite de venta como cota de seguridad, debe ser decisión expresa y
documentarse en §9.2, con su propio horizonte, no el de un flip.

**¿Cambia el caso dorado?** No (flip). Cambian los análisis rentista con coste de capital > 4,16 %.

**Tamaño:** pequeño (M12 y un test rentista nuevo), con decisión del responsable sobre si se
conserva la cota.

---

## E5 · «Colchón de plazo» (§9.5) y coste financiero del depósito (§6.6): no implementados

**Qué dice la especificación.**
- §9.5: «Colchón de plazo = meses extra soportables hasta B=0 (por coste de tenencia + capital
  mensual)», como salida obligatoria del informe, a P_objetivo y a P_max.
- §6.6: «Coste del depósito (5 %) y de depósitos de subastas perdidas — coste financiero del
  capital inmovilizado (P7)».
- P7: «toda inmovilización (consignaciones incluidas) se computa».

**Qué hace el código.** Nada de lo dos. No hay ningún «colchón» en el motor. M06 no tiene
partida del depósito (`m06_costes.py`, desglose P50/P80). El depósito solo aparece como importe
en el plan de puja y en el checklist (M13, M14).

**Qué harían y cuánto mueven** (caso §19, coste de capital 1,5 %):

**Colchón de plazo** = B / (tenencia mensual + cc · I / 12):

| | A P_objetivo | A P_max |
|---|---|---|
| Sin coste de capital | 147,3 meses | 108,6 meses |
| Con 1,5 % | **84,8 meses** | **60,9 meses** |
| Con 5 % | 42,6 meses | — |

- **Para qué sirve:** dice cuánto puede alargarse la operación antes de perder dinero. Es la
  métrica natural para el riesgo de plazo (ocupación, licencias). Es una salida nueva:
  **no cambia** ningún precio, el semáforo ni el caso dorado; añade una línea al informe.
- **Ojo:** hay que decidir si se calcula con el beneficio base o con el pesimista; la
  especificación no lo dice. Con el pesimista sale mucho menor.

**Depósito:** 7.600 € (5 % de 152.000 €) inmovilizados entre la consignación y el pago del remate:
- **Coste:** 9,50 € por mes a 1,5 %. Llevado a C_F: P_objetivo 60.011 → 60.002 € con un mes y
  → 59.993 € con dos.
- **Cambia el caso dorado** en unos pocos euros (un mes: −9 € en P_objetivo; los demás peldaños
  bajan en la misma proporción).
- **Necesita un dato que hoy no existe:** los meses de inmovilización. Es parte del «perfil de
  fuente» (§3.2: plazos de pago por tipo de subasta) y tendría que ser un parámetro T3 nuevo por
  fuente.
- **Lo que no puede resolverse por análisis:** el coste de los depósitos de subastas **perdidas**
  es de cartera (§11.3) y no de un análisis concreto.

**Tamaño:** colchón, pequeño (M12 o M14 y la interfaz). Depósito, medio (parámetro nuevo por
fuente, M06, tests y caso dorado).

---

## E6 · VAN al coste de capital y diferencial TIR − coste de capital (opción «D»)

**Qué dice la especificación.** Nada: no hay VAN, tasa de descuento ni tasa mínima exigida, salvo
y_suelo en el rentista. P7 pide que el tiempo cueste.

**Diseño concreto.**
- **Convenciones:**
  - **Tasa:** `cc` es **tasa efectiva anual**, convertida a mensual con `r = (1+cc)^(1/12) − 1`.
    Es la misma convención con la que `_tir_anual` anualiza la TIR (`m11_rentabilidad.py:69-86`),
    así que **VAN = 0 exactamente a cc = TIR**, y el diferencial y el VAN cuentan la misma
    historia.
  - **Escenario y precio:** los de la TIR, escenario base a P_objetivo (`pipeline.py:90-91`), con
    el mismo vector de flujos (`_flujos_detallados`). Ningún supuesto nuevo.
  - **Diferencial:** `TIR − cc`, en puntos porcentuales.
- **Ficheros:**
  - `app/engine/contracts.py`: `RentabilidadResultado` gana `van_coste_capital: float | None` y
    `diferencial_tir_coste_capital: float | None`, con `None` por defecto (resultados antiguos).
  - `app/engine/modules/m11_rentabilidad.py::evaluar`: ya recibe `params` y tiene los flujos; son
    unas pocas líneas.
  - `app/engine/modules/m14_informe.py`: dos filas en la página de decisión y en §7, con `pct` y
    `eur` de `formato.py`.
  - `app/services/parametros_simulables_service.py`: añadir los dos campos al resumen comparado.
  - `app/parametros/catalogo.py`: la advertencia y el impacto de `capital.coste_capital_anual`
    deben decir que el parámetro también afecta al VAN (hoy dicen «no entra en el ROI ni en la
    TIR», que seguiría siendo cierto). El campo `modulo` es `Literal["M12","M13"]`: añadir
    «M11» o dejarlo en M12.
  - Frontend: `lib/types.ts`, `components/resultado.tsx` (métricas) y la comparación; `null` en
    resultados antiguos.
  - Especificación §7.7 y un ADR con las convenciones.
- **Tests:**
  - VAN(cc = 0) = beneficio base.
  - VAN decreciente en cc.
  - VAN(cc = TIR) ≈ 0.
  - Valores fijos en el §19.
  - `None` en un resultado antiguo.
  - La guarda de 5G.4 sigue intacta (ningún valor previo cambia).

**Impacto medido** (caso §19, escenario base a P_objetivo; con hipoteca, igual, por H1 y H2):

| Coste de capital | VAN | TIR − coste de capital |
|---|---|---|
| 0 | 35.349 € (= beneficio base) | 33,87 pp |
| 0,015 | 33.230 € | 32,37 pp |
| 0,03 | 31.180 € | 30,87 pp |
| 0,06 | 27.269 € | 27,87 pp |
| 0,10 | 22.417 € | 23,87 pp |
| 0,15 | 16.871 € | 18,87 pp |

**Lectura.** A 1,5 % el VAN baja 2.119 € respecto al beneficio, mientras que el precio límite
descuenta 3.659 €. No es contradictorio: miden cosas distintas (P_objetivo con calendario real
frente a P_max con toda la inversión a P80). Pero conviene que el informe lo explique si se
muestran juntos.

**¿Cambia el caso dorado?** **No**, si el VAN es informativo y no entra en el ICO ni en el
semáforo. Los análisis nuevos traerán dos campos más.

**Tamaño:** medio-pequeño.

---

## E8 · Hallazgo añadido: la utilidad de rentabilidad del ICO no depende de la operación

Sale de H2 y no estaba en el encargo, pero condiciona la 5H.

**Qué dice la especificación** (§8.5): rentabilidad, peso 25, «u = 0 si ROI_a ≤ ½·m_a_min; u = 60
en m_a_objetivo; u = 100 en ≥ 1,6·m_a_objetivo», con m_a el margen anualizado exigido al perfil.
No dice a qué precio se evalúa el ROI. §19 lo evalúa a P_objetivo y da «rentabilidad 15,0», que
es exactamente 60 × 0,25.

**Qué hace el código** (`m12_decision.py:167-178`): ROI anualizado a P_objetivo (H2), comparado
con los márgenes del perfil **sin** el ajuste de riesgo `mult_m`.

**Impacto medido** (caso §19):

| Cambio | Aportación de rentabilidad al ICO | ICO |
|---|---|---|
| VS × 0,8 (operación mucho peor) | 15,0 | 64 |
| VS × 1,0 | 15,0 | 64 |
| VS × 1,2 (operación mucho mejor) | 15,0 | 64 |
| Banda de riesgo «bajo» (mult_m 0,90) | 12,74 | 62 |
| Banda «medio» (mult_m 1,00) | 15,0 | 64 |
| Banda «alto» (mult_m 1,20) | 18,3 | 68 |
| Banda «muy alto» (mult_m 1,45) | 22,42 | 72 |

- **Un cuarto del ICO es constante** para una banda y un plazo dados: no distingue una operación
  buena de una mala.
- **Premia el riesgo:** a más riesgo, más margen exigido, más ROI a P_objetivo y más ICO. Va en
  contra de P6 y del espíritu de §8.

**Propuesta para decidir en la 5H.** Evaluar la rentabilidad del ICO al **precio de adjudicación
esperado** (M13, §11.1), que sí depende de la operación y de la competencia. En el §19,
P_adj = 63.840 € daría ROI ≈ 21,5 % y ROI anualizado ≈ 19,7 % (cálculo directo con
I(P) = P·1,064 + 77.544). Otra opción es comparar con los márgenes **ajustados** a riesgo.
Cualquiera de las dos cambia el ICO y, potencialmente, el semáforo de muchos análisis.

**¿Cambia el caso dorado?** **Sí** (ICO del §19 y quizá su semáforo). Necesita decisión de
producto y ADR.

**Tamaño:** medio.

---

## E7 · Orden recomendado para la 5H

### Primero, lo que NO cambia el caso dorado

1. **E6 · VAN y diferencial TIR − coste de capital.** Informativo, sin tocar ningún valor
   existente. Completa ADR-0016 (opción «D»).
2. **E1 · D5:** coste de capital solo sobre el capital propio con hipoteca. Ya decidido. Solo
   cambia análisis con hipoteca.
3. **E4 · Perfil rentista según §9.2.** Necesita decisión sobre si se conserva la cota de venta.
   Solo cambia rentistas con coste de capital > 4,16 %.
4. **E5 · Colchón de plazo:** salida nueva del informe. Necesita decidir si va con el beneficio
   base o el pesimista.
5. **E2 (a) · Documentar en §9.1 la fórmula actual del coste de capital**, y H3: regenerar el §19
   de la especificación con las cifras del motor. Solo documentación.

### Después, lo que SÍ cambia el caso dorado (cada uno con su ADR y su actualización explícita de guardas)

6. **E3 · Calendario de la TIR con los plazos reales de M06.** TIR del §19 33,87 → 34,73 %; ningún
   precio ni el semáforo cambian. ROI anualizado como cifra principal.
7. **E2 (b) · Nueva definición de P_límite** (beneficio estresado = coste de oportunidad del
   capital propio). P_límite del §19 −36 €; integra D5. Si se adopta, sustituye al punto 2.
8. **E5 · Coste del depósito en C_F.** −9 € por mes de inmovilización; necesita un parámetro
   nuevo por fuente.
9. **E8 · Rentabilidad del ICO** evaluada al precio de adjudicación esperado o con márgenes
   ajustados. Es el de mayor impacto: mueve el ICO y quizá el semáforo. Decisión de producto
   antes de tocar código.

**Prerrequisito de todos:** la regla 8 de `CLAUDE.md` (no tocar `app/engine/` sin indicación
expresa) exige que la 5H lo autorice punto por punto. Los que cambian el caso dorado deben llevar
la actualización de sus guardas de forma explícita, como hizo la 5G.4-B con
`FORMATO_5G4B`, nunca regenerando valores a ciegas.

## Reproducir las medidas

Los scripts (fuera del repositorio) importan `app.engine.pipeline.ejecutar_analisis` con la
entrada de `tests/test_golden_caso19.py`, aplican overrides con `Parametros.con_overrides` y, para
la TIR y el VAN, reutilizan `m11_rentabilidad._flujos_detallados` y `_tir_anual` sobre el
escenario base. No escriben en ninguna base. Cualquier cifra de este documento se obtiene en
segundos con el motor en memoria.
