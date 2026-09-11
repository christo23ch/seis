import { z } from "zod";

const num = z.coerce.number();
const optNum = z.preprocess(
  (v) => (v === "" || v === null || v === undefined || (typeof v === "number" && Number.isNaN(v)) ? undefined : v),
  z.coerce.number().optional(),
);

export const esquemaAnalisis = z.object({
  perfil: z.string().min(1),
  subasta: z.object({
    fuente: z.string().min(1),
    valor_subasta: num.positive("Introduzca el valor de subasta"),
    puja_minima: optNum,
    deposito_pct: num.min(0).max(100),
    horas_hasta_cierre: optNum,
    subastas_desiertas_previas: num.int().min(0),
    identificador_externo: z.string().optional(),
  }),
  activo: z.object({
    tipologia: z.string(),
    superficie_m2: num.positive("Superficie requerida"),
    estado_conservacion: z.string(),
    anio_construccion: optNum,
    es_vivienda_habitual: z.boolean(),
    vpo: z.boolean(),
    vpo_precio_max_legal: optNum,
    ref_catastral: z.string().optional(),
    finca_registral: z.string().optional(),
    direccion: z.string().optional(),
    municipio: z.string().min(1, "Municipio requerido"),
    provincia: z.string(),
    ccaa: z.string().min(1),
    lat: optNum,
    lng: optNum,
  }),
  cargas: z.array(z.object({
    tipo: z.string(),
    importe: optNum,
    es_anterior: z.boolean(),
    se_purga: z.boolean(),
    verificada: z.boolean(),
    prohibicion_disponer: z.boolean(),
    condicion_resolutoria: z.boolean(),
  })),
  ocupacion: z.object({ estado: z.string(), renta_mensual: optNum }),
  urbanistico: z.object({
    uso_compatible: z.boolean(),
    fuera_ordenacion: z.boolean(),
    orden_demolicion: z.boolean(),
    suelo_protegido: z.boolean(),
    cargas_urbanizacion: num.min(0),
    servidumbres_incompatibles: z.boolean(),
    zona_inundable_alta: z.boolean(),
  }),
  zona: z.object({
    macro: z.object({
      tendencia_5a_pct: num, stock_meses: num.min(0), dom_venta_dias: num.min(1),
      dom_alquiler_dias: num.min(1), crecimiento_pobl_5a_pct: num,
      renta_hogar: num.min(0), y_zona_pct: num.min(0),
    }),
    micro: z.object({
      transporte: num, seguridad: num, sanidad: num, educacion: num, comercio: num,
      zonas_verdes: num, pipeline_urbanistico: num, potencial_transformacion: num, entorno_construido: num,
    }),
    precio_m2_p85: optNum,
  }),
  comparables: z.array(z.object({
    precio_m2: num.positive("€/m² requerido"),
    estado: z.string(),
    origen: z.string(),
    meses_antiguedad: num.min(0),
  })).min(1, "Añada al menos un comparable"),
  reforma: z.object({
    nivel_override: z.string().optional(),
    visita_interior: z.boolean(),
    k_provincia: num.positive(),
    coste_m2_override: optNum,
    partidas_extra: num.min(0),
  }),
  costes: z.object({
    regimen_fiscal: z.string(),
    transmitente_empresario: z.boolean(),
    primera_entrega: z.boolean(),
    comprador_deduce_iva: z.boolean(),
    itp_tipo_override: optNum,          // en %
    // Base imponible del ITP: el mayor de (valor de referencia, declarado, puja).
    // Vacío ⇒ el motor usa la puja como suelo y lo declara como carencia.
    valor_referencia_catastral: optNum,
    valor_declarado: optNum,
    atrasos_comunidad_ibi: optNum,
    adquisicion_fija_override: optNum,
    tenencia_mensual: optNum,
    plusvalia_municipal_estimada: num.min(0),
  }),
  financiacion: z.object({
    tipo: z.enum(["cash", "hipoteca"]),
    preaprobada: z.boolean(),
    ltv: num.min(0).max(100),           // en %
    interes_anual_pct: num.min(0),
  }),
  rentista: z.object({
    renta_mensual_estimada: num.min(0),
    vacancia_pct: num.min(0),
    ibi_anual: num.min(0),
    comunidad_mensual: num.min(0),
    seguro_anual: num.min(0),
    mantenimiento_pct_renta: num.min(0),
    gestion_pct_renta: num.min(0),
  }),
  documentos: z.object({
    nota_simple: z.boolean(), nota_simple_dias: optNum, cert_cargas: z.boolean(),
    posesion_verificada: z.boolean(), avaluo: z.boolean(), fotos_interior_o_visita: z.boolean(),
    fotos_exterior: z.boolean(), cert_comunidad: z.boolean(), recibo_ibi: z.boolean(),
    ite_cee: z.boolean(), catastro_conciliado: z.boolean(),
    inc_superficie: z.boolean(), inc_cargas: z.boolean(), inc_tasacion: z.boolean(),
  }),
});

export type ValoresAnalisis = z.infer<typeof esquemaAnalisis>;

export const valoresIniciales: ValoresAnalisis = {
  perfil: "flip_integral",
  subasta: { fuente: "judicial_boe", valor_subasta: 0, puja_minima: undefined, deposito_pct: 5,
             horas_hasta_cierre: undefined, subastas_desiertas_previas: 0, identificador_externo: "" },
  activo: { tipologia: "vivienda", superficie_m2: 0, estado_conservacion: "regular", anio_construccion: undefined,
            es_vivienda_habitual: false, vpo: false, vpo_precio_max_legal: undefined, ref_catastral: "",
            finca_registral: "", direccion: "", municipio: "", provincia: "", ccaa: "madrid",
            lat: undefined, lng: undefined },
  cargas: [],
  ocupacion: { estado: "desconocida", renta_mensual: undefined },
  urbanistico: { uso_compatible: true, fuera_ordenacion: false, orden_demolicion: false, suelo_protegido: false,
                 cargas_urbanizacion: 0, servidumbres_incompatibles: false, zona_inundable_alta: false },
  zona: {
    macro: { tendencia_5a_pct: 0, stock_meses: 8, dom_venta_dias: 120, dom_alquiler_dias: 40,
             crecimiento_pobl_5a_pct: 0, renta_hogar: 30000, y_zona_pct: 5.5 },
    micro: { transporte: 50, seguridad: 50, sanidad: 50, educacion: 50, comercio: 50,
             zonas_verdes: 50, pipeline_urbanistico: 50, potencial_transformacion: 50, entorno_construido: 50 },
    precio_m2_p85: undefined,
  },
  comparables: [{ precio_m2: 0, estado: "reformado", origen: "testigo", meses_antiguedad: 0 }],
  reforma: { nivel_override: "", visita_interior: false, k_provincia: 1, coste_m2_override: undefined, partidas_extra: 0 },
  costes: { regimen_fiscal: "auto", transmitente_empresario: false, primera_entrega: false, comprador_deduce_iva: false,
            itp_tipo_override: undefined, valor_referencia_catastral: undefined, valor_declarado: undefined,
            atrasos_comunidad_ibi: undefined, adquisicion_fija_override: undefined,
            tenencia_mensual: undefined, plusvalia_municipal_estimada: 0 },
  financiacion: { tipo: "cash", preaprobada: false, ltv: 0, interes_anual_pct: 3.5 },
  rentista: { renta_mensual_estimada: 0, vacancia_pct: 5, ibi_anual: 0, comunidad_mensual: 0,
              seguro_anual: 300, mantenimiento_pct_renta: 5, gestion_pct_renta: 0 },
  documentos: { nota_simple: false, nota_simple_dias: undefined, cert_cargas: false, posesion_verificada: false,
                avaluo: false, fotos_interior_o_visita: false, fotos_exterior: false, cert_comunidad: false,
                recibo_ibi: false, ite_cee: false, catastro_conciliado: false,
                inc_superficie: false, inc_cargas: false, inc_tasacion: false },
};

export const PASOS: { titulo: string; descripcion: string; campos: string[] }[] = [
  { titulo: "Datos generales", descripcion: "Fuente, valor de subasta y perfil de inversión", campos: ["perfil", "subasta"] },
  { titulo: "Tipo de activo", descripcion: "Tipología, superficie y estado", campos: ["activo.tipologia", "activo.superficie_m2", "activo.estado_conservacion", "activo.anio_construccion", "activo.vpo", "activo.vpo_precio_max_legal", "activo.es_vivienda_habitual"] },
  { titulo: "Datos registrales", descripcion: "Cargas, finca y situación posesoria", campos: ["activo.ref_catastral", "activo.finca_registral", "cargas", "ocupacion"] },
  { titulo: "Datos urbanísticos", descripcion: "Compatibilidad de uso y restricciones", campos: ["urbanistico"] },
  { titulo: "Ubicación", descripcion: "Dirección, coordenadas e indicadores micro", campos: ["activo.direccion", "activo.municipio", "activo.provincia", "activo.ccaa", "activo.lat", "activo.lng", "zona.micro"] },
  { titulo: "Valoraciones", descripcion: "Comparables y mercado macro de la zona", campos: ["comparables", "zona.macro", "zona.precio_m2_p85"] },
  { titulo: "Costes", descripcion: "Fiscalidad, atrasos y tenencia", campos: ["costes"] },
  { titulo: "Reforma", descripcion: "Nivel de obra, visita y baremos", campos: ["reforma"] },
  { titulo: "Financiación", descripcion: "Estructura de pago y, si aplica, alquiler", campos: ["financiacion", "rentista"] },
  { titulo: "Validación", descripcion: "Documentación disponible (alimenta el ICI)", campos: ["documentos"] },
  { titulo: "Resultado", descripcion: "Decisión del motor experto", campos: [] },
];

export function aPayload(v: ValoresAnalisis) {
  const d = v.documentos;
  const inconsistencias = [
    d.inc_superficie && "superficie_inconsistente",
    d.inc_cargas && "cargas_mismatch",
    d.inc_tasacion && "tasacion_anomala",
  ].filter(Boolean) as string[];

  const payload: Record<string, unknown> = {
    perfil: v.perfil,
    activo: { ...v.activo },
    subasta: { ...v.subasta, deposito_pct: v.subasta.deposito_pct / 100 },
    cargas: v.cargas,
    ocupacion: v.ocupacion,
    urbanistico: v.urbanistico,
    zona: v.zona,
    comparables: v.comparables,
    reforma: { ...v.reforma, nivel_override: v.reforma.nivel_override || undefined },
    costes: {
      ...v.costes,
      itp_tipo_override: v.costes.itp_tipo_override != null ? v.costes.itp_tipo_override / 100 : undefined,
    },
    financiacion: { ...v.financiacion, ltv: v.financiacion.ltv / 100 },
    documentos: {
      nota_simple: d.nota_simple, nota_simple_dias: d.nota_simple_dias, cert_cargas: d.cert_cargas,
      posesion_verificada: d.posesion_verificada, avaluo: d.avaluo,
      fotos_interior_o_visita: d.fotos_interior_o_visita, fotos_exterior: d.fotos_exterior,
      cert_comunidad: d.cert_comunidad, recibo_ibi: d.recibo_ibi, ite_cee: d.ite_cee,
      catastro_conciliado: d.catastro_conciliado, inconsistencias,
    },
  };
  if (v.perfil === "rentista") payload.rentista = v.rentista;
  return payload;
}
