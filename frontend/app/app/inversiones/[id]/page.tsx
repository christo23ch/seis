"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { eur, fecha, num, pct } from "@/lib/format";
import { SEM_COLOR } from "@/components/resultado";
import {
  ChecklistLista, CondicionesVetos, EscaleraPrecios, EscenariosPanel,
  IcoDesglose, MetricasClave, RiesgosPanel, SemaforoHero,
} from "@/components/resultado";
import MapaLeaflet from "@/components/mapa-leaflet";
import { Button, Card, CardContent, CardHeader, CardTitle, ErrorBox, Spinner, TabPanel, Tabs, TabsLista } from "@/components/ui";
import { FileDown } from "lucide-react";
import { useState } from "react";

export default function DetalleInversion() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useQuery({ queryKey: ["detalle", id], queryFn: () => api.detalle(id) });
  const [bajando, setBajando] = useState(false);

  if (isLoading) return <Spinner />;
  if (error || !data) return <ErrorBox mensaje={(error as Error)?.message ?? "No encontrado"} />;

  const res = data.resultado;
  const d = res.decision;
  const act = data.entrada?.activo ?? {};
  const lat = act.lat != null ? Number(act.lat) : null;
  const lng = act.lng != null ? Number(act.lng) : null;

  async function descargarPdf() {
    setBajando(true);
    try {
      const blob = await api.pdf(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `SEIS_informe_${id.slice(0, 8)}.pdf`; a.click();
      URL.revokeObjectURL(url);
    } finally { setBajando(false); }
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="h-display text-2xl font-bold capitalize">
            {act.tipologia ?? "Activo"} · {act.municipio ?? "—"}
          </h1>
          <p className="text-sm text-slate-500">
            {data.perfil} · {num(act.superficie_m2 ?? 0)} m² · {fecha(data.creado_en)} ·
            reglas v{data.version_reglas} · parámetros v{data.version_parametros}
          </p>
        </div>
        <Button variante="secundario" onClick={descargarPdf} cargando={bajando}>
          <FileDown className="h-4 w-4" /> Descargar informe PDF
        </Button>
      </header>

      <SemaforoHero d={d} />

      <Tabs defecto="resumen">
        <TabsLista items={[
          { valor: "resumen", etiqueta: "Resumen" },
          { valor: "riesgos", etiqueta: "Riesgos" },
          { valor: "puja", etiqueta: "Estrategia de puja" },
          { valor: "checklist", etiqueta: "Checklist" },
          { valor: "informe", etiqueta: "Informe" },
          { valor: "datos", etiqueta: "Datos de entrada" },
        ]} />

        <TabPanel valor="resumen">
          <div className="space-y-4">
            <div className="grid gap-4 xl:grid-cols-2">
              <EscaleraPrecios d={d} />
              <MetricasClave res={res} />
            </div>
            <CondicionesVetos d={d} />
            <div className="grid gap-4 xl:grid-cols-2">
              <EscenariosPanel r={res.rentabilidad} />
              <IcoDesglose d={d} />
            </div>
            <div className="grid gap-4 xl:grid-cols-3">
              <Card>
                <CardHeader><CardTitle>Valoración</CardTitle></CardHeader>
                <CardContent className="space-y-1.5 text-sm">
                  <Fila k="VS (salida)" v={eur(res.valoracion.vs)} />
                  <Fila k="VS prudente" v={eur(res.vs_prudente)} />
                  <Fila k="VM (estado actual)" v={eur(res.valoracion.vm)} />
                  <Fila k="€/m² salida" v={eur(res.valoracion.vs_m2)} />
                  <Fila k="Comparables · CV" v={`${res.valoracion.n_comparables} · ${pct(res.valoracion.dispersion_cv)}`} />
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle>Costes</CardTitle></CardHeader>
                <CardContent className="space-y-1.5 text-sm">
                  <Fila k="C_F (P50 / P80)" v={`${eur(res.costes.c_f_p50)} / ${eur(res.costes.c_f_p80)}`} />
                  <Fila k="c_v" v={pct(res.costes.c_v)} />
                  <Fila k="Reforma" v={`${res.reforma.nivel} · ${eur(res.reforma.total_p50)}`} />
                  <Fila k="Plazo (P50 / P80)" v={`${num(res.costes.plazo_meses_p50)} / ${num(res.costes.plazo_meses_p80)} meses`} />
                  <Fila k="Contingencia" v={pct(res.costes.contingencia_pct, 0)} />
                </CardContent>
              </Card>
              {lat != null && lng != null ? (
                <MapaLeaflet puntos={[{ lat, lng, etiqueta: act.direccion ?? act.municipio ?? "Activo", color: SEM_COLOR[d.semaforo] }]} alto="260px" />
              ) : (
                <Card><CardContent className="flex h-full items-center justify-center text-sm text-slate-400">
                  Sin coordenadas: añada lat/lng en el paso Ubicación para ver el mapa.
                </CardContent></Card>
              )}
            </div>
          </div>
        </TabPanel>

        <TabPanel valor="riesgos"><RiesgosPanel riesgos={res.riesgos} /></TabPanel>

        <TabPanel valor="puja">
          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Plan de puja</CardTitle></CardHeader>
              <CardContent>
                <div className="mb-3 grid grid-cols-3 gap-3 text-center">
                  <MiniStat k="P. adjudicación" v={eur(res.puja.p_adj_esperado)} />
                  <MiniStat k="Ratio segmento" v={pct(res.puja.ratio_base, 0)} />
                  <MiniStat k="RVC" v={`${res.puja.rvc.toFixed(2)} (${res.puja.banda_rvc})`} />
                </div>
                <ul className="space-y-1.5 text-sm text-slate-700">
                  {res.puja.plan.map((p, i) => <li key={i} className="flex gap-2"><span className="text-primario">▸</span>{p}</li>)}
                </ul>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Riesgo de ejecución del proceso</CardTitle></CardHeader>
              <CardContent>
                <ul className="space-y-1.5 text-sm text-slate-700">
                  {res.puja.riesgo_ejecucion.map((p, i) => <li key={i} className="flex gap-2"><span className="text-sem-naranja">▸</span>{p}</li>)}
                </ul>
              </CardContent>
            </Card>
          </div>
        </TabPanel>

        <TabPanel valor="checklist">
          <Card><CardContent><ChecklistLista items={res.checklist} /></CardContent></Card>
        </TabPanel>

        <TabPanel valor="informe">
          <Card><CardContent>
            <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap font-cifra text-[12.5px] leading-relaxed text-slate-700">
              {res.informe_markdown}
            </pre>
          </CardContent></Card>
        </TabPanel>

        <TabPanel valor="datos">
          <Card><CardContent>
            <pre className="max-h-[70vh] overflow-auto font-cifra text-[12px] text-slate-600">
              {JSON.stringify(data.entrada, null, 2)}
            </pre>
          </CardContent></Card>
        </TabPanel>
      </Tabs>
    </div>
  );
}
const Fila = ({ k, v }: { k: string; v: string }) => (
  <div className="flex items-baseline justify-between gap-3 border-b border-slate-50 pb-1">
    <span className="text-[12.5px] text-slate-500">{k}</span>
    <span className="cifra font-semibold">{v}</span>
  </div>
);
const MiniStat = ({ k, v }: { k: string; v: string }) => (
  <div className="rounded-md bg-slate-50 px-2 py-2">
    <div className="text-[11px] uppercase tracking-wide text-slate-400">{k}</div>
    <div className="cifra text-sm font-semibold">{v}</div>
  </div>
);
