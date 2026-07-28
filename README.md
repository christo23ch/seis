# SEIS — Sistema Experto de Inversión en Subastas

Plataforma SaaS que analiza oportunidades de inversión en subastas (judiciales, AEAT, TGSS, concursales, notariales, de banco y privadas) y produce una decisión determinista, auditable y explicable: **escalera de precios** (ideal / objetivo / máximo / límite absoluto), **ROI**, **TIR**, **margen de seguridad**, índices **ICO** y **RA**, **semáforo**, **informe completo** y **checklist previo a la puja** — implementando la *Especificación Funcional y Técnica SEIS v1.0* como única fuente de verdad.

> El sistema **recomienda**; la decisión final de puja pertenece siempre al comité de inversión. Los parámetros legales y fiscales son datos versionados (T3) que deben validarse con asesoría profesional.

## Arquitectura

```
seis/
├── docker-compose.yml          # PostgreSQL+PostGIS · Redis · backend · worker Celery
├── backend/                    # FastAPI · SQLAlchemy 2 · Pydantic v2
│   ├── app/
│   │   ├── core/               # configuración y sesión de BD
│   │   ├── models.py           # esquema §5.2 (snapshot inmutable de análisis)
│   │   ├── engine/             # ★ EL MOTOR — puro, determinista, sin I/O
│   │   │   ├── contracts.py    # contratos tipados entre módulos (§4.5)
│   │   │   ├── pipeline.py     # DAG M01→M14 sobre la pizarra de hechos (§4.6)
│   │   │   ├── params/         # T3: parámetros versionados (defaults.yaml + store)
│   │   │   ├── rules/          # T2: motor de reglas (AST seguro) + catálogo YAML
│   │   │   └── modules/        # M01…M14, un fichero por módulo de la especificación
│   │   ├── services/           # persistencia del snapshot (P1)
│   │   ├── api/                # REST /api/v1
│   │   └── tasks/              # Celery (lotes y re-análisis por eventos)
│   ├── scripts/init_db.py      # esquema + siembra de conocimiento
│   └── tests/                  # ★ caso dorado §19 + vetos + precios + API + notificaciones + migraciones (118 tests)
└── frontend/                   # Next.js 15 · React 19 · TS · Tailwind · RHF+Zod · TanStack Query · Recharts · Leaflet
    ├── app/                    # login, dashboard, nueva (11 pasos), inversiones[/id],
    │                           # comparativa, mapa, configuracion, reglas, parametros, administracion
    ├── components/             # sistema de UI, widgets de resultado (escalera, riesgos…), mapa
    └── lib/                    # cliente API tipado, auth, esquema Zod del asistente
```

**Módulos** — correspondencia 1:1 con la especificación: M01 Captura · M02 Validación (ICI) · M03 Valoración · M04 Mercado (ICU) · M05 Reforma · M06 Costes · M07 R. jurídico/documental/ocupación · M08 R. urbanístico/técnico · M09 R. financiero · M10 R. comercial/liquidez/mercado · M11 Rentabilidad y escenarios · M12 Motor de decisión (vetos → RA con dominancia → ICO → escalera §9 → semáforo) · M13 Estrategia de puja (P_adj, RVC) · M14 Informe y checklist.

**Principios implementados:** P1 trazabilidad total (snapshot + reglas disparadas con versión) · P2 explicabilidad · P4 la ausencia de datos degrada, nunca se rellena a favor · P5 prudencia asimétrica (δ_v, P80, atrasos al alza) · P6 vetos no compensatorios · P8 fronteras tipadas.

## Puesta en marcha

```bash
cp .env.example .env            # OBLIGATORIO: rellenar JWT_SECRET y ADMIN_PASSWORD
                                # (vienen vacíos; con SEIS_ENV=production el arranque
                                #  falla si no se definen — ver .env.example)
docker compose up -d --build    # db + redis + backend (siembra automática) + worker
# Aplicación: http://localhost:3000   (admin@seis.local + el ADMIN_PASSWORD que definiste)
# API:        http://localhost:8000/api/v1 · Swagger en /docs
```

Desarrollo local sin Docker:

```bash
cd backend
pip install -r requirements-dev.txt
python -m scripts.init_db && uvicorn app.main:app --reload
```

## Tests

```bash
cd backend && python -m pytest -q        # 118 recogidos: 113 pasan, 2 fallan, 3 se omiten
                                        # (los 2 rojos son de PDF y preexisten: falta la
                                        #  fuente DejaVu fuera de Docker, ver docs/PENDIENTES.md)
```

`tests/test_golden_caso19.py` reproduce **íntegro el ejemplo numérico del §19** de la especificación (ICI, ICU, matriz de riesgos, RA 40, δ_v 6 %, C_F, escalera 51,1k/60,1k/69,1k/~80k, ROI 25 %, MS 25 %, RVC 1,08, semáforo AMARILLO con condiciones) y es la prueba de regresión fundacional: cualquier cambio de reglas o parámetros que altere la decisión rompe el test de forma visible.

## Endpoints principales (Fase 1)

| Método | Ruta | Uso |
|---|---|---|
| POST | `/api/v1/analisis` | Ejecuta el motor y **persiste** el snapshot |
| POST | `/api/v1/analisis/simular` | Ejecuta sin persistir (paso 11 del asistente) |
| GET | `/api/v1/analisis` · `/{id}` | Listado y detalle completo |
| GET | `/api/v1/analisis/{id}/informe` | Informe Markdown (§12) |
| GET | `/api/v1/analisis/{id}/checklist` | Checklist previo a la puja (§13) |
| GET | `/api/v1/perfiles` · `/parametros` · `/reglas` · `/opciones` | Conocimiento T2/T3 y catálogos |

## Plan de fases

| Fase | Contenido | Estado |
|---|---|---|
| **1** | Infra Docker + motor completo M01–M14 + API + tests dorados | ✅ Completada |
| **2** | Auth JWT + roles, CRUD versionado de reglas/parámetros/perfiles con vigencias y auditoría, informe PDF, Celery async, Alembic | ✅ Completada |
| **3** | Frontend Next.js 15 / React 19 / Tailwind: login, shell, dashboard, listado, detalle | ✅ Completada |
| **4** | Asistente de nueva inversión en 11 pasos (RHF + Zod, simulación y guardado) | ✅ Completada |
| **5** | Mapa Leaflet de cartera y en detalle, comparativa multi-análisis, gráficos Recharts | ✅ Completada |
| **6** | Administración de usuarios, editor del motor de reglas con historial, editor de parámetros, hardening (standalone, roles, auditoría) | ✅ Completada |
| **9** | Multi-tenancy por organización: entidad `Organizacion`, roles en dos ejes, aislamiento de análisis (recurso ajeno = 404), migración `0002` con backfill | ✅ Completada |
| **12** | Notificaciones multicanal (email/Telegram con digest y baja firmada), alertas por usuario, captación con scoring exprés, migraciones `0003`/`0004` | ✅ Completada |
| **9.5** | Saneamiento del sistema de migraciones: revisión fundacional única `0005` en sustitución de `0001`-`0004`, batería T1-T6 que ejerce Alembic de verdad, test de deriva T4 con prueba de mutación y barrera en CI | ✅ Bloques A-J ejecutados (pendiente RC-3 y merge) |
| **10** | Alta self-service: registro, verificación de email y recuperación de contraseña — migración `0006` | ⏳ **Siguiente**, tras fusionar la 9.5 |
| 11, 13-20 | Infraestructura, monetización, RGPD, landing, seguridad, captación BOE real, analítica, beta | ⏳ Pendientes |

> **Estado de las migraciones (Fase 9.5, bloques A-J ejecutados).** El historial de Alembic es **una sola revisión fundacional, `0005_esquema_base`**, con `down_revision = None`, que sustituye a la cadena `0001`-`0004` retirada (su contenido permanece en el historial de git). Antes de esta fase `alembic upgrade head` fallaba sobre una base limpia y una instalación nueva no levantaba; **medido tras la reparación**: `docker compose down -v && up -d --build` sobre volumen destruido deja el backend en `HTTP 200` sobre `/api/v1/health`, con `alembic_version = 0005`, 21 tablas y 19 columnas `jsonb`. Numeración vigente: **Fase 10 → `0006`, Fase 13 → `0007`**. Detalle y evidencias en `docs/FASE_95_PLAN_EJECUCION.md`.

**Decisiones de fase documentadas:** (a) `lat/lng` se persisten como `Numeric(9,6)`. **La migración a `geometry(Point,4326)` NO ha ocurrido**: pese a que la Fase 5 figura como completada, el esquema no tiene ninguna columna geométrica ni el proyecto declara `geoalchemy2`. La imagen desplegada es `postgis/postgis`, pero sus capacidades geoespaciales **no se usan**; convertirlas en uso real es trabajo futuro, no un hecho consumado (verificado en la Fase 9.5, Bloque J). (b) El orden del DAG resuelve la dependencia contingencia←(RA, ICI) ejecutando los módulos de riesgo antes de cerrar M06, conforme a §6.6/§9.4.


**Manual de pruebas y despliegue online:** ver `MANUAL_DE_PRUEBAS.md` (Docker local, Swagger, VPS y Render+Vercel, guion funcional del caso §19, cURL y troubleshooting).
