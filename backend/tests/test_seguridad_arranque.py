"""Guardia de secretos en producción — cierre del hallazgo C1.

C1: el flujo documentado `cp .env.example .env` desplegaba en producción con un
`JWT_SECRET` y un `ADMIN_PASSWORD` publicados en el repositorio, porque la guardia
comparaba contra dos cadenas concretas y los placeholders del fichero no estaban
entre ellas. Estos tests fijan el comportamiento corregido: la validación es
estructural y ningún valor de ejemplo puede arrancar en producción.
"""
from pathlib import Path

import pytest

from app.core.config import (ENTORNOS_ESTRICTOS, ENTORNOS_SOPORTADOS,
                             EntornoNoSoportadoError, SecretoInseguroError, Settings,
                             _validar_seguridad_entorno)

RAIZ_REPO = Path(__file__).resolve().parents[2]

SECRETO_FUERTE = "kJ7pQz2Xv9RtNw4bYm6HcE8sLdA3fUgW1oPiZxTqVnMr5eBk"
PASSWORD_FUERTE = "Zq8Rm2Vt6Yx4Bn7Kw"


def _leer_env_example() -> dict[str, str]:
    """Devuelve las variables declaradas en `.env.example` (clave → valor literal)."""
    valores = {}
    for linea in (RAIZ_REPO / ".env.example").read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, _, valor = linea.partition("=")
            valores[clave.strip()] = valor.strip()
    return valores


def _ajustes(**overrides) -> Settings:
    base = dict(seis_env="production", jwt_secret=SECRETO_FUERTE,
                admin_password=PASSWORD_FUERTE)
    base.update(overrides)
    return Settings(**base)


def test_secretos_fuertes_permiten_arrancar_en_produccion():
    _validar_seguridad_entorno(_ajustes())      # no debe lanzar


def test_desarrollo_y_tests_no_se_ven_afectados():
    """La suite corre con los secretos triviales de conftest: no debe romperse."""
    for entorno in ("development", "test"):
        _validar_seguridad_entorno(
            _ajustes(seis_env=entorno, jwt_secret="secreto-de-test",
                     admin_password="admin"))


@pytest.mark.parametrize("campo", ["jwt_secret", "admin_password"])
def test_valor_vacio_aborta_el_arranque(campo):
    with pytest.raises(SecretoInseguroError):
        _validar_seguridad_entorno(_ajustes(**{campo: ""}))


@pytest.mark.parametrize("campo", ["jwt_secret", "admin_password"])
def test_valor_por_defecto_del_modelo_aborta_el_arranque(campo):
    """El defecto se lee del propio modelo, no de una cadena escrita a mano."""
    defecto = Settings.model_fields[campo].default
    with pytest.raises(SecretoInseguroError):
        _validar_seguridad_entorno(_ajustes(**{campo: defecto}))


def test_secreto_corto_o_poco_variado_aborta_el_arranque():
    with pytest.raises(SecretoInseguroError):
        _validar_seguridad_entorno(_ajustes(jwt_secret="corto"))
    with pytest.raises(SecretoInseguroError):
        # Longitud suficiente pero variedad ínfima: predecible.
        _validar_seguridad_entorno(_ajustes(jwt_secret="ababababababababababababababababab"))


@pytest.mark.parametrize("placeholder", [
    "cambia-este-secreto-largo-y-aleatorio",      # el que entregaba .env.example (C1)
    "cambia-la-clave-inicial-del-admin",          # idem, para ADMIN_PASSWORD
    "your-super-secret-key-goes-here-please",
    "REPLACE_ME_WITH_A_REAL_SECRET_VALUE_1234",
    "clave-de-ejemplo-para-el-entorno-de-demo",
])
def test_cualquier_placeholder_aborta_el_arranque(placeholder):
    """No depende de conocer la cadena exacta: se detecta el marcador de plantilla."""
    with pytest.raises(SecretoInseguroError):
        _validar_seguridad_entorno(_ajustes(jwt_secret=placeholder))


def test_env_example_no_entrega_secretos_utilizables():
    """Regresión directa de C1: el fichero de ejemplo no debe traer valores usables.

    Si alguien vuelve a publicar un placeholder en `.env.example`, este test falla
    aunque la guardia lo detectase: el vector se cierra también en el origen.
    """
    valores = _leer_env_example()
    for clave in ("JWT_SECRET", "ADMIN_PASSWORD"):
        assert clave in valores, f"{clave} debe seguir documentada en .env.example"
        assert valores[clave] == "", (
            f"{clave} en .env.example debe estar VACÍA; cualquier valor ahí es "
            f"público (está en el repositorio). Valor encontrado: {valores[clave]!r}")


def test_valores_de_env_example_rechazados_por_la_guardia():
    """Doble red: aunque alguien copie .env.example tal cual, producción no arranca."""
    valores = _leer_env_example()
    with pytest.raises(SecretoInseguroError):
        _validar_seguridad_entorno(_ajustes(
            jwt_secret=valores.get("JWT_SECRET", ""),
            admin_password=valores.get("ADMIN_PASSWORD", "")))


def test_seis_env_con_mayusculas_no_evade_la_guardia():
    with pytest.raises(SecretoInseguroError):
        _validar_seguridad_entorno(_ajustes(seis_env="Production", jwt_secret=""))


# ── P1-1: un entorno desconocido no puede desactivar la validación ──────────

@pytest.mark.parametrize("entorno", [
    "produccion",     # grafía española: desactivaba la guardia en silencio
    "prod",           # abreviatura habitual
    "stagging",       # errata de «staging»: parecerse no basta (Fase 11, Bloque D)
    "stage",          # abreviatura de «staging»: tampoco basta
    "PROD",
    "",               # sin valor
    "producción",     # con tilde
])
def test_entorno_desconocido_aborta_el_arranque(entorno):
    """P1-1: antes, cualquier valor distinto de «production» dejaba pasar
    secretos vacíos sin decir nada. Ahora el arranque se detiene de forma
    explícita en vez de continuar sin protección."""
    with pytest.raises(EntornoNoSoportadoError):
        _validar_seguridad_entorno(_ajustes(seis_env=entorno, jwt_secret=""))


@pytest.mark.parametrize("entorno", ENTORNOS_SOPORTADOS)
def test_entornos_soportados_no_se_rechazan(entorno):
    """Los cuatro entornos declarados son válidos con secretos fuertes.

    Se parametriza sobre la constante y no sobre una lista escrita a mano: así,
    añadir un quinto entorno obliga a que pase por aquí en vez de entrar sin que
    ningún test lo mire.
    """
    _validar_seguridad_entorno(_ajustes(seis_env=entorno))


def test_variantes_de_grafia_de_production_siguen_siendo_estrictas():
    """Mayúsculas y espacios se aceptan como `production`, pero SIN relajar nada."""
    for variante in ("Production", "PRODUCTION", "  production  "):
        with pytest.raises(SecretoInseguroError):
            _validar_seguridad_entorno(_ajustes(seis_env=variante, jwt_secret=""))


# ── Fase 11, Bloque D: staging es un entorno soportado Y estricto ───────────

def test_staging_es_un_entorno_soportado():
    """Antes de la Fase 11, `SEIS_ENV=staging` abortaba el arranque por desconocido.

    El Plan Maestro exige un entorno de pruebas idéntico al real, así que el
    entorno tenía que existir. Lo que NO podía pasar es que existiera siendo laxo.
    """
    assert "staging" in ENTORNOS_SOPORTADOS
    _validar_seguridad_entorno(_ajustes(seis_env="staging"))      # no debe lanzar


def test_staging_es_estricto_y_esta_en_la_lista_de_estrictos():
    assert "staging" in ENTORNOS_ESTRICTOS


@pytest.mark.parametrize("campo", ["jwt_secret", "admin_password"])
def test_staging_con_secreto_debil_aborta_el_arranque(campo):
    """Test negativo capital del bloque.

    Un staging es una réplica del sistema real, alcanzable desde internet y a
    menudo poblada con una copia de los datos de producción. Soportarlo con la
    guardia de secretos desactivada habría sido la peor combinación posible: la
    superficie de producción con la puerta abierta.
    """
    with pytest.raises(SecretoInseguroError):
        _validar_seguridad_entorno(_ajustes(seis_env="staging", **{campo: ""}))


def test_staging_con_secreto_de_plantilla_aborta_el_arranque():
    """La validación estructural del hallazgo C1 aplica igual en staging."""
    with pytest.raises(SecretoInseguroError):
        _validar_seguridad_entorno(
            _ajustes(seis_env="staging", jwt_secret="cambia-este-secreto-en-staging"))


def test_variantes_de_grafia_de_staging_siguen_siendo_estrictas():
    """Normalizar mayúsculas y espacios no puede servir para colarse sin secretos."""
    for variante in ("Staging", "STAGING", "  staging  "):
        with pytest.raises(SecretoInseguroError):
            _validar_seguridad_entorno(_ajustes(seis_env=variante, jwt_secret=""))


@pytest.mark.parametrize("entorno", ENTORNOS_ESTRICTOS)
def test_get_settings_aborta_el_arranque_con_un_secreto_debil(entorno, monkeypatch):
    """El único test que ejercita la guardia POR DONDE EL PROCESO ARRANCA.

    Todos los demás llaman a `_validar_seguridad_entorno` directamente. Eso prueba
    la función, no el comportamiento: si alguien borrase la línea que la invoca
    dentro de `get_settings`, la guardia quedaría **completamente muerta** y los
    veinte tests seguirían verdes. El entregable de este bloque no es que una
    función privada devuelva un error, es que **el proceso no arranque**.

    `get_settings` está cacheada con `lru_cache`, de ahí el vaciado antes y
    después: sin el segundo, este test dejaría envenenada la caché para toda la
    suite.
    """
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        monkeypatch.setenv("SEIS_ENV", entorno)
        monkeypatch.setenv("JWT_SECRET", "corto")
        monkeypatch.setenv("ADMIN_PASSWORD", "admin")

        with pytest.raises(SecretoInseguroError):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_el_mensaje_de_error_nombra_el_entorno_real_y_no_produccion():
    """Quien despliega staging debe leer «staging» en el error, no «production».

    Con un mensaje que solo hablara de producción, el operador buscaría el fallo
    en el sitio equivocado — y el arranque abortado sería un misterio en vez de
    una instrucción.
    """
    with pytest.raises(SecretoInseguroError) as fallo:
        _validar_seguridad_entorno(_ajustes(seis_env="staging", jwt_secret=""))

    assert "staging" in str(fallo.value)
    assert "SEIS_ENV=production" not in str(fallo.value)


# ── P0-1: la contraseña de la base de datos tampoco puede ser pública ───────

def test_env_example_no_entrega_contrasena_de_base_de_datos():
    """P0-1: `POSTGRES_PASSWORD` no puede traer ningún valor en el repositorio."""
    valores = _leer_env_example()
    assert "POSTGRES_PASSWORD" in valores, "debe seguir documentada en .env.example"
    assert valores["POSTGRES_PASSWORD"] == "", (
        "POSTGRES_PASSWORD en .env.example debe estar VACÍA: cualquier valor ahí "
        f"es público. Valor encontrado: {valores['POSTGRES_PASSWORD']!r}")


def test_compose_no_incrusta_contrasenas_por_defecto():
    """P0-1: docker-compose no puede traer un respaldo público de ningún secreto.

    `${VAR:-valor}` aplicaría un valor embebido —y por tanto público— cuando la
    variable falte; los secretos deben usar `${VAR:?...}`, que aborta el arranque.
    """
    compose = (RAIZ_REPO / "docker-compose.yml").read_text(encoding="utf-8")
    for secreto in ("POSTGRES_PASSWORD", "JWT_SECRET", "ADMIN_PASSWORD"):
        assert f"${{{secreto}:-" not in compose, (
            f"{secreto} tiene un valor por defecto embebido en docker-compose.yml; "
            "sería público. Debe declararse como ${" + secreto + ":?...}")
        assert f"${{{secreto}:?" in compose, (
            f"{secreto} debe declararse obligatorio con ${{{secreto}:?...}}")
