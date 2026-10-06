#!/usr/bin/env bash
# Alta de punta a punta: levanta backend + frontend, rellena el formulario con un
# navegador real y comprueba que el dato llegó a la base.
#
# Por qué existe: la Fase 14 hizo obligatorios los consentimientos en
# `/auth/registro`. El backend quedó con 474 tests en verde y el alta REAL estaba
# rota, porque el frontend no los enviaba. Cada lado se probaba contra su propia
# idea del contrato y nadie probaba el contrato.
#
# Fase 5G.4-C: mismo lanzador que `correr_simulaciones.sh`, para que funcione en
# Windows (Git Bash) igual que en Linux/CI. Lo que cambió respecto a la versión
# anterior, y por qué:
#   · Sonda de salud `/api/v1/health` (liveness). La anterior esperaba a
#     `/health/vivo`, que no existe: el bucle agotaba sus 20 s y seguía igual.
#   · Puertos dedicados (8020/3020 por defecto), nunca 8000 ni 3000, que suelen
#     tener el entorno de desarrollo en marcha. Como `NEXT_PUBLIC_API_URL` se
#     INCRUSTA al compilar, este guion compila el frontend apuntando a su propio
#     backend (salvo E2E_SIN_BUILD=1, si ya se compiló con esa URL).
#   · Python del entorno virtual del backend si existe, no el del sistema.
#   · Base, correo y registros en un directorio temporal FUERA del repo, con ruta
#     nativa (`cygpath -m` en Git Bash): Python en Windows no entiende `/tmp/...`.
#   · Al terminar mata también los procesos NATIVOS por su PID de Windows: en
#     Git Bash, `kill` sobre un lanzador no llega a sus hijos.
#
# Uso:
#   Linux / CI:         bash e2e/correr.sh
#   Windows (Git Bash): CHROMIUM_PATH="C:/Program Files/Google/Chrome/Application/chrome.exe" \
#                         bash e2e/correr.sh
# Variables: PUERTO_API, PUERTO_WEB, PY, CHROMIUM_PATH (o PLAYWRIGHT_CHROMIUM, por
# compatibilidad), E2E_SIN_BUILD=1, E2E_CONSERVAR=1 (no borra el directorio temporal).
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUERTO_API="${PUERTO_API:-8020}"
PUERTO_WEB="${PUERTO_WEB:-3020}"

if [ -z "${PY:-}" ]; then
  if [ -x "$RAIZ/backend/.venv/Scripts/python.exe" ]; then PY="$RAIZ/backend/.venv/Scripts/python.exe"
  elif [ -x "$RAIZ/backend/.venv/bin/python" ]; then PY="$RAIZ/backend/.venv/bin/python"
  else PY="python"; fi
fi

nativo() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi; }

TMP_E2E="$(mktemp -d "${TMPDIR:-/tmp}/seis-e2e-alta-XXXXXX")"
E2E_DIR="$(nativo "$TMP_E2E")"
export E2E_BD="$E2E_DIR/e2e-alta.db"
export E2E_EMAIL_FICHERO="$E2E_DIR/e2e-email.txt"
export E2E_BACKEND="http://localhost:${PUERTO_API}/api/v1"
export E2E_FRONTEND="http://localhost:${PUERTO_WEB}"

ENTORNO_BACKEND=(SEIS_ENV=test JWT_SECRET="secreto-de-e2e-sin-valor-productivo-1234567890"
                 ADMIN_PASSWORD="admin-de-e2e" DATABASE_URL="sqlite:///${E2E_BD}"
                 SEIS_CORS_ORIGINS="$E2E_FRONTEND")

pids=()
limpiar() {
  for p in "${pids[@]:-}"; do
    [ -z "$p" ] && continue
    if [ -r "/proc/$p/winpid" ] && command -v taskkill >/dev/null 2>&1; then
      taskkill //F //T //PID "$(cat "/proc/$p/winpid")" >/dev/null 2>&1 || true
    fi
    kill "$p" 2>/dev/null || true
  done
  if [ "${E2E_CONSERVAR:-0}" = "1" ]; then echo "· Conservado: $E2E_DIR"; else rm -rf "$TMP_E2E"; fi
}
trap limpiar EXIT

esperar() {   # url, intentos
  for _ in $(seq 1 "$2"); do curl -sf -o /dev/null "$1" && return 0; sleep 0.5; done
  echo "E2E: no respondió $1"; return 1
}

for puerto in "$PUERTO_API" "$PUERTO_WEB"; do
  if curl -s -o /dev/null "http://localhost:$puerto"; then
    echo "E2E: el puerto $puerto ya está en uso; elija otro con PUERTO_API/PUERTO_WEB."; exit 1
  fi
done

if [ "${E2E_SIN_BUILD:-0}" != "1" ]; then
  echo "· Compilando el frontend contra $E2E_BACKEND"
  (cd "$RAIZ/frontend" && NEXT_PUBLIC_API_URL="http://localhost:${PUERTO_API}" \
     node node_modules/next/dist/bin/next build >"$E2E_DIR/next-build.log" 2>&1) \
    || { echo "E2E: falló la compilación (ver $E2E_DIR/next-build.log)"; exit 1; }
fi

echo "· Levantando el backend en :${PUERTO_API} (base: $E2E_BD)"
cd "$RAIZ/backend"
env "${ENTORNO_BACKEND[@]}" "$PY" -m uvicorn app.main:app --port "$PUERTO_API" --log-level warning \
  >"$E2E_DIR/backend.log" 2>&1 &
pids+=($!)
# El esquema lo crea el propio arranque en `test` (ADR-0004), pero se espera a
# que la sonda responda: arrancar el navegador contra un backend a medio subir
# produce fallos que parecen del formulario y no lo son.
esperar "${E2E_BACKEND}/health" 60 || exit 1

echo "· Sembrando el esquema y el conocimiento"
env "${ENTORNO_BACKEND[@]}" "$PY" -m scripts.init_db >/dev/null || { echo "E2E: falló init_db"; exit 1; }

echo "· Levantando el frontend en :${PUERTO_WEB}"
cd "$RAIZ/frontend"
node node_modules/next/dist/bin/next start -p "$PUERTO_WEB" >"$E2E_DIR/next.log" 2>&1 &
pids+=($!)
esperar "${E2E_FRONTEND}/registro" 120 || exit 1

echo
# El guion del navegador vive en `frontend/e2e/` y no aquí: Node resuelve los
# imports de un `.mjs` desde la carpeta DEL FICHERO, no desde el directorio de
# trabajo, así que playwright —que es devDependency del frontend— solo se
# encuentra desde allí. Medido: con el fichero en la raíz falla con
# ERR_MODULE_NOT_FOUND aunque se invoque con `cd frontend`.
node "$RAIZ/frontend/e2e/alta-real.mjs"; navegador=$?
cd "$RAIZ/backend" && "$PY" "$RAIZ/e2e/comprobar_alta.py"; base=$?

if [ $navegador -ne 0 ] || [ $base -ne 0 ]; then
  echo "E2E: FALLÓ (navegador=$navegador base=$base). Registros en $E2E_DIR (usar E2E_CONSERVAR=1 para verlos)."
  exit 1
fi
echo "E2E: alta de punta a punta correcta."
