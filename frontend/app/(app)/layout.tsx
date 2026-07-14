"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Spinner } from "@/components/ui";
import { BarChart3, FilePlus2, FolderKanban, Gavel, LogOut, Map, Scale, Settings2, SlidersHorizontal, Users, UsersRound } from "lucide-react";
import type { Usuario } from "@/lib/types";

// El menú se construye según el usuario (Fase 9): «Conocimiento» solo para el
// superadmin de plataforma; «Mi equipo» solo para el propietario de la organización.
function construirNav(usuario: Usuario) {
  const grupos: { grupo: string; items: { href: string; etiqueta: string; icono: any }[] }[] = [
    { grupo: "Operaciones", items: [
      { href: "/", etiqueta: "Dashboard", icono: BarChart3 },
      { href: "/nueva", etiqueta: "Nueva inversión", icono: FilePlus2 },
      { href: "/inversiones", etiqueta: "Inversiones", icono: FolderKanban },
      { href: "/comparativa", etiqueta: "Comparativa", icono: Scale },
      { href: "/mapa", etiqueta: "Mapa", icono: Map },
    ]},
  ];
  if (usuario.es_superadmin) {
    grupos.push({ grupo: "Conocimiento", items: [
      { href: "/reglas", etiqueta: "Motor de reglas", icono: Gavel },
      { href: "/parametros", etiqueta: "Parámetros", icono: SlidersHorizontal },
      { href: "/configuracion", etiqueta: "Perfiles", icono: Settings2 },
    ]});
  }
  const sistema = [{ href: "/administracion", etiqueta: "Administración", icono: Users }];
  if (usuario.rol_org === "propietario" || usuario.es_superadmin) {
    sistema.unshift({ href: "/equipo", etiqueta: "Mi equipo", icono: UsersRound });
  }
  grupos.push({ grupo: "Sistema", items: sistema });
  return grupos;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { usuario, cargando, salir } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!cargando && !usuario) router.replace("/login");
  }, [cargando, usuario, router]);

  if (cargando || !usuario) return <Spinner />;

  const NAV = construirNav(usuario);

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 w-60 overflow-y-auto bg-tinta text-slate-300">
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
                  const activo = i.href === "/" ? pathname === "/" : pathname.startsWith(i.href);
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
      <main className="ml-60 min-h-screen flex-1 px-8 py-7">{children}</main>
    </div>
  );
}
