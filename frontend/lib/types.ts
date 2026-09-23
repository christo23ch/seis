export type Semaforo = "verde" | "amarillo" | "naranja" | "rojo";

export interface Precios { p_ideal: number; p_objetivo: number; p_max: number; p_limite: number; degenerada: boolean; detalle: Record<string, number>; }
export interface Veto { codigo: string; motivo: string; dimension?: string | null; subsanable_con?: string | null; }
export interface RiesgoDim { dimension: string; probabilidad: number; impacto: number; score: number; nivel: string; mitigable: boolean; condiciones: string[]; evidencias: string[]; }
export interface EscenarioOut { nombre: string; probabilidad: number; vs: number; coste_total: number; beneficio: number; roi: number; roi_anualizado: number; plazo_meses: number; }
export interface ChecklistItem { grupo: string; orden: number; texto: string; bloqueante: boolean; estado: "ok" | "pendiente" | "no_aplica"; detalle?: string | null; }

export interface Decision {
  semaforo: Semaforo; ico: number; ico_desglose: Record<string, number>; ra: number; ici: number; icu: number;
  precios: Precios; margen_seguridad_valor: number; rvc: number; p_adj_esperado: number;
  vetos: Veto[]; condiciones: string[]; techos_aplicados: string[]; razones: string[];
  version_reglas: string; version_parametros: string;
}

export interface Resultado {
  decision: Decision;
  ici: { ici: number; carencias: string[]; penalizaciones: string[]; desglose: Record<string, number> };
  valoracion: { vm: number; vs: number; vs_m2: number; n_comparables: number; dispersion_cv: number; confianza: number; metodo: string };
  icu: { icu: number; macro_score: number; micro_score: number; potencial_revalorizacion: number; dom_venta_dias: number; tendencia_5a_pct: number };
  reforma: { nivel: string; total_p50: number; total_p80: number; plazo_obra_meses: number };
  costes: { c_v: number; c_f_p50: number; c_f_p80: number; desglose_p50: Record<string, number>; contingencia_pct: number; plazo_meses_p50: number; plazo_meses_p80: number; regimen_fiscal: string };
  riesgos: { ra: number; ra_base: number; banda: string; dominancia_aplicada: string | null; dimensiones: RiesgoDim[] };
  rentabilidad: { inversion_total: number; beneficio: number; roi: number; roi_anualizado: number; tir_anual: number; valor_esperado: number; escenarios: EscenarioOut[]; y_neta?: number | null; dscr?: number | null };
  puja: { p_adj_esperado: number; ratio_base: number; rvc: number; banda_rvc: string; plan: string[]; riesgo_ejecucion: string[] };
  checklist: ChecklistItem[];
  reglas_disparadas: { codigo: string; version: string; categoria: string }[];
  informe_markdown: string;
  delta_v: number; vs_prudente: number;
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
export interface Opciones { tipologias: string[]; fuentes: string[]; estados_conservacion: string[]; estados_ocupacion: string[]; ccaa: string[]; perfiles: Record<string, string>; }

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
