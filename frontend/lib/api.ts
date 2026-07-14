import type { Detalle, ListItem, Opciones, Resultado, Usuario } from "./types";

const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export const getToken = () => (typeof window === "undefined" ? null : localStorage.getItem("seis_token"));
export const setToken = (t: string | null) => {
  if (typeof window === "undefined") return;
  if (t) localStorage.setItem("seis_token", t);
  else localStorage.removeItem("seis_token");
};

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (init.body && !(init.body instanceof URLSearchParams)) headers["Content-Type"] = "application/json";
  const t = getToken();
  if (t) headers["Authorization"] = `Bearer ${t}`;
  const r = await fetch(BASE + path, { ...init, headers });
  if (r.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth")) {
    setToken(null);
    window.location.href = "/login";
  }
  if (!r.ok) {
    let detalle = `Error ${r.status}`;
    try { const j = await r.json(); detalle = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j); } catch {}
    throw new ApiError(r.status, detalle);
  }
  const ct = r.headers.get("content-type") ?? "";
  return (ct.includes("application/json") ? r.json() : (r.text() as unknown)) as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    req<{ access_token: string; rol: string; nombre?: string }>("/auth/login", {
      method: "POST", body: new URLSearchParams({ username: email, password }),
    }),
  me: () => req<Usuario>("/auth/me"),
  crearUsuario: (b: { email: string; password: string; nombre?: string; rol: string }) =>
    req<{ email: string; rol: string }>("/auth/usuarios", { method: "POST", body: JSON.stringify(b) }),

  listar: () => req<ListItem[]>("/analisis"),
  detalle: (id: string) => req<Detalle>(`/analisis/${id}`),
  checklist: (id: string) => req<Detalle["resultado"]["checklist"]>(`/analisis/${id}/checklist`),
  informe: (id: string) => req<string>(`/analisis/${id}/informe`),
  pdf: async (id: string) => {
    const t = getToken();
    const r = await fetch(`${BASE}/analisis/${id}/informe.pdf`, { headers: t ? { Authorization: `Bearer ${t}` } : {} });
    if (!r.ok) throw new ApiError(r.status, "No se pudo generar el PDF");
    return r.blob();
  },
  simular: (payload: unknown) => req<Resultado>("/analisis/simular", { method: "POST", body: JSON.stringify(payload) }),
  crear: (payload: unknown) => req<{ id: string; resultado: Resultado }>("/analisis", { method: "POST", body: JSON.stringify(payload) }),

  opciones: () => req<Opciones>("/opciones"),
  perfiles: () => req<Record<string, any>>("/perfiles"),
  putPerfil: (codigo: string, parametros: any) =>
    req(`/perfiles/${codigo}`, { method: "PUT", body: JSON.stringify({ parametros }) }),
  parametros: () => req<any>("/parametros"),
  putParametro: (b: { clave: string; valor: any; fuente_legal?: string }) =>
    req("/parametros", { method: "PUT", body: JSON.stringify(b) }),
  reglas: () => req<{ version: string; reglas: any[] }>("/reglas"),
  historialRegla: (codigo: string) => req<any[]>(`/reglas/${codigo}/historial`),
  nuevaRegla: (definicion: any, justificacion: string) =>
    req<{ codigo: string; version: string }>("/reglas", { method: "POST", body: JSON.stringify({ definicion, justificacion }) }),
};
