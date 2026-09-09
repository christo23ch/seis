"""Fase 17-A — Ingesta: dedupe, transaccionalidad por ítem y alcance del matcher.

El alcance según el origen es la decisión del [[ADR-0011]]. Los dos tests que lo
cubren están comprobados por mutación: volver al `organizacion_id=None` ambiguo
de la Fase 12 los pone en rojo, y también los pone en rojo una fuga plausible del
tipo «otras alertas que también casan» en el cuerpo del aviso.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from app.ingesta.contratos import OrigenCaptacion, SubastaCaptada


# ─────────────────────────── Ingesta: dedupe ───────────────────────────

def _captada(identificador: str | None, valor: float = 120000.0) -> SubastaCaptada:
    return SubastaCaptada(fuente_codigo="judicial_boe",
                          identificador_externo=identificador, valor_subasta=valor)


def test_reingerir_el_mismo_lote_no_duplica(api):
    """Una tarea diaria reingiere el listado entero cada noche."""
    from app.core.db import SessionLocal
    from app.services import ingesta_service

    db = SessionLocal()
    try:
        lote = [_captada("DEDUPE-1"), _captada("DEDUPE-2")]
        primera, _ = ingesta_service.procesar_lote(db, lote, OrigenCaptacion.plataforma())
        segunda, _ = ingesta_service.procesar_lote(db, lote, OrigenCaptacion.plataforma())

        assert primera.insertadas == 2 and primera.duplicadas == 0
        assert segunda.insertadas == 0 and segunda.duplicadas == 2

        from app import models
        assert db.query(models.Subasta).filter(
            models.Subasta.identificador_externo == "DEDUPE-1").count() == 1
    finally:
        db.close()


def test_sin_identificador_externo_no_se_dedupea(api):
    """Decisión explícita: dos altas manuales sin identificador son
    indistinguibles de dos subastas distintas, y unirlas por aproximación
    (valor + fecha) uniría subastas legítimamente diferentes."""
    from app.core.db import SessionLocal
    from app.services import ingesta_service

    db = SessionLocal()
    try:
        r1, _ = ingesta_service.procesar_lote(db, [_captada(None, 111000.0)],
                                              OrigenCaptacion.plataforma())
        r2, _ = ingesta_service.procesar_lote(db, [_captada(None, 111000.0)],
                                              OrigenCaptacion.plataforma())
        assert r1.insertadas == 1 and r2.insertadas == 1
    finally:
        db.close()


class _ItemQueRompeAlGuardar(SubastaCaptada):
    """Un ítem que solo revienta al ESCRIBIR, no al construirse.

    Es el caso que de verdad pone a prueba el aislamiento por ítem: el fallo
    ocurre dentro del savepoint, con la fila ya pendiente de flush, de modo que
    deshacerlo mal se llevaría por delante lo insertado antes en el mismo lote.
    Un dato que no pasa validación, en cambio, ni siquiera llega a la sesión.
    """

    def model_dump(self, *args, **kwargs):
        datos = super().model_dump(*args, **kwargs)
        datos["ilegible"] = object()          # PortableJSON no puede escribirlo
        return datos


def test_un_item_invalido_no_tumba_el_lote(api):
    """199 de 200 es un resultado aceptable; 0 de 200 no."""
    from app.core.db import SessionLocal
    from app.services import ingesta_service

    db = SessionLocal()
    try:
        buena_1, buena_2 = _captada("LOTE-OK-1"), _captada("LOTE-OK-2")
        rota = _ItemQueRompeAlGuardar(fuente_codigo="judicial_boe",
                                      identificador_externo="LOTE-ROTA",
                                      valor_subasta=120000.0)

        resumen, nuevas = ingesta_service.procesar_lote(
            db, [buena_1, rota, buena_2], OrigenCaptacion.plataforma())

        assert resumen.insertadas == 2
        assert resumen.fallidas == 1
        assert [s.identificador_externo for s in nuevas] == ["LOTE-OK-1", "LOTE-OK-2"]
        assert resumen.motivos_de_fallo, "un fallo silencioso es peor que uno ruidoso"

        from app import models
        assert db.query(models.Subasta).filter(
            models.Subasta.identificador_externo == "LOTE-ROTA").count() == 0
        # Lo insertado ANTES del ítem roto sigue ahí: el savepoint deshizo solo el suyo.
        assert db.query(models.Subasta).filter(
            models.Subasta.identificador_externo == "LOTE-OK-1").count() == 1
    finally:
        db.close()


def test_dos_ingestas_simultaneas_del_mismo_lote_no_duplican(api):
    """La restricción de unicidad es la garantía dura; la comprobación previa
    solo evita ruido en el caso normal. Bajo carrera manda la base de datos."""
    from app.core.db import SessionLocal
    from app.services import ingesta_service
    from app import models

    lote = [_captada("CARRERA-1"), _captada("CARRERA-2")]

    def ingerir():
        db = SessionLocal()
        try:
            return ingesta_service.procesar_lote(db, lote, OrigenCaptacion.plataforma())[0]
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as ex:
        resumenes = [f.result() for f in [ex.submit(ingerir) for _ in range(2)]]

    db = SessionLocal()
    try:
        for identificador in ("CARRERA-1", "CARRERA-2"):
            assert db.query(models.Subasta).filter(
                models.Subasta.identificador_externo == identificador).count() == 1
    finally:
        db.close()
    assert sum(r.insertadas for r in resumenes) == 2


# ───────────────── Alcance del matcher según el origen (ADR-0011) ─────────────────

def _alerta_amplia(api, headers, nombre):
    return api.post("/api/v1/alertas", headers=headers,
                    json={"nombre": nombre, "criterios": {"fuente": "judicial_boe"}}).json()


def test_la_ingesta_de_plataforma_alcanza_a_todas_las_organizaciones(api, dos_organizaciones):
    """El caso que justifica el ADR-0011: con el alcance anterior, una ingesta
    automática no habría notificado a NADIE, en silencio."""
    from app.core.db import SessionLocal
    from app.services import ingesta_service
    from app import models

    a_h, b_h = dos_organizaciones["a_h"], dos_organizaciones["b_h"]
    alerta_a = _alerta_amplia(api, a_h, "Plataforma alcanza A")
    alerta_b = _alerta_amplia(api, b_h, "Plataforma alcanza B")

    db = SessionLocal()
    try:
        resumen, _ = ingesta_service.procesar_lote(
            db, [_captada("PLATAFORMA-1")], OrigenCaptacion.plataforma())
        assert resumen.notificaciones >= 2

        for alerta_id in (alerta_a["id"], alerta_b["id"]):
            assert db.query(models.Notificacion).filter(
                models.Notificacion.alerta_id == alerta_id).count() == 1
    finally:
        db.close()


def test_el_alta_manual_sigue_sin_salir_de_su_organizacion(api, dos_organizaciones):
    """Regresión de la regla de la Fase 12 (P0.2): ampliar el alcance de la
    ingesta automática NO puede aflojar el del acto manual de un tenant."""
    from app.core.db import SessionLocal
    from app import models

    a_h, b_h = dos_organizaciones["a_h"], dos_organizaciones["b_h"]
    alerta_a = _alerta_amplia(api, a_h, "Manual solo A")
    alerta_b = _alerta_amplia(api, b_h, "Manual no debe llegar a B")

    r = api.post("/api/v1/subastas", headers=a_h,
                 json={"fuente_codigo": "judicial_boe", "identificador_externo": "MANUAL-1",
                       "valor_subasta": 120000})
    assert r.status_code == 201, r.text

    db = SessionLocal()
    try:
        assert db.query(models.Notificacion).filter(
            models.Notificacion.alerta_id == alerta_a["id"]).count() == 1
        assert db.query(models.Notificacion).filter(
            models.Notificacion.alerta_id == alerta_b["id"]).count() == 0
    finally:
        db.close()


def test_una_notificacion_de_plataforma_no_contiene_datos_de_otra_organizacion(
        api, dos_organizaciones):
    """Alcance ampliado NO es datos compartidos.

    Que el matcher alcance a todas las organizaciones significa que cada usuario
    recibe SU aviso sobre un dato compartido —la subasta—, no que el aviso lleve
    nada de otra organización. Este test falla si alguien, al construir el
    cuerpo, mete el nombre de la alerta ajena, el correo del otro usuario o su
    identificador de organización.
    """
    from app.core.db import SessionLocal
    from app.services import ingesta_service
    from app import models

    a_h, b_h = dos_organizaciones["a_h"], dos_organizaciones["b_h"]
    alerta_a = _alerta_amplia(api, a_h, "SECRETO-DE-A")
    alerta_b = _alerta_amplia(api, b_h, "SECRETO-DE-B")

    db = SessionLocal()
    try:
        ingesta_service.procesar_lote(db, [_captada("AISLAMIENTO-1")],
                                      OrigenCaptacion.plataforma())

        usuario_a = db.get(models.Usuario, db.get(models.Alerta, alerta_a["id"]).usuario_id)
        usuario_b = db.get(models.Usuario, db.get(models.Alerta, alerta_b["id"]).usuario_id)

        n_a = db.query(models.Notificacion).filter(
            models.Notificacion.alerta_id == alerta_a["id"]).one()
        n_b = db.query(models.Notificacion).filter(
            models.Notificacion.alerta_id == alerta_b["id"]).one()

        # Cada uno recibe el suyo, con SU nombre de alerta y nada del otro.
        for notificacion, propio, ajeno, usuario_ajeno in (
                (n_a, "SECRETO-DE-A", "SECRETO-DE-B", usuario_b),
                (n_b, "SECRETO-DE-B", "SECRETO-DE-A", usuario_a)):
            texto = f"{notificacion.asunto}\n{notificacion.cuerpo}"
            assert propio in texto
            assert ajeno not in texto, "se ha filtrado el nombre de una alerta ajena"
            assert usuario_ajeno.email not in texto, "se ha filtrado un correo ajeno"
            assert (usuario_ajeno.organizacion_id or "@@") not in texto, \
                "se ha filtrado el identificador de otra organización"
    finally:
        db.close()
