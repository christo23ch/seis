import { describe, expect, it } from "vitest";
import { NO_CONSTA, filasProcedimiento } from "@/lib/procedimiento";
import { descartarOcultos, esquemaAnalisis, prepararEnvio, rutasOcultas, valoresIniciales, type EntradaFormulario } from "@/lib/schema";
import type { ProcedimientoResultado } from "@/lib/types";

/** Alta con solo los obligatorios (mismo criterio que `schema.test.ts`). */
function soloObligatorios(): EntradaFormulario {
  const v = structuredClone(valoresIniciales);
  return {
    ...v,
    subasta: { ...v.subasta, valor_subasta: "152.000" },
    activo: { ...v.activo, superficie_m2: "82", municipio: "Madrid" },
    comparables: [{ ...v.comparables[0], precio_m2: "2.293" }],
  };
}
const enviar = (v: EntradaFormulario) => prepararEnvio(esquemaAnalisis.parse(descartarOcultos(v))) as any;
const errores = (v: EntradaFormulario) => {
  const r = esquemaAnalisis.safeParse(descartarOcultos(v));
  return r.success ? {} : Object.fromEntries(r.error.issues.map((i) => [i.path.join("."), i.message]));
};

describe("preguntas del procedimiento (5J-1): valores por defecto visibles", () => {
  it("parte de judicial, «No sé» y vivienda habitual «No consta»", () => {
    expect(valoresIniciales.subasta.procedimiento).toBe("judicial");
    expect(valoresIniciales.subasta.regimen_judicial).toBe("no_se");
    expect(valoresIniciales.activo.vivienda_habitual_ejecutado).toBe("no_consta");
  });

  it("envía lo respondido y el booleano antiguo derivado (solo «Sí» es verdadero)", () => {
    const cuerpo = enviar(soloObligatorios());
    expect(cuerpo.subasta.procedimiento).toBe("judicial");
    expect(cuerpo.subasta.regimen_judicial).toBe("no_se");
    expect(cuerpo.subasta.cantidad_reclamada).toBeUndefined();           // opcional vacío: no viaja
    expect(cuerpo.activo.vivienda_habitual_ejecutado).toBe("no_consta");
    expect(cuerpo.activo.es_vivienda_habitual).toBe(false);
    const v = soloObligatorios();
    const si = enviar({ ...v, activo: { ...v.activo, vivienda_habitual_ejecutado: "si" } });
    expect(si.activo.es_vivienda_habitual).toBe(true);
  });

  it("convierte la cantidad reclamada con punto de miles", () => {
    const v = soloObligatorios();
    const cuerpo = enviar({ ...v, subasta: { ...v.subasta, cantidad_reclamada: "65.000" } });
    expect(cuerpo.subasta.cantidad_reclamada).toBe(65000);
  });
});

describe("preguntas del procedimiento (5J-1): campos condicionados", () => {
  it("el régimen solo se pregunta en la vía judicial", () => {
    const v = soloObligatorios();
    expect(rutasOcultas(v)).not.toContain("subasta.regimen_judicial");
    const aeat = { ...v, subasta: { ...v.subasta, procedimiento: "aeat" as const } };
    expect(rutasOcultas(aeat)).toContain("subasta.regimen_judicial");
    expect(enviar(aeat).subasta.regimen_judicial).toBeUndefined();     // oculto: no viaja
  });

  it("la cantidad reclamada solo donde cambia la puja mínima aprobable", () => {
    const v = soloObligatorios();
    for (const p of ["judicial", "extrajudicial", "tgss"] as const) {
      expect(rutasOcultas({ ...v, subasta: { ...v.subasta, procedimiento: p } })).not.toContain("subasta.cantidad_reclamada");
    }
    for (const p of ["aeat", "notarial", "concursal", "no_aplica"] as const) {
      const oculto = { ...v, subasta: { ...v.subasta, procedimiento: p, cantidad_reclamada: "-3" } };
      expect(rutasOcultas(oculto)).toContain("subasta.cantidad_reclamada");
      expect(errores(oculto)["subasta.cantidad_reclamada"]).toBeUndefined();   // lo oculto no se valida
    }
  });
});

describe("preguntas del procedimiento (5J-1): validación con mensajes en español", () => {
  it("rechaza una cantidad reclamada no positiva o que no es un número", () => {
    const v = soloObligatorios();
    expect(errores({ ...v, subasta: { ...v.subasta, cantidad_reclamada: "0" } })["subasta.cantidad_reclamada"])
      .toBe("Debe ser mayor que cero");
    expect(errores({ ...v, subasta: { ...v.subasta, cantidad_reclamada: "mucho" } })["subasta.cantidad_reclamada"])
      .toBe("Introduzca un número");
  });

  it("rechaza respuestas fuera de la lista", () => {
    const v = soloObligatorios() as any;
    const e = errores({ ...v, subasta: { ...v.subasta, procedimiento: "subastilla" },
                        activo: { ...v.activo, vivienda_habitual_ejecutado: "quizas" } });
    expect(e["subasta.procedimiento"]).toBe("Elija una opción de la lista");
    expect(e["activo.vivienda_habitual_ejecutado"]).toBe("Elija una opción de la lista");
  });
});

const BASE: ProcedimientoResultado = {
  procedimiento: "judicial", procedimiento_deducido: false, regimen: "judicial_lec_2025",
  regimen_nombre: "Judicial (LEC tras la LO 1/2025)", regimen_asumido: true,
  vivienda_habitual: "no_consta", vivienda_habitual_asumida: true, valor_subasta: 152000, cantidad_reclamada: null,
  deposito_pct: 0.2, deposito_eur: 30400, deposito_declarado_pct: 0.05, capital_para_pujar: 30400,
  plazo_pago_dias: 20, plazo_pago_unidad: "naturales", meses_inmovilizacion: 1.8,
  umbral_aprobacion_pct: 0.7, puja_minima_aprobable: 106400, umbral_aprobacion_segura_pct: 0.7,
  puja_aprobacion_segura: 106400, suelo_absoluto_pct: 0.6, suelo_absoluto: 91200,
  datos_legales: [], avisos: [], aviso_orientativo: "Cálculo orientativo…",
};
const fila = (r: ProcedimientoResultado, clave: string) => filasProcedimiento(r).find((f) => f.clave === clave)!;

describe("filasProcedimiento: presenta lo que calcula el backend, sin calcular", () => {
  it("formatea importes, porcentajes, plazos y meses en español", () => {
    expect(fila(BASE, "deposito").valor).toMatch(/^30\.400\s€$/);
    expect(fila(BASE, "deposito").detalle).toBe("20 % del valor de subasta");
    expect(fila(BASE, "capital").detalle).toBeUndefined();
    expect(fila(BASE, "plazo").valor).toBe("20 días naturales");
    expect(fila(BASE, "inmovilizacion").valor).toBe("1,8 meses");
    expect(fila(BASE, "regimen").detalle).toBe("Supuesto: no consta la fecha de inicio");
    expect(fila({ ...BASE, plazo_pago_unidad: "habiles", plazo_pago_dias: 5 }, "plazo").valor).toBe("5 días hábiles");
  });

  it("un dato ausente se muestra como «No consta», nunca como 0", () => {
    const ausente = { ...BASE, deposito_eur: null, capital_para_pujar: null, plazo_pago_dias: null,
                      meses_inmovilizacion: null, puja_minima_aprobable: null, suelo_absoluto: null };
    for (const clave of ["deposito", "capital", "plazo", "inmovilizacion", "minima", "suelo"]) {
      expect(fila(ausente, clave).valor).toBe(NO_CONSTA);
      expect(fila(ausente, clave).detalle).toBeUndefined();
    }
  });

  it("5J-2b: los meses que se suman al plazo y su origen, como en el informe (ADR-0026)", () => {
    // BASE es un resultado anterior a la fase: solo el plazo legal.
    expect(fila(BASE, "inmovilizacion")).toMatchObject({ valor: "1,8 meses", detalle: "Plazo legal máximo" });
    const sinFecha = { ...BASE, meses_inmovilizacion_aplicados: 2.5, meses_inmovilizacion_asumidos: false };
    expect(fila(sinFecha, "inmovilizacion")).toMatchObject(
      { valor: "2,5 meses", detalle: "Régimen judicial más largo: no consta la fecha de inicio" });
    const conFecha = { ...sinFecha, regimen_asumido: false, meses_inmovilizacion_aplicados: 1.8 };
    expect(fila(conFecha, "inmovilizacion")).toMatchObject({ valor: "1,8 meses", detalle: "Plazo legal máximo" });
    const sinNorma = { ...BASE, procedimiento: "no_aplica", regimen_asumido: false, meses_inmovilizacion: null,
                       meses_inmovilizacion_aplicados: 2.5, meses_inmovilizacion_asumidos: true };
    expect(fila(sinNorma, "inmovilizacion")).toMatchObject(
      { valor: "2,5 meses", detalle: "Estimación prudente, sin base legal" });
  });

  it("mantiene el orden de la tabla del informe", () => {
    expect(filasProcedimiento(BASE).map((f) => f.clave))
      .toEqual(["regimen", "deposito", "capital", "plazo", "inmovilizacion", "minima", "segura", "suelo"]);
  });
});
