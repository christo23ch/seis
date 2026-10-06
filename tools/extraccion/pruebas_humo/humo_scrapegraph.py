"""Prueba de humo del entorno de ScrapeGraphAI contra sitios de demostración (Fase E0).

Ejecutar con el entorno de ScrapeGraphAI:
    SCRAPEGRAPHAI_TELEMETRY_ENABLED=false .venv-scrapegraph/Scripts/python pruebas_humo/humo_scrapegraph.py

Qué comprueba, y qué NO usa a propósito (ADR-0021):
- Que scrapegraphai importa y que su telemetría queda desactivada.
- Que el Playwright de este entorno navega con User-Agent identificable,
  verificación TLS activa, robots.txt consultado antes y retardo entre peticiones.
- NO usa `ChromiumLoader` ni los grafos de ScrapeGraphAI: aplican siempre
  `undetected_playwright.Malenia.apply_stealth` y abren el contexto con
  `ignore_https_errors=True`, sin opción para desactivarlo (versión 2.3.1).
- NO llama a ningún modelo: `langchain-anthropic` no está instalado.
"""

import asyncio
import os
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from comun import DOMINIOS_PERMITIDOS, RETARDO_SEGUNDOS, USER_AGENT, guardar, traza

URLS = ["https://quotes.toscrape.com/", "https://example.com/"]


def comprobar_telemetria() -> None:
    if os.environ.get("SCRAPEGRAPHAI_TELEMETRY_ENABLED", "").lower() != "false":
        raise SystemExit("Exporta SCRAPEGRAPHAI_TELEMETRY_ENABLED=false antes de ejecutar")
    from importlib.metadata import version

    from scrapegraphai.telemetry.telemetry import is_telemetry_enabled

    if is_telemetry_enabled():
        raise SystemExit("La telemetría de ScrapeGraphAI sigue activa")
    print(f"scrapegraphai {version('scrapegraphai')} importado; telemetría desactivada")


def robots_permite(url: str) -> tuple[bool, str]:
    """Consulta robots.txt con nuestro User-Agent. Falla cerrado salvo un 404 explícito."""
    partes = urlparse(url)
    robots_url = f"{partes.scheme}://{partes.netloc}/robots.txt"
    peticion = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(peticion, timeout=15) as resp:
            parser = RobotFileParser()
            parser.parse(resp.read().decode("utf-8", errors="replace").splitlines())
            return parser.can_fetch(USER_AGENT, url), f"robots.txt {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True, "robots.txt 404 (sin restricciones)"
        return False, f"robots.txt HTTP {e.code}: no se extrae"
    except Exception as e:  # red caída, TLS, DNS: sin robots.txt legible no se extrae
        return False, f"robots.txt ilegible ({type(e).__name__}): no se extrae"


async def descargar(urls: list[str]) -> tuple[list[dict], list[dict]]:
    from playwright.async_api import async_playwright

    trazas, resultados = [], []
    async with async_playwright() as p:
        navegador = await p.chromium.launch(headless=True)
        contexto = await navegador.new_context(user_agent=USER_AGENT, ignore_https_errors=False)
        pagina = await contexto.new_page()
        ultima = 0.0
        for url in urls:
            dominio = urlparse(url).netloc
            if dominio not in DOMINIOS_PERMITIDOS:
                resultados.append({"url": url, "estado": "fuera de la lista de demostración"})
                continue
            permitido, motivo = robots_permite(url)
            if not permitido:
                resultados.append({"url": url, "estado": f"OMITIDA — {motivo}"})
                continue
            espera = RETARDO_SEGUNDOS - (time.monotonic() - ultima)
            if espera > 0:
                await asyncio.sleep(espera)
            try:
                respuesta = await pagina.goto(url, wait_until="domcontentloaded", timeout=30_000)
                ultima = time.monotonic()
                html = await pagina.content()
                trazas.append(traza(url, html.encode("utf-8"), "playwright (entorno scrapegraph)", respuesta.status))
                citas = await pagina.locator("div.quote").count()
                resultados.append({
                    "url": url,
                    "estado": f"OK — {motivo}",
                    "titulo": await pagina.title(),
                    "citas": citas,
                })
            except Exception as e:
                ultima = time.monotonic()
                resultados.append({"url": url, "estado": f"FALLO — {type(e).__name__}: {str(e).splitlines()[0]}"})
        await navegador.close()
    return trazas, resultados


def main() -> None:
    comprobar_telemetria()
    trazas, resultados = asyncio.run(descargar(URLS))
    destino = guardar("humo_scrapegraph", trazas + [{"resultado": r} for r in resultados])

    print("\n=== Resumen entorno ScrapeGraphAI ===")
    for r in resultados:
        print(r)
    for t in trazas:
        print(f"{t['estado_http']}  {t['url']}  sha256={t['sha256'][:16]}…  {t['bytes']} B")
    print(f"Trazas en: {destino}")
    if not any(r.get("citas") for r in resultados):
        raise SystemExit("La prueba de humo no obtuvo ninguna cita")


if __name__ == "__main__":
    main()
