#!/usr/bin/env bash
# Simulaciones e informes oficiales de punta a punta (Fase 5F.7.9): levanta un
# backend y un frontend PROPIOS, recorre el flujo con un navegador real y
# comprueba en la base que lo que se ve es lo que se guardó.
#
# Mismo patrón que `correr.sh` (alta), con tres diferencias medidas en Windows:
#   · Puertos dedicados (8010/3010 por defecto), nunca 8000 ni 3000, que suelen
#     tener el entorno de desarrollo en marcha. Como `NEXT_PUBLIC_API_URL` se
#     INCRUSTA al compilar, este guion compila el frontend apuntando a su propio
#     backend (salvo E2E_SIN_BUILD=1, si ya se compiló con esa URL).
#   · La base SQLite vive en un directorio temporal del sistema, FUERA del repo,
#     con ruta nativa (`cygpath -m` en Git Bash): Python en Windows no entiende
#     las rutas `/tmp/...` de MSYS.
#   · Al terminar mata también los procesos NATIVOS (python, node) por su PID de
#     Windows: en Git Bash, `kill` sobre un lanzador no llega a sus hijos.
#
# Uso:
#   Linux / CI:        bash e2e/correr_simulaciones.sh
#   Windows (Git Bash) CHROMIUM_PATH="C:/Program Files/Google/Chrome/Application/chrome.exe" \
#                        bash e2e/correr_simulaciones.sh
# Variables: PUERTO_API, PUERTO_WEB, PY, CHROMIUM_PATH (o PLAYWRIGHT_CHROMIUM, por
# compatibilidad; ver frontend/scripts/navegador.mjs), E2E_SIN_BUILD=1,
# E2E_CONSERVAR=1 (no borra el directorio temporal: capturas, PDF y base).
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUERTO_API="${PUERTO_API:-8010}"
PUERTO_WEB="${PUERTO_WEB:-3010}"

# El Python del backend: el del entorno virtual si existe (Windows o POSIX).
if [ -z "${PY:-}" ]; then
  if [ -x "$RAIZ/backend/.venv/Scripts/python.exe" ]; then PY="$RAIZ/backend/.venv/Scripts/python.exe"
  elif [ -x "$RAIZ/backend/.venv/bin/python" ]; then PY="$RAIZ/backend/.venv/bin/python"
  else PY="python"; fi
fi

nativo() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi; }

TMP_E2E="$(mktemp -d "${TMPDIR:-/tmp}/seis-e2e-sim-XXXXXX")"
export E2E_DIR="$(nativo "$TMP_E2E")"
export E2E_BD="$E2E_DIR/e2e-simulaciones.db"
export E2E_ENTRADA="$E2E_DIR/entrada.json"
export E2E_IDS="$E2E_DIR/ids.json"
export E2E_BACKEND="http://localhost:${PUERTO_API}/api/v1"
export E2E_FRONTEND="http://localhost:${PUERTO_WEB}"
export E2E_ADMIN_EMAIL="admin@seis.local"
export E2E_ADMIN_PASSWORD="admin-de-e2e"

ENTORNO_BACKEND=(SEIS_ENV=test JWT_SECRET="secreto-de-e2e-sin-valor-productivo-1234567890"
                 ADMIN_PASSWORD="$E2E_ADMIN_PASSWORD" DATABASE_URL="sqlite:///${E2E_BD}"
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
esperar "${E2E_BACKEND}/health" 60 || exit 1

echo "· Sembrando el esquema y el conocimiento"
env "${ENTORNO_BACKEND[@]}" "$PY" -m scripts.init_db >/dev/null || { echo "E2E: falló init_db"; exit 1; }

# La entrada del análisis es la misma que usa la suite (`tests/conftest.py`): datos
# realistas sin duplicarlos en JavaScript.
"$PY" -c "import json,sys; from tests.conftest import entrada_base; \
open(sys.argv[1],'w',encoding='utf-8').write(entrada_base().model_dump_json())" "$E2E_ENTRADA" \
  || { echo "E2E: no se pudo generar la entrada"; exit 1; }

echo "· Levantando el frontend en :${PUERTO_WEB}"
cd "$RAIZ/frontend"
node node_modules/next/dist/bin/next start -p "$PUERTO_WEB" >"$E2E_DIR/next.log" 2>&1 &
pids+=($!)
esperar "${E2E_FRONTEND}/login" 120 || exit 1

echo
# Vive en `frontend/e2e/` por la misma razón que `alta-real.mjs`: Node resuelve
# `playwright` desde la carpeta del fichero, y es devDependency del frontend.
node "$RAIZ/frontend/e2e/simulaciones.mjs"; navegador=$?
cd "$RAIZ/backend" && "$PY" "$RAIZ/e2e/comprobar_simulaciones.py"; base=$?

if [ $navegador -ne 0 ] || [ $base -ne 0 ]; then
  echo "E2E: FALLÓ (navegador=$navegador base=$base). Registros en $E2E_DIR (usar E2E_CONSERVAR=1 para verlos)."
  exit 1
fi
echo "E2E: simulaciones e informes oficiales de punta a punta, correctos."
