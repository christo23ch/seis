---
tipo: adr
fase: "E0"
estado: aceptado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aceptado
  - area/captacion
---

# ADR-0021: política de extracción web

**Fecha:** 2026-10-06 · **Fase:** E0 (herramientas de extracción) · **Base:** `CLAUDE.md`
§ «Extracción de datos web (webscraping)», especificación P1 (determinismo) y P4 (la ausencia
de datos penaliza). **Alcance:** todo dato que SEIS obtenga de una web ajena, lo haga el
producto (conectores de captación) o Claude Code al investigar (`tools/extraccion/`).

## Contexto

Varias fases necesitan datos de webs: los selectores del BOE (17-B), la fuente de comparables
(17-C, decisión abierta) y el callejero. Hasta hoy las reglas vivían como una lista breve en
`CLAUDE.md`. La Fase E0 instaló tres herramientas en `tools/extraccion/` (Scrapling 0.4.15,
ScrapeGraphAI 2.3.1, Agent Reach 1.5.0) y, al leer su código antes de usarlas, encontró que
**varias traen la evasión anti-bot activada de fábrica**:

| Herramienta | Qué hace por defecto | Medido en |
|---|---|---|
| Scrapling `FetcherSession` / `Fetcher` | `impersonate="chrome"` (huella TLS de Chrome vía curl_cffi) y `stealthy_headers=True` (cabeceras de navegador inventadas) | `scrapling/engines/static.py` |
| Scrapling `StealthyFetcher`, `patchright` | Navegador parcheado para no ser detectado | paquete `patchright` 1.63.0 |
| Scrapling `Spider` | `robots_txt_obey=False`; con `True`, evalúa robots.txt con el agente `*` y, si no lo puede descargar, **lo trata como «todo permitido»** | `scrapling/spiders/robotstxt.py` |
| ScrapeGraphAI `ChromiumLoader` (y con él sus grafos) | **Siempre** `Malenia.apply_stealth` (undetected-playwright) y `ignore_https_errors=True`, sin opción para desactivarlo | `scrapegraphai/docloaders/chromium.py` |
| ScrapeGraphAI `utils/proxy_rotation` | Busca y rota proxies gratuitos con `free-proxy` | `scrapegraphai/utils/proxy_rotation.py` |
| ScrapeGraphAI `RobotsNode` | Interpreta robots.txt **con un LLM** | `scrapegraphai/nodes/robots_node.py` |
| ScrapeGraphAI telemetría | Activa salvo `SCRAPEGRAPHAI_TELEMETRY_ENABLED=false`; envía a `sgai-oss-tracing.onrender.com` | `scrapegraphai/telemetry/telemetry.py` |
| Agent Reach `--system` | Copia su skill en `~/.claude/skills/` y recomienda proxies residenciales y cookies de cuentas | `agent_reach/cli.py`, `docs/install.md` |

Usar estas herramientas «tal cual» incumpliría las reglas de `CLAUDE.md` sin que nadie lo
decidiera. Hace falta una política explícita, verificable y con un responsable que apruebe.

## Decisión

### 1 · Fuentes oficiales primero

Orden obligatorio: **API oficial o descarga de datos abiertos** (Catastro, CartoCiudad/IGN,
INE, BOE, datos.gob.es…) → **página estable con Scrapling** → **página heterogénea con
ScrapeGraphAI** → **Agent Reach** solo para investigación de Claude Code. Saltarse un escalón
exige justificarlo en la ficha de la fuente.

### 2 · robots.txt y condiciones de uso

- Se consulta robots.txt **con nuestro User-Agent** antes de la primera petición a un dominio
  y se respetan `Disallow`, `Crawl-delay` y `Request-rate`.
- **Falla cerrado:** si robots.txt no se puede leer (error de red, TLS, 5xx), no se extrae.
  Solo un 404 explícito equivale a «sin restricciones». La ruta por defecto de Scrapling
  (falla abierto) **no basta** para fuentes reales: se comprueba antes con
  `urllib.robotparser`, como hace `tools/extraccion/pruebas_humo/humo_scrapegraph.py`.
- robots.txt nunca lo interpreta un LLM (P1): el `RobotsNode` de ScrapeGraphAI no se usa.
- Se leen las condiciones de uso y el aviso legal. Si prohíben la extracción automatizada o la
  reutilización, **no se extrae** y se busca otra fuente.

### 3 · Frecuencia limitada e identificación

- Una petición concurrente por dominio y **≥ 2 s entre peticiones** (más si robots.txt lo
  pide). Reintentos limitados y con espera creciente; un 429 o 503 detiene la extracción.
- **Caché obligatoria**: no se descarga dos veces lo mismo dentro del periodo de la ficha.
- **User-Agent identificable**: `SEIS-investigacion/<versión> (+https://github.com/christo23ch/seis)`
  o el que fije la ficha. Nunca un User-Agent de navegador.
- Fuera de horas punta cuando la fuente sea un servicio público.

### 4 · Sin evasión anti-bot

Prohibido, sin excepción y aunque la herramienta lo traiga activado de fábrica:

- **Huella o cabeceras falsas**: en Scrapling, `impersonate=None` y `stealthy_headers=False`
  siempre, de forma explícita.
- **Navegadores sigilosos**: `StealthyFetcher`, `patchright`, `camoufox`,
  `undetected-playwright` / `Malenia`, `undetected-chromedriver`, y por tanto el
  `ChromiumLoader` de ScrapeGraphAI y todo grafo que lo use para descargar. Con un navegador,
  Playwright directo, sin capa sigilosa y con `ignore_https_errors=False`.
- **Rotación de IP o proxies**: `free-proxy`, `ProxyRotator`, proxies residenciales y
  servicios de descarga por proxy (Scrape.do, BrowserBase).
- **Resolver o eludir CAPTCHAs**, inicios de sesión, muros de pago o límites de cuota.

`free-proxy` y `undetected-playwright` se instalan porque ScrapeGraphAI 2.3.1 los declara
como dependencias obligatorias. **Instalados no significa autorizados**: ningún código de SEIS
ni de `tools/extraccion/` los importa. Un CAPTCHA, un 403 o un bloqueo son la respuesta de la
fuente, y se acatan.

### 5 · Sin datos personales

No se extraen datos personales de particulares (nombres, DNI, teléfonos, correos, firmas,
datos de deudores o ejecutados). Si una página los contiene junto a los datos útiles, el
extractor los descarta **antes de guardar nada**. No se usan cookies ni cuentas de redes
sociales. Las subastas y los comparables describen inmuebles, no personas.

### 6 · Ficha por fuente

Cada fuente tiene su ficha en `tools/extraccion/ficha_fuentes/<fuente>.md` (plantilla al
final). Sin ficha **aprobada** no se hace ni una petición a esa fuente. La ficha se revisa
cuando cambian la web, sus condiciones o el uso que hacemos de ella.

### 7 · Trazabilidad

Cada descarga guarda como mínimo **URL, fecha y hora UTC, SHA-256 del contenido, estado
HTTP, herramienta y versión**. El contenido bruto se conserva en `datos_crudos/` (ignorado por
git) durante el periodo de la ficha, de modo que cualquier dato ingestado se puede volver a
derivar del original (P1). Lo cumple ya `pruebas_humo/comun.py::traza`.

### 8 · Validación con esquema antes de ingestar

Nada extraído entra en la base de SEIS sin pasar por un **esquema Pydantic** que valide tipos,
rangos y campos obligatorios. Un campo ausente o inválido se marca como ausente, **nunca se
rellena** con un valor supuesto (P4). Lo que extraiga un LLM (ScrapeGraphAI) se valida con el
mismo rigor y queda marcado como de origen no determinista: **la IA estructura, no decide**.

### 9 · Aprobación del responsable

El responsable del proyecto aprueba **cada ficha** antes de la primera extracción y **cada
primera ingesta** de una fuente en SEIS. Claude Code propone; no activa fuentes por su cuenta.

## Consecuencias

- Las pruebas de humo de E0 se limitan a `quotes.toscrape.com` y `example.com`. Desde esta red,
  `example.com` reinicia la conexión durante el handshake TLS (curl, PowerShell y Scrapling
  por igual); Scrapling siguió adelante (falla abierto) y la prueba con `urllib.robotparser` la
  omitió (falla cerrado). Esa diferencia es la razón del punto 2.
- ScrapeGraphAI queda limitado, por ahora, a estructurar HTML ya descargado por una vía
  conforme; sus grafos de descarga no se usan mientras `ChromiumLoader` imponga el modo
  sigiloso. Además, sin `langchain-anthropic` (no instalado hasta que se pida) no puede llamar
  a ningún modelo.
- Agent Reach solo se usa en modo de comprobación, sin `--system`, sin cookies y sin cuentas.
- Cada conector de captación futuro (17-B, 17-C) nace con su ficha y con tests sobre páginas
  guardadas, nunca contra la web real.
- La revisión de código de cualquier extractor busca estos nombres:
  `impersonate`, `stealthy_headers`, `StealthyFetcher`, `patchright`, `camoufox`, `Malenia`,
  `undetected`, `free_proxy`, `FreeProxy`, `ProxyRotator`, `ChromiumLoader`,
  `ignore_https_errors=True`, `robots_txt_obey = False`.

## Alternativas descartadas

- **Dejar las reglas solo en `CLAUDE.md`:** no fijaban los valores por defecto peligrosos de
  cada herramienta ni el fallo cerrado de robots.txt.
- **Desinstalar `free-proxy` y `undetected-playwright` a mano:** ScrapeGraphAI los importa
  en sus módulos y dejaría de cargar; prohibir su uso y vigilarlo en revisión es más honesto
  que un entorno roto.
- **Usar ScrapeGraphAI de extremo a extremo:** su descarga es sigilosa por diseño y su
  interpretación de robots.txt depende de un LLM; incompatible con los puntos 2 y 4.

---

## Plantilla: ficha de fuente

Copiar a `tools/extraccion/ficha_fuentes/<identificador>.md` y rellenar **todos** los campos.
Un campo sin respuesta se escribe «no consta», nunca se deja en blanco.

```markdown
# Ficha de fuente: <nombre>

| Campo | Valor |
|---|---|
| Identificador | <slug-sin-espacios> |
| Titular de la web | |
| URL base | |
| Datos que se quieren obtener | |
| Fase y uso en SEIS | |
| ¿Existe API oficial o descarga de datos abiertos? | sí / no — enlace y por qué no se usa si existe |
| Herramienta elegida y por qué (escalón del punto 1) | |
| Versión de la herramienta | |
| robots.txt — URL y fecha de lectura | |
| robots.txt — rutas permitidas / prohibidas relevantes | |
| robots.txt — Crawl-delay / Request-rate | |
| Condiciones de uso — URL y fecha de lectura | |
| Condiciones de uso — ¿permiten extracción y reutilización? (cita literal) | |
| Licencia de los datos | |
| ¿Hay datos personales en las páginas? ¿Cómo se descartan? | |
| ¿Requiere inicio de sesión, cookies o CAPTCHA? (si sí: no se extrae) | |
| User-Agent | |
| Retardo entre peticiones (s) y concurrencia | |
| Frecuencia de extracción (p. ej. diaria) y volumen estimado | |
| Caché — duración | |
| Retención de `datos_crudos/` | |
| Esquema de validación (módulo Pydantic) | |
| Fixtures para tests (ruta de las páginas guardadas) | |
| Riesgos y plan si la web cambia o bloquea | |
| Propuesta — autor y fecha | |
| **Aprobación del responsable — nombre y fecha** | pendiente |
| **Primera ingesta aprobada — fecha** | pendiente |
```
