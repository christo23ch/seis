// `useGrouping: "always"`: es-ES no agrupa por defecto los números de 4 cifras
// (minimumGroupingDigits = 2 en CLDR) y salía «7600 €» frente al «7.600 €» del
// informe. Solo afecta a `eur`; `num`, `pct` y `fecha` siguen igual.
const EUR = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0, useGrouping: "always" });
export const eur = (n: number | null | undefined) => (n == null ? "—" : EUR.format(n));
export const pct = (n: number | null | undefined, dec = 1) =>
  n == null ? "—" : `${(n * 100).toFixed(dec).replace(".", ",")} %`;
/** Tasa anual como porcentaje sin ceros sobrantes (Fase 5G.4), como `formato.tasa`
 * del backend: 0.015 → «1,5 %», 0.0125 → «1,25 %», 0.06 → «6 %». */
export const tasa = (n: number) =>
  // `Number(...)` quita los ceros sobrantes sin expresiones regulares: «1.50» → 1.5.
  `${String(Number((n * 100).toFixed(2))).replace(".", ",")} %`;
/** Diferencia en puntos porcentuales con signo (Fase 5H.1-A): 32.37 → «+32,37 puntos». */
export const puntos = (n: number | null | undefined) =>
  n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(2).replace(".", ",")} puntos`;
export const num = (n: number | null | undefined, dec = 0) =>
  n == null ? "—" : new Intl.NumberFormat("es-ES", { maximumFractionDigits: dec }).format(n);
export const fecha = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" }) : "—";
