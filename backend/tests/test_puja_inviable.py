"""M13 no puede reventar en las operaciones que debe rechazar.

Encontrado con un caso REAL de la Agencia Tributaria —vivienda de 44 m² de 1940
en Santiponce, tasada en 23.391,72 €, sin comparables de mercado— al recorrer el
flujo de punta a punta. Una fixture sintética no lo habría dado: el caso dorado
§19 pasa porque es una operación BUENA, y este fallo solo aparece cuando la
operación es tan mala que la puja máxima sensata sale por debajo de cero.

Lo que hacía el fallo especialmente caro: **el motor ya estaba decidiendo bien.**
M12 marca `escalera.degenerada` y fuerza semáforo rojo con «la estructura de
costes consume el valor (§9.3)». Era M13, que corre después para armar el plan de
puja, quien lanzaba `StopIteration` al no encontrar banda para un `rvc` negativo.
El motor sabía decir que no y se caía al decirlo — y el endpoint devolvía un 500.

QUÉ CUBRE (ADR-0014): que el pipeline TERMINE y clasifique como `inviable` una
escalera con `p_max` no positivo, en los tres estados de conservación.

QUÉ NO CUBRE:

- No comprueba que el resto del pipeline sea numéricamente correcto con valores
  negativos; solo que no aborta y que el veredicto es rojo.
- No vigila la calibración de las bandas intermedias (`alcanzable`, `ajustado`,
  `improbable`).
- **No vigila que `rvc_bandas` conserve su banda suelo.** Si alguien borrara
  `{min: 0.0, banda: inviable}` de `defaults.yaml`, el valor por defecto de M13
  seguiría salvando la ejecución y este test seguiría en verde. Lo que se prueba
  es que M13 no lanza, no que la tabla esté completa.
"""
from __future__ import annotations

import pytest

from app.engine.contracts import AnalisisInput
from app.engine.pipeline import ejecutar_analisis


def _caso_inviable(estado: str = "regular") -> AnalisisInput:
    """Lo esencial del caso real: tasación baja y sin comparables.

    Sin comparables, M03 devuelve VM = valor de subasta con confianza 0, el ICI
    se hunde y la contingencia que eso impone se come el valor. La puja máxima
    sale negativa: el negocio no se sostiene ni pujando cero.
    """
    return AnalisisInput(**{
        "perfil": "flip_integral",
        "activo": {"tipologia": "vivienda", "superficie_m2": 44.0,
                   "estado_conservacion": estado, "anio_construccion": 1940,
                   "municipio": "Santiponce", "provincia": "Sevilla",
                   "ccaa": "andalucia"},
        "subasta": {"fuente": "aeat", "valor_subasta": 23391.72,
                    "puja_minima": 2339.17, "tramo": 500.0, "deposito_pct": 0.05},
        "comparables": [],
        "ocupacion": {"estado": "desconocida"},
    })


@pytest.mark.parametrize("estado", ["malo", "regular", "bueno"])
def test_una_operacion_sin_puja_positiva_se_clasifica_inviable(estado):
    """Antes lanzaba `StopIteration` y el endpoint devolvía 500."""
    resultado = ejecutar_analisis(_caso_inviable(estado))

    assert resultado.decision.precios.p_max <= 0, (
        "premisa del test: este caso debe producir una puja máxima no positiva. "
        "Si deja de hacerlo, ya no está probando lo que dice.")
    assert resultado.puja.banda_rvc == "inviable"
    assert resultado.decision.semaforo == "rojo"


def test_el_motor_entrega_informe_aunque_la_escalera_sea_negativa():
    """La aserción mínima, sin depender de la clasificación: que TERMINE y
    produzca el entregable. Un análisis que no llega al informe no sirve de nada
    a quien tiene que decidir si puja."""
    resultado = ejecutar_analisis(_caso_inviable())

    assert resultado.decision.precios.degenerada is True
    assert resultado.informe_markdown, "sin informe no hay entregable"
    assert resultado.checklist


def test_una_operacion_buena_no_se_vuelve_inviable():
    """Regresión: el valor por defecto no puede convertirlo todo en «inviable».

    Se construye una operación sana —con comparables y documentación— para que
    si el arreglo hubiera tocado la clasificación normal, se viera aquí.
    """
    inp = AnalisisInput(**{
        "perfil": "flip_integral",
        "activo": {"tipologia": "vivienda", "superficie_m2": 82.0,
                   "estado_conservacion": "regular", "anio_construccion": 1985,
                   "ccaa": "madrid"},
        "subasta": {"fuente": "judicial_boe", "valor_subasta": 120000.0,
                    "deposito_pct": 0.05, "horas_hasta_cierre": 200},
        "comparables": [{"precio_m2": v, "estado": "reformado", "origen": "testigo"}
                        for v in (2600, 2700, 2750, 2800, 2850)],
        "ocupacion": {"estado": "vacio"},
        "documentos": {"nota_simple": True, "cert_cargas": True,
                       "posesion_verificada": True, "avaluo": True,
                       "fotos_interior_o_visita": True, "fotos_exterior": True,
                       "cert_comunidad": True, "recibo_ibi": True,
                       "ite_cee": True, "catastro_conciliado": True},
    })
    resultado = ejecutar_analisis(inp)

    assert resultado.decision.precios.p_max > 0
    assert resultado.decision.precios.degenerada is False
    assert resultado.puja.banda_rvc != "inviable"
