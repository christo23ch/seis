"use client";
import { Loader2 } from "lucide-react";
import { cloneElement, createContext, isValidElement, useContext, useEffect, useId, useRef, useState } from "react";

export const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(" ");

export function Button({ variante = "primario", className, cargando, children, ...p }:
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variante?: "primario" | "secundario" | "peligro" | "fantasma"; cargando?: boolean }) {
  const base = "inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none";
  const v = {
    primario: "bg-primario text-white hover:bg-primario-hover",
    secundario: "bg-white text-tinta border border-borde-control hover:bg-slate-50",
    peligro: "bg-sem-rojo text-white hover:opacity-90",
    fantasma: "text-slate-600 hover:bg-slate-100",
  }[variante];
  return (
    <button className={cx(base, v, className)} disabled={cargando || p.disabled} {...p}>
      {cargando && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export const Card = ({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cx("rounded-lg border border-borde-linea bg-papel-carta shadow-carta", className)} {...p} />
);
export const CardHeader = ({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cx("border-b border-borde-linea px-5 py-3.5", className)} {...p} />
);
export const CardTitle = ({ className, ...p }: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={cx("text-[13px] font-semibold uppercase tracking-wide text-slate-500", className)} {...p} />
);
export const CardContent = ({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cx("px-5 py-4", className)} {...p} />
);

export const Label = ({ className, ...p }: React.LabelHTMLAttributes<HTMLLabelElement>) => (
  <label className={cx("mb-1 block text-[13px] font-medium text-slate-600", className)} {...p} />
);
export const Input = ({ className, ...p }: React.InputHTMLAttributes<HTMLInputElement>) => (
  <input className={cx("w-full rounded-md border border-borde-control bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus:border-primario aria-[invalid=true]:border-sem-rojo", className)} {...p} />
);
export const Select = ({ className, ...p }: React.SelectHTMLAttributes<HTMLSelectElement>) => (
  <select className={cx("w-full rounded-md border border-borde-control bg-white px-3 py-2 text-sm aria-[invalid=true]:border-sem-rojo", className)} {...p} />
);
export const Textarea = ({ className, ...p }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) => (
  <textarea className={cx("w-full rounded-md border border-borde-control bg-white px-3 py-2 font-cifra text-xs", className)} {...p} />
);
// `label` es ReactNode y no string: las casillas de consentimiento (Fase 14)
// llevan dentro el enlace al texto que se acepta. `items-start` porque esas
// etiquetas ocupan varias líneas y con `items-center` la casilla queda flotando
// a media altura del párrafo.
export const Check = ({ label, className, ...p }: React.InputHTMLAttributes<HTMLInputElement> & { label: React.ReactNode }) => (
  <label className={cx("flex cursor-pointer items-start gap-2 text-sm text-slate-700", className)}>
    <input type="checkbox" className="mt-0.5 h-4 w-4 shrink-0 rounded border-borde-control accent-[#2E4B8F]" {...p} />
    <span>{label}</span>
  </label>
);

/** Campo con etiqueta, ayuda y error. Fase 5I-B: la etiqueta se asocia al
 * control (`htmlFor`), los obligatorios llevan marca visible (`*`, oculta al
 * lector, que oye `aria-required`) y el control recibe `aria-invalid` y
 * `aria-describedby` hacia su error y su ayuda. El hijo debe ser UN control que
 * acepte `id` y `aria-*` (`Input`, `Select`); lo que traiga propio se respeta:
 * su `id` y su `aria-describedby` se conservan y se combinan. */
export function Campo({ label, error, children, ayuda, obligatorio }:
  { label: string; error?: string; ayuda?: string; obligatorio?: boolean; children: React.ReactNode }) {
  const base = useId();
  const hijo = isValidElement<Record<string, unknown>>(children) ? children : null;
  const idControl = (hijo?.props.id as string | undefined) ?? `${base}-control`;
  const idError = `${base}-error`;
  const idAyuda = `${base}-ayuda`;
  const describe = [hijo?.props["aria-describedby"] as string | undefined,
                    error ? idError : undefined, ayuda ? idAyuda : undefined].filter(Boolean).join(" ");
  const control = hijo
    ? cloneElement(hijo, {
        id: idControl,
        "aria-invalid": error ? true : hijo.props["aria-invalid"],
        "aria-describedby": describe || undefined,
        "aria-required": obligatorio || hijo.props["aria-required"],
      })
    : children;
  return (
    <div>
      <Label htmlFor={hijo ? idControl : undefined}>
        {label}
        {obligatorio && <span className="ml-0.5 text-sem-rojo" aria-hidden="true">*</span>}
      </Label>
      {control}
      {error && <p id={idError} className="mt-1 text-[12px] text-sem-rojo" data-error-campo="">{error}</p>}
      {ayuda && <p id={idAyuda} className="mt-1 text-[12px] text-slate-500">{ayuda}</p>}
    </div>
  );
}

export const Badge = ({ tono = "neutro", className, ...p }: React.HTMLAttributes<HTMLSpanElement> & { tono?: "neutro" | "verde" | "amarillo" | "naranja" | "rojo" | "azul" }) => {
  const t = {
    neutro: "bg-slate-100 text-slate-600",
    verde: "bg-sem-verdebg text-sem-verde",
    amarillo: "bg-sem-amarillobg text-sem-amarillo",
    naranja: "bg-sem-naranjabg text-sem-naranja",
    rojo: "bg-sem-rojobg text-sem-rojo",
    azul: "bg-primario-tenue text-primario",
  }[tono];
  return <span className={cx("inline-flex items-center rounded-full px-2.5 py-0.5 text-[12px] font-semibold", t, className)} {...p} />;
};

export const Spinner = () => (
  <div className="flex items-center justify-center py-16 text-slate-400">
    <Loader2 className="h-6 w-6 animate-spin" />
  </div>
);

/** Caja de error. `role="alert"` por defecto (un fallo que acaba de ocurrir se
 * anuncia); un estado persistente e informativo pasa `rol="status"`. */
export function ErrorBox({ mensaje, children, rol = "alert", ...p }:
  { mensaje: string; children?: React.ReactNode; rol?: "alert" | "status"; ref?: React.Ref<HTMLDivElement> }
  & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div role={rol} {...p} className="rounded-md border border-sem-rojo/30 bg-sem-rojobg px-4 py-3 text-sm text-sem-rojo">
      {mensaje}
      {children}
    </div>
  );
}

/* Tabs mínimas controladas */
const TabsCtx = createContext<{ v: string; set: (v: string) => void }>({ v: "", set: () => {} });
export function Tabs({ defecto, children }: { defecto: string; children: React.ReactNode }) {
  const [v, set] = useState(defecto);
  return <TabsCtx.Provider value={{ v, set }}>{children}</TabsCtx.Provider>;
}
export function TabsLista({ items }: { items: { valor: string; etiqueta: string }[] }) {
  const { v, set } = useContext(TabsCtx);
  return (
    <div className="mb-4 flex flex-wrap gap-1 border-b border-borde-linea">
      {items.map((i) => (
        <button key={i.valor} onClick={() => set(i.valor)}
          className={cx("border-b-2 px-3 py-2 text-sm font-medium",
            v === i.valor ? "border-primario text-primario" : "border-transparent text-slate-500 hover:text-tinta")}>
          {i.etiqueta}
        </button>
      ))}
    </div>
  );
}
export function TabPanel({ valor, children }: { valor: string; children: React.ReactNode }) {
  const { v } = useContext(TabsCtx);
  return v === valor ? <div>{children}</div> : null;
}

export function Stat({ etiqueta, valor, sub, cifra = true }: { etiqueta: string; valor: React.ReactNode; sub?: string; cifra?: boolean }) {
  return (
    <Card>
      <CardContent className="py-3.5">
        <div className="text-[12px] font-medium uppercase tracking-wide text-slate-500">{etiqueta}</div>
        <div className={cx("mt-1 text-xl font-semibold", cifra && "cifra")}>{valor}</div>
        {sub && <div className="mt-0.5 text-[12px] text-slate-400">{sub}</div>}
      </CardContent>
    </Card>
  );
}

/** Diálogo de confirmación sobre `<dialog>` nativo: `showModal()` ya da foco
 * dentro, cierre con Escape y fondo inerte, sin librerías. Compartido por la
 * pestaña Simulaciones (validar, descartar) y por Informes oficiales (emitir). */
export function Confirmacion({ abierta, titulo, texto, boton, peligro, onConfirmar, onCancelar }: {
  abierta: boolean; titulo: string; texto: string; boton: string; peligro?: boolean;
  onConfirmar: () => void; onCancelar: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const idTitulo = useId();
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (abierta && !d.open) d.showModal();
    if (!abierta && d.open) d.close();
  }, [abierta]);
  return (
    <dialog ref={ref} onCancel={(e) => { e.preventDefault(); onCancelar(); }} aria-labelledby={idTitulo}
      className="w-[min(440px,calc(100vw-32px))] rounded-lg border border-borde-linea p-0 shadow-carta backdrop:bg-tinta/40">
      <div className="px-5 py-4">
        <h2 id={idTitulo} className="text-base font-semibold text-tinta">{titulo}</h2>
        <p className="mt-2 text-sm text-slate-600">{texto}</p>
      </div>
      <div className="flex justify-end gap-2 border-t border-borde-linea px-5 py-3">
        <Button variante="fantasma" onClick={onCancelar}>Cancelar</Button>
        <Button variante={peligro ? "peligro" : "primario"} onClick={onConfirmar}>{boton}</Button>
      </div>
    </dialog>
  );
}
