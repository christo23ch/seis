"use client";
import { useEffect, useRef } from "react";
import type { Map as LeafletMap } from "leaflet";

export interface Punto { lat: number; lng: number; etiqueta: string; color: string; href?: string; }

export default function MapaLeaflet({ puntos, alto = "100%", centro }: { puntos: Punto[]; alto?: string; centro?: [number, number] }) {
  const ref = useRef<HTMLDivElement>(null);
  const mapaRef = useRef<LeafletMap | null>(null);

  useEffect(() => {
    let cancelado = false;
    (async () => {
      const L = await import("leaflet");
      if (cancelado || !ref.current || mapaRef.current) return;
      const inicial: [number, number] = centro ?? (puntos[0] ? [puntos[0].lat, puntos[0].lng] : [40.4168, -3.7038]);
      const mapa = L.map(ref.current, { scrollWheelZoom: true }).setView(inicial, puntos.length ? 12 : 5);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(mapa);
      const capa = L.featureGroup().addTo(mapa);
      puntos.forEach((p) => {
        const m = L.circleMarker([p.lat, p.lng], { radius: 9, color: p.color, weight: 2, fillColor: p.color, fillOpacity: 0.55 });
        m.bindPopup(p.href ? `<a href="${p.href}" style="font-weight:600">${p.etiqueta}</a>` : p.etiqueta);
        capa.addLayer(m);
      });
      if (puntos.length > 1) mapa.fitBounds(capa.getBounds().pad(0.2));
      mapaRef.current = mapa;
    })();
    return () => { cancelado = true; mapaRef.current?.remove(); mapaRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(puntos)]);

  return <div ref={ref} style={{ height: alto, minHeight: 260 }} className="z-0 w-full rounded-lg border border-slate-200" />;
}
