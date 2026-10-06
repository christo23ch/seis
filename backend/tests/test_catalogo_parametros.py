"""Fase 5C — catálogo técnico de metadatos de parámetros T3 (M12/M13).

Estos tests son puro Python: no tocan BD, no usan `api`/`headers` (no hay
HTTP ni persistencia en el alcance de esta fase). Verifican el catálogo en
sí mismo, no el motor (M12/M13 no se modifican aquí — ver `catalogo.py`).
"""
from __future__ import annotations

from app.engine.params.store import cargar_defaults
from app.parametros import catalogo


# ─────────────────────────── 1. Carga básica ───────────────────────────

def test_catalogo_carga_correctamente():
    entradas = catalogo.obtener_catalogo()
    assert len(entradas) > 0
    assert all(isinstance(p, catalogo.ParametroCatalogo) for p in entradas)


# ─────────────────────── 2. Claves T1 esperadas ────────────────────────

def test_todas_las_claves_t1_esperadas_representadas():
    claves = {p.clave for p in catalogo.obtener_catalogo()}
    fijas_esperadas = [
        "riesgos.pesos.juridico", "riesgos.pesos.mercado",
        "riesgos.dominancia.una_alta", "riesgos.dominancia.critica_no_mitigable",
        "riesgos.bandas_ra",
        "valoracion.delta_base_pp", "valoracion.delta_dispersion", "valoracion.delta_max_pct",
        "precios.m_exc_mult",
        "financiacion.stress_tipos_pp", "financiacion.dscr_minimo",
        "capital.coste_capital_anual",
        "ico.pesos.rentabilidad", "ico.pesos.informacion",
        "ico.escalon_alta", "ico.bonus_equity_financiero",
        "ico.liquidez_dom.full", "ico.liquidez_dom.zero",
        "ico.utilidad_rentabilidad.cero_en_frac_min", "ico.utilidad_rentabilidad.u_objetivo",
        "ico.utilidad_rentabilidad.u_max_frac",
        "ici.multiplicador_ico_umbral",
        "semaforo.verde.ico_min", "semaforo.verde.ms_valor_min",
        "semaforo.verde.rvc_min", "semaforo.verde.ici_min",
        "semaforo.amarillo.pes_piso_frac_i", "semaforo.naranja.rvc_min",
        "adjudicacion.ajuste_desierta_pp", "adjudicacion.ajuste_chollo_pp",
        "adjudicacion.rvc_bandas",
        # Fase 5C.1 — las 3 claves físicas de perfiles.rentista detectadas
        # por la auditoría PRE-5D (no existen en ningún otro perfil hoy).
        "perfiles.rentista.coc_min", "perfiles.rentista.y_suelo_pp_sobre_bono",
        "perfiles.rentista.y_bono_10a",
    ]
    faltantes = [c for c in fijas_esperadas if c not in claves]
    assert not faltantes, f"Claves T1 fijas ausentes del catálogo: {faltantes}"

    patrones_esperados = {
        "perfiles.{perfil}.m_objetivo", "perfiles.{perfil}.m_minimo",
        # Fase 5C.1 — a diferencia de m_objetivo/m_minimo, existen en los 6 perfiles.
        "perfiles.{perfil}.piso_pesimista_frac_i", "perfiles.{perfil}.rvc_veto",
        "primas_ra.{banda}.mult_m", "primas_ra.{banda}.stress_mercado",
        "primas_ra.{banda}.y_req_pp", "primas_ra.{banda}.delta_mercado_pp",
        "adjudicacion.ratios.{fuente}",
    }
    patrones_reales = {p.patron_clave for p in catalogo.obtener_plantillas()}
    assert patrones_esperados == patrones_reales


# ───────────────────────── 3. Sin duplicados ─────────────────────────

def test_no_hay_claves_duplicadas():
    claves = [p.clave for p in catalogo.obtener_catalogo()]
    assert len(claves) == len(set(claves)), "Hay claves repetidas en el catálogo"

    patrones = [p.patron_clave for p in catalogo.obtener_plantillas()]
    assert len(patrones) == len(set(patrones)), "Hay patrones de plantilla repetidos"


# ─────────────────── 4. Hardcodes no editables (TIPO 2) ───────────────────

def test_hardcodes_marcados_no_editables():
    assert len(catalogo.CONSTANTES_HARDCODE) == 12
    for p in catalogo.CONSTANTES_HARDCODE:
        assert p.editable is False, f"{p.clave} es TIPO 2 y debe ser editable=False"
        assert p.rango is None
        assert p.dependencia is None
        assert p.clave.startswith("hardcode.")


def test_hardcodes_no_aparecen_en_editables():
    editables = {p.clave for p in catalogo.obtener_parametros_editables()}
    for p in catalogo.CONSTANTES_HARDCODE:
        assert p.clave not in editables


# ─────────────────── 5. Datos de entrada (TIPO 4) excluidos ───────────────────

def test_datos_entrada_no_aparecen_como_editables():
    # Nota: "ocupacion" SÍ existe legítimamente como dimensión de riesgo T1
    # (`riesgos.pesos.ocupacion`, un peso, no un dato de entrada). El dato de
    # entrada real es `inp.ocupacion.estado`/`inp.ocupacion.documentacion`
    # (M13 los lee, pero no son parámetros del modelo) — se comprueba por
    # ruta completa, no por substring, para no colisionar con el peso T1.
    claves_editables = {p.clave for p in catalogo.obtener_parametros_editables()}
    assert not any(c.startswith("ocupacion.") for c in claves_editables)

    prohibidas = [
        "valor_subasta", "puja_minima", "deposito_pct",
        "comparables", "cargas", "documentacion",
        "superficie_m2", "estado_conservacion", "renta_mensual_estimada",
    ]
    for termino in prohibidas:
        coincidencias = [c for c in claves_editables if termino in c]
        assert not coincidencias, f"'{termino}' (dato de entrada) aparece como editable: {coincidencias}"


# ─────── 6. Valor de referencia coincide con defaults.yaml vigente ────────

def test_valor_referencia_coincide_con_defaults_para_claves_fijas():
    params = cargar_defaults()
    for p in catalogo.PARAMETROS_FIJOS:
        esperado = params.get(p.clave)
        obtenido = catalogo.resolver_valor_referencia(p.clave, params)
        assert obtenido == esperado, f"{p.clave}: catálogo/defaults.yaml divergen"


def test_resolver_valor_referencia_usa_defaults_por_defecto():
    valor_explicito = catalogo.resolver_valor_referencia(
        "capital.coste_capital_anual", cargar_defaults())
    valor_por_defecto = catalogo.resolver_valor_referencia("capital.coste_capital_anual")
    assert valor_explicito == valor_por_defecto


# ─────────────── 7. Plantillas resuelven correctamente ───────────────

def test_plantillas_resuelven_correctamente_por_dimension():
    params = cargar_defaults()
    resueltos = catalogo.resolver_plantillas(params)
    bandas_reales = set(params.seccion("primas_ra").keys())

    mult_m = {r.clave: r.valor_referencia for r in resueltos
              if r.plantilla.patron_clave == "primas_ra.{banda}.mult_m"}
    assert set(mult_m.keys()) == {f"primas_ra.{b}.mult_m" for b in bandas_reales}
    for banda in bandas_reales:
        assert mult_m[f"primas_ra.{banda}.mult_m"] == params.get(f"primas_ra.{banda}.mult_m")

    fuentes_reales = set(params.seccion("adjudicacion.ratios").keys())
    ratios = {r.clave: r.valor_referencia for r in resueltos
              if r.plantilla.patron_clave == "adjudicacion.ratios.{fuente}"}
    assert set(ratios.keys()) == {f"adjudicacion.ratios.{f}" for f in fuentes_reales}
    assert ratios["adjudicacion.ratios.judicial_boe"] == params.seccion("adjudicacion.ratios")["judicial_boe"]


def test_perfil_rentista_no_genera_instancia_m_objetivo():
    resueltos = catalogo.resolver_plantillas(cargar_defaults())
    claves_m_objetivo = {r.clave for r in resueltos
                         if r.plantilla.patron_clave == "perfiles.{perfil}.m_objetivo"}
    assert "perfiles.rentista.m_objetivo" not in claves_m_objetivo
    assert "perfiles.flip_ligero.m_objetivo" in claves_m_objetivo

    claves_m_minimo = {r.clave for r in resueltos
                       if r.plantilla.patron_clave == "perfiles.{perfil}.m_minimo"}
    assert "perfiles.rentista.m_minimo" not in claves_m_minimo


# ──── 7bis. Fase 5C.1 — las 5 claves T3 de M12/M13 cerradas tras la auditoría ────

def test_piso_pesimista_y_rvc_veto_resuelven_en_los_6_perfiles():
    # A diferencia de m_objetivo/m_minimo (solo 5 perfiles de venta), estas
    # dos SÍ existen en 'rentista' — la auditoría PRE-5D lo señaló como el
    # matiz a no pasar por alto al extender el catálogo.
    params = cargar_defaults()
    perfiles_reales = set(params.seccion("perfiles").keys())
    assert perfiles_reales == {"flip_ligero", "flip_integral", "cambio_uso",
                               "division_horizontal", "oportunista", "rentista"}

    resueltos = catalogo.resolver_plantillas(params)
    for patron in ("perfiles.{perfil}.piso_pesimista_frac_i", "perfiles.{perfil}.rvc_veto"):
        instancias = {r.clave: r.valor_referencia for r in resueltos
                     if r.plantilla.patron_clave == patron}
        assert set(instancias.keys()) == {f"perfiles.{p}.{patron.split('.')[-1]}" for p in perfiles_reales}
        for perfil in perfiles_reales:
            clave = f"perfiles.{perfil}.{patron.split('.')[-1]}"
            assert instancias[clave] == params.get(clave)


def test_claves_rentista_fijas_resuelven_contra_el_motor():
    params = cargar_defaults()
    for clave, esperado in (
        ("perfiles.rentista.coc_min", 0.07),
        ("perfiles.rentista.y_suelo_pp_sobre_bono", 2.5),
        ("perfiles.rentista.y_bono_10a", 3.2),
    ):
        assert params.get(clave) == esperado, f"{clave}: valor inesperado en defaults.yaml"
        assert catalogo.resolver_valor_referencia(clave, params) == esperado
        entrada = catalogo.obtener_parametro(clave)
        assert entrada is not None and entrada.editable is True


def test_rvc_veto_distingue_parametro_de_regla():
    plantilla_rvc_veto = next(p for p in catalogo.PLANTILLAS
                              if p.patron_clave == "perfiles.{perfil}.rvc_veto")
    assert plantilla_rvc_veto.dependencia == "A"
    # La descripción debe citar la regla T2 que lo consume sin que el
    # catálogo la trate como si fuera él mismo la regla.
    assert "VETO-COMP-01" in plantilla_rvc_veto.descripcion
    assert plantilla_rvc_veto.patron_clave != "VETO-COMP-01"


# ────────── 8. Un rango pendiente nunca se lee como rango válido ──────────

def test_parametro_pendiente_no_se_interpreta_como_rango_valido():
    pendientes = [p for p in catalogo.obtener_catalogo() if p.rango == catalogo.PENDIENTE_DE_DEFINIR]
    assert pendientes, "Se esperaba al menos un parámetro con rango pendiente de definir"
    for p in pendientes:
        assert not isinstance(p.rango, tuple)
        assert p.rango == "pendiente_de_definir"

    con_rango_concreto = [p for p in catalogo.obtener_catalogo() if isinstance(p.rango, tuple)]
    for p in con_rango_concreto:
        assert p.rango != catalogo.PENDIENTE_DE_DEFINIR
        lo, hi = p.rango
        assert lo < hi


# ──────── 9. El catálogo no modifica Parametros ni defaults.yaml ────────

def test_catalogo_no_modifica_parametros_ni_defaults():
    antes = cargar_defaults().raw()
    catalogo.obtener_catalogo()
    catalogo.obtener_parametros_editables()
    catalogo.resolver_plantillas()
    for p in catalogo.PARAMETROS_FIJOS[:5]:
        catalogo.resolver_valor_referencia(p.clave)
    despues = cargar_defaults().raw()
    assert antes == despues


# ───────────────────── API adicional / sanidad ─────────────────────

def test_obtener_parametro_por_clave():
    encontrado = catalogo.obtener_parametro("capital.coste_capital_anual")
    assert encontrado is not None
    assert encontrado.clave == "capital.coste_capital_anual"
    assert catalogo.obtener_parametro("clave.que.no.existe") is None


def test_dependencia_poblada_en_editables_y_ausente_en_hardcode():
    for p in catalogo.obtener_parametros_editables():
        assert p.dependencia in ("A", "B")
    for p in catalogo.CONSTANTES_HARDCODE:
        assert p.dependencia is None


def test_calculos_derivados_tipo3_no_editables_ni_en_catalogo():
    claves_catalogo = {p.clave for p in catalogo.obtener_catalogo()}
    derivados = catalogo.obtener_calculos_derivados()
    assert len(derivados) > 0
    nombres_derivados = {d.nombre for d in derivados}
    assert not (nombres_derivados & claves_catalogo)
