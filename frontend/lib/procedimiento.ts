/**
 * Fase 5J-1 (ADR-0022) — presentación de los datos del procedimiento.
 *
 * Solo da forma a lo que calcula el backend (`app/engine/procedimiento.py`): no
 * calcula ningún importe ni decide ningún supuesto. Un importe `null` es dato
 * ausente (P4) y se muestra como «No consta», nunca como 0.
 */
import { eur, num, pct } from "@/lib/format";
import type { ProcedimientoResultado } from "@/lib/types";

export const NO_CONSTA = "No consta";
const UNIDAD_PLAZO: Record<string, string> = { naturales: "días naturales", habiles: "días hábiles" };

export interface FilaProcedimiento { clave: string; etiqueta: string; valor: string; detalle?: string }

/** «30.400 € · 20 % del valor de subasta», o «No consta». */
function importe(valor: number | null, porcentaje: number | null): { valor: string; detalle?: string } {
  if (valor == null) return { valor: NO_CONSTA };
  return { valor: eur(valor), detalle: porcentaje == null ? undefined : `${pct(porcentaje, 0)} del valor de subasta` };
}

/** Filas del panel, en el mismo orden que la tabla del informe (§8). */
export function filasProcedimiento(r: ProcedimientoResultado): FilaProcedimiento[] {
  const plazo = r.plazo_pago_dias == null ? NO_CONSTA
    : `${r.plazo_pago_dias} ${UNIDAD_PLAZO[r.plazo_pago_unidad ?? ""] ?? "días"}`;
  const meses = r.meses_inmovilizacion == null ? NO_CONSTA : `${num(r.meses_inmovilizacion, 1)} meses`;
  return [
    { clave: "regimen", etiqueta: "Procedimiento y régimen", valor: r.regimen_nombre ?? NO_CONSTA,
      detalle: r.regimen_asumido ? "Supuesto: no consta la fecha de inicio" : undefined },
    { clave: "deposito", etiqueta: "Depósito exigido", ...importe(r.deposito_eur, r.deposito_pct) },
    { clave: "capital", etiqueta: "Capital necesario para pujar", ...importe(r.capital_para_pujar, null) },
    { clave: "plazo", etiqueta: "Pago del resto del precio", valor: plazo },
    { clave: "inmovilizacion", etiqueta: "Inmovilización estimada del depósito", valor: meses,
      detalle: r.meses_inmovilizacion == null ? undefined : "Plazo legal máximo" },
    { clave: "minima", etiqueta: "Puja mínima aprobable sin depender de la autoridad",
      ...importe(r.puja_minima_aprobable, r.umbral_aprobacion_pct) },
    { clave: "segura", etiqueta: "Puja de aprobación segura",
      ...importe(r.puja_aprobacion_segura, r.umbral_aprobacion_segura_pct) },
    { clave: "suelo", etiqueta: "Suelo absoluto", ...importe(r.suelo_absoluto, r.suelo_absoluto_pct) },
  ];
}

export const etiquetaEstado = (estado: "confirmado" | "sin_confirmar") =>
  estado === "confirmado" ? "Confirmado" : "Sin confirmar";
