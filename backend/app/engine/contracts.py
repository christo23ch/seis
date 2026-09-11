"""Contratos tipados entre módulos (§4.5). Toda frontera se valida aquí (P8)."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Tipologia = Literal["vivienda", "garaje", "trastero", "local", "oficina", "nave",
                    "suelo_urbano", "suelo_rustico", "hotel", "singular"]
EstadoConservacion = Literal["ruina", "malo", "regular", "bueno", "reformado"]
EstadoOcupacion = Literal["desconocida", "vacio", "propietario", "precario",
                          "arrendado_posterior", "arrendado_anterior", "renta_antigua"]
Semaforo = Literal["verde", "amarillo", "naranja", "rojo"]
NivelRiesgo = Literal["bajo", "medio", "alto", "critico"]
Dimension = Literal["juridico", "documental", "ocupacion", "urbanistico", "tecnico",
                    "financiero", "comercial", "liquidez", "mercado"]


# ────────────────────────── ENTRADA (pasos del asistente) ──────────────────────────
class ActivoInput(BaseModel):
    tipologia: Tipologia = "vivienda"
    superficie_m2: float = Field(gt=0)
    estado_conservacion: EstadoConservacion = "regular"
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
    vpo: bool = False
    vpo_precio_max_legal: float | None = None
    atributos: dict = Field(default_factory=dict)


class SubastaInput(BaseModel):
    fuente: str = "judicial_boe"
    valor_subasta: float = Field(gt=0)                 # VT
    puja_minima: float | None = None
    tramo: float | None = None
    deposito_pct: float = 0.05
    fecha_cierre: date | None = None
    horas_hasta_cierre: float | None = None            # si se conoce con precisión
    subastas_desiertas_previas: int = 0
    identificador_externo: str | None = None
    url: str | None = None


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
    meses_antiguedad: float = 0.0
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
class ICIResultado(BaseModel):
    ici: int
    desglose: dict[str, float]
    carencias: list[str]
    penalizaciones: list[str]
    efecto_delta_v_pp: float
    efecto_contingencia_pp: float
    techo_semaforo: Semaforo | None


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


class RiesgoOut(BaseModel):
    dimension: Dimension
    probabilidad: int
    impacto: int
    score: int
    nivel: NivelRiesgo
    mitigable: bool = True
    condiciones: list[str] = Field(default_factory=list)
    evidencias: list[str] = Field(default_factory=list)


class RAResultado(BaseModel):
    ra: int
    ra_base: float
    banda: Literal["bajo", "medio", "alto", "muy_alto", "critico"]
    dominancia_aplicada: str | None
    dimensiones: list[RiesgoOut]


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


class EscaleraPrecios(BaseModel):
    p_ideal: float
    p_objetivo: float
    p_max: float
    p_limite: float
    degenerada: bool = False
    detalle: dict[str, float] = Field(default_factory=dict)


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


class PujaResultado(BaseModel):
    p_adj_esperado: float
    ratio_base: float
    rvc: float
    banda_rvc: str
    plan: list[str]
    riesgo_ejecucion: list[str]


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
