# Informe de análisis SEIS

## 1 · Página de decisión

# 🟡 AMARILLO

| Métrica | Valor |
|---|---|
| **ICO** (calidad de la oportunidad) | **64 / 100** |
| **RA** (riesgo agregado) | 40 / 100 (medio) |
| ICI (calidad de la información) | 63 / 100 |
| ICU (calidad de ubicación) | 66 / 100 |
| **Precio ideal** | 51.317 € |
| **Precio objetivo** | 60.011 € |
| **Precio máximo recomendado** | 68.731 € |
| **Precio límite absoluto** | 80.022 € — infranqueable |
| ROI base (a P objetivo) | 25.0% (22.9% anualizado) |
| TIR anual | 33.9% |
| Margen de seguridad (caída de VS soportable) | 24.8% |
| Valor esperado (3 escenarios) | 32.361 € |
| P. adjudicación esperado · RVC | 63.840 € · **1.08** (alcanzable) |

**Razones principales:** ICO 64 en banda 60–74 o límites de Verde no alcanzados

**Condiciones (si Naranja/Amarillo):**
- Judicial: depósito del 5% y pago del remate en plazo legal sin condición suspensiva; cesión de remate solo por el ejecutante (§3.2)
- Solicitar certificado de deuda de la comunidad antes de la puja (deuda estimada al alza mientras tanto, P5)
- Verificar la situación posesoria in situ antes de pujar; dotar provisión de desalojo P80

**Vetos:**
- (ninguno)

## 2 · Activo y subasta
Vivienda de 82 m² en Ciudad Ejemplo (Ejemplo), estado malo. Subasta judicial_boe, valor de subasta 152.000 €, depósito 5%. Ocupación declarada: precario.

## 3 · Valoración
Método comparables_ajustados con 7 comparables (CV 5.3%, confianza 76%). VM actual 135.379 € · VS de salida 188.026 € (2.293 €/m²) · δ_v aplicado 6.0% ⇒ **VS prudente 176.744 €**.

## 4 · Mercado y ubicación
ICU 66 (macro 73 · micro 62). Tendencia +3.0 %/a · DOM venta 75 d · DOM alquiler 25 d · Potencial de revalorización 58/100.

## 5 · Plan de obra y costes
Reforma nivel **media**: 50.053 € (P50) / 61.064 € (P80), 3 meses de obra. c_v = 6.40% (ITP). Plazo total 13 m (P50) / 18 m (P80). Contingencia 10%.

| Partida C_F (P50) | Importe |
|---|---|
| reforma | 50.053 € |
| ocupacion_desalojo | 6.500 € |
| atrasos_comunidad_ibi | 2.432 € |
| adquisicion_fija | 2.700 € |
| tenencia | 3.120 € |
| comercializacion | 6.841 € |
| contingencia | 5.898 € |
| cargas_subsistentes | 0 € |
| plusvalia_municipal | 0 € |
| **Total C_F P50 / P80** | **77.544 € / 87.708 €** |

## 6 · Riesgos (matriz P×I, §7)
| Dimensión | P×I | Nivel | Mitigación |
|---|---|---|---|
| juridico | 2×3 = 6 | medio | — |
| documental | 2×3 = 6 | medio | Subsanar: posesion_verificada; Subsanar: fotos_interior_o_visita; Subsanar: cert_comunidad; Subsanar: ite_cee |
| ocupacion | 4×3 = 12 | alto | — |
| urbanistico | 2×2 = 4 | bajo | — |
| tecnico | 3×3 = 9 | medio | Visita interior (o con cerrajero tras adjudicación) para cerrar presupuesto P50 |
| financiero | 1×2 = 2 | bajo | — |
| comercial | 2×3 = 6 | medio | — |
| liquidez | 2×2 = 4 | bajo | — |
| mercado | 2×3 = 6 | medio | — |

Riesgo agregado **RA 40** (banda medio, dominancia: una_alta).

## 7 · Análisis financiero (a precio objetivo 60.011 €)
| Escenario | Prob. | VS | Coste total | Beneficio | ROI | ROI anual | Plazo |
|---|---|---|---|---|---|---|---|
| pesimista | 25% | 160.837 € | 151.559 € | 9.278 € | 6.1% | 4.0% | 18 m |
| base | 55% | 176.744 € | 141.396 € | 35.349 € | 25.0% | 22.9% | 13 m |
| optimista | 20% | 186.996 € | 133.996 € | 53.000 € | 39.6% | 43.6% | 11 m |

## 8 · Estrategia de puja
Ratio histórico del segmento: 42% sobre valor de subasta.
- Cargar límites en la interfaz antes de abrir la puja: objetivo 60,011 € · máximo 68,731 € · límite absoluto 80,022 € (infranqueable por software)
- Pujar siempre el tramo mínimo; sin pujas psicológicas redondas
- Entrar tarde con límites precargados: la extensión automática del cierre neutraliza el sniping; la ventaja es la disciplina
- Depósito requerido: 7,600 € (5% del valor de subasta)
- Si aparece información nueva durante la subasta, re-análisis exprés; si el semáforo cae, retirada

**Riesgo de ejecución del proceso:**
- Suspensión/sobreseimiento del procedimiento: capital del depósito inmovilizado sin operación
- Pago del remate en plazo legal sin condición suspensiva de financiación (incumplir ⇒ pérdida del depósito)
- Cargas descubiertas entre puja y pago: mitigación con nota simple ≤ 5 días antes del cierre
- Cesión de remate solo disponible para el ejecutante: la estructura compradora final debe pujar directamente

## 9 · Checklist previo a la puja — bloqueantes pendientes
- [ ] **[B]** Nota simple actualizada ≤ 5 días antes del cierre, cotejada con el edicto — _Antigüedad declarada: 10 días_
- [ ] **[B]** Situación posesoria verificada según árbol §8.7.2 — _Estado declarado: precario_
- [ ] **[B]** Depósito disponible y transferido en plazo — _7.600 €_

## 10 · Trazabilidad
Reglas disparadas (versión reglas 2026.07 · parámetros 2026.07):
- `SEM-OCU-02` v2026.07 (semaforo)
- `SEM-DOC-01` v2026.07 (semaforo)
- `SEM-EJEC-01` v2026.07 (puja)

---
*Informe generado por SEIS. Los parámetros legales y fiscales aplicados son datos versionados que deben validarse con asesoría profesional (§20 de la especificación). La decisión final de puja corresponde al comité de inversión.*
