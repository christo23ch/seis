"""Fase 2 — Corte duro cuando no existe ancla de valoración (§6.3, M03→M12).

Antes de esta fase, `m03_valoracion.ejecutar` con `n_comparables=0` producía
`VM=VS=VT` (el propio valor de subasta) con `confianza=0.0`, y ese resultado
seguía hacia M12 pudiendo generar una escalera de precios y un semáforo
verde/amarillo/naranja — presentando una cifra sin ancla independiente como si
fuera una valoración de mercado. Ver `docs/PLAN_FASES.md`, Fase 17-C, caso real
de Santiponce.

Estos tests demuestran que, sin comparables, el sistema se niega: semáforo
rojo con razón explícita, y el informe deja de presentar VM/VS como cifras
centrales. Con comparables suficientes, nada cambia — verificado aquí también
con un caso equivalente al de siempre, y por la suite existente
(`test_golden_caso19.py`, `test_precios.py`), que se ejecuta sin modificar.
"""
from __future__ import annotations

from app.engine.pipeline import ejecutar_analisis
from tests.conftest import entrada_base


def _resultado_sin_comparables():
    return ejecutar_analisis(entrada_base(comparables=[]))


def test_sin_comparables_no_es_valorable():
    """M03 sigue marcando confianza 0 y método sin_comparables (sin tocar M03)."""
    r = _resultado_sin_comparables()
    assert r.valoracion.metodo == "sin_comparables"
    assert r.valoracion.n_comparables == 0
    assert r.valoracion.confianza == 0.0


def test_sin_comparables_nunca_verde_amarillo_ni_naranja():
    r = _resultado_sin_comparables()
    assert r.decision.semaforo == "rojo"
    assert r.decision.semaforo not in ("verde", "amarillo", "naranja")


def test_sin_comparables_razon_explicita_en_decision():
    r = _resultado_sin_comparables()
    razones = " ".join(r.decision.razones).lower()
    assert "ancla de mercado" in razones
    assert "comparables" in razones


def test_sin_comparables_el_corte_es_el_unico_motivo():
    """La razón de rechazo es la ÚNICA en decision.razones: prueba que
    decidir_semaforo cortó ANTES de evaluar vetos/ICO/RVC/riesgos — igual que
    el patrón ya existente para vetos —, así que ninguna otra lógica de la
    escalera llegó a tratarse como recomendación."""
    r = _resultado_sin_comparables()
    assert len(r.decision.razones) == 1
    assert "sin ancla de mercado independiente" in r.decision.razones[0].lower()


def test_sin_comparables_informe_dice_no_determinable():
    r = _resultado_sin_comparables()
    inf = r.informe_markdown.lower()
    assert "no determinable: sin comparables de mercado" in inf


def test_sin_comparables_valor_de_subasta_diferenciado_de_la_valoracion():
    """Si el valor de subasta aparece en la sección de valoración, debe quedar
    etiquetado como tal y explícitamente NO como una valoración de mercado."""
    r = _resultado_sin_comparables()
    seccion = r.informe_markdown.split("## 3 · Valoración")[1].split("## 4")[0]
    assert "valor de subasta" in seccion.lower()
    assert "no una valoración de mercado" in seccion.lower()
    # Y las cifras VM/VS/confianza (propias de un método con comparables) no
    # aparecen aquí como si fueran la valoración vigente.
    assert "vm actual" not in seccion.lower()
    assert "vs de salida" not in seccion.lower()


def test_sin_comparables_no_impide_calcular_costes_ni_riesgos():
    """El resto del pipeline (M04–M11, M13) sigue ejecutándose sin tocar —
    solo cambia que el semáforo se niega a recomendar. Confirma que no se
    introdujo un atajo que rompa el DAG."""
    r = _resultado_sin_comparables()
    assert r.riesgos.ra >= 0
    assert r.costes.c_f_p50 >= 0
    assert r.decision.precios.p_objetivo != 0 or r.decision.precios.degenerada


# ───────────────────── Cierre de la deuda: checklist de escalera ─────────────────────
# El checklist es el único sitio del sistema que AFIRMA activamente "la escalera
# está lista para usarse en la puja" (a diferencia de solo mostrar cifras junto
# al semáforo). Dejarlo en "ok" cuando sin_comparables prometía una
# recomendación de puja que no existe.

def _item_escalera(checklist):
    return next(c for c in checklist
                if c.texto == "Escalera de precios cargada en la interfaz de puja")


def test_sin_comparables_checklist_escalera_no_es_ok():
    r = _resultado_sin_comparables()
    item = _item_escalera(r.checklist)
    assert item.estado == "pendiente"
    assert item.bloqueante is True
    assert "no determinable" in (item.detalle or "").lower()
    assert "comparables" in (item.detalle or "").lower()


def test_sin_comparables_checklist_escalera_aparece_entre_los_bloqueantes_pendientes():
    r = _resultado_sin_comparables()
    seccion_bloqueantes = r.informe_markdown.split("## 9 · Checklist")[1]
    assert "Escalera de precios cargada en la interfaz de puja" in seccion_bloqueantes


def test_con_comparables_checklist_escalera_sigue_igual_que_antes(base_input):
    """Regresión: con comparables válidos, el ítem no cambia de estado ni de texto."""
    r = ejecutar_analisis(base_input)
    item = _item_escalera(r.checklist)
    assert item.estado == "ok"
    assert item.detalle is not None
    assert "Objetivo" in item.detalle and "Máx" in item.detalle and "Límite" in item.detalle


def test_con_comparables_suficientes_sigue_igual(base_input):
    """`base_input` (fixture de conftest) trae 7 comparables — el caso de
    siempre. El corte de la Fase 2 no debe activarse ni cambiar nada."""
    r = ejecutar_analisis(base_input)
    assert r.valoracion.metodo == "comparables_ajustados"
    assert r.decision.semaforo != "rojo" or "ancla de mercado" not in " ".join(r.decision.razones).lower()
    inf = r.informe_markdown.lower()
    assert "no determinable: sin comparables de mercado" not in inf
