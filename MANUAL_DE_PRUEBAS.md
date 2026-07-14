# SEIS — Manual de instrucciones para probar el programa

Este manual explica, paso a paso, cómo levantar SEIS y probarlo de forma completa: en tu máquina con Docker, **online** desplegándolo en un servidor o en servicios gratuitos, y mediante la API con Swagger. Incluye un guion de prueba funcional con datos reales (el caso de referencia §19 de la especificación) y los resultados que debes obtener.

---

## 1 · Requisitos

| Opción | Necesitas |
|---|---|
| A — Local con Docker | Docker Desktop o Docker Engine + Compose v2 |
| B — Solo API (Swagger) | Un navegador (la API incluye interfaz de pruebas en `/docs`) |
| C — Online en VPS | Un servidor Linux (Hetzner, DigitalOcean, OVH…) con 2 GB RAM |
| D — Online en PaaS | Cuenta gratuita en Render/Railway (backend) y Vercel (frontend) |

Credenciales iniciales (se crean solas en el primer arranque):
**`admin@seis.local` / `admin`** — cámbialas inmediatamente creando otro admin y usa variables de entorno en producción.

---

## 2 · Opción A — Prueba local completa (3 comandos)

```bash
cd seis
cp .env.example .env          # opcional: edita contraseñas
docker compose up -d --build  # PostgreSQL+PostGIS, Redis, backend, worker y frontend
```

Espera ~2-4 minutos la primera vez (compila el frontend). Después:

| Servicio | URL |
|---|---|
| **Aplicación web** | http://localhost:3000 |
| API + Swagger interactivo | http://localhost:8000/docs |
| Salud del backend | http://localhost:8000/api/v1/health |

Entra en http://localhost:3000 → **Iniciar sesión** con `admin@seis.local` / `admin`.

Comandos útiles:
```bash
docker compose logs -f backend     # ver el motor en marcha
docker compose down                # parar
docker compose down -v             # parar y BORRAR la base de datos (reset total)
```

---

## 3 · Opción B — Probar online solo con la API (Swagger)

Cualquier despliegue del backend expone en **`/docs`** una consola interactiva completa:

1. Abre `https://TU-BACKEND/docs`.
2. `POST /api/v1/auth/login` → *Try it out* → username `admin@seis.local`, password `admin` → copia el `access_token`.
3. Pulsa el botón **Authorize** (candado, arriba a la derecha) y pega el token.
4. Ya puedes ejecutar `POST /api/v1/analisis/simular` con el JSON del §6 de este manual y ver la decisión completa sin tocar el frontend.

---

## 4 · Opción C — Despliegue online en un VPS (todo en uno)

En un servidor Ubuntu 22/24 recién creado:

```bash
# 1) Docker
curl -fsSL https://get.docker.com | sh

# 2) Sube el proyecto (desde tu máquina):
scp seis_completo.zip root@TU_IP:/opt/ && ssh root@TU_IP
cd /opt && apt-get install -y unzip && unzip seis_completo.zip && cd seis

# 3) Configuración de producción
cp .env.example .env && nano .env
#   POSTGRES_PASSWORD=una-clave-larga
#   SEIS_CORS_ORIGINS=http://TU_IP:3000        (o https://tu-dominio)
# añade también:
#   JWT_SECRET=otra-clave-larga-aleatoria
#   ADMIN_PASSWORD=clave-inicial-admin

# 4) Arranque (el frontend debe conocer la URL pública del backend)
NEXT_PUBLIC_API_URL=http://TU_IP:8000 docker compose up -d --build
```

Abre en el navegador `http://TU_IP:3000`. Puertos a permitir en el firewall: **3000** y **8000** (o pon delante Caddy/Nginx con HTTPS y expón solo 80/443 — recomendado en producción real).

---

## 5 · Opción D — Despliegue online gratuito (Render + Vercel)

**Backend en Render** (o Railway, equivalente):
1. *New → Web Service → Deploy from repo/zip* apuntando a la carpeta `backend/` (tiene su `Dockerfile`).
2. Añade una base **PostgreSQL** gestionada del propio Render y copia su *Internal URL*.
3. Variables de entorno del servicio:
   `DATABASE_URL=postgresql+psycopg2://…` (la URL anterior, cambiando `postgres://` por `postgresql+psycopg2://`)
   `JWT_SECRET=…` · `ADMIN_PASSWORD=…` · `SEIS_CORS_ORIGINS=https://TU-APP.vercel.app`
4. *Start command*: `sh -c "python -m scripts.init_db && uvicorn app.main:app --host 0.0.0.0 --port $PORT"`
5. Comprueba `https://TU-BACKEND.onrender.com/docs`.

**Frontend en Vercel:**
1. *Add New → Project*, importa la carpeta `frontend/` (framework Next.js detectado solo).
2. Variable de entorno: `NEXT_PUBLIC_API_URL=https://TU-BACKEND.onrender.com`.
3. *Deploy* → tu URL pública `https://TU-APP.vercel.app` ya sirve SEIS completo.

> Redis/Celery son opcionales para probar: el análisis principal es síncrono. Para el modo asíncrono en PaaS añade un Redis gestionado y un *worker* con `celery -A app.tasks.celery_app.celery worker`.

---

## 6 · Guion de prueba funcional (caso de referencia §19)

Inicia sesión y pulsa **Nueva inversión**. Introduce exactamente esto (lo no mencionado, déjalo por defecto):

| Paso | Valores |
|---|---|
| **1 · Datos generales** | Perfil **Reforma integral + venta (flip)** · Fuente **judicial_boe** · Valor de subasta **152000** · Depósito **5** · Horas hasta cierre **200** |
| **2 · Tipo de activo** | Vivienda · Superficie **82** · Estado **malo** · Año **1975** |
| **3 · Registrales** | Sin cargas · Situación posesoria **precario** |
| **4 · Urbanísticos** | Todo por defecto (uso compatible ✓) |
| **5 · Ubicación** | Municipio **Ciudad Ejemplo** · CCAA **ejemplo** · Micro: transporte 70, seguridad 60, sanidad 65, educación 60, comercio 70, verdes 55, pipeline 55, potencial 60, entorno 65 |
| **6 · Valoraciones** | 7 comparables **reformado/testigo**: 2100 · 2200 · 2250 · 2293 · 2350 · 2420 · 2490 €/m². Macro: tendencia **3**, stock **6**, DOM venta **75**, DOM alquiler **25**, población **0.5**, renta **32000**, yield **5.5** |
| **7 · Costes** | ITP manual **6** % (resto vacío = estimación prudente) |
| **8 · Reforma** | Automático · **sin** visita interior |
| **9 · Financiación** | 100 % equity (cash) |
| **10 · Validación** | Marca: nota simple (**10** días), cert. cargas, avalúo, fotos exteriores, IBI, catastro conciliado. Deja sin marcar: posesión verificada, fotos interiores, cert. comunidad, ITE |
| **11 · Resultado** | Se calcula solo |

**Resultado esperado** (tolerancias de redondeo):

- Semáforo **🟡 AMARILLO** con condiciones · **ICO 64** (60–74) · **RA 40** (medio, dominancia *una_alta* por ocupación 4×3)
- ICI ≈ 63 · ICU ≈ 66 · δ_v 6 % · VS prudente ≈ **176.700 €**
- Escalera: ideal **≈ 51.300** · objetivo **≈ 60.000** · máximo **≈ 68.700** · límite **≈ 80.000 €** (la línea discontinua del P. adjudicación esperado, **63.840 €**, cruza entre objetivo y máximo)
- ROI base **25 %** (≈ 23 % anualizado) · TIR ~26 % · Margen de seguridad **≈ 25 %** · RVC **1,08 (alcanzable)**
- Condiciones: verificación posesoria in situ; certificado de comunidad
- Checklist: bloqueantes pendientes de **nota simple ≤ 5 días** y **verificación posesoria**

Pulsa **Guardar análisis** → detalle con pestañas · **Descargar informe PDF** debe producir un PDF real de varias páginas.

### Pruebas de vetos (comprueba que ninguna virtud compensa un defecto letal)
- Repite con **ocupación = renta_antigua** → **ROJO** con veto `VETO-OCU-01`.
- Repite con **financiación hipoteca sin preaprobar** → **ROJO** con `VETO-FIN-01` y su vía de subsanación.
- Repite con **valor de subasta 400000** → **ROJO** competitivo `VETO-COMP-01` (RVC < 0,80).

### Pruebas de gobernanza del conocimiento
1. **Parámetros** → cambia ITP de `ejemplo` a **8** y guarda. Vuelve al asistente (mismo caso pero con el ITP manual **vacío**): `c_v` pasa de 6,4 % a **8,4 %** y todos los precios bajan; el análisis estampa `version_parametros …+1ov`. Restaura a 6.
2. **Motor de reglas** → en `SEM-EJEC-01` pulsa *Nueva versión*, cambia el texto de la condición, justifica y publica: el historial muestra la vigencia cerrada y los nuevos análisis usan la redacción v2.
3. **Administración** → crea un usuario rol **lector**; entra con él: puede consultar, pero *Nueva inversión* y las ediciones devuelven acceso denegado (403).

---

## 7 · Recetario cURL (para pruebas automatizadas)

```bash
API=http://localhost:8000/api/v1

TOKEN=$(curl -s -X POST $API/auth/login -d "username=admin@seis.local&password=admin" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# analizar y persistir (payload: guarda el JSON del §6 como caso.json)
curl -s -X POST $API/analisis -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @caso.json

# listado · detalle · informe markdown · checklist · PDF
curl -s $API/analisis -H "Authorization: Bearer $TOKEN"
curl -s $API/analisis/{ID} -H "Authorization: Bearer $TOKEN"
curl -s $API/analisis/{ID}/informe -H "Authorization: Bearer $TOKEN"
curl -s -o informe.pdf $API/analisis/{ID}/informe.pdf -H "Authorization: Bearer $TOKEN"

# análisis asíncrono vía Celery (con worker y Redis levantados)
curl -s -X POST $API/analisis/async -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @caso.json
curl -s $API/tareas/{TAREA_ID} -H "Authorization: Bearer $TOKEN"
```

Suite de tests del motor (49 pruebas, incluye el caso dorado):
```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest -q
```

---

## 8 · Solución de problemas

| Síntoma | Causa y solución |
|---|---|
| El frontend carga pero el login falla con *Failed to fetch* | El navegador no alcanza el backend o CORS: revisa `NEXT_PUBLIC_API_URL` (se fija **al compilar** el frontend) y `SEIS_CORS_ORIGINS` en el backend; reconstruye con `docker compose up -d --build`. |
| `401 Credenciales inválidas` tras reiniciar | El token caducó (12 h) → vuelve a iniciar sesión. |
| Quiero empezar de cero | `docker compose down -v && docker compose up -d --build`. |
| El PDF sale sin acentos raros | Falta `fonts-dejavu-core` (ya incluido en la imagen); reconstruye el backend. |
| Puerto ocupado | Cambia el mapeo en `docker-compose.yml` (`3001:3000`, `8001:8000`) y ajusta las variables. |

## 9 · Seguridad mínima antes de exponerlo a Internet

1. `JWT_SECRET` y `POSTGRES_PASSWORD` largos y únicos; `ADMIN_PASSWORD` propio y cambio de contraseña tras el primer login.
2. HTTPS con un proxy (Caddy: dos líneas de configuración) y cerrar 8000/5432 al exterior.
3. Los tipos fiscales y reglas legales del sistema son **parámetros versionados**: valídalos con asesoría profesional antes de operar con dinero real (§20 de la especificación). El sistema recomienda; la decisión de puja es del comité.
