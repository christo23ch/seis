"""Prueba de humo de Scrapling contra sitios de demostración (Fase E0).

Ejecutar con el entorno de Scrapling:
    .venv-scrapling/Scripts/python pruebas_humo/humo_scrapling.py

Configuración conforme al ADR-0021:
- robots_txt_obey=True y una sola petición concurrente con retardo fijo.
- impersonate=None y stealthy_headers=False: Scrapling trae de fábrica la huella TLS
  de Chrome y cabeceras de navegador falsas; aquí se desactivan y se envía un
  User-Agent identificable.
- allowed_domains limita el rastreo a los sitios de demostración.
"""

import logging
from urllib.parse import urlparse

from scrapling.fetchers import FetcherSession
from scrapling.spiders import Spider

from comun import DOMINIOS_PERMITIDOS, RETARDO_SEGUNDOS, USER_AGENT, guardar, traza

PAGINAS_MAXIMAS = 2


class HumoSpider(Spider):
    name = "humo_e0"
    start_urls = ["https://quotes.toscrape.com/", "https://example.com/"]
    allowed_domains = DOMINIOS_PERMITIDOS
    robots_txt_obey = True
    concurrent_requests = 1
    download_delay = RETARDO_SEGUNDOS
    logging_level = logging.INFO

    def __init__(self):
        self.trazas: list[dict] = []
        self.paginas_citas = 0
        super().__init__()

    def configure_sessions(self, manager):
        manager.add(
            "default",
            FetcherSession(
                impersonate=None,
                stealthy_headers=False,
                headers={"User-Agent": USER_AGENT},
                retries=1,
            ),
        )

    async def parse(self, response):
        self.trazas.append(traza(response.url, response.body, "scrapling", response.status))
        dominio = urlparse(response.url).netloc

        if dominio == "example.com":
            yield {"fuente": dominio, "titulo": response.css("h1::text").get()}
            return

        self.paginas_citas += 1
        for cita in response.css("div.quote"):
            yield {
                "fuente": dominio,
                "texto": cita.css("span.text::text").get(),
                "etiquetas": cita.css("a.tag::text").getall(),
            }
        siguiente = response.css("li.next a::attr(href)").get()
        if siguiente and self.paginas_citas < PAGINAS_MAXIMAS:
            yield response.follow(siguiente)


def main() -> None:
    spider = HumoSpider()
    resultado = spider.start()
    items = list(resultado.items)
    destino = guardar("humo_scrapling", spider.trazas + [{"item": i} for i in items])

    print("\n=== Resumen Scrapling ===")
    for t in spider.trazas:
        print(f"{t['estado_http']}  {t['url']}  sha256={t['sha256'][:16]}…  {t['bytes']} B")
    print(f"Elementos extraídos: {len(items)}")
    print(f"Estadísticas: {resultado.stats.to_dict()}")
    print(f"Trazas en: {destino}")

    citas = [i for i in items if i.get("fuente") == "quotes.toscrape.com"]
    ejemplo = [i for i in items if i.get("fuente") == "example.com"]
    print(f"quotes.toscrape.com: {'OK' if citas else 'FALLO'} ({len(citas)} citas)")
    print(f"example.com: {'OK' if ejemplo else 'FALLO (ver el registro de errores)'}")
    if not citas:
        raise SystemExit("La prueba de humo no extrajo ninguna cita")


if __name__ == "__main__":
    main()
