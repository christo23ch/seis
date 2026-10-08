export type Semaforo = "verde" | "amarillo" | "naranja" | "rojo";

export interface Precios { p_ideal: number; p_objetivo: number; p_max: number; p_limite: number; degenerada: boolean; detalle: Record<string, number>;
  /** Fase 5J-2a: tramo fiscal con que se resolvió cada precio (unico | bajo | alto | frontera). */
  tramos_fiscales?: Record<string, string> | null; }
export interface Veto { codigo: string; motivo: string; dimension?: string | null; subsanable_con?: string | null; }
export interface RiesgoDim { dimension: string; probabilidad: number; impacto: number; score: number; nivel: string; mitigable: boolean; condiciones: string[]; evidencias: string[];
  /** Fase 5J-2a: las mismas evidencias como {dato, valor}; ausente en resultados anteriores. */
  evidencias_detalle?: { dato: string; valor: string | null }[] | null; }
export interface EscenarioOut { nombre: string; probabilidad: number; vs: number; coste_total: number; beneficio: number; roi: number; roi_anualizado: number; plazo_meses: number; }
export interface ChecklistItem { grupo: string; orden: number; texto: string; bloqueante: boolean; estado: "ok" | "pendiente" | "no_aplica"; detalle?: string | null; }

export interface Decision {
  semaforo: Semaforo; ico: number; ico_desglose: Record<string, number>; ra: number; ici: number; icu: number;
  precios: Precios; margen_seguridad_valor: number; rvc: number; p_adj_esperado: number;
  vetos: Veto[]; condiciones: string[]; techos_aplicados: string[]; razones: string[];
  version_reglas: string; version_parametros: string;
  /** Fase 5H.1-C (§9.5, ADR-0019): meses hasta beneficio cero; ausentes en resultados anteriores. */
  colchon_plazo_meses?: number | null; colchon_plazo_meses_p_max?: number | null;
  /** Fase 5J-2a: operandos del colchón a P_objetivo. */
  colchon_detalle?: { beneficio: number; inversion: number; tenencia_mensual: number; intereses_mensuales: number;
                      coste_capital_mensual: number; coste_mensual: number } | null;
  /** Fase 5J-4 (ADR-0028): veredicto de la puja; ausente en resultados anteriores o sin escalera. */
  veredicto?: VeredictoPuja | null;
}

/** Fase 5J-4 (ADR-0028) — las tres cifras de la puja y si los números merecen la pena. Los textos
 * los redacta el motor (iguales que en el informe). Informativo: no veta nada. */
export interface VeredictoPuja {
  estado: "viable" | "inviable" | "sin_umbral";
  p_max: number; p_objetivo: number; p_limite?: number | null;
  /** Inviable: la mínima aprobable cabe en P_límite (semáforo como máximo naranja) o no (rojo). */
  cabe_en_limite?: boolean | null;
  aprobacion?: "no_aprobable" | "solo_si_cubre_deuda" | "discrecional" | null;
  aprobacion_texto?: string | null; condicion?: string | null;
  puja_minima_aprobable?: number | null; puja_minima_efectiva?: number | null;
  puja_aprobacion_segura?: number | null; puja_recomendada?: number | null; puja_evaluada: number;
  puja_minima_sin_vivienda?: number | null; alternativa_vivienda?: string | null;
  autoridad?: string | null; titulo: string; texto: string; cambios: string[];
  aviso_rentabilidad?: string | null;
}

export interface Resultado {
  decision: Decision;
  ici: { ici: number; carencias: string[]; penalizaciones: string[]; desglose: Record<string, number>;
    /** Fase 5J-2a: penalizaciones estructuradas. */
    penalizaciones_detalle?: { codigo: string; puntos: number }[] | null };
  valoracion: { vm: number; vs: number; vs_m2: number; n_comparables: number; dispersion_cv: number; confianza: number; metodo: string;
    /** Fase 5K-D: trazabilidad que ya devolvía el backend (opcional: resultados antiguos). */
    detalle_comparables?: { precio_ajustado_m2: number; normalizado_m2: number; peso: number }[];
    k_estado_activo?: number | null; vs_capitalizacion?: number | null };
  icu: { icu: number; macro_score: number; micro_score: number; potencial_revalorizacion: number; dom_venta_dias: number; tendencia_5a_pct: number };
  reforma: { nivel: string; total_p50: number; total_p80: number; plazo_obra_meses: number; partidas?: Record<string, number> };
  costes: { c_v: number; c_f_p50: number; c_f_p80: number; desglose_p50: Record<string, number>; contingencia_pct: number; plazo_meses_p50: number; plazo_meses_p80: number; regimen_fiscal: string;
    /** Fase 5K-D: desgloses que ya devolvía el backend (opcionales: resultados antiguos). */
    desglose_p80?: Record<string, number>; c_v_desglose?: Record<string, number>;
    base_fiscal_minima?: number; tipo_base_minima?: number;
    /** Fase 5J-2a: meses de ocupación, obra y comercialización, y el multiplicador del P80. */
    /** `inmovilizacion` (5J-2b, ADR-0026): cierre → pago del resto → posesión; ausente en resultados anteriores. */
    plazo_desglose?: { ocupacion: number; obra: number; comercializacion: number; inmovilizacion?: number;
                       multiplicador_p80: number } | null };
  riesgos: { ra: number; ra_base: number; banda: string; dominancia_aplicada: string | null; dimensiones: RiesgoDim[];
    /** Fase 5J-2a: pesos de agregación y suelo de la dominancia aplicada. */
    pesos?: Record<string, number> | null; suelo_dominancia?: number | null };
  rentabilidad: { precio_evaluado?: number; inversion_total: number; beneficio: number; roi: number; roi_anualizado: number; tir_anual: number; valor_esperado: number; escenarios: EscenarioOut[]; y_neta?: number | null; dscr?: number | null;
    /** Fase 5H.1-A (ADR-0017): informativos; ausentes en resultados anteriores. */
    van_coste_capital?: number | null; diferencial_tir_coste_capital?: number | null;
    /** Fase 5J-2a: flujos mensuales del escenario base (TIR y VAN) y tasa del VAN. */
    flujos_base?: number[] | null; tasa_van?: number | null };
  puja: { p_adj_esperado: number; ratio_base: number; rvc: number; banda_rvc: string; plan: string[]; riesgo_ejecucion: string[];
    /** Fase 5J-2a: ratio del segmento antes de ajustes, ajustes aplicados y si se acotó. */
    ratio_segmento?: number | null; ajustes_ratio?: { concepto: string; ajuste: number }[] | null; ratio_acotado?: boolean | null };
  checklist: ChecklistItem[];
  reglas_disparadas: { codigo: string; version: string; categoria: string }[];
  informe_markdown: string;
  delta_v: number; vs_prudente: number;
  /** Fase 5J-1 (ADR-0022): informativo; ausente en resultados anteriores a la fase. */
  procedimiento?: ProcedimientoResultado | null;
}

/** Fase 5J-1 — un dato legal aplicado, con su artículo y si está confirmado. */
export interface DatoLegal { dato: string; valor: number | null; articulo: string; estado: "confirmado" | "sin_confirmar"; nota?: string | null;
  /** 5J-2b: valor descriptivo de un dato que no es una cifra (la forma de puja). */
  texto?: string | null; }
/** Fase 5J-3 (ADR-0027) — la puja máxima no alcanza la aprobación segura del remate. */
export interface AvisoAprobacion {
  franja: "sujeta_a_mejora" | "discrecional" | "bajo_suelo"; techo_naranja: boolean;
  p_max: number; p_max_pct: number; puja_aprobacion_segura: number; umbral_aprobacion_segura_pct: number;
  puja_minima_aprobable: number | null; umbral_aprobacion_pct: number | null;
  suelo_absoluto: number | null; suelo_absoluto_pct: number | null;
  vivienda_habitual_asumida: boolean; regimen_asumido: boolean;
  titulo: string; riesgo: string; condicion: string; datos_legales: DatoLegal[];
  /** Redactados por el motor, iguales que en el informe. */
  alcance?: string; umbrales?: string[];
}
/** Fase 5J-1 — datos del procedimiento (`app/engine/procedimiento.py`). Importes `null`
 * = dato ausente (P4). Los umbrales son informativos; desde la 5J-2b el depósito, la forma
 * de puja y los meses de inmovilización entran en el cálculo (ADR-0024 a ADR-0026). */
export interface ProcedimientoResultado {
  procedimiento: string; procedimiento_deducido: boolean;
  regimen: string | null; regimen_nombre: string | null; regimen_asumido: boolean;
  vivienda_habitual: "si" | "no" | "no_consta"; vivienda_habitual_asumida: boolean;
  valor_subasta: number; cantidad_reclamada: number | null;
  deposito_pct: number | null; deposito_eur: number | null; deposito_declarado_pct: number;
  capital_para_pujar: number | null;
  plazo_pago_dias: number | null; plazo_pago_unidad: string | null; meses_inmovilizacion: number | null;
  /** 5J-2b: meses sumados al plazo; `asumidos` = estimación sin base legal. Ausentes antes de la fase. */
  meses_inmovilizacion_aplicados?: number | null; meses_inmovilizacion_asumidos?: boolean | null;
  forma_puja?: string | null;
  umbral_aprobacion_pct: number | null; puja_minima_aprobable: number | null;
  umbral_aprobacion_segura_pct: number | null; puja_aprobacion_segura: number | null;
  suelo_absoluto_pct: number | null; suelo_absoluto: number | null;
  datos_legales: DatoLegal[]; avisos: string[]; aviso_orientativo: string;
  /** 5J-3: ausente en resultados anteriores y cuando P_max alcanza la aprobación segura. */
  aviso_aprobacion?: AvisoAprobacion | null;
}

export interface ListItem {
  id: string; creado_en: string; perfil: string; semaforo: Semaforo; ico: number; ra: number; ici: number; icu: number;
  p_objetivo: number; p_max: number; rvc: number; tipologia?: string | null; municipio?: string | null;
  superficie_m2?: number | null; lat?: number | null; lng?: number | null; direccion?: string | null;
}

// Fase 5E: `resultado` es el de la configuración ACTUAL; `simulacion_validada_id`
// dice cuál es (null ⇒ configuración original). `version_*` son las del análisis original.
export interface Detalle {
  id: string; creado_en: string; perfil: string; version_reglas: string; version_parametros: string;
  entrada: any; resultado: Resultado; simulacion_validada_id: string | null;
}
/** Fase 5I: lo que el motor aplica si el campo opcional va vacío (catálogo T3 vigente). */
export interface ValoresDefecto {
  itp_por_ccaa: Record<string, number>; tenencia_mensual: number;
  atrasos_pct_valor_subasta: number; atrasos_minimo: number;
  adquisicion_fija: number; tasacion_banco: number; baremos_reforma_m2: Record<string, number>;
  /** Fase 5I-D: estado que asume el motor si el de conservación no consta. */
  estado_conservacion_desconocido: string;
}
export interface Opciones { tipologias: string[]; fuentes: string[]; estados_conservacion: string[]; estados_ocupacion: string[]; ccaa: string[]; perfiles: Record<string, string>; valores_defecto: ValoresDefecto;
  /** Fase 5J-1: etiquetas de los procedimientos, el de cada fuente y la fecha de la LO 1/2025. */
  procedimientos?: Record<string, string>; procedimiento_por_fuente?: Record<string, string>; fecha_lo_1_2025?: string; }

// Fase 9 — multi-tenancy
export type RolOrg = "propietario" | "miembro";
export interface Usuario {
  email: string; rol: string; nombre?: string | null;
  organizacion_id?: string | null; organizacion_nombre?: string | null;
  rol_org?: RolOrg; es_superadmin?: boolean;
}
export interface Miembro { id: string; email: string; nombre?: string | null; rol: string; rol_org: RolOrg; activo: boolean; }

// Fase 10 — respuesta común de los endpoints de alta self-service
export interface RespuestaSimple { ok: boolean; mensaje: string; }
export interface Organizacion { id: string; nombre: string; rol_org: RolOrg; puede_gestionar: boolean; miembros: Miembro[]; }

// Fase 12 — notificaciones, alertas y captación
export interface PreferenciasNotificacion {
  canales: string[]; modo: "instantaneo" | "digest_diario" | "digest_semanal";
  hora_digest: number; silencio_inicio?: number | null; silencio_fin?: number | null;
  telegram_vinculado: boolean; comunicaciones_activas: boolean;
}
export interface Alerta { id: string; nombre: string; criterios: Record<string, any>; activa: boolean; }
export interface CodigoTelegram { codigo: string; expira_en: string; enlace?: string | null; }
export interface SubastaCaptada {
  id: string; fuente_codigo: string; identificador_externo?: string | null; url?: string | null;
  valor_subasta: number; fecha_cierre?: string | null; estado: string;
  subastas_desiertas_previas: number; score?: number | null;
  score_desglose?: Record<string, number> | null; creado_en?: string | null;
}

// ─── Fases 5F.4 a 5F.7.3 — simulaciones, catálogo simulable e informes oficiales ───
// Tipados a partir de las respuestas reales de `backend/app/api/routes.py` y de
// `parametros_simulables_service.py`. Los valores de parámetros son JSON arbitrario:
// nunca `any`.

export type ValorJson = number | string | boolean | null | ValorJson[] | { [clave: string]: ValorJson };
export type Overrides = Record<string, ValorJson>;

export type EstadoSimulacion = "pendiente" | "validada" | "descartada";

/** Fila de `GET /analisis/{id}/simulaciones`. Métricas leídas del resultado persistido. */
export interface SimulacionResumen {
  id: string; estado: EstadoSimulacion; creado_en: string | null; fecha_validacion: string | null;
  usuario: string | null; overrides: Overrides;
  semaforo: Semaforo | null; ico: number | null; p_objetivo: number | null; p_max: number | null;
  es_configuracion_actual: boolean;
}

/** `POST …/simulaciones`, `GET …/{sid}`, `…/validar`, `…/descartar`, `…/seleccionar`. */
export interface SimulacionDetalle {
  id: string; analisis_id: string; estado: EstadoSimulacion; overrides: Overrides;
  parametros_aplicados: { [clave: string]: ValorJson }; resultado: Resultado;
  version_parametros_base: string | null; version_reglas: string | null; usuario: string | null;
  creado_en: string | null; fecha_validacion: string | null;
}

/** `rango` tal cual lo da el catálogo: cota concreta, sin rango o sin definir. */
export type RangoParametro = [number, number] | null | "pendiente_de_definir";

export interface PlantillaParametro {
  patron: string; dimension: string; instancia: string; coincide_con_analisis: boolean | null;
}

export interface ParametroEditable {
  clave: string; nombre_legible: string; modulo: string; descripcion: string; unidad: string;
  tipo: "numero" | "estructura"; rango: RangoParametro;
  advertencia: string; impacto: string; nivel_riesgo_modificacion: string;
  /** Fase 5G.4: aviso NO bloqueante si el valor supera `umbral_aviso`; `null` sin aviso. */
  umbral_aviso: number | null; texto_aviso: string | null;
  dependencia: string | null; origen: string;
  plantilla: PlantillaParametro | null;
  valor_vigente: ValorJson; valor_original: ValorJson | null; difiere_de_original: boolean | null;
}

/** `GET /analisis/{id}/parametros-simulables` (Fase 5F.7.2). */
export interface ParametrosSimulables {
  analisis_id: string; version_parametros_vigente: string | null; tiene_parametros_originales: boolean;
  editables: ParametroEditable[];
  no_editables: { clave: string; nombre_legible: string; modulo: string; descripcion: string; unidad: string; origen: string }[];
  derivados: { nombre: string; modulo: string; descripcion: string; origen: string }[];
}

export interface FilaComparacion {
  clave: string; nombre_legible: string | null; unidad: string | null; editable: boolean;
  valor_original: ValorJson | null; override: ValorJson | null; tiene_override: boolean;
  valor_aplicado: ValorJson | null; modificado: boolean;
  causa: "override" | "conocimiento_vigente" | null;
}

export interface ResumenResultadoComparado {
  semaforo: Semaforo | null; ico: number | null; ra: number | null; ici: number | null; icu: number | null;
  p_ideal: number | null; p_objetivo: number | null; p_max: number | null; p_limite: number | null;
  rvc: number | null; p_adj_esperado: number | null; margen_seguridad_valor: number | null;
  /** Fase 5G.3: la marca de M12 tal cual; `null` en resultados antiguos que no la traen. */
  escalera_degenerada: boolean | null;
  /** Fase 5H.1-A (ADR-0017): VAN al coste de capital (€) y TIR − coste de capital (puntos). */
  van_coste_capital: number | null; diferencial_tir_coste_capital: number | null;
  /** Fase 5H.1-C (§9.5, ADR-0019): colchón de plazo a precio objetivo, en meses. */
  colchon_plazo_meses: number | null;
}

/** `GET /analisis/{id}/simulaciones/{sid}/comparacion` (Fase 5F.7.3). */
export interface ComparacionSimulacion {
  analisis_id: string;
  simulacion: {
    id: string; estado: EstadoSimulacion; creado_en: string | null; fecha_validacion: string | null;
    version_parametros_base: string | null; version_reglas: string | null; es_configuracion_actual: boolean;
  };
  original: { creado_en: string | null; version_parametros: string; version_reglas: string; parametros_disponibles: boolean };
  parametros: FilaComparacion[];
  resultado: { original: ResumenResultadoComparado; simulacion: ResumenResultadoComparado };
}

/** Fila de `GET /analisis/{id}/informes`. `simulacion_id` null ⇒ emitido desde la configuración original. */
export interface InformeOficialResumen {
  id: string; analisis_id: string; simulacion_id: string | null;
  generado_por: string | null; generado_en: string | null;
  semaforo: Semaforo | null; ico: number | null;
}

/** `POST /analisis/{id}/informes` y `GET …/informes/{iid}`: contenido congelado íntegro. */
export interface InformeOficialDetalle {
  id: string; analisis_id: string; simulacion_id: string | null;
  entrada_snapshot: { [clave: string]: ValorJson };
  parametros_aplicados: { [clave: string]: ValorJson } | null;   // null ⇒ análisis anterior a 0014
  overrides: Overrides; resultado: Resultado;
  generado_por: string | null; generado_en: string | null;
}
