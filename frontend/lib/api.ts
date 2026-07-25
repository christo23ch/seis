import type { Alerta, CodigoTelegram, Detalle, ListItem, Miembro, Opciones, Organizacion, PreferenciasNotificacion, Resultado, SubastaCaptada, Usuario } from "./types";

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

  // Fase 9 — organización y miembros
  organizacion: () => req<Organizacion>("/organizacion"),
  crearMiembro: (b: { email: string; password: string; nombre?: string; rol: string }) =>
    req<Miembro>("/organizacion/miembros", { method: "POST", body: JSON.stringify(b) }),
  patchMiembro: (id: string, activo: boolean) =>
    req<Miembro>(`/organizacion/miembros/${id}`, { method: "PATCH", body: JSON.stringify({ activo }) }),

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
  // Fase 12 — notificaciones, alertas y captación
  preferencias: () => req<PreferenciasNotificacion>("/notificaciones/preferencias"),
  putPreferencias: (b: Partial<PreferenciasNotificacion>) =>
    req<PreferenciasNotificacion>("/notificaciones/preferencias", { method: "PUT", body: JSON.stringify(b) }),
  codigoTelegram: () => req<CodigoTelegram>("/notificaciones/telegram/codigo", { method: "POST" }),
  desvincularTelegram: () => req<{ ok: boolean }>("/notificaciones/telegram", { method: "DELETE" }),
  baja: (token: string) => req<{ ok: boolean; mensaje: string }>("/notificaciones/baja", { method: "POST", body: JSON.stringify({ token }) }),
  alertas: () => req<Alerta[]>("/alertas"),
  crearAlerta: (b: { nombre: string; criterios: Record<string, any>; activa?: boolean }) =>
    req<Alerta>("/alertas", { method: "POST", body: JSON.stringify(b) }),
  patchAlerta: (id: string, b: Partial<Pick<Alerta, "nombre" | "criterios" | "activa">>) =>
    req<Alerta>(`/alertas/${id}`, { method: "PATCH", body: JSON.stringify(b) }),
  eliminarAlerta: (id: string) => req<void>(`/alertas/${id}`, { method: "DELETE" }),
  subastas: (scoreMin?: number) =>
    req<SubastaCaptada[]>(`/subastas${scoreMin != null ? `?score_min=${scoreMin}` : ""}`),
  captarSubasta: (b: Record<string, any>) =>
    req<SubastaCaptada & { alertas_disparadas: number }>("/subastas", { method: "POST", body: JSON.stringify(b) }),

  reglas: () => req<{ version: string; reglas: any[] }>("/reglas"),
  historialRegla: (codigo: string) => req<any[]>(`/reglas/${codigo}/historial`),
  nuevaRegla: (definicion: any, justificacion: string) =>
    req<{ codigo: string; version: string }>("/reglas", { method: "POST", body: JSON.stringify({ definicion, justificacion }) }),
};
