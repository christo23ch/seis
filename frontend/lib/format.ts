// `useGrouping: "always"`: es-ES no agrupa por defecto los números de 4 cifras
// (minimumGroupingDigits = 2 en CLDR) y salía «7600 €» frente al «7.600 €» del
// informe. Solo afecta a `eur`; `num`, `pct` y `fecha` siguen igual.
const EUR = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0, useGrouping: "always" });
export const eur = (n: number | null | undefined) => (n == null ? "—" : EUR.format(n));
export const pct = (n: number | null | undefined, dec = 1) =>
  n == null ? "—" : `${(n * 100).toFixed(dec).replace(".", ",")} %`;
export const num = (n: number | null | undefined, dec = 0) =>
  n == null ? "—" : new Intl.NumberFormat("es-ES", { maximumFractionDigits: dec }).format(n);
export const fecha = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" }) : "—";
