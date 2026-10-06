---
tipo: puente
aliases:
  - Extracción de datos web
  - Webscraping
tags:
  - tipo/puente
  - area/captacion
---

# Herramientas de extracción web

> Nota-puente. El contenido vive en [[CLAUDE-md|CLAUDE.md]], sección **«Extracción de datos web
> (webscraping)»**, al final del fichero. Esta nota no lo repite: la lista y las reglas se
> mantienen en un solo sitio.

📄 Fichero real: `CLAUDE.md` § Extracción de datos web (webscraping)

## Para qué es la referencia

Es el punto de partida obligado de toda fase que tenga que obtener datos de webs. Hoy, en
concreto:

- **17-B — selectores del BOE y comparables:** el conector de subastas existe pero no está
  ajustado al HTML real del portal, y la fuente de comparables es una decisión abierta (17-C,
  `docs/ESTADO_ACTUAL.md`).
- **Callejero:** geocodificar la dirección del inmueble para no depender de la coordenada
  aproximada de la capital de provincia que introdujo la [[Fase-5I]] (deuda 25 de
  `docs/ESTADO_ACTUAL.md` §4).

## Lo que fija, en resumen

- **Orden de preferencia:** primero una API oficial (Catastro, CartoCiudad/IGN, INE, BOE…), y
  solo si no existe, una herramienta de extracción (Scrapling, ScrapeGraphAI, Agent Reach).
  El callejero, por ejemplo, tiene API oficial: CartoCiudad ya la usa
  `frontend/scripts/coordenadas-provincias.mjs`.
- **Cada scraper nace con un ADR** que elige la herramienta tras leer su README y su versión
  actual, no de memoria.
- **Límites:** robots.txt y condiciones de uso, sin evasión de CAPTCHAs ni antibot (si una
  herramienta ofrece modos de ese tipo, no se usan), frecuencia moderada con caché y
  User-Agent identificable, sin datos personales de particulares.
- **Pruebas con páginas guardadas**, nunca contra la web real; la dependencia entra solo en la
  fase que la necesita.

## Política y banco de trabajo (Fase E0)

- **Política obligatoria:** [[ADR-0021-politica-de-extraccion-web|ADR-0021 — política de
  extracción web]], con la plantilla de ficha de fuente.
- **Herramientas instaladas** en `tools/extraccion/` (entornos separados, fuera del backend):
  Scrapling 0.4.15, ScrapeGraphAI 2.3.1 y Agent Reach 1.5.0. Agent Reach es investigación
  de Claude Code, no producto.
