"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";
import type { Usuario } from "./types";

interface Ctx {
  usuario: Usuario | null;
  cargando: boolean;
  entrar: (email: string, password: string) => Promise<void>;
  salir: () => void;
}
const AuthCtx = createContext<Ctx>({ usuario: null, cargando: true, entrar: async () => {}, salir: () => {} });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    if (!getToken()) { setCargando(false); return; }
    api.me().then(setUsuario).catch(() => setToken(null)).finally(() => setCargando(false));
  }, []);

  const entrar = useCallback(async (email: string, password: string) => {
    const r = await api.login(email, password);
    setToken(r.access_token);
    setUsuario(await api.me());
  }, []);

  const salir = useCallback(() => { setToken(null); setUsuario(null); window.location.href = "/login"; }, []);

  return <AuthCtx.Provider value={{ usuario, cargando, entrar, salir }}>{children}</AuthCtx.Provider>;
}
export const useAuth = () => useContext(AuthCtx);
