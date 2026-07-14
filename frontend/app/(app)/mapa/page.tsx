"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Semaforo } from "@/lib/types";
import { SEM_COLOR } from "@/components/resultado";
import MapaLeaflet from "@/components/mapa-leaflet";
import { Card, CardContent, ErrorBox, Spinner } from "@/components/ui";

export default function MapaCartera() {
  const { data, isLoading, error } = useQuery({ queryKey: ["analisis"], queryFn: api.listar });
  if (isLoading) return <Spinner />;
  if (error) return <ErrorBox mensaje={(error as Error).message} />;

  const conCoords = (data ?? []).filter((a) => a.lat != null && a.lng != null);
  const sinCoords = (data ?? []).length - conCoords.length;
  const puntos = conCoords.map((a) => ({
    lat: a.lat as number, lng: a.lng as number,
    etiqueta: `${a.tipologia ?? "activo"} · ${a.municipio ?? "—"} · ICO ${a.ico}`,
    color: SEM_COLOR[a.semaforo], href: `/inversiones/${a.id}`,
  }));

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="h-display text-2xl font-bold">Mapa de la cartera</h1>
          <p className="text-sm text-slate-500">
            {puntos.length} activos geolocalizados{sinCoords > 0 && ` · ${sinCoords} sin coordenadas`}.
          </p>
        </div>
        <div className="flex gap-3 text-[12px]">
          {(["verde", "amarillo", "naranja", "rojo"] as Semaforo[]).map((s) => (
            <span key={s} className="flex items-center gap-1.5 capitalize text-slate-600">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: SEM_COLOR[s] }} /> {s}
            </span>
          ))}
        </div>
      </header>
      {puntos.length ? (
        <div className="min-h-0 flex-1"><MapaLeaflet puntos={puntos} alto="100%" /></div>
      ) : (
        <Card><CardContent className="py-14 text-center text-slate-400">
          Añada latitud y longitud en el paso Ubicación del asistente para situar los activos en el mapa.
        </CardContent></Card>
      )}
    </div>
  );
}
