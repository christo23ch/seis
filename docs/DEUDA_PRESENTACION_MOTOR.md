# Deuda de presentación que exige tocar el motor o el backend (para la 5J-2)

**Origen:** Fase 5K (presentación), 2026-10-07. La 5K solo podía tocar `frontend/` y la
documentación; todo lo que pedía un dato que el resultado del motor no trae, o un texto que el
motor emite mal, queda aquí con el archivo donde se resuelve y el dato que falta.
**Relacionado:** `docs/INVENTARIO_PRESENTACION.md` (5J-0), que la 5K resolvió en lo que dependía
solo del frontend.

> Ninguno de estos puntos cambia una cifra: son datos que el motor ya calcula pero no **emite**, o
> textos que emite con claves internas. Aun así tocan `app/engine/`, así que necesitan la
> autorización de CLAUDE.md §6.8, y añadir campos al resultado obliga a vigilar la foto del §19
> (`tests/test_invariante_5h1.py`: añadir hojas nuevas no la rompe; cambiar las existentes, sí).

---

## Estado tras la Fase 5J-2a (2026-10-07)

| Puntos | Estado |
|---|---|
| 1-13 (datos para «Ver cálculo») | ✅ **Resueltos.** El resultado emite cada operando como campo nuevo y opcional, y «Ver cálculo» los usa (ADR-0023) |
| 14 (pesos del ICO anteriores a la 0014) | ⏸️ Sin solución posible, por diseño |
| 15-17 (textos con códigos y sin tilde) | ✅ **Resueltos en el informe y el PDF** de los análisis nuevos: M14 redacta con `app/engine/textos.py`. Los **informes oficiales ya emitidos** conservan su texto congelado. Los 7 textos de la foto del §19 (3 ítems del checklist y 4 condiciones «Subsanar: …») se redactan legibles, pero el dato no cambia (ver ADR-0023) |
| 18 (depósito del alta frente al legal) | ⏳ Pendiente: mueve cifras |
| 19-20 (catálogo global y su cobertura) | ⏳ Pendiente (backend) |
| §4 (frontend fuera de alcance) | ⏳ Pendiente |

---

## 1 · Datos que «Ver cálculo» no puede mostrar porque no viajan en el resultado

Hoy cada uno se muestra como **«Cálculo no disponible aún: falta en el resultado …»**
(`frontend/lib/calculos.ts`).

| # | Métrica | Dato que falta en el resultado | Dónde lo calcula el motor | Propuesta |
|---|---|---|---|---|
| 1 | **P_ideal** | El margen excepcional `m_exc = m_objetivo × precios.m_exc_mult` | `m12_decision.py`, `calcular_escalera` (`m_exc`) | Añadir `m_excepcional_ajustado` a `precios.detalle` |
| 2 | **P por escenario pesimista** (candidato de P_max) | `stress_mercado` de la banda de RA y `piso_pesimista_frac_i` del perfil (solo viaja `vs_pesimista` y el resultado) | `m12_decision.py`, rama `venta` (`vs_pes`, `piso`, `p_pes`) | Añadir `stress_mercado` y `piso_pesimista` a `precios.detalle` |
| 3 | **Escalera con dos tramos fiscales** (base imponible mínima) | Qué tramo resolvió cada precio (`p_bajo` / `p_alto` / frontera) y el `extra` = `t · B` | `fiscal.py`, `resolver_por_tramos`; también `sobrecoste` en `inversion` | Emitir el tramo usado por precio, o el `c_v` efectivo y el fijo extra |
| 4 | **Escalera del perfil rentista** | Los candidatos de P_max: rentabilidad exigida, DSCR estresado y cash-on-cash | `m12_decision.py`, rama `rentista` (`candidatos`) | Añadir los tres candidatos a `precios.detalle` |
| 5 | **P_límite bruto** | Se muestra como fórmula sustituida, pero el valor bruto antes del coste de capital no se emite | `m12_decision.py` (`p_lim_bruto`) | Añadir `p_limite_bruto` a `precios.detalle` |
| 6 | **RA** (riesgo agregado) | Los pesos de agregación (`riesgos.pesos`) y el suelo por dominancia aplicado | `m12_decision.py`, `agregar_ra` | Emitir los pesos usados y el suelo de dominancia en `riesgos` |
| 7 | **P_adj esperado** (y por tanto el detalle del RVC) | Los ajustes del ratio: −8 pp por subasta desierta, +6 pp si VT/VM < 0,6 y el acotado a [0,10; 1,10] | `m13_puja.py`, líneas 8-36 | Emitir `ratio_ajustado` y la lista de ajustes aplicados |
| 8 | **TIR anual** | Los flujos y sus fechas | `m11_rentabilidad.py`, `_tir_anual` | Emitir el calendario de flujos del escenario base |
| 9 | **VAN al coste de capital** | Los flujos descontados | `m11_rentabilidad.py` | Ídem (mismo calendario) |
| 10 | **Colchón de plazo** | El beneficio de partida y el coste mensual por el que se divide | `m11_rentabilidad.py`, `colchon_plazo` | Emitir ambos operandos |
| 11 | **Plazo P50 / P80** | Su composición (ocupación + obra + comercialización) | `m06_costes.py` (cálculo del plazo, ~línea 72) | Emitir el desglose del plazo |
| 12 | **Penalizaciones del ICI** | Se leen del texto «código (−N)»; no hay campo estructurado | `m02_validacion.py` (`penalizaciones`) | Emitir `{codigo, puntos}` además del texto |
| 13 | **Evidencias de riesgo** | Llegan como «clave=valor» (`ICI=63`, `nivel_reforma=media`, `DOM=75d`) | `m07`–`m10` (`evidencias`) | Emitir `{dato, valor}` estructurado |
| 14 | **Pesos del ICO de análisis anteriores a la 0014** | Sin `parametros_aplicados` no hay pesos con que se calculó; se muestran los puntos sin máximo | — (no reconstruible, ADR de la 5F.1) | Ninguna: es la consecuencia aceptada de no tener snapshot |

## 2 · Textos que el motor emite con claves internas

La 5K los hace legibles **al mostrarlos** (`frontend/lib/formulas.ts`) en la interfaz. El texto de
origen no cambia, y por eso **el PDF oficial los sigue mostrando en crudo**
(`backend/app/services/pdf_service.py` no pasa por el frontend).

| # | Texto | Dónde nace | Qué falta |
|---|---|---|---|
| 15 | Símbolos con barra baja: `C_F`, `c_v`, `δ_v` (informe), `P_max` (motivo de VETO-COMP-01), `P_ideal` (plan de puja) | `m14_informe.py` (líneas 55, 72, 104, 191, 267-272), `rules/catalogo.yaml:149`, `m13_puja.py:77` | Notación legible en origen (también llega al PDF). El de la regla exige una versión nueva de la regla |
| 16 | Claves internas: `judicial_boe`, `comparables_ajustados`, `una_alta`, `Subsanar: posesion_verificada`… | `m14_informe.py:188, 258, 279`, `m07_riesgo_juridico.py:52` | Etiquetas legibles en origen |
| 17 | **Palabras sin tilde ni barra baja**: partidas de C_F (`reforma`, `tenencia`, `comercializacion`, `contingencia`) y dimensiones de riesgo (`juridico`, `tecnico`, `urbanistico`…) en las tablas del informe | `m06_costes.py:104-111` (claves), `m14_informe.py:155, 161` | La 5K **no las traduce al mostrar** a propósito: «reforma» o «tenencia» también son palabras normales de la prosa del informe, y una sustitución ciega cambiaría frases correctas. Hay que emitir la etiqueta en origen |
| 18 | El informe y el PDF muestran el depósito del alta (5 %) y no el legal | `m13_puja.py:71`, `m14_informe.py:258` | Ver deuda de la 5J-1 (`docs/ESTADO_ACTUAL.md`) |

## 3 · Backend (sin motor)

| # | Qué | Dónde | Por qué |
|---|---|---|---|
| 19 | **Endpoint global del catálogo de parámetros** (nombres y unidades sin depender de un análisis) | `backend/app/api/conocimiento.py`, `services/parametros_simulables_service.py` | La pantalla Parámetros pide el catálogo del análisis más reciente (`frontend/lib/catalogo.ts`): sus metadatos no dependen del análisis, pero sin ningún análisis en la organización las claves se humanizan |
| 20 | El catálogo cubre solo M12 y M13 | `backend/app/parametros/catalogo.py` | El resto del árbol T3 (fiscal, costes, ICI, ICU, procedimiento…) se muestra con la clave humanizada y sin unidad |

## 4 · Frontend pendiente, fuera del alcance de la 5K

No necesitan el motor; quedan anotados para una fase de presentación posterior.

- **Motor de reglas** (`frontend/app/app/reglas/page.tsx`): condiciones como código (`hecho op valor`) y el editor en JSON.
- **Simulaciones** (`components/simulaciones/editor.tsx`, `comparacion.tsx`): valores en bruto (`0.015`) y estructuras en JSON plegado (deudas 3 y 4 de `ESTADO_ACTUAL.md`).
- **Informes oficiales, «Cambios aplicados»** (`components/informes/informes-oficiales.tsx`, `Valor`): clave cruda y JSON plegado.
