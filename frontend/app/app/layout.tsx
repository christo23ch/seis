"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { rutaApp } from "@/lib/rutas";
import { Spinner } from "@/components/ui";
import { BarChart3, Bell, FilePlus2, FolderKanban, Gavel, LogOut, Map, Menu, Radar, Scale, Settings2, SlidersHorizontal, Users, UsersRound, X } from "lucide-react";
import type { Usuario } from "@/lib/types";

// El menú se construye según el usuario (Fase 9): «Conocimiento» solo para el
// superadmin de plataforma; «Mi equipo» solo para el propietario de la organización.
function construirNav(usuario: Usuario) {
  const grupos: { grupo: string; items: { href: string; etiqueta: string; icono: any }[] }[] = [
    { grupo: "Operaciones", items: [
      { href: rutaApp(), etiqueta: "Dashboard", icono: BarChart3 },
      { href: rutaApp("/nueva"), etiqueta: "Nueva inversión", icono: FilePlus2 },
      { href: rutaApp("/inversiones"), etiqueta: "Inversiones", icono: FolderKanban },
      { href: rutaApp("/comparativa"), etiqueta: "Comparativa", icono: Scale },
      { href: rutaApp("/mapa"), etiqueta: "Mapa", icono: Map },
    ]},
    { grupo: "Captación", items: [
      { href: rutaApp("/subastas"), etiqueta: "Subastas", icono: Radar },
      { href: rutaApp("/alertas"), etiqueta: "Alertas", icono: Bell },
    ]},
  ];
  if (usuario.es_superadmin) {
    grupos.push({ grupo: "Conocimiento", items: [
      { href: rutaApp("/reglas"), etiqueta: "Motor de reglas", icono: Gavel },
      { href: rutaApp("/parametros"), etiqueta: "Parámetros", icono: SlidersHorizontal },
      { href: rutaApp("/configuracion"), etiqueta: "Perfiles", icono: Settings2 },
    ]});
  }
  const sistema = [{ href: rutaApp("/administracion"), etiqueta: "Administración", icono: Users }];
  if (usuario.rol_org === "propietario" || usuario.es_superadmin) {
    sistema.unshift({ href: rutaApp("/equipo"), etiqueta: "Mi equipo", icono: UsersRound });
  }
  grupos.push({ grupo: "Sistema", items: sistema });
  return grupos;
}

// El armazón no tenía maquetación móvil: `aside.fixed.w-60` + `main.ml-60` sin un
// solo punto de ruptura, así que a 390 px el contenido empezaba en el píxel 272 y
// las DOCE rutas privadas desbordaban en horizontal (medido: /inversiones daba
// 889 px de página en un móvil de 390). Por debajo de `md` la barra pasa a ser un
// cajón sobre una cabecera con botón; a partir de `md` nada cambia respecto a antes.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { usuario, cargando, salir } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [cajonAbierto, setCajonAbierto] = useState(false);

  useEffect(() => {
    if (!cargando && !usuario) router.replace("/login");
  }, [cargando, usuario, router]);

  // Navegar cierra el cajón: si no, se queda tapando la pantalla a la que acabas
  // de ir, que en móvil es toda la pantalla.
  useEffect(() => { setCajonAbierto(false); }, [pathname]);

  // Escape cierra, como cualquier diálogo. Es lo que espera el teclado.
  useEffect(() => {
    if (!cajonAbierto) return;
    const alPulsar = (e: KeyboardEvent) => { if (e.key === "Escape") setCajonAbierto(false); };
    document.addEventListener("keydown", alPulsar);
    return () => document.removeEventListener("keydown", alPulsar);
  }, [cajonAbierto]);

  if (cargando || !usuario) return <Spinner />;

  const NAV = construirNav(usuario);

  return (
    <div className="flex min-h-screen">
      {/* Cabecera solo de móvil: es lo que da acceso al menú cuando la barra se esconde. */}
      <header className="fixed inset-x-0 top-0 z-30 flex h-14 items-center gap-3 border-b border-borde-linea bg-papel-carta px-4 md:hidden">
        <button type="button" onClick={() => setCajonAbierto(true)}
          aria-label="Abrir el menú" aria-expanded={cajonAbierto} aria-controls="menu-lateral"
          className="-ml-1 rounded-md p-2 text-tinta hover:bg-papel">
          <Menu className="h-5 w-5" />
        </button>
        <Link href={rutaApp()} className="flex items-center gap-2 text-guia font-semibold text-tinta">
          <Gavel className="h-4 w-4 text-primario" /> SEIS
        </Link>
      </header>

      {/* Velo: cierra al tocar fuera, y solo existe cuando el cajón está abierto. */}
      {cajonAbierto && (
        <div onClick={() => setCajonAbierto(false)} aria-hidden="true"
          className="fixed inset-0 z-40 bg-tinta/50 md:hidden" />
      )}

      <aside id="menu-lateral"
        className={`fixed inset-y-0 z-50 w-60 overflow-y-auto bg-tinta text-slate-300 transition-transform
          md:translate-x-0 ${cajonAbierto ? "translate-x-0" : "-translate-x-full"}`}>
        <button type="button" onClick={() => setCajonAbierto(false)} aria-label="Cerrar el menú"
          className="absolute right-2 top-3 rounded-md p-2 text-slate-400 hover:bg-tinta-suave hover:text-white md:hidden">
          <X className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-2.5 px-5 py-5 text-white">
          <Gavel className="h-5 w-5 text-primario-tenue" />
          <span className="text-[15px] font-semibold tracking-wide">SEIS</span>
        </div>
        <nav className="space-y-5 px-3 pb-6">
          {NAV.map((g) => (
            <div key={g.grupo}>
              <div className="px-2 pb-1.5 text-[10.5px] font-semibold uppercase tracking-wider text-slate-500">{g.grupo}</div>
              <div className="space-y-0.5">
                {g.items.map((i) => {
                  const activo = i.href === rutaApp() ? pathname === rutaApp() : pathname.startsWith(i.href);
                  const Ico = i.icono;
                  return (
                    <Link key={i.href} href={i.href}
                      className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13.5px] font-medium transition-colors
                        ${activo ? "bg-tinta-suave text-white" : "hover:bg-tinta-suave/60 hover:text-white"}`}>
                      <Ico className="h-4 w-4" /> {i.etiqueta}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
        <div className="absolute inset-x-0 bottom-0 border-t border-tinta-borde px-4 py-3">
          <div className="truncate text-[13px] text-white">{usuario.nombre ?? usuario.email}</div>
          <div className="flex items-center justify-between">
            <span className="text-[11px] uppercase tracking-wide text-slate-500">{usuario.rol}</span>
            <button onClick={salir} className="flex items-center gap-1 text-[12px] text-slate-400 hover:text-white">
              <LogOut className="h-3.5 w-3.5" /> Salir
            </button>
          </div>
        </div>
      </aside>
      {/* `min-w-0` no es decorativo: sin él un hijo con contenido ancho —una tabla,
          una gráfica— estira el flex y vuelve el desbordamiento por la puerta de atrás. */}
      <main className="min-w-0 min-h-screen flex-1 px-4 pb-7 pt-[4.5rem] md:ml-60 md:px-8 md:py-7">
        {children}
      </main>
    </div>
  );
}
