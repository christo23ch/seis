import type {
  Alerta, CodigoTelegram, ComparacionSimulacion, Detalle, InformeOficialDetalle, InformeOficialResumen,
  ListItem, Miembro, Opciones, Organizacion, Overrides, ParametrosSimulables, PreferenciasNotificacion,
  RespuestaSimple, Resultado, SimulacionDetalle, SimulacionResumen, SubastaCaptada, Usuario,
} from "./types";

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

/** Texto legible de un error del backend. `detail` es un string en los errores
 * propios; en un 422 de validación de FastAPI es una lista de `{loc, msg}`, que se
 * resume en vez de volcar el JSON crudo al usuario. */
function textoDeDetalle(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const partes = detail.map((e) => {
      const loc = Array.isArray(e?.loc) ? e.loc.filter((p: unknown) => p !== "body").join(".") : "";
      const msg = typeof e?.msg === "string" ? e.msg : "valor no válido";
      return loc ? `${loc}: ${msg}` : msg;
    });
    return `Petición no válida — ${partes.join("; ")}`;
  }
  return `Error ${status}`;
}

async function fallo(r: Response, path: string): Promise<ApiError> {
  if (r.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth")) {
    setToken(null);
    window.location.href = "/login";
  }
  let detail: unknown;
  try { detail = (await r.json()).detail; } catch {}
  return new ApiError(r.status, textoDeDetalle(detail, r.status));
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (init.body && !(init.body instanceof URLSearchParams)) headers["Content-Type"] = "application/json";
  const t = getToken();
  if (t) headers["Authorization"] = `Bearer ${t}`;
  const r = await fetch(BASE + path, { ...init, headers });
  if (!r.ok) throw await fallo(r, path);
  const ct = r.headers.get("content-type") ?? "";
  return (ct.includes("application/json") ? r.json() : (r.text() as unknown)) as Promise<T>;
}

/** Descarga autenticada de un binario: mismo patrón que tenía el PDF del
 * detalle (fetch con Bearer → blob), pero con el tratamiento de errores y de
 * 401 de `req`. El guardado lo hace `guardarBlob`, en el navegador. */
async function blobAutenticado(path: string): Promise<Blob> {
  const t = getToken();
  const r = await fetch(BASE + path, { headers: t ? { Authorization: `Bearer ${t}` } : {} });
  if (!r.ok) throw await fallo(r, path);
  return r.blob();
}

export function guardarBlob(blob: Blob, nombre: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = nombre; a.click();
  URL.revokeObjectURL(url);
}

const enc = encodeURIComponent;

export const api = {
  login: (email: string, password: string) =>
    req<{ access_token: string; rol: string; nombre?: string }>("/auth/login", {
      method: "POST", body: new URLSearchParams({ username: email, password }),
    }),
  me: () => req<Usuario>("/auth/me"),
  crearUsuario: (b: { email: string; password: string; nombre?: string; rol: string }) =>
    req<{ email: string; rol: string }>("/auth/usuarios", { method: "POST", body: JSON.stringify(b) }),

  // Fase 10 — alta self-service. Todos cuelgan de /auth, que `req` ya exime del
  // redirect global a /login ante un 401, así que funcionan sin sesión.
  // Fase 14 (RGPD): los dos obligatorios NO son opcionales en el tipo. El
  // backend responde 422 sin ellos, y dejarlos opcionales aquí solo trasladaría
  // el fallo de la compilación al tiempo de ejecución.
  registro: (b: {
    email: string; password: string; nombre?: string;
    acepta_terminos: boolean; acepta_privacidad: boolean;
    acepta_comunicaciones_comerciales?: boolean;
  }) => req<RespuestaSimple>("/auth/registro", { method: "POST", body: JSON.stringify(b) }),
  textoLegal: (tipo: string) =>
    req<{ tipo: string; titulo: string; version: string; cuerpo: string;
          obligatorio: boolean; pendiente_de_redaccion: boolean }>(`/legal/${tipo}`),
  verificar: (token: string) =>
    req<RespuestaSimple>("/auth/verificar", { method: "POST", body: JSON.stringify({ token }) }),
  reenviarVerificacion: (email: string) =>
    req<RespuestaSimple>("/auth/reenviar-verificacion", { method: "POST", body: JSON.stringify({ email }) }),
  recuperar: (email: string) =>
    req<RespuestaSimple>("/auth/recuperar", { method: "POST", body: JSON.stringify({ email }) }),
  resetear: (token: string, nueva: string) =>
    req<RespuestaSimple>("/auth/resetear", { method: "POST", body: JSON.stringify({ token, nueva }) }),
  cambiarPassword: (actual: string, nueva: string) =>
    req<RespuestaSimple>("/auth/cambiar-password", { method: "POST", body: JSON.stringify({ actual, nueva }) }),

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
  // Fase 5F.7.4: la UI ya no ofrece `/informe.pdf` (PDF de la configuración actual,
  // indistinguible impreso de uno oficial). El endpoint sigue en el backend; los
  // únicos PDF descargables desde la UI son los de `informes.descargarPdf`.

  // Fase 5F.6 — simulaciones de un análisis. Autorización y transiciones las decide el backend.
  simulaciones: {
    listar: (analisisId: string) =>
      req<SimulacionResumen[]>(`/analisis/${enc(analisisId)}/simulaciones`),
    obtener: (analisisId: string, simulacionId: string) =>
      req<SimulacionDetalle>(`/analisis/${enc(analisisId)}/simulaciones/${enc(simulacionId)}`),
    crear: (analisisId: string, overrides: Overrides) =>
      req<SimulacionDetalle>(`/analisis/${enc(analisisId)}/simulaciones`,
        { method: "POST", body: JSON.stringify({ overrides }) }),
    validar: (analisisId: string, simulacionId: string) =>
      req<SimulacionDetalle>(`/analisis/${enc(analisisId)}/simulaciones/${enc(simulacionId)}/validar`, { method: "POST" }),
    descartar: (analisisId: string, simulacionId: string) =>
      req<SimulacionDetalle>(`/analisis/${enc(analisisId)}/simulaciones/${enc(simulacionId)}/descartar`, { method: "POST" }),
    seleccionar: (analisisId: string, simulacionId: string) =>
      req<SimulacionDetalle>(`/analisis/${enc(analisisId)}/simulaciones/${enc(simulacionId)}/seleccionar`, { method: "POST" }),
    volverAOriginal: (analisisId: string) =>
      req<Detalle>(`/analisis/${enc(analisisId)}/configuracion/original`, { method: "POST" }),
  },
  // Fase 5F.7.2 / 5F.7.3 — catálogo simulable y comparación (solo lectura).
  parametrosSimulables: (analisisId: string) =>
    req<ParametrosSimulables>(`/analisis/${enc(analisisId)}/parametros-simulables`),
  compararSimulacion: (analisisId: string, simulacionId: string) =>
    req<ComparacionSimulacion>(`/analisis/${enc(analisisId)}/simulaciones/${enc(simulacionId)}/comparacion`),
  // Fase 5F.4 — informes oficiales: snapshots congelados, nunca se regeneran.
  informes: {
    emitir: (analisisId: string) =>
      req<InformeOficialDetalle>(`/analisis/${enc(analisisId)}/informes`, { method: "POST" }),
    listar: (analisisId: string) =>
      req<InformeOficialResumen[]>(`/analisis/${enc(analisisId)}/informes`),
    obtener: (analisisId: string, informeId: string) =>
      req<InformeOficialDetalle>(`/analisis/${enc(analisisId)}/informes/${enc(informeId)}`),
    descargarPdf: (analisisId: string, informeId: string) =>
      blobAutenticado(`/analisis/${enc(analisisId)}/informes/${enc(informeId)}/pdf`),
  },
  simular: (payload: unknown) => req<Resultado>("/analisis/simular", { method: "POST", body: JSON.stringify(payload) }),
  // `subastaId` (Fase 1 — puente captación → análisis): si se pasa, el backend
  // reutiliza esa Subasta ya captada en vez de crear una nueva.
  crear: (payload: unknown, subastaId?: string) =>
    req<{ id: string; resultado: Resultado }>(
      `/analisis${subastaId ? `?subasta_id=${encodeURIComponent(subastaId)}` : ""}`,
      { method: "POST", body: JSON.stringify(payload) },
    ),

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

  // Fase 15 — checklist de arranque. Ninguna de las dos lleva usuario_id: el
  // backend actúa sobre la sesión y no ofrece forma de pedir la de otro.
  onboarding: () => req<EstadoOnboarding>("/cuenta/onboarding"),
  marcarPasoOnboarding: (clave: string) =>
    req<EstadoOnboarding>(`/cuenta/onboarding/${clave}`, { method: "POST" }),
};

export type PasoOnboarding = {
  clave: string;
  titulo: string;
  descripcion: string;
  accion: string | null;
  completado: boolean;
  /** `datos` ⇒ el backend lo deduce y no se puede marcar a mano. */
  origen: "datos" | "declarado";
  completado_en: string | null;
};

export type EstadoOnboarding = {
  pasos: PasoOnboarding[];
  completados: number;
  total: number;
  terminado: boolean;
};
