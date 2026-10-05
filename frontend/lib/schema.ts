import { z } from "zod";
import { aNumero, limpiarVacios } from "@/lib/formulario";

/* ── campos numéricos ──────────────────────────────────────────────────────
 * Fase 5I: TODO número del formulario pasa por `aNumero` (coma decimal, punto de
 * miles) y nunca por `z.coerce.number()`, que convertía un campo vacío en 0 y un
 * texto cualquiera en NaN sin avisar.
 *
 *   · `requerido`: obligatorio para el contrato (`AnalisisInput`) o para el
 *     asistente. Vacío ⇒ «Campo obligatorio».
 *   · `opcional`: vacío ⇒ `undefined` ⇒ el campo NO se envía, y el backend aplica
 *     su valor por defecto o lo trata como dato ausente (P4/P5). Los que tienen un
 *     valor inicial en `valoresIniciales` son opcionales igualmente: vaciarlos es
 *     volver al valor por defecto del contrato, no un error.
 */
export const MENSAJES = {
  obligatorio: "Campo obligatorio",
  numero: "Introduzca un número",
  entero: "Introduzca un número entero",
  positivo: "Debe ser mayor que cero",
  noNegativo: "No puede ser negativo",
  porcentaje: "Debe estar entre 0 y 100",
} as const;

type Ajuste = (n: z.ZodNumber) => z.ZodNumber;
const tal: Ajuste = (n) => n;
const base = () => z.number({ required_error: MENSAJES.obligatorio, invalid_type_error: MENSAJES.numero });
const requerido = (ajuste: Ajuste = tal) => z.preprocess((v) => aNumero(v), ajuste(base()));
const opcional = (ajuste: Ajuste = tal) => z.preprocess((v) => aNumero(v), ajuste(base()).optional());
/** Opcional en el que el punto es SIEMPRE decimal: tasas, coeficientes y
 * coordenadas («3.500» de interés es 3,5, no 3500). Ver `aNumero`. */
const decimal = (ajuste: Ajuste = tal) =>
  z.preprocess((v) => aNumero(v, { puntoDeMiles: false }), ajuste(base()).optional());

const positivo: Ajuste = (n) => n.positive(MENSAJES.positivo);
const noNegativo: Ajuste = (n) => n.min(0, MENSAJES.noNegativo);
const enteroNoNegativo: Ajuste = (n) => n.int(MENSAJES.entero).min(0, MENSAJES.noNegativo);
const porcentaje: Ajuste = (n) => n.min(0, MENSAJES.porcentaje).max(100, MENSAJES.porcentaje);
const indicador: Ajuste = (n) => n.min(0).max(100);
const variacion: Ajuste = (n) => n.min(-100, "Debe estar entre -100 y 100").max(100, "Debe estar entre -100 y 100");

export const esquemaAnalisis = z.object({
  perfil: z.string().min(1, MENSAJES.obligatorio),
  subasta: z.object({
    fuente: z.string().min(1, MENSAJES.obligatorio),
    valor_subasta: requerido(positivo),
    puja_minima: opcional(positivo),
    deposito_pct: decimal(porcentaje),
    horas_hasta_cierre: opcional(noNegativo),
    subastas_desiertas_previas: opcional(enteroNoNegativo),
    identificador_externo: z.string().optional(),
  }),
  activo: z.object({
    tipologia: z.string(),
    superficie_m2: requerido(positivo),
    estado_conservacion: z.string(),
    anio_construccion: opcional((n) => n.int(MENSAJES.entero).min(1500, "Año no válido").max(2100, "Año no válido")),
    es_vivienda_habitual: z.boolean(),
    vpo: z.boolean(),
    vpo_precio_max_legal: opcional(positivo),
    ref_catastral: z.string().optional(),
    finca_registral: z.string().optional(),
    direccion: z.string().optional(),
    municipio: z.string().trim().min(1, MENSAJES.obligatorio),
    provincia: z.string(),
    ccaa: z.string().min(1, MENSAJES.obligatorio),
    lat: decimal((n) => n.min(-90, "Latitud no válida").max(90, "Latitud no válida")),
    lng: decimal((n) => n.min(-180, "Longitud no válida").max(180, "Longitud no válida")),
  }),
  cargas: z.array(z.object({
    tipo: z.string(),
    importe: opcional(noNegativo),
    es_anterior: z.boolean(),
    se_purga: z.boolean(),
    verificada: z.boolean(),
    prohibicion_disponer: z.boolean(),
    condicion_resolutoria: z.boolean(),
  })),
  ocupacion: z.object({ estado: z.string(), renta_mensual: opcional(noNegativo) }),
  urbanistico: z.object({
    uso_compatible: z.boolean(),
    fuera_ordenacion: z.boolean(),
    orden_demolicion: z.boolean(),
    suelo_protegido: z.boolean(),
    cargas_urbanizacion: opcional(noNegativo),
    servidumbres_incompatibles: z.boolean(),
    zona_inundable_alta: z.boolean(),
  }),
  zona: z.object({
    macro: z.object({
      tendencia_5a_pct: decimal(variacion), stock_meses: decimal(noNegativo),
      dom_venta_dias: opcional((n) => n.min(1, "Debe ser al menos 1")),
      dom_alquiler_dias: opcional((n) => n.min(1, "Debe ser al menos 1")),
      crecimiento_pobl_5a_pct: decimal(variacion),
      renta_hogar: opcional(noNegativo), y_zona_pct: decimal(porcentaje),
    }),
    micro: z.object({
      transporte: decimal(indicador), seguridad: decimal(indicador), sanidad: decimal(indicador),
      educacion: decimal(indicador), comercio: decimal(indicador), zonas_verdes: decimal(indicador),
      pipeline_urbanistico: decimal(indicador), potencial_transformacion: decimal(indicador),
      entorno_construido: decimal(indicador),
    }),
    precio_m2_p85: opcional(positivo),
  }),
  comparables: z.array(z.object({
    precio_m2: requerido(positivo),
    estado: z.string(),
    origen: z.string(),
    // Fase 5I: la antigüedad no puede ser negativa. El motor (M03) pondera cada
    // comparable con 1/(1 + meses/6): con −3 meses pesaba el doble que uno de hoy
    // y con −6 dividía por cero.
    meses_antiguedad: opcional(noNegativo),
  })).min(1, "Añada al menos un comparable"),
  reforma: z.object({
    nivel_override: z.string().optional(),
    visita_interior: z.boolean(),
    k_provincia: decimal((n) => n.positive(MENSAJES.positivo).max(5, "Debe ser como máximo 5")),
    coste_m2_override: opcional(noNegativo),
    partidas_extra: opcional(noNegativo),
  }),
  costes: z.object({
    regimen_fiscal: z.string(),
    transmitente_empresario: z.boolean(),
    primera_entrega: z.boolean(),
    comprador_deduce_iva: z.boolean(),
    itp_tipo_override: decimal(porcentaje),          // en %
    // Base imponible del ITP: el mayor de (valor de referencia, declarado, puja).
    // Vacío ⇒ el motor usa la puja como suelo y lo declara como carencia.
    valor_referencia_catastral: opcional(positivo),
    valor_declarado: opcional(positivo),
    atrasos_comunidad_ibi: opcional(noNegativo),
    adquisicion_fija_override: opcional(noNegativo),
    tenencia_mensual: opcional(noNegativo),
    plusvalia_municipal_estimada: opcional(noNegativo),
  }),
  financiacion: z.object({
    tipo: z.enum(["cash", "hipoteca"]),
    preaprobada: z.boolean(),
    ltv: decimal(porcentaje),                         // en %
    interes_anual_pct: decimal(porcentaje),
  }),
  rentista: z.object({
    renta_mensual_estimada: opcional(noNegativo),
    vacancia_pct: decimal(porcentaje),
    ibi_anual: opcional(noNegativo),
    comunidad_mensual: opcional(noNegativo),
    seguro_anual: opcional(noNegativo),
    mantenimiento_pct_renta: decimal(porcentaje),
    gestion_pct_renta: decimal(porcentaje),
  }).optional(),     // sus campos se dan de baja al ocultarse (perfil no rentista)
  documentos: z.object({
    nota_simple: z.boolean(), nota_simple_dias: opcional(enteroNoNegativo), cert_cargas: z.boolean(),
    posesion_verificada: z.boolean(), avaluo: z.boolean(), fotos_interior_o_visita: z.boolean(),
    fotos_exterior: z.boolean(), cert_comunidad: z.boolean(), recibo_ibi: z.boolean(),
    ite_cee: z.boolean(), catastro_conciliado: z.boolean(),
    inc_superficie: z.boolean(), inc_cargas: z.boolean(), inc_tasacion: z.boolean(),
  }),
});

/** Lo que el formulario contiene (texto tal cual lo escribe la persona). */
export type EntradaFormulario = z.input<typeof esquemaAnalisis>;
/** Lo que sale de validar: números ya convertidos, vacíos como `undefined`. */
export type ValoresAnalisis = z.output<typeof esquemaAnalisis>;

/**
 * Valores iniciales del asistente. Criterio (Fase 5I):
 *   · VALOR escrito en el campo cuando es el valor por defecto del contrato y el
 *     motor lo usaría igual si se vaciara (depósito 5 %, indicadores micro 50,
 *     macro de referencia…): es un supuesto razonable que se ve y se corrige.
 *   · Campo VACÍO con el valor por defecto en el texto de ayuda o en el
 *     marcador cuando vacío significa «el motor estima» (atrasos, tenencia,
 *     ITP, costes fijos…): escribir ahí el número cambiaría su significado, de
 *     estimación prudente a dato declarado (P4/P5).
 *   · Obligatorios VACÍOS (valor de subasta, superficie, €/m² del comparable):
 *     antes valían 0, un valor falso que parecía rellenado.
 */
export const valoresIniciales: EntradaFormulario = {
  perfil: "flip_integral",
  subasta: { fuente: "judicial_boe", valor_subasta: "", puja_minima: "", deposito_pct: 5,
             horas_hasta_cierre: "", subastas_desiertas_previas: 0, identificador_externo: "" },
  activo: { tipologia: "vivienda", superficie_m2: "", estado_conservacion: "regular", anio_construccion: "",
            es_vivienda_habitual: false, vpo: false, vpo_precio_max_legal: "", ref_catastral: "",
            finca_registral: "", direccion: "", municipio: "", provincia: "", ccaa: "madrid",
            lat: "", lng: "" },
  cargas: [],
  ocupacion: { estado: "desconocida", renta_mensual: "" },
  urbanistico: { uso_compatible: true, fuera_ordenacion: false, orden_demolicion: false, suelo_protegido: false,
                 cargas_urbanizacion: 0, servidumbres_incompatibles: false, zona_inundable_alta: false },
  zona: {
    macro: { tendencia_5a_pct: 0, stock_meses: 8, dom_venta_dias: 120, dom_alquiler_dias: 40,
             crecimiento_pobl_5a_pct: 0, renta_hogar: 30000, y_zona_pct: 5.5 },
    micro: { transporte: 50, seguridad: 50, sanidad: 50, educacion: 50, comercio: 50,
             zonas_verdes: 50, pipeline_urbanistico: 50, potencial_transformacion: 50, entorno_construido: 50 },
    precio_m2_p85: "",
  },
  comparables: [{ precio_m2: "", estado: "reformado", origen: "testigo", meses_antiguedad: 0 }],
  reforma: { nivel_override: "", visita_interior: false, k_provincia: 1, coste_m2_override: "", partidas_extra: 0 },
  costes: { regimen_fiscal: "auto", transmitente_empresario: false, primera_entrega: false, comprador_deduce_iva: false,
            itp_tipo_override: "", valor_referencia_catastral: "", valor_declarado: "",
            atrasos_comunidad_ibi: "", adquisicion_fija_override: "",
            tenencia_mensual: "", plusvalia_municipal_estimada: 0 },
  financiacion: { tipo: "cash", preaprobada: false, ltv: 0, interes_anual_pct: 3.5 },
  rentista: { renta_mensual_estimada: 0, vacancia_pct: 5, ibi_anual: 0, comunidad_mensual: 0,
              seguro_anual: 300, mantenimiento_pct_renta: 5, gestion_pct_renta: 0 },
  documentos: { nota_simple: false, nota_simple_dias: "", cert_cargas: false, posesion_verificada: false,
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

/** Rutas que se escriben en % y viajan en fracción (ver `aPayload`). */
export const RUTAS_EN_FRACCION: ReadonlySet<string> =
  new Set(["subasta.deposito_pct", "costes.itp_tipo_override", "financiacion.ltv"]);

/** `x / 100` respetando la ausencia: un porcentaje vacío sigue vacío. */
const fraccion = (x: number | undefined) => (x === undefined ? undefined : x / 100);

/**
 * Valores ya VALIDADOS (salida de `esquemaAnalisis`) → cuerpo de `AnalisisInput`.
 * Solo traduce unidades y forma; los vacíos los retira `prepararEnvio`.
 */
export function aPayload(v: ValoresAnalisis): Record<string, unknown> {
  const d = v.documentos;
  const inconsistencias = [
    d.inc_superficie && "superficie_inconsistente",
    d.inc_cargas && "cargas_mismatch",
    d.inc_tasacion && "tasacion_anomala",
  ].filter(Boolean) as string[];

  const payload: Record<string, unknown> = {
    perfil: v.perfil,
    activo: v.activo,
    subasta: { ...v.subasta, deposito_pct: fraccion(v.subasta.deposito_pct) },
    cargas: v.cargas,
    ocupacion: v.ocupacion,
    urbanistico: v.urbanistico,
    zona: v.zona,
    comparables: v.comparables,
    reforma: v.reforma,
    costes: { ...v.costes, itp_tipo_override: fraccion(v.costes.itp_tipo_override) },
    financiacion: { ...v.financiacion, ltv: fraccion(v.financiacion.ltv) },
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

/**
 * Fase 5I — el ÚNICO camino del formulario al backend: valores validados →
 * forma del contrato → sin vacíos. Lo usan «Calcular», «Recalcular» y «Guardar».
 */
export function prepararEnvio(v: ValoresAnalisis): Record<string, unknown> {
  return limpiarVacios(aPayload(v));
}

/**
 * Fase 5I-B — paso del asistente al que pertenece la ruta de un campo
 * («comparables.1.precio_m2» → 5), para llevar a la persona al primer campo
 * pendiente aunque esté en otro paso. `undefined` si no es de ningún paso.
 */
export function pasoDeRuta(ruta: string): number | undefined {
  const i = PASOS.findIndex((p) => p.campos.some((c) => ruta === c || ruta.startsWith(`${c}.`)));
  return i === -1 ? undefined : i;
}
