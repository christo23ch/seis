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

export interface Detalle { id: string; creado_en: string; perfil: string; version_reglas: string; version_parametros: string; entrada: any; resultado: Resultado; }
export interface Opciones { tipologias: string[]; fuentes: string[]; estados_conservacion: string[]; estados_ocupacion: string[]; ccaa: string[]; perfiles: Record<string, string>; }

// Fase 9 — multi-tenancy
export type RolOrg = "propietario" | "miembro";
export interface Usuario {
  email: string; rol: string; nombre?: string | null;
  organizacion_id?: string | null; organizacion_nombre?: string | null;
  rol_org?: RolOrg; es_superadmin?: boolean;
}
export interface Miembro { id: string; email: string; nombre?: string | null; rol: string; rol_org: RolOrg; activo: boolean; }
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
