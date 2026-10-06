# Herramientas de extracción web

Banco de trabajo **local** para investigar fuentes web antes de construir un conector del
producto. Nada de esta carpeta forma parte de SEIS: no lo importa `backend/`, no lo sirve
`frontend/` y no se despliega.

> **Política obligatoria:** [ADR-0021 — política de extracción web](../../30-Decisiones/ADR/ADR-0021-politica-de-extraccion-web.md).
> Ninguna fuente real se toca sin su ficha rellena y aprobada por el responsable.

## Estructura

| Ruta | Qué contiene | ¿Entra en git? |
|---|---|---|
| `README.md` | Este documento | Sí |
| `.gitignore` | Excluye entornos, cachés, datos, cookies y claves | Sí |
| `ficha_fuentes/` | Una ficha por fuente (plantilla en el ADR-0021) | Sí, las fichas |
| `datos_crudos/` | Salidas de extracción, con URL, fecha y hash | **No** |
| `.venv-scrapling/` | Entorno de Scrapling | **No** |
| `.venv-scrapegraph/` | Entorno de ScrapeGraphAI | **No** |
| `.venv-agentreach/` | Entorno de Agent Reach | **No** |
| `requisitos/` | `pip freeze` de cada entorno | Sí |
| `pruebas_humo/` | Pruebas contra sitios de demostración | Sí |

## Entornos

Dos entornos virtuales **separados**, porque ScrapeGraphAI arrastra un árbol de dependencias
(LangChain, `free-proxy`, `undetected-playwright`…) que no debe mezclarse con Scrapling ni,
sobre todo, con el entorno del backend. Requieren **Python ≥ 3.10**.

```bash
cd tools/extraccion
python --version                       # ≥ 3.10

# Scrapling
python -m venv .venv-scrapling
.venv-scrapling/Scripts/python -m pip install "scrapling[fetchers]"
.venv-scrapling/Scripts/scrapling install

# ScrapeGraphAI (telemetría desactivada SIEMPRE)
export SCRAPEGRAPHAI_TELEMETRY_ENABLED=false
python -m venv .venv-scrapegraph
.venv-scrapegraph/Scripts/python -m pip install scrapegraphai
.venv-scrapegraph/Scripts/python -m playwright install chromium
```

Para reproducir exactamente lo verificado, instala desde las listas congeladas:
`pip install -r requisitos/scrapling.txt` (o `scrapegraph.txt`, `agent-reach.txt`).

### Versiones verificadas (2026-10-06, Python 3.12.10, Windows 11)

| Entorno | Paquete | Versión |
|---|---|---|
| `.venv-scrapling` | scrapling | 0.4.15 |
| | playwright · patchright | 1.63.0 · 1.63.0 |
| | curl_cffi · browserforge | 0.16.3 · 1.2.4 |
| `.venv-scrapegraph` | scrapegraphai | 2.3.1 |
| | playwright | 1.63.0 |
| | langchain · langchain-core | 1.4.3 · 1.6.7 |
| | free-proxy · undetected-playwright | 1.3.0 · 0.3.0 (**prohibido su uso**, ADR-0021) |
| | langchain-anthropic | **no instalado** |
| `.venv-agentreach` | agent-reach | 1.5.0 (commit `a19a171`) |

En Linux/macOS, `Scripts/` es `bin/`. Los navegadores de Playwright se descargan en la caché
del usuario (`%LOCALAPPDATA%\ms-playwright`), no aquí.

`langchain-anthropic` **no se instala** hasta que el responsable lo pida: sin él, ScrapeGraphAI
no puede llamar a ningún modelo y solo se usan sus utilidades de carga.

## Agent Reach

Herramienta de **investigación para Claude Code**, no parte del producto
(<https://github.com/Panniantong/agent-reach>). Solo se ejecuta su comprobación segura, sin
`--system`, sin cookies y sin cuentas de redes sociales.

## Reglas rápidas (detalle en el ADR-0021)

1. API oficial antes que scraping.
2. `robots.txt` y condiciones de uso respetados; si prohíben, no se extrae.
3. Retardo entre peticiones, caché y User-Agent identificable.
4. Sin evasión anti-bot: ni modos *stealth*, ni proxies rotativos, ni resolución de CAPTCHAs.
5. Sin datos personales de particulares.
6. Cada extracción guarda URL, fecha y hash SHA-256 del contenido.
7. Nada se ingesta en SEIS sin validarlo con un esquema y sin aprobación del responsable.
