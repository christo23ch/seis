#!/usr/bin/env bash
# Alta de punta a punta: levanta backend + frontend, rellena el formulario con un
# navegador real y comprueba que el dato llegó a la base.
#
# Por qué existe: la Fase 14 hizo obligatorios los consentimientos en
# `/auth/registro`. El backend quedó con 474 tests en verde y el alta REAL estaba
# rota, porque el frontend no los enviaba. Cada lado se probaba contra su propia
# idea del contrato y nadie probaba el contrato.
#
# Todo lo que toca es desechable: SQLite en /tmp y puertos altos. No mira ni
# escribe en la base de desarrollo.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export E2E_BD="${E2E_BD:-/tmp/e2e-seis.db}"
export E2E_EMAIL_FICHERO="${E2E_EMAIL_FICHERO:-/tmp/e2e-email.txt}"
# 8000 y no un puerto alto: `NEXT_PUBLIC_API_URL` se INCRUSTA en el bundle
# durante `next build`, así que exportarla al arrancar no cambiaría nada — el
# frontend ya compilado apunta a localhost:8000, que es su valor por defecto.
# Cambiar el puerto exigiría recompilar; usar el suyo cuesta cero.
PUERTO_API="${PUERTO_API:-8000}"
PUERTO_WEB="${PUERTO_WEB:-3099}"
PY="${PY:-python}"

export E2E_BACKEND="http://localhost:${PUERTO_API}/api/v1"
export E2E_FRONTEND="http://localhost:${PUERTO_WEB}"

rm -f "$E2E_BD" "$E2E_EMAIL_FICHERO"
pids=()
limpiar() { for p in "${pids[@]:-}"; do kill "$p" 2>/dev/null || true; done; }
trap limpiar EXIT

echo "· Levantando el backend en :${PUERTO_API}"
cd "$RAIZ/backend"
SEIS_ENV=test \
JWT_SECRET="secreto-de-e2e-sin-valor-productivo-1234567890" \
ADMIN_PASSWORD="admin-de-e2e" \
DATABASE_URL="sqlite:///${E2E_BD}" \
SEIS_CORS_ORIGINS="${E2E_FRONTEND}" \
  "$PY" -m uvicorn app.main:app --port "$PUERTO_API" --log-level warning &
pids+=($!)

# El esquema lo crea el propio arranque en `test` (ADR-0004), pero se espera a
# que la sonda responda: arrancar el navegador contra un backend a medio subir
# produce fallos que parecen del formulario y no lo son.
for _ in $(seq 1 40); do
  curl -sf "http://localhost:${PUERTO_API}/api/v1/health/vivo" >/dev/null && break
  sleep 0.5
done

echo "· Sembrando el esquema y el conocimiento"
cd "$RAIZ/backend"
SEIS_ENV=test JWT_SECRET="secreto-de-e2e-sin-valor-productivo-1234567890" \
ADMIN_PASSWORD="admin-de-e2e" DATABASE_URL="sqlite:///${E2E_BD}" \
  "$PY" -m scripts.init_db >/dev/null

echo "· Levantando el frontend en :${PUERTO_WEB}"
cd "$RAIZ/frontend"
npx next start -p "$PUERTO_WEB" >/tmp/e2e-next.log 2>&1 &
pids+=($!)
for _ in $(seq 1 60); do
  curl -sf "${E2E_FRONTEND}/registro" >/dev/null && break
  sleep 0.5
done

echo
# El guion del navegador vive en `frontend/e2e/` y no aquí: Node resuelve los
# imports de un `.mjs` desde la carpeta DEL FICHERO, no desde el directorio de
# trabajo, así que playwright —que es devDependency del frontend— solo se
# encuentra desde allí. Medido: con el fichero en la raíz falla con
# ERR_MODULE_NOT_FOUND aunque se invoque con `cd frontend`.
node "$RAIZ/frontend/e2e/alta-real.mjs"; navegador=$?
cd "$RAIZ/backend" && "$PY" "$RAIZ/e2e/comprobar_alta.py"; base=$?

if [ $navegador -ne 0 ] || [ $base -ne 0 ]; then
  echo "E2E: FALLÓ (navegador=$navegador base=$base)"
  exit 1
fi
echo "E2E: alta de punta a punta correcta."
