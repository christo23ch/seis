"""Contratos tipados entre módulos (§4.5). Toda frontera se valida aquí (P8)."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Tipologia = Literal["vivienda", "garaje", "trastero", "local", "oficina", "nave",
                    "suelo_urbano", "suelo_rustico", "hotel", "singular"]
EstadoConservacion = Literal["ruina", "malo", "regular", "bueno", "reformado"]
# Fase 5I-D (ADR-0020): el inmueble analizado admite además «desconocido» («No
# consta»); el motor usa entonces el estado de `conservacion.desconocido_usa`. Los
# comparables NO: un testigo sin estado no se puede normalizar.
EstadoActivo = Literal["ruina", "malo", "regular", "bueno", "reformado", "desconocido"]
EstadoOcupacion = Literal["desconocida", "vacio", "propietario", "precario",
                          "arrendado_posterior", "arrendado_anterior", "renta_antigua"]
Semaforo = Literal["verde", "amarillo", "naranja", "rojo"]
NivelRiesgo = Literal["bajo", "medio", "alto", "critico"]
Dimension = Literal["juridico", "documental", "ocupacion", "urbanistico", "tecnico",
                    "financiero", "comercial", "liquidez", "mercado"]
# Fase 5J-1 (ADR-0022): datos del procedimiento de subasta, solo para resultados
# informativos (`app/engine/procedimiento.py`); ningún módulo M01-M14 los lee.
Procedimiento = Literal["judicial", "aeat", "tgss", "notarial", "extrajudicial", "concursal",
                        "no_aplica"]
# Cuándo se inició el procedimiento judicial respecto de la LO 1/2025 (3-4-2025).
RegimenJudicial = Literal["posterior", "anterior", "no_se"]
SiNoConsta = Literal["si", "no", "no_consta"]


# ────────────────────────── ENTRADA (pasos del asistente) ──────────────────────────
class ActivoInput(BaseModel):
    tipologia: Tipologia = "vivienda"
    superficie_m2: float = Field(gt=0)
    estado_conservacion: EstadoActivo = "regular"
    anio_construccion: int | None = None
    direccion: str | None = None
    municipio: str = ""
    provincia: str = ""
    ccaa: str = "madrid"
    lat: float | None = None
    lng: float | None = None
    ref_catastral: str | None = None
    finca_registral: str | None = None
    es_vivienda_habitual: bool = False
    # Fase 5J-1: la misma pregunta con «No consta». Solo la lee `procedimiento.py`;
    # el booleano de arriba sigue alimentando el hecho de M01 sin cambios. `None`
    # (entradas anteriores a 5J-1) ⇒ «si» si el booleano es verdadero, «no_consta» si
    # no: un `False` antiguo no distingue «no» de «no marcado» (P4).
    vivienda_habitual_ejecutado: SiNoConsta | None = None
    vpo: bool = False
    vpo_precio_max_legal: float | None = None
    atributos: dict = Field(default_factory=dict)


class SubastaInput(BaseModel):
    fuente: str = "judicial_boe"
    valor_subasta: float = Field(gt=0)                 # VT
    puja_minima: float | None = None
    tramo: float | None = None
    deposito_pct: float = 0.05
    # Fase 5I-C: importe del depósito tal como se escribió, si se dio en euros. Solo
    # se conserva para trazabilidad, en la entrada guardada del análisis (no en la
    # tabla `subasta`): el formulario lo convierte a `deposito_pct` y NINGÚN módulo
    # lo lee (`tests/test_deposito_importe_5i.py` lo vigila).
    deposito_importe: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    fecha_cierre: date | None = None
    horas_hasta_cierre: float | None = None            # si se conoce con precisión
    subastas_desiertas_previas: int = 0
    identificador_externo: str | None = None
    url: str | None = None
    # Fase 5J-1 (ADR-0022): solo para resultados informativos. `procedimiento=None`
    # ⇒ se deduce de la fuente (`procedimiento.deducido_de_fuente`) y se avisa.
    procedimiento: Procedimiento | None = None
    regimen_judicial: RegimenJudicial = "no_se"
    cantidad_reclamada: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class CargaInput(BaseModel):
    tipo: str = "embargo"
    importe: float | None = None
    es_anterior: bool = False
    se_purga: bool = True
    verificada: bool = False
    prohibicion_disponer: bool = False
    condicion_resolutoria: bool = False


class OcupacionInput(BaseModel):
    estado: EstadoOcupacion = "desconocida"
    renta_mensual: float | None = None
    fecha_contrato: date | None = None


class DocumentosInput(BaseModel):
    """Checklist documental que alimenta el ICI (§6.2)."""
    nota_simple: bool = False
    nota_simple_dias: int | None = None
    cert_cargas: bool = False
    posesion_verificada: bool = False
    avaluo: bool = False
    fotos_interior_o_visita: bool = False
    fotos_exterior: bool = False
    cert_comunidad: bool = False
    recibo_ibi: bool = False
    ite_cee: bool = False
    catastro_conciliado: bool = False
    inconsistencias: list[str] = Field(default_factory=list)   # códigos §6.2


class ComparableInput(BaseModel):
    precio_m2: float = Field(gt=0)
    estado: EstadoConservacion = "reformado"
    origen: Literal["portal_oferta", "testigo", "notarial", "registro"] = "testigo"
    # Fase 5I.1-A: no negativa y finita. M03 pondera con 1/(1 + meses/6): con −3 el
    # testigo pesaba el doble que uno de hoy, con −6 la API daba 500 (división por cero)
    # y con `inf` pesaba 0 (todos los testigos con `inf` ⇒ suma de pesos 0).
    meses_antiguedad: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    superficie_m2: float | None = None


class ZonaMacroInput(BaseModel):
    tendencia_5a_pct: float = 0.0            # %/año medio
    stock_meses: float = 8.0
    dom_venta_dias: float = 120.0
    dom_alquiler_dias: float = 40.0
    crecimiento_pobl_5a_pct: float = 0.0
    renta_hogar: float = 30000.0
    y_zona_pct: float = 5.5                  # yield neta de referencia de la zona (rentista)


class ZonaMicroInput(BaseModel):
    """Puntuaciones 0–100 por indicador micro (§6.4). Manual en F1; APIs en F2."""
    transporte: float = 50
    seguridad: float = 50
    sanidad: float = 50
    educacion: float = 50
    comercio: float = 50
    zonas_verdes: float = 50
    pipeline_urbanistico: float = 50
    potencial_transformacion: float = 50
    entorno_construido: float = 50


class ZonaInput(BaseModel):
    macro: ZonaMacroInput = Field(default_factory=ZonaMacroInput)
    micro: ZonaMicroInput = Field(default_factory=ZonaMicroInput)
    precio_m2_p85: float | None = None       # para regla comercial "producto caro para su calle"


class ReformaInput(BaseModel):
    nivel_override: Literal["ninguna", "refresco", "ligera", "media", "integral", "estructural"] | None = None
    visita_interior: bool = False
    k_provincia: float = 1.0
    coste_m2_override: float | None = None
    partidas_extra: float = 0.0              # derramas, amianto... importe conocido


class UrbanisticoInput(BaseModel):
    uso_compatible: bool = True
    fuera_ordenacion: bool = False
    orden_demolicion: bool = False
    suelo_protegido: bool = False
    cargas_urbanizacion: float = 0.0
    servidumbres_incompatibles: bool = False
    zona_inundable_alta: bool = False


class CostesInput(BaseModel):
    regimen_fiscal: Literal["auto", "itp", "iva"] = "auto"
    transmitente_empresario: bool = False
    primera_entrega: bool = False
    comprador_deduce_iva: bool = False
    itp_tipo_override: float | None = None
    # Base imponible del ITP: es el MAYOR de (valor de referencia, valor declarado,
    # precio pagado) —art. 10 TRLITPAJD—, no la puja. Sin ninguno de los dos, el
    # motor usa la puja como SUELO y lo declara como carencia: no lo estima.
    valor_referencia_catastral: float | None = Field(default=None, gt=0)
    valor_declarado: float | None = Field(default=None, gt=0)
    atrasos_comunidad_ibi: float | None = None    # None ⇒ estimación prudente al alza (P5)
    adquisicion_fija_override: float | None = None
    tenencia_mensual: float | None = None
    plusvalia_municipal_estimada: float = 0.0


class FinanciacionInput(BaseModel):
    tipo: Literal["cash", "hipoteca"] = "cash"
    preaprobada: bool = False
    ltv: float = 0.0
    interes_anual_pct: float = 3.5


class RentistaInput(BaseModel):
    renta_mensual_estimada: float = 0.0
    vacancia_pct: float = 5.0
    ibi_anual: float = 0.0
    comunidad_mensual: float = 0.0
    seguro_anual: float = 300.0
    mantenimiento_pct_renta: float = 5.0
    gestion_pct_renta: float = 0.0


class AnalisisInput(BaseModel):
    """Entrada completa del asistente (pasos 1–10)."""
    perfil: str = "flip_integral"
    activo: ActivoInput
    subasta: SubastaInput
    cargas: list[CargaInput] = Field(default_factory=list)
    ocupacion: OcupacionInput = Field(default_factory=OcupacionInput)
    documentos: DocumentosInput = Field(default_factory=DocumentosInput)
    comparables: list[ComparableInput] = Field(default_factory=list)
    zona: ZonaInput = Field(default_factory=ZonaInput)
    reforma: ReformaInput = Field(default_factory=ReformaInput)
    urbanistico: UrbanisticoInput = Field(default_factory=UrbanisticoInput)
    costes: CostesInput = Field(default_factory=CostesInput)
    financiacion: FinanciacionInput = Field(default_factory=FinanciacionInput)
    rentista: RentistaInput | None = None

    @model_validator(mode="after")
    def _coherencia(self) -> "AnalisisInput":
        if self.perfil == "rentista" and self.rentista is None:
            self.rentista = RentistaInput()
        return self


# ────────────────────────── SALIDAS DE MÓDULOS ──────────────────────────
class PenalizacionICI(BaseModel):
    """Fase 5J-2a: penalización del ICI estructurada (el texto sigue en `penalizaciones`)."""
    codigo: str
    puntos: float


class ICIResultado(BaseModel):
    ici: int
    desglose: dict[str, float]
    carencias: list[str]
    penalizaciones: list[str]
    # Fase 5J-2a (informativo, opcional): las mismas penalizaciones con sus puntos.
    penalizaciones_detalle: list[PenalizacionICI] | None = None
    efecto_delta_v_pp: float
    efecto_contingencia_pp: float
    techo_semaforo: Semaforo | None


class ComparableValoradoOut(BaseModel):
    """Fase 4: intermedios de M03 para un comparable — expone, sin recalcular,
    lo que el bucle de `m03_valoracion.ejecutar` ya produce y hoy descarta.
    En el mismo orden que `AnalisisInput.comparables` (posición i ⇔ comparables[i])."""
    precio_ajustado_m2: float   # variable `precio` tras los ajustes de origen/temporal
    normalizado_m2: float       # `normalizados[i]` = precio_ajustado_m2 / k_estado[estado]
    peso: float                 # `pesos[i]`, peso de frescura usado en la mediana ponderada


class ValoracionResultado(BaseModel):
    vm: float
    vm_rango: tuple[float, float]
    vs: float
    vs_rango: tuple[float, float]
    vs_m2: float
    metodo: str
    n_comparables: int
    dispersion_cv: float
    confianza: float
    hechos: list[str] = Field(default_factory=list)
    # Fase 4 — trazabilidad de valoración: expone intermedios que M03 ya calcula
    # y hoy descarta. No participan en ningún cálculo; solo se leen al final.
    detalle_comparables: list[ComparableValoradoOut] = Field(default_factory=list)
    k_estado_activo: float | None = None          # k_estado[activo.estado_conservacion]
    ratio_sanidad: float | None = None             # variable `ratio` (VT/VM)
    vs_antes_de_capitalizacion: float | None = None  # `vs` justo antes del override rentista
    vs_capitalizacion: float | None = None           # `vs_cap` que lo sustituyó


class ICUResultado(BaseModel):
    icu: int
    macro_score: float
    micro_score: float
    desglose: dict[str, float]
    potencial_revalorizacion: int
    dom_venta_dias: float
    dom_alquiler_dias: float
    tendencia_5a_pct: float
    y_zona_pct: float


class ReformaResultado(BaseModel):
    nivel: str
    obra_p50: float
    obra_p80: float
    tecnicos_licencia_p50: float
    tecnicos_licencia_p80: float
    total_p50: float
    total_p80: float
    plazo_obra_meses: float
    partidas: dict[str, float]


class CostesResultado(BaseModel):
    c_v: float                                # proporcional a P
    c_v_desglose: dict[str, float]
    c_f_p50: float
    c_f_p80: float
    desglose_p50: dict[str, float]
    desglose_p80: dict[str, float]
    contingencia_pct: float
    tenencia_mensual: float
    plazo_meses_p50: float
    plazo_meses_p80: float
    regimen_fiscal: str
    tipo_impositivo: float
    # Suelo de la base imponible y tipo al que se le aplica (0.0 ⇒ el impuesto es
    # proporcional a P, como antes de la corrección; ver app/engine/fiscal.py).
    base_fiscal_minima: float = 0.0
    base_fiscal_origen: str = "precio_pagado"
    tipo_base_minima: float = 0.0
    # Fase 5J-2a (informativo, opcional): composición del plazo P50 (meses de ocupación,
    # obra y comercialización) y el multiplicador que da el P80.
    plazo_desglose: dict[str, float] | None = None


class RiesgoOut(BaseModel):
    dimension: Dimension
    probabilidad: int
    impacto: int
    score: int
    nivel: NivelRiesgo
    mitigable: bool = True
    condiciones: list[str] = Field(default_factory=list)
    evidencias: list[str] = Field(default_factory=list)
    # Fase 5J-2a (informativo, opcional): las mismas evidencias como {dato, valor}.
    evidencias_detalle: list["EvidenciaOut"] | None = None


class EvidenciaOut(BaseModel):
    """Fase 5J-2a: una evidencia de riesgo estructurada. `valor` None ⇒ marca sin valor."""
    dato: str
    valor: str | None = None


class RAResultado(BaseModel):
    ra: int
    ra_base: float
    banda: Literal["bajo", "medio", "alto", "muy_alto", "critico"]
    dominancia_aplicada: str | None
    dimensiones: list[RiesgoOut]
    # Fase 5J-2a (informativo, opcional): pesos de agregación usados y suelo de la
    # dominancia aplicada. RA = máx(RA base, suelo), redondeado y ≤ 100.
    pesos: dict[str, float] | None = None
    suelo_dominancia: float | None = None


class EscenarioOut(BaseModel):
    nombre: Literal["pesimista", "base", "optimista"]
    probabilidad: float
    vs: float
    coste_total: float
    beneficio: float
    roi: float
    roi_anualizado: float
    plazo_meses: float


class RentabilidadResultado(BaseModel):
    precio_evaluado: float
    inversion_total: float
    beneficio: float
    roi: float
    roi_anualizado: float
    tir_anual: float
    valor_esperado: float
    escenarios: list[EscenarioOut]
    y_neta: float | None = None
    dscr: float | None = None
    cash_on_cash: float | None = None
    # Fase 5H.1-A (ADR-0017): informativos, con los mismos flujos que la TIR. `None` en
    # resultados anteriores a la fase. No entran en el ICO, el semáforo ni la escalera.
    van_coste_capital: float | None = None              # € al coste de capital
    diferencial_tir_coste_capital: float | None = None  # TIR − coste de capital, en puntos
    # Fase 5J-2a (informativo, opcional): flujos mensuales del escenario base con que se
    # calculan la TIR y el VAN (índice = mes; el 0 es la compra), y la tasa del VAN.
    flujos_base: list[float] | None = None
    tasa_van: float | None = None


class EscaleraPrecios(BaseModel):
    p_ideal: float
    p_objetivo: float
    p_max: float
    p_limite: float
    degenerada: bool = False
    detalle: dict[str, float] = Field(default_factory=dict)
    # Fase 5J-2a (informativo, opcional): tramo fiscal con que se resolvió cada precio
    # (`unico`, `bajo`, `alto` o `frontera`; ver `fiscal.resolver_con_tramo`).
    tramos_fiscales: dict[str, str] | None = None


class VetoOut(BaseModel):
    codigo: str
    motivo: str
    dimension: str | None = None
    subsanable_con: str | None = None


class ReglaDisparadaOut(BaseModel):
    codigo: str
    version: str
    categoria: str
    efecto: dict
    evidencias: list[str] = Field(default_factory=list)


class AjusteRatio(BaseModel):
    """Fase 5J-2a: un ajuste aplicado al ratio de adjudicación (en tanto por uno)."""
    concepto: str
    ajuste: float


class PujaResultado(BaseModel):
    p_adj_esperado: float
    ratio_base: float          # el ratio YA ajustado y acotado (nombre histórico)
    rvc: float
    banda_rvc: str
    plan: list[str]
    riesgo_ejecucion: list[str]
    # Fase 5J-2a (informativo, opcional): ratio del segmento antes de ajustes, ajustes
    # aplicados y si el resultado se acotó a [0,10; 1,10].
    ratio_segmento: float | None = None
    ajustes_ratio: list[AjusteRatio] | None = None
    ratio_acotado: bool | None = None


class ColchonDetalle(BaseModel):
    """Fase 5J-2a: operandos del colchón de plazo a P_objetivo (`m11.colchon_plazo`)."""
    beneficio: float
    inversion: float
    tenencia_mensual: float
    intereses_mensuales: float
    coste_capital_mensual: float
    coste_mensual: float


class DatoLegal(BaseModel):
    """Fase 5J-1: un dato legal aplicado, con su origen (parámetro T3)."""
    dato: str
    valor: float | None
    articulo: str
    estado: Literal["confirmado", "sin_confirmar"]
    nota: str | None = None
    # Fase 5J-2b: valor descriptivo de un dato que no es una cifra (la forma de puja).
    texto: str | None = None


class AvisoAprobacion(BaseModel):
    """Fase 5J-3 (ADR-0027): la puja máxima recomendada cae por debajo de la aprobación segura
    del remate y su aprobación ya no es automática. Informativo: no cambia ningún número; añade
    una condición y, solo en las franjas «discrecional» y «bajo_suelo», un techo naranja al
    semáforo (nunca un veto)."""
    franja: Literal["sujeta_a_mejora", "discrecional", "bajo_suelo"]
    techo_naranja: bool = False                       # decisión del responsable: no en «sujeta_a_mejora»
    p_max: float
    p_max_pct: float                                  # sobre el valor de subasta
    puja_aprobacion_segura: float
    umbral_aprobacion_segura_pct: float
    puja_minima_aprobable: float | None = None
    umbral_aprobacion_pct: float | None = None
    suelo_absoluto: float | None = None
    suelo_absoluto_pct: float | None = None
    vivienda_habitual_asumida: bool = False
    regimen_asumido: bool = False
    titulo: str
    riesgo: str
    condicion: str
    alcance: str = ""                                 # qué hace con el semáforo, redactado por el motor
    umbrales: list[str] = []                          # los umbrales aplicados, redactados (informe e interfaz)
    datos_legales: list[DatoLegal] = []               # los umbrales aplicados, con su estado


class ProcedimientoResultado(BaseModel):
    """Fase 5J-1 (ADR-0022): datos del procedimiento de subasta. INFORMATIVO: no
    alimenta la escalera, el RVC, el semáforo ni la rentabilidad. Los importes
    `None` son DATO AUSENTE (P4): la norma no da un valor fiable o falta un dato."""
    procedimiento: Procedimiento
    procedimiento_deducido: bool               # no lo dijo el alta: salió de la fuente
    regimen: str | None                        # clave de `procedimiento.regimenes`
    regimen_nombre: str | None
    regimen_asumido: bool                      # judicial con «No sé»: se aplica el desfavorable
    vivienda_habitual: SiNoConsta
    vivienda_habitual_asumida: bool            # «No consta» ⇒ se aplica la regla de vivienda habitual
    valor_subasta: float
    cantidad_reclamada: float | None
    deposito_pct: float | None
    deposito_eur: float | None
    deposito_declarado_pct: float
    capital_para_pujar: float | None           # lo que hay que consignar para poder pujar
    plazo_pago_dias: int | None
    plazo_pago_unidad: str | None              # naturales | habiles
    meses_inmovilizacion: float | None
    # Fase 5J-2b (ADR-0026): meses que se suman al plazo de la operación. Si la norma no los da,
    # los de `procedimiento.meses_inmovilizacion_si_no_consta` (asumidos = True, sin base legal);
    # si no consta el régimen judicial, los del régimen judicial más largo.
    meses_inmovilizacion_aplicados: float | None = None
    meses_inmovilizacion_asumidos: bool | None = None
    # Fase 5J-2b (ADR-0025): cómo se puja en este régimen; decide la táctica de M13.
    forma_puja: str | None = None
    umbral_aprobacion_pct: float | None        # umbral aplicable a la puja mínima aprobable
    puja_minima_aprobable: float | None        # sin depender de la decisión de la autoridad
    umbral_aprobacion_segura_pct: float | None
    puja_aprobacion_segura: float | None
    suelo_absoluto_pct: float | None           # por debajo, prohibido (vivienda habitual) o no admitido
    suelo_absoluto: float | None
    datos_legales: list[DatoLegal]
    avisos: list[str]
    aviso_orientativo: str
    # Fase 5J-3 (revisión, M1): la norma exige SUPERAR la mínima aprobable, no igualarla
    # (régimen anterior: «supere el 50 %»). Falso si la rebaja la deuda («cubra») o la vivienda habitual.
    puja_minima_estricta: bool | None = None
    # Fase 5J-3 (ADR-0027): solo si la puja máxima no alcanza la aprobación segura.
    aviso_aprobacion: AvisoAprobacion | None = None


class ChecklistItem(BaseModel):
    grupo: str
    orden: int
    texto: str
    bloqueante: bool
    estado: Literal["ok", "pendiente", "no_aplica"]
    detalle: str | None = None


class DecisionFinal(BaseModel):
    semaforo: Semaforo
    ico: int
    ico_desglose: dict[str, float]
    ra: int
    ici: int
    icu: int
    precios: EscaleraPrecios
    margen_seguridad_valor: float
    rvc: float
    p_adj_esperado: float
    vetos: list[VetoOut]
    condiciones: list[str]
    techos_aplicados: list[str]
    razones: list[str]
    version_reglas: str
    version_parametros: str
    # Fase 5H.1-C (§9.5, ADR-0019): meses extra hasta beneficio base cero por tenencia y
    # coste de capital, a P_objetivo y a P_max. Informativo; `None` en resultados anteriores
    # o si no hay ningún coste mensual que agote el beneficio.
    colchon_plazo_meses: float | None = None
    # Fase 5J-2a (informativo, opcional): operandos del colchón a P_objetivo.
    colchon_detalle: ColchonDetalle | None = None
    colchon_plazo_meses_p_max: float | None = None


class AnalisisResult(BaseModel):
    """Resultado íntegro del pipeline: lo que persiste el snapshot y consume el frontend."""
    decision: DecisionFinal
    ici: ICIResultado
    valoracion: ValoracionResultado
    icu: ICUResultado
    reforma: ReformaResultado
    costes: CostesResultado
    riesgos: RAResultado
    rentabilidad: RentabilidadResultado
    puja: PujaResultado
    checklist: list[ChecklistItem]
    reglas_disparadas: list[ReglaDisparadaOut]
    informe_markdown: str
    delta_v: float
    vs_prudente: float
    # Fase 5J-1 (ADR-0022): informativo; `None` en resultados anteriores a la fase.
    procedimiento: ProcedimientoResultado | None = None
