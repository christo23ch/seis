"""Fase 5I — formulario de alta: lo que el backend le ofrece y lo que acepta de él.

El formulario NO se arregla en el backend: el contrato sigue rechazando `""` en un
campo numérico (es una cadena que no es un número), y lo correcto es que el
formulario omita el campo vacío. Estos tests fijan las dos mitades del acuerdo:
el cuerpo mínimo que envía ahora el formulario se acepta, y los valores por
defecto que muestra salen del catálogo T3 vigente y no de cifras copiadas.
"""
from __future__ import annotations

# El cuerpo que produce `prepararEnvio` con SOLO los obligatorios rellenados
# (frontend/tests/schema.test.ts): los opcionales vacíos no viajan.
CUERPO_MINIMO = {
    "perfil": "flip_integral",
    "subasta": {"fuente": "judicial_boe", "valor_subasta": 152000, "deposito_pct": 0.05,
                "subastas_desiertas_previas": 0,
                # Fase 5J-1: preguntas del procedimiento con sus valores por defecto.
                "procedimiento": "judicial", "regimen_judicial": "no_se"},
    "activo": {"tipologia": "vivienda", "superficie_m2": 82, "estado_conservacion": "desconocido",
               "es_vivienda_habitual": False, "vivienda_habitual_ejecutado": "no_consta",
               "vpo": False, "municipio": "Madrid", "provincia": "", "ccaa": "madrid"},
    "cargas": [],
    "ocupacion": {"estado": "desconocida"},
    "comparables": [{"precio_m2": 2293, "estado": "reformado", "origen": "testigo", "meses_antiguedad": 0}],
}


def test_el_cuerpo_minimo_del_formulario_se_analiza(api, headers):
    r = api.post("/api/v1/analisis/simular", json=CUERPO_MINIMO, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["decision"]["semaforo"] in {"verde", "amarillo", "naranja", "rojo"}


def test_la_cadena_vacia_sigue_siendo_un_error_del_cliente(api, headers):
    """No se relaja el contrato: «» no es un número. El arreglo es no enviarla."""
    cuerpo = {**CUERPO_MINIMO, "activo": {**CUERPO_MINIMO["activo"], "anio_construccion": ""}}
    r = api.post("/api/v1/analisis/simular", json=cuerpo, headers=headers)
    assert r.status_code == 422
    assert any(e["loc"][-2:] == ["activo", "anio_construccion"] for e in r.json()["detail"])


def test_opciones_conserva_lo_que_ya_devolvia(api, headers):
    d = api.get("/api/v1/opciones", headers=headers).json()
    assert {"tipologias", "fuentes", "estados_conservacion", "estados_ocupacion", "ccaa",
            "perfiles", "valores_defecto"} <= d.keys()


def test_los_valores_por_defecto_son_los_del_catalogo_semilla(api, headers):
    """Cifras literales de `defaults.yaml`: un cambio de la semilla se ve aquí."""
    d = api.get("/api/v1/opciones", headers=headers).json()["valores_defecto"]
    assert d["tenencia_mensual"] == 240
    assert d["adquisicion_fija"] == 2700          # 2.100 aranceles + 600 procurador
    assert d["tasacion_banco"] == 400
    assert d["atrasos_pct_valor_subasta"] == 0.016 and d["atrasos_minimo"] == 1500
    assert d["itp_por_ccaa"]["madrid"] == 0.06
    assert d["baremos_reforma_m2"]["media"] == 560


def test_el_coste_fijo_mostrado_es_el_que_aplica_el_motor(api, headers):
    """No basta con leer el mismo YAML: el cuerpo mínimo, sin override, debe dar en
    M06 exactamente la cifra que el formulario muestra como valor por defecto."""
    d = api.get("/api/v1/opciones", headers=headers).json()["valores_defecto"]
    res = api.post("/api/v1/analisis/simular", json=CUERPO_MINIMO, headers=headers).json()
    assert res["costes"]["desglose_p50"]["adquisicion_fija"] == d["adquisicion_fija"]


def test_los_valores_por_defecto_siguen_al_catalogo_vigente(api, headers):
    """Un cambio de parámetro en BD (sin desplegar) se refleja en el formulario."""
    def poner(clave: str, valor: float) -> None:
        r = api.put("/api/v1/parametros", headers=headers,
                    json={"clave": clave, "valor": valor, "fuente_legal": "test 5I"})
        assert r.status_code == 200, r.text

    vigentes = api.get("/api/v1/parametros", headers=headers).json()
    tenencia, procurador = vigentes["tenencia"]["mensual_defecto"], vigentes["aranceles"]["procurador"]
    fija = vigentes["aranceles"]["adquisicion_fija"]
    try:
        poner("tenencia.mensual_defecto", tenencia + 60)
        poner("aranceles.procurador", procurador + 100)
        d = api.get("/api/v1/opciones", headers=headers).json()["valores_defecto"]
        assert d["tenencia_mensual"] == tenencia + 60
        assert d["adquisicion_fija"] == fija + procurador + 100
    finally:
        # Restaurar el valor que había (no un literal): los módulos comparten base.
        poner("tenencia.mensual_defecto", tenencia)
        poner("aranceles.procurador", procurador)
