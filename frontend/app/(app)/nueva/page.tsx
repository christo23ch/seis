"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FormProvider, useFieldArray, useFormContext, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { api } from "@/lib/api";
import { PASOS, aPayload, esquemaAnalisis, valoresIniciales, type ValoresAnalisis } from "@/lib/schema";
import type { Opciones, Resultado } from "@/lib/types";
import { Button, Campo, Card, CardContent, CardHeader, CardTitle, Check, ErrorBox, Input, Select, Spinner } from "@/components/ui";
import { CondicionesVetos, EscaleraPrecios, EscenariosPanel, IcoDesglose, MetricasClave, RiesgosPanel, SemaforoHero } from "@/components/resultado";
import { Check as CheckIcon, ChevronLeft, ChevronRight, Plus, RefreshCw, Save, Trash2 } from "lucide-react";

/* ── utilidades de formulario ─────────────────────────────────────────── */
function getError(errors: any, path: string): string | undefined {
  const nodo = path.split(".").reduce((acc: any, k) => (acc ? acc[k] : undefined), errors);
  return nodo?.message ?? nodo?.root?.message;
}
function FIn({ name, label, tipo = "text", ayuda, step, placeholder }:
  { name: string; label: string; tipo?: string; ayuda?: string; step?: string; placeholder?: string }) {
  const { register, formState: { errors } } = useFormContext();
  return (
    <Campo label={label} error={getError(errors, name)} ayuda={ayuda}>
      <Input type={tipo} step={step} placeholder={placeholder} {...register(name as never)} />
    </Campo>
  );
}
function FSel({ name, label, opciones, ayuda }:
  { name: string; label: string; opciones: { v: string; t: string }[]; ayuda?: string }) {
  const { register, formState: { errors } } = useFormContext();
  return (
    <Campo label={label} error={getError(errors, name)} ayuda={ayuda}>
      <Select {...register(name as never)}>
        {opciones.map((o) => <option key={o.v} value={o.v}>{o.t}</option>)}
      </Select>
    </Campo>
  );
}
function FCheck({ name, label }: { name: string; label: string }) {
  const { register } = useFormContext();
  return <Check label={label} {...register(name as never)} />;
}
function FSlider({ name, label }: { name: string; label: string }) {
  const { register, watch } = useFormContext();
  const v = watch(name as never) as unknown as number;
  return (
    <div>
      <div className="mb-1 flex justify-between text-[13px]">
        <span className="font-medium text-slate-600">{label}</span>
        <span className="cifra text-slate-500">{v}</span>
      </div>
      <input type="range" min={0} max={100} step={5} className="w-full accent-[#2E4B8F]" {...register(name as never)} />
    </div>
  );
}
const cap = (s: string) => s.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
const aOps = (xs: string[]) => xs.map((x) => ({ v: x, t: cap(x) }));

/* ── pasos ────────────────────────────────────────────────────────────── */
function Paso1({ op }: { op?: Opciones }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <FSel name="perfil" label="Perfil de inversión"
        opciones={Object.entries(op?.perfiles ?? { flip_integral: "Reforma integral + venta" }).map(([v, t]) => ({ v, t }))} />
      <FSel name="subasta.fuente" label="Fuente de la subasta" opciones={aOps(op?.fuentes ?? ["judicial_boe"])} />
      <FIn name="subasta.valor_subasta" label="Valor de subasta / tasación (€)" tipo="number" step="any" />
      <FIn name="subasta.puja_minima" label="Puja mínima (€, opcional)" tipo="number" step="any" />
      <FIn name="subasta.deposito_pct" label="Depósito (%)" tipo="number" step="0.5" />
      <FIn name="subasta.horas_hasta_cierre" label="Horas hasta el cierre (opcional)" tipo="number" step="1" />
      <FIn name="subasta.subastas_desiertas_previas" label="Subastas previas desiertas" tipo="number" step="1" />
      <FIn name="subasta.identificador_externo" label="Identificador / expediente (opcional)" />
    </div>
  );
}
function Paso2({ op }: { op?: Opciones }) {
  const { watch } = useFormContext();
  const vpo = watch("activo.vpo");
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <FSel name="activo.tipologia" label="Tipología" opciones={aOps(op?.tipologias ?? ["vivienda"])} />
      <FIn name="activo.superficie_m2" label="Superficie construida (m²)" tipo="number" step="any" />
      <FSel name="activo.estado_conservacion" label="Estado de conservación"
        opciones={aOps(op?.estados_conservacion ?? ["regular"])} />
      <FIn name="activo.anio_construccion" label="Año de construcción (opcional)" tipo="number" step="1" />
      <div className="space-y-2.5 sm:col-span-2">
        <FCheck name="activo.es_vivienda_habitual" label="Vivienda habitual del ejecutado (plazos posesorios reforzados)" />
        <FCheck name="activo.vpo" label="Vivienda de protección oficial (VPO)" />
      </div>
      {vpo && <FIn name="activo.vpo_precio_max_legal" label="Precio máximo legal VPO (€)" tipo="number" step="any" />}
    </div>
  );
}
function Paso3() {
  const { control, watch } = useFormContext<ValoresAnalisis>();
  const { fields, append, remove } = useFieldArray({ control, name: "cargas" });
  const estadoOcu = watch("ocupacion.estado");
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <FIn name="activo.ref_catastral" label="Referencia catastral (opcional)" />
        <FIn name="activo.finca_registral" label="Finca registral (opcional)" />
      </div>
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-sm font-semibold text-slate-700">Cargas registrales</h4>
          <Button type="button" variante="secundario" onClick={() =>
            append({ tipo: "embargo", importe: undefined, es_anterior: false, se_purga: true,
                     verificada: false, prohibicion_disponer: false, condicion_resolutoria: false } as never)}>
            <Plus className="h-4 w-4" /> Añadir carga
          </Button>
        </div>
        {fields.length === 0 && <p className="text-[13px] text-slate-400">Sin cargas declaradas. Si la nota simple muestra cargas anteriores, decláralas: el motor las cuantifica o veta.</p>}
        <div className="space-y-3">
          {fields.map((f, i) => (
            <div key={f.id} className="rounded-md border border-slate-200 p-3">
              <div className="grid gap-3 sm:grid-cols-3">
                <FSel name={`cargas.${i}.tipo`} label="Tipo"
                  opciones={aOps(["embargo", "hipoteca", "afeccion_fiscal", "anotacion", "servidumbre", "otro"])} />
                <FIn name={`cargas.${i}.importe`} label="Importe (€) — vacío si indeterminado" tipo="number" step="any" />
                <div className="flex items-end justify-end">
                  <Button type="button" variante="fantasma" onClick={() => remove(i)}><Trash2 className="h-4 w-4" /> Quitar</Button>
                </div>
              </div>
              <div className="mt-2 grid gap-2 sm:grid-cols-3">
                <FCheck name={`cargas.${i}.es_anterior`} label="Anterior a la que se ejecuta" />
                <FCheck name={`cargas.${i}.se_purga`} label="Se purga con la adjudicación" />
                <FCheck name={`cargas.${i}.verificada`} label="Verificada con nota ≤ 5 días" />
                <FCheck name={`cargas.${i}.prohibicion_disponer`} label="Prohibición de disponer" />
                <FCheck name={`cargas.${i}.condicion_resolutoria`} label="Condición resolutoria" />
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <FSel name="ocupacion.estado" label="Situación posesoria declarada"
          opciones={aOps(["desconocida", "vacio", "propietario", "precario", "arrendado_posterior", "arrendado_anterior", "renta_antigua"])}
          ayuda="Si es desconocida, el motor asume precario (prudencia P5) y exige verificación in situ." />
        {estadoOcu.startsWith("arrendado") || estadoOcu === "renta_antigua" ? (
          <FIn name="ocupacion.renta_mensual" label="Renta mensual actual (€)" tipo="number" step="any" />
        ) : null}
      </div>
    </div>
  );
}
function Paso4() {
  return (
    <div className="space-y-3">
      <FCheck name="urbanistico.uso_compatible" label="El uso previsto por la estrategia es compatible con la norma zonal" />
      <FCheck name="urbanistico.fuera_ordenacion" label="Edificio en situación de fuera de ordenación" />
      <FCheck name="urbanistico.orden_demolicion" label="Orden de demolición o disciplina urbanística no caducada" />
      <FCheck name="urbanistico.suelo_protegido" label="Suelo rústico protegido" />
      <FCheck name="urbanistico.servidumbres_incompatibles" label="Servidumbres incompatibles con la estrategia" />
      <FCheck name="urbanistico.zona_inundable_alta" label="Zona inundable de alta probabilidad (SNCZI)" />
      <div className="max-w-xs pt-1">
        <FIn name="urbanistico.cargas_urbanizacion" label="Cargas de urbanización pendientes (€)" tipo="number" step="any" />
      </div>
    </div>
  );
}
function Paso5({ op }: { op?: Opciones }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <FIn name="activo.direccion" label="Dirección" />
        <FIn name="activo.municipio" label="Municipio" />
        <FIn name="activo.provincia" label="Provincia" />
        <FSel name="activo.ccaa" label="Comunidad autónoma (fiscalidad T3)" opciones={aOps(op?.ccaa ?? ["madrid"])} />
        <FIn name="activo.lat" label="Latitud (opcional)" tipo="number" step="any" placeholder="40.4168" />
        <FIn name="activo.lng" label="Longitud (opcional)" tipo="number" step="any" placeholder="-3.7038" />
      </div>
      <div>
        <h4 className="mb-3 text-sm font-semibold text-slate-700">Indicadores micro de la ubicación (0–100)</h4>
        <div className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
          <FSlider name="zona.micro.transporte" label="Transporte" />
          <FSlider name="zona.micro.seguridad" label="Seguridad" />
          <FSlider name="zona.micro.sanidad" label="Sanidad" />
          <FSlider name="zona.micro.educacion" label="Educación" />
          <FSlider name="zona.micro.comercio" label="Comercio" />
          <FSlider name="zona.micro.zonas_verdes" label="Zonas verdes" />
          <FSlider name="zona.micro.pipeline_urbanistico" label="Pipeline urbanístico verificado" />
          <FSlider name="zona.micro.potencial_transformacion" label="Potencial de transformación" />
          <FSlider name="zona.micro.entorno_construido" label="Entorno construido" />
        </div>
      </div>
    </div>
  );
}
function Paso6() {
  const { control, formState: { errors } } = useFormContext<ValoresAnalisis>();
  const { fields, append, remove } = useFieldArray({ control, name: "comparables" });
  const errRaiz = (errors.comparables as any)?.message ?? (errors.comparables as any)?.root?.message;
  return (
    <div className="space-y-6">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-sm font-semibold text-slate-700">Comparables de salida (€/m²)</h4>
          <Button type="button" variante="secundario" onClick={() =>
            append({ precio_m2: 0, estado: "reformado", origen: "testigo", meses_antiguedad: 0 } as never)}>
            <Plus className="h-4 w-4" /> Añadir comparable
          </Button>
        </div>
        {errRaiz && <p className="mb-2 text-[12px] text-sem-rojo">{errRaiz}</p>}
        <div className="space-y-2">
          {fields.map((f, i) => (
            <div key={f.id} className="grid items-end gap-3 rounded-md border border-slate-200 p-3 sm:grid-cols-5">
              <FIn name={`comparables.${i}.precio_m2`} label="€/m²" tipo="number" step="any" />
              <FSel name={`comparables.${i}.estado`} label="Estado" opciones={aOps(["reformado", "bueno", "regular", "malo", "ruina"])} />
              <FSel name={`comparables.${i}.origen`} label="Origen" opciones={aOps(["testigo", "portal_oferta", "notarial", "registro"])} />
              <FIn name={`comparables.${i}.meses_antiguedad`} label="Antigüedad (meses)" tipo="number" step="1" />
              <Button type="button" variante="fantasma" onClick={() => remove(i)}><Trash2 className="h-4 w-4" /> Quitar</Button>
            </div>
          ))}
        </div>
        <p className="mt-2 text-[12px] text-slate-400">El ICI exige n ≥ 6 con CV ≤ 20 % para puntuar el bloque de comparables (§6.2).</p>
      </div>
      <div>
        <h4 className="mb-3 text-sm font-semibold text-slate-700">Mercado macro de la zona</h4>
        <div className="grid gap-4 sm:grid-cols-3">
          <FIn name="zona.macro.tendencia_5a_pct" label="Tendencia precio 5a (%/año)" tipo="number" step="any" />
          <FIn name="zona.macro.stock_meses" label="Stock (meses de absorción)" tipo="number" step="any" />
          <FIn name="zona.macro.dom_venta_dias" label="DOM venta (días)" tipo="number" step="1" />
          <FIn name="zona.macro.dom_alquiler_dias" label="DOM alquiler (días)" tipo="number" step="1" />
          <FIn name="zona.macro.crecimiento_pobl_5a_pct" label="Crecimiento población 5a (%)" tipo="number" step="any" />
          <FIn name="zona.macro.renta_hogar" label="Renta media hogar (€)" tipo="number" step="any" />
          <FIn name="zona.macro.y_zona_pct" label="Yield neta zona (%)" tipo="number" step="any" />
          <FIn name="zona.precio_m2_p85" label="€/m² percentil 85 zona (opcional)" tipo="number" step="any" />
        </div>
      </div>
    </div>
  );
}
function Paso7() {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-3">
        <FSel name="costes.regimen_fiscal" label="Régimen fiscal" opciones={aOps(["auto", "itp", "iva"])}
          ayuda="Auto: el motor aplica el árbol §8.7.3 con los datos declarados." />
        <FIn name="costes.itp_tipo_override" label="ITP manual (%) — opcional" tipo="number" step="any"
          ayuda="Si se deja vacío se usa la tabla T3 de la CCAA." />
        <FIn name="costes.plusvalia_municipal_estimada" label="Plusvalía municipal estimada (€)" tipo="number" step="any" />
        <FIn name="costes.valor_referencia_catastral" label="Valor de referencia del Catastro (€) — opcional" tipo="number" step="any"
          ayuda="El ITP se liquida sobre el MAYOR de (valor de referencia, valor declarado, precio de remate). Si se deja vacío el motor usa el remate como suelo y avisa de que el impuesto es un mínimo." />
        <FIn name="costes.valor_declarado" label="Valor declarado en escritura (€) — opcional" tipo="number" step="any"
          ayuda="Solo si difiere del precio de remate." />
      </div>
      <div className="space-y-2.5">
        <FCheck name="costes.transmitente_empresario" label="El transmitente es empresario o profesional" />
        <FCheck name="costes.primera_entrega" label="Primera entrega (obra nueva)" />
        <FCheck name="costes.comprador_deduce_iva" label="El comprador puede deducir IVA (inversión del sujeto pasivo)" />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <FIn name="costes.atrasos_comunidad_ibi" label="Atrasos comunidad/IBI conocidos (€)" tipo="number" step="any"
          ayuda="Vacío ⇒ estimación prudente al alza (P5)." />
        <FIn name="costes.tenencia_mensual" label="Coste de tenencia mensual (€)" tipo="number" step="any"
          ayuda="IBI/12 + comunidad + seguro + suministros. Vacío ⇒ valor por defecto T3." />
        <FIn name="costes.adquisicion_fija_override" label="Costes fijos de adquisición (€)" tipo="number" step="any"
          ayuda="Notaría + registro + gestoría + procurador. Vacío ⇒ estimación T3." />
      </div>
    </div>
  );
}
function Paso8() {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-3">
        <FSel name="reforma.nivel_override" label="Nivel de reforma (vacío = automático por estado)"
          opciones={[{ v: "", t: "Automático" }, ...aOps(["ninguna", "refresco", "ligera", "media", "integral", "estructural"])]} />
        <FIn name="reforma.k_provincia" label="Coeficiente provincial de costes" tipo="number" step="0.01" />
        <FIn name="reforma.coste_m2_override" label="€/m² manual (opcional)" tipo="number" step="any" />
        <FIn name="reforma.partidas_extra" label="Partidas extra conocidas (€)" tipo="number" step="any"
          ayuda="Derramas, amianto, refuerzos… importes ya identificados." />
      </div>
      <FCheck name="reforma.visita_interior" label="Se ha visitado el interior (reduce el spread P80 del presupuesto)" />
    </div>
  );
}
function Paso9() {
  const { watch } = useFormContext();
  const tipo = watch("financiacion.tipo");
  const perfil = watch("perfil");
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <FSel name="financiacion.tipo" label="Estructura de pago" opciones={[{ v: "cash", t: "100 % equity (cash)" }, { v: "hipoteca", t: "Con hipoteca" }]} />
        {tipo === "hipoteca" && (
          <>
            <FIn name="financiacion.ltv" label="LTV (%)" tipo="number" step="1" />
            <FIn name="financiacion.interes_anual_pct" label="Interés anual (%)" tipo="number" step="0.1" />
            <div className="sm:col-span-3">
              <FCheck name="financiacion.preaprobada" label="Financiación preaprobada en firme (sin preaprobación ⇒ VETO-FIN-01)" />
            </div>
          </>
        )}
      </div>
      {perfil === "rentista" && (
        <div>
          <h4 className="mb-3 text-sm font-semibold text-slate-700">Explotación en alquiler (perfil rentista)</h4>
          <div className="grid gap-4 sm:grid-cols-3">
            <FIn name="rentista.renta_mensual_estimada" label="Renta mensual de mercado (€)" tipo="number" step="any" />
            <FIn name="rentista.vacancia_pct" label="Vacancia (%)" tipo="number" step="any" />
            <FIn name="rentista.ibi_anual" label="IBI anual (€)" tipo="number" step="any" />
            <FIn name="rentista.comunidad_mensual" label="Comunidad mensual (€)" tipo="number" step="any" />
            <FIn name="rentista.seguro_anual" label="Seguro anual (€)" tipo="number" step="any" />
            <FIn name="rentista.mantenimiento_pct_renta" label="Mantenimiento (% renta)" tipo="number" step="any" />
          </div>
        </div>
      )}
    </div>
  );
}
function Paso10() {
  const { watch } = useFormContext();
  const nota = watch("documentos.nota_simple");
  return (
    <div className="space-y-5">
      <p className="text-[13px] text-slate-500">
        Marque la documentación realmente disponible. La ausencia degrada el ICI y endurece precios y semáforo — nunca se rellena a favor (P4/P5).
      </p>
      <div className="grid gap-2.5 sm:grid-cols-2">
        <FCheck name="documentos.nota_simple" label="Nota simple registral" />
        <FCheck name="documentos.cert_cargas" label="Certificación de cargas / condiciones" />
        <FCheck name="documentos.posesion_verificada" label="Situación posesoria verificada in situ" />
        <FCheck name="documentos.avaluo" label="Avalúo / tasación de la subasta" />
        <FCheck name="documentos.fotos_interior_o_visita" label="Fotos interiores o visita" />
        <FCheck name="documentos.fotos_exterior" label="Fotos exteriores recientes" />
        <FCheck name="documentos.cert_comunidad" label="Certificado de deuda de comunidad" />
        <FCheck name="documentos.recibo_ibi" label="Último recibo de IBI" />
        <FCheck name="documentos.ite_cee" label="ITE / IEE y certificado energético" />
        <FCheck name="documentos.catastro_conciliado" label="Catastro conciliado con registro" />
      </div>
      {nota && (
        <div className="max-w-xs">
          <FIn name="documentos.nota_simple_dias" label="Antigüedad de la nota simple (días)" tipo="number" step="1" />
        </div>
      )}
      <div>
        <h4 className="mb-2 text-sm font-semibold text-slate-700">Inconsistencias detectadas (penalizan el ICI)</h4>
        <div className="grid gap-2.5 sm:grid-cols-3">
          <FCheck name="documentos.inc_superficie" label="Superficies incoherentes" />
          <FCheck name="documentos.inc_cargas" label="Cargas edicto ≠ nota" />
          <FCheck name="documentos.inc_tasacion" label="Tasación anómala" />
        </div>
      </div>
    </div>
  );
}
function PasoResultado({ res, cargando, error, onRecalcular, onGuardar, guardando }:
  { res: Resultado | null; cargando: boolean; error?: string; onRecalcular: () => void; onGuardar: () => void; guardando: boolean }) {
  if (cargando) return <div><Spinner /><p className="text-center text-sm text-slate-500">Ejecutando el motor M01–M14…</p></div>;
  if (error) return <div className="space-y-3"><ErrorBox mensaje={error} /><Button variante="secundario" onClick={onRecalcular}><RefreshCw className="h-4 w-4" /> Reintentar</Button></div>;
  if (!res) return null;
  return (
    <div className="space-y-4">
      <SemaforoHero d={res.decision} />
      <div className="grid gap-4 xl:grid-cols-2">
        <EscaleraPrecios d={res.decision} />
        <MetricasClave res={res} />
      </div>
      <CondicionesVetos d={res.decision} />
      <div className="grid gap-4 xl:grid-cols-2">
        <RiesgosPanel riesgos={res.riesgos} />
        <div className="space-y-4">
          <EscenariosPanel r={res.rentabilidad} />
          <IcoDesglose d={res.decision} />
        </div>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <Button variante="secundario" onClick={onRecalcular}><RefreshCw className="h-4 w-4" /> Recalcular</Button>
        <Button onClick={onGuardar} cargando={guardando}><Save className="h-4 w-4" /> Guardar análisis</Button>
      </div>
    </div>
  );
}

/* ── página ───────────────────────────────────────────────────────────── */
export default function NuevaInversion() {
  const router = useRouter();
  const { data: opciones } = useQuery({ queryKey: ["opciones"], queryFn: api.opciones });
  const form = useForm<ValoresAnalisis>({
    resolver: zodResolver(esquemaAnalisis), defaultValues: valoresIniciales, mode: "onBlur",
  });
  const [paso, setPaso] = useState(0);
  const [resultado, setResultado] = useState<Resultado | null>(null);

  const simular = useMutation({ mutationFn: (p: unknown) => api.simular(p), onSuccess: setResultado });
  const guardar = useMutation({
    mutationFn: (p: unknown) => api.crear(p),
    onSuccess: (r) => router.push(`/inversiones/${r.id}`),
  });

  async function siguiente() {
    const campos = PASOS[paso].campos;
    const ok = campos.length ? await form.trigger(campos as never) : true;
    if (!ok) return;
    const nuevo = Math.min(paso + 1, PASOS.length - 1);
    setPaso(nuevo);
    if (nuevo === PASOS.length - 1) {
      setResultado(null);
      simular.mutate(aPayload(form.getValues()));
    }
  }
  const recalcular = () => { setResultado(null); simular.mutate(aPayload(form.getValues())); };

  const contenido = [
    <Paso1 key={0} op={opciones} />, <Paso2 key={1} op={opciones} />, <Paso3 key={2} />, <Paso4 key={3} />,
    <Paso5 key={4} op={opciones} />, <Paso6 key={5} />, <Paso7 key={6} />, <Paso8 key={7} />,
    <Paso9 key={8} />, <Paso10 key={9} />,
    <PasoResultado key={10} res={resultado} cargando={simular.isPending}
      error={simular.isError ? (simular.error as Error).message : undefined}
      onRecalcular={recalcular} onGuardar={() => guardar.mutate(aPayload(form.getValues()))}
      guardando={guardar.isPending} />,
  ];

  return (
    <div className="space-y-5">
      <header>
        <h1 className="h-display text-2xl font-bold">Nueva inversión</h1>
        <p className="text-sm text-slate-500">Asistente de análisis en 11 pasos. Toda la lógica se ejecuta en el backend.</p>
      </header>
      <div className="flex gap-6">
        <aside className="hidden w-60 shrink-0 lg:block">
          <ol className="space-y-0.5">
            {PASOS.map((p, i) => {
              const estado = i < paso ? "hecho" : i === paso ? "actual" : "pendiente";
              return (
                <li key={p.titulo}>
                  <button type="button" disabled={i > paso}
                    onClick={() => i < paso && setPaso(i)}
                    className={`flex w-full items-start gap-2.5 rounded-md px-2.5 py-2 text-left
                      ${estado === "actual" ? "bg-primario-tenue" : i < paso ? "hover:bg-slate-100" : "opacity-50"}`}>
                    <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold
                      ${estado === "hecho" ? "bg-primario text-white" : estado === "actual" ? "border-2 border-primario text-primario" : "border border-borde-control text-slate-400"}`}>
                      {estado === "hecho" ? <CheckIcon className="h-3 w-3" /> : i + 1}
                    </span>
                    <span>
                      <span className={`block text-[13px] font-medium ${estado === "actual" ? "text-primario" : "text-slate-700"}`}>{p.titulo}</span>
                      <span className="block text-[11px] text-slate-400">{p.descripcion}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        </aside>
        <div className="min-w-0 flex-1">
          <FormProvider {...form}>
            <Card>
              <CardHeader className="flex items-center justify-between">
                <CardTitle>Paso {paso + 1} de 11 — {PASOS[paso].titulo}</CardTitle>
                {guardar.isError && <span className="text-[12px] text-sem-rojo">{(guardar.error as Error).message}</span>}
              </CardHeader>
              <CardContent>{contenido[paso]}</CardContent>
            </Card>
            {paso < PASOS.length - 1 && (
              <div className="mt-4 flex justify-between">
                <Button variante="secundario" onClick={() => setPaso(Math.max(0, paso - 1))} disabled={paso === 0}>
                  <ChevronLeft className="h-4 w-4" /> Atrás
                </Button>
                <Button onClick={siguiente}>
                  {paso === PASOS.length - 2 ? "Calcular decisión" : "Siguiente"} <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            )}
            {paso === PASOS.length - 1 && (
              <div className="mt-4">
                <Button variante="secundario" onClick={() => setPaso(paso - 1)}><ChevronLeft className="h-4 w-4" /> Volver a Validación</Button>
              </div>
            )}
          </FormProvider>
        </div>
      </div>
    </div>
  );
}
