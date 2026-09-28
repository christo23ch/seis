"use client";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Overrides, ParametroEditable, ParametrosSimulables, ValorJson } from "@/lib/types";
import { Button, Check, ErrorBox, Input, Spinner } from "@/components/ui";

/** Editor de overrides de una simulación nueva.
 *
 * Todo lo que muestra sale de `GET /parametros-simulables` (Fase 5F.7.2): el
 * frontend no tiene listas, tipos, rangos ni etiquetas propias. Solo edita los
 * parámetros de tipo «numero»; las estructuras se muestran en solo lectura porque
 * el catálogo no describe su esquema. La única validación local es de ENTRADA
 * (¿es un número finito?): rangos y reglas los decide el backend. */
export function EditorSimulacion({ analisisId, creando, bloqueado, error, onCrear, onCerrar }: {
  analisisId: string;
  creando: boolean;                        // la petición de crear está en curso
  bloqueado: boolean;                      // cualquier petición de la pestaña está en curso
  error: string | null;                    // texto del backend del último intento
  onCrear: (overrides: Overrides) => void;
  onCerrar: () => void;
}) {
  const catalogo = useQuery({
    queryKey: ["parametros-simulables", analisisId],
    queryFn: () => api.parametrosSimulables(analisisId),
  });
  // Solo los campos que el usuario ha tocado; el resto muestra `valor_vigente`.
  // Se conservan aunque falle la creación: nunca se pierde lo escrito.
  const [textos, setTextos] = useState<Record<string, string>>({});
  const [busqueda, setBusqueda] = useState("");
  const [soloModificados, setSoloModificados] = useState(false);
  // Lo que el usuario abrió o cerró a mano, por grupo; sin entrada, decide `abiertoPorDefecto`.
  const [abiertosManual, setAbiertosManual] = useState<Record<string, boolean>>({});

  const estados = useMemo(() => {
    const out = new Map<string, EstadoCampo>();
    for (const p of catalogo.data?.editables ?? []) {
      if (p.tipo === "numero") out.set(p.clave, estadoCampo(p, textos[p.clave]));
    }
    return out;
  }, [catalogo.data, textos]);

  if (catalogo.isPending) return <Spinner />;
  if (catalogo.isError) {
    return <ErrorBox mensaje={`No se pudo cargar el catálogo de parámetros: ${catalogo.error.message}`} />;
  }
  const cat = catalogo.data;

  const overrides: Overrides = {};
  let conError = 0;
  for (const [clave, e] of estados) {
    if (e.error) conError++;
    else if (e.cambiado && e.valor !== null) overrides[clave] = e.valor;
  }
  const nCambios = Object.keys(overrides).length;
  const puedeCrear = nCambios > 0 && conError === 0 && !bloqueado;

  const filtro = busqueda.trim().toLowerCase();
  const visible = (p: ParametroEditable) => {
    if (filtro && !p.clave.toLowerCase().includes(filtro) && !p.nombre_legible.toLowerCase().includes(filtro)) return false;
    if (soloModificados) { const e = estados.get(p.clave); return !!e && (e.cambiado || !!e.error); }
    return true;
  };
  const grupos = agrupar(cat.editables.filter((p) => p.tipo === "numero" && visible(p)));
  const estructuras = cat.editables.filter((p) => p.tipo === "estructura" && visible(p));

  const escribir = (clave: string, texto: string) => setTextos((t) => ({ ...t, [clave]: texto }));
  const restaurar = (clave: string) => setTextos((t) => { const n = { ...t }; delete n[clave]; return n; });

  return (
    <section aria-label="Nueva simulación" className="rounded-md border border-primario/30">
      {/* Cabecera fija: avisos, contador y acciones siempre a la vista. */}
      <div className="sticky top-14 z-20 space-y-2 rounded-t-md border-b border-borde-linea bg-papel-carta px-4 py-3 md:top-0">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-tinta">Nueva simulación</h3>
          <span className="text-[13px] text-slate-600" aria-live="polite">
            <span className="cifra font-semibold">{nCambios}</span> {nCambios === 1 ? "cambio" : "cambios"}
            {conError > 0 && <span className="text-sem-rojo"> · {conError} con error</span>}
          </span>
        </div>
        <p className="text-[13px] text-slate-600">
          Solo afecta a esta simulación; <b>no cambia los parámetros del sistema</b>.
        </p>
        <p className="text-[13px] text-slate-600">
          La simulación parte del conocimiento <b>vigente</b>
          {cat.version_parametros_vigente && <> (parámetros <span className="cifra">v{cat.version_parametros_vigente}</span>)</>},
          {" "}no necesariamente del que usó el análisis original.
          {!cat.tiene_parametros_originales && (
            <> El análisis es anterior al registro de parámetros: <b>no hay valor original con el que comparar</b>.</>
          )}
        </p>
        {error && <ErrorBox mensaje={error} />}
        <div className="flex flex-wrap gap-2">
          <Button disabled={!puedeCrear} aria-disabled={!puedeCrear} cargando={creando}
            onClick={() => onCrear(overrides)}>
            Crear simulación ({nCambios} {nCambios === 1 ? "cambio" : "cambios"})
          </Button>
          <Button variante="secundario" disabled={bloqueado || Object.keys(textos).length === 0}
            onClick={() => setTextos({})}>
            Descartar cambios
          </Button>
          <Button variante="fantasma" disabled={bloqueado} onClick={onCerrar}>Cerrar</Button>
        </div>
      </div>

      <div className="space-y-4 px-4 py-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Input type="search" aria-label="Buscar parámetro" placeholder="Buscar por clave o nombre"
            value={busqueda} onChange={(e) => setBusqueda(e.target.value)} className="sm:max-w-xs" />
          <Check label="Solo modificados" checked={soloModificados}
            onChange={(e) => setSoloModificados(e.target.checked)} />
        </div>

        {grupos.length === 0 && estructuras.length === 0 && (
          <p className="text-sm text-slate-500">Ningún parámetro coincide con el filtro.</p>
        )}

        {grupos.map((g) => {
          const est = g.parametros.map((p) => estados.get(p.clave)!);
          const modificados = est.filter((e) => e.cambiado && !e.error).length;
          const errores = est.filter((e) => e.error).length;
          // Se abren solos: con cambios o errores, con una instancia del propio
          // análisis, o si hay un filtro activo (los grupos ya vienen filtrados).
          const abiertoPorDefecto = modificados > 0 || errores > 0 || filtro !== "" || soloModificados
            || g.parametros.some((p) => p.plantilla?.coincide_con_analisis === true);
          const abierto = abiertosManual[g.clave] ?? abiertoPorDefecto;
          return (
            // `open` controlado: el clic en el resumen lo decide React, no el
            // navegador, para que el estado automático y el manual no se pisen.
            <details key={g.clave} data-grupo={g.clave} open={abierto}
              className="min-w-0 rounded-md border border-borde-linea">
              <summary
                onClick={(e) => { e.preventDefault(); setAbiertosManual((m) => ({ ...m, [g.clave]: !abierto })); }}
                className="flex cursor-pointer flex-wrap items-baseline gap-x-2 gap-y-0.5 px-3 py-2 text-[12px] text-slate-600">
                <span className="font-semibold uppercase tracking-wide text-slate-500">{g.titulo}</span>
                <span>· <span className="cifra">{g.parametros.length}</span> {g.parametros.length === 1 ? "parámetro" : "parámetros"}</span>
                <span>· <span className="cifra">{modificados}</span> {modificados === 1 ? "modificado" : "modificados"}</span>
                {errores > 0 && <span className="text-sem-rojo">· <span className="cifra">{errores}</span> con error</span>}
              </summary>
              <div className="grid gap-2.5 border-t border-borde-linea p-2.5 xl:grid-cols-2">
                {g.parametros.map((p) => (
                  <CampoNumerico key={p.clave} p={p} estado={estados.get(p.clave)!} texto={textos[p.clave]}
                    bloqueado={bloqueado} escribir={escribir} restaurar={restaurar} />
                ))}
              </div>
            </details>
          );
        })}

        {estructuras.length > 0 && (
          <fieldset className="min-w-0">
            <legend className="mb-1 text-[12px] font-semibold uppercase tracking-wide text-slate-500">
              Estructuras (solo lectura)
            </legend>
            <p className="mb-2 text-[12px] text-slate-500">Edición de estructuras no disponible en esta versión.</p>
            <div className="grid gap-2.5 xl:grid-cols-2">
              {estructuras.map((p) => <Estructura key={p.clave} p={p} />)}
            </div>
          </fieldset>
        )}

        <Informativos cat={cat} />
      </div>
    </section>
  );
}

// ─────────────────────────── estado de un campo ───────────────────────────

interface EstadoCampo { valor: number | null; error: string | null; cambiado: boolean }

// Número decimal con punto o coma (una sola) y exponente opcional. Nada de separadores de miles.
const NUMERO = /^[+-]?(\d+([.,]\d*)?|[.,]\d+)([eE][+-]?\d+)?$/;

function estadoCampo(p: ParametroEditable, texto: string | undefined): EstadoCampo {
  if (texto === undefined) return { valor: null, error: null, cambiado: false };
  const limpio = texto.trim();
  const n = NUMERO.test(limpio) ? Number(limpio.replace(",", ".")) : NaN;
  if (!Number.isFinite(n)) return { valor: null, error: "No es un número", cambiado: true };
  return { valor: n, error: null, cambiado: n !== p.valor_vigente };
}

// ─────────────────────────── agrupación (sin etiquetas propias) ───────────────────────────

interface Grupo { clave: string; titulo: string; parametros: ParametroEditable[] }

/** Fijos por el primer segmento de su clave; instancias de plantilla por
 * `plantilla.dimension`. Los títulos salen de esos mismos datos. */
function agrupar(parametros: ParametroEditable[]): Grupo[] {
  const mapa = new Map<string, Grupo>();
  for (const p of parametros) {
    const clave = p.plantilla ? `plantilla:${p.plantilla.dimension}` : `fijo:${p.clave.split(".")[0]}`;
    const titulo = p.plantilla ? `Por ${p.plantilla.dimension}` : p.clave.split(".")[0];
    if (!mapa.has(clave)) mapa.set(clave, { clave, titulo, parametros: [] });
    mapa.get(clave)!.parametros.push(p);
  }
  // Fijos primero, luego plantillas; dentro, el orden que ya da el backend.
  return [...mapa.values()].sort((a, b) =>
    (a.clave.startsWith("plantilla") ? 1 : 0) - (b.clave.startsWith("plantilla") ? 1 : 0) || a.clave.localeCompare(b.clave));
}

// ─────────────────────────── piezas ───────────────────────────

const sinDefinir = (t: string) => (t === "pendiente_de_definir" ? "sin definir" : t);
const mostrar = (v: ValorJson | null) =>
  v === null ? "—" : typeof v === "object" ? JSON.stringify(v) : String(v);

function Marca({ children, fuerte = false }: { children: React.ReactNode; fuerte?: boolean }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
      fuerte ? "bg-primario text-white" : "border border-borde-control bg-white text-tinta"}`}>
      {children}
    </span>
  );
}

function CampoNumerico({ p, estado, texto, bloqueado, escribir, restaurar }: {
  p: ParametroEditable; estado: EstadoCampo; texto: string | undefined; bloqueado: boolean;
  escribir: (clave: string, texto: string) => void; restaurar: (clave: string) => void;
}) {
  const id = `param-${p.clave}`;
  const idError = `${id}-error`;
  return (
    <div data-parametro={p.clave}
      className={`min-w-0 rounded-md border px-3 py-2.5 ${estado.cambiado ? "border-primario/40 bg-primario-tenue/40" : "border-borde-linea"}`}>
      <div className="flex flex-wrap items-center gap-1.5">
        <label htmlFor={id} className="text-[13px] font-medium text-tinta">{p.nombre_legible}</label>
        {p.plantilla?.coincide_con_analisis === true && <Marca>de este análisis</Marca>}
        {p.difiere_de_original === true && <Marca>difiere del original</Marca>}
        {estado.cambiado && !estado.error && <Marca fuerte>modificado</Marca>}
      </div>
      <div className="cifra break-all text-[11px] text-slate-500">{p.clave} · {p.modulo}</div>
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        <Input id={id} inputMode="decimal" autoComplete="off" disabled={bloqueado}
          value={texto ?? String(p.valor_vigente)}
          onChange={(e) => escribir(p.clave, e.target.value)}
          aria-invalid={!!estado.error} aria-describedby={estado.error ? idError : undefined}
          className={`cifra !w-36 text-right ${estado.error ? "!border-sem-rojo" : ""}`} />
        <span className="min-w-0 text-[12px] text-slate-500">{p.unidad}</span>
        {texto !== undefined && (
          <Button variante="fantasma" className="!px-2 !py-1 text-[12px]" disabled={bloqueado}
            onClick={() => restaurar(p.clave)}>
            Restaurar
          </Button>
        )}
      </div>
      {estado.error && <p id={idError} className="mt-1 text-[12px] text-sem-rojo">{estado.error}</p>}
      <p className="mt-1 text-[12px] text-slate-500">
        Vigente <span className="cifra">{mostrar(p.valor_vigente)}</span>
        {" · "}Original <span className="cifra">{mostrar(p.valor_original)}</span>
        {Array.isArray(p.rango) && <> · Cota técnica <span className="cifra">{p.rango[0]}–{p.rango[1]}</span></>}
      </p>
      <Detalles p={p} />
    </div>
  );
}

function Estructura({ p }: { p: ParametroEditable }) {
  return (
    <div data-parametro={p.clave} className="min-w-0 rounded-md border border-dashed border-borde-control px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[13px] font-medium text-tinta">{p.nombre_legible}</span>
        <Marca>solo lectura</Marca>
        {p.plantilla?.coincide_con_analisis === true && <Marca>de este análisis</Marca>}
        {p.difiere_de_original === true && <Marca>difiere del original</Marca>}
      </div>
      <div className="cifra break-all text-[11px] text-slate-500">{p.clave} · {p.modulo}</div>
      <details className="mt-1.5">
        <summary className="cursor-pointer text-[12px] text-slate-600">Valor vigente</summary>
        <pre className="cifra mt-1 max-h-60 overflow-auto whitespace-pre-wrap break-all rounded bg-slate-50 p-2 text-[11px]">
          {JSON.stringify(p.valor_vigente, null, 2)}
        </pre>
      </details>
      <Detalles p={p} />
    </div>
  );
}

function Detalles({ p }: { p: ParametroEditable }) {
  return (
    <details className="mt-1">
      <summary className="cursor-pointer text-[12px] text-slate-600">Descripción y advertencias</summary>
      <dl className="mt-1 space-y-1 text-[12px] text-slate-600">
        <div><dt className="inline font-semibold">Descripción: </dt><dd className="inline">{sinDefinir(p.descripcion)}</dd></div>
        <div><dt className="inline font-semibold">Advertencia: </dt><dd className="inline">{sinDefinir(p.advertencia)}</dd></div>
        <div><dt className="inline font-semibold">Impacto: </dt><dd className="inline">{sinDefinir(p.impacto)}</dd></div>
        <div><dt className="inline font-semibold">Unidad: </dt><dd className="inline">{p.unidad}</dd></div>
        <div className="break-all"><dt className="inline font-semibold">Origen: </dt><dd className="inline cifra">{p.origen}</dd></div>
      </dl>
    </details>
  );
}

function Informativos({ cat }: { cat: ParametrosSimulables }) {
  return (
    <details className="rounded-md border border-borde-linea px-3 py-2">
      <summary className="cursor-pointer text-[13px] font-medium text-slate-600">
        No editables ({cat.no_editables.length}) y cálculos derivados ({cat.derivados.length}) — informativo
      </summary>
      <div className="mt-2 space-y-3 text-[12px] text-slate-600">
        <div>
          <p className="font-semibold">Constantes del código (no editables)</p>
          <ul className="mt-1 space-y-1">
            {cat.no_editables.map((n) => (
              <li key={n.clave} className="break-words">
                <span className="cifra">{n.clave}</span> — {n.nombre_legible}. {n.descripcion}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-semibold">Cálculos derivados (sin clave editable)</p>
          <ul className="mt-1 space-y-1">
            {cat.derivados.map((d) => (
              <li key={d.nombre} className="break-words">
                <span className="cifra">{d.nombre}</span> ({d.modulo}) — {d.descripcion}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </details>
  );
}
