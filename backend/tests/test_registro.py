"""Alta self-service (Fase 10): registro, verificación, recuperación y anti-abuso.

Los dos criterios que estos tests vigilan por encima de todo:

* **La API no revela si una dirección tiene cuenta.** `/registro` y `/recuperar`
  responden exactamente lo mismo exista o no el email; quien se entera del
  intento es el titular, por correo.
* **Los tokens son de un solo uso de verdad.** Antes de esta fase el `jti` se
  emitía pero nadie lo comprobaba: un enlace servía tantas veces como cupiera en
  su TTL.

El canal de email no está configurado en tests, así que `NotificadorEmail` cae en
su rama honesta y deja el mensaje en `notificadores.email.ultimo_email`. Es de
ahí de donde estos tests sacan los enlaces, igual que hace `test_notificaciones`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app import models
from app.core.security import crear_token_proposito

API = "/api/v1/auth"


# ─────────────── utilidades ───────────────

def _buffer():
    from app.notificadores import email as email_mod
    return email_mod.ultimo_email or {}


def _vaciar_buffer() -> None:
    from app.notificadores import email as email_mod
    email_mod.ultimo_email = None


def _enlace(fragmento: str) -> str:
    """Extrae del último correo la primera URL que contenga `fragmento`."""
    cuerpo = _buffer().get("cuerpo") or ""
    for palabra in cuerpo.split():
        if fragmento in palabra:
            return palabra
    raise AssertionError(f"No hay ningún enlace con «{fragmento}» en: {cuerpo!r}")


def _token(fragmento: str) -> str:
    return _enlace(fragmento).split("token=", 1)[1]


def _registrar(api, email: str, password: str = "unaClaveLarga1",
               nombre: str | None = None):
    _vaciar_buffer()
    return api.post(f"{API}/registro",
                    json={"email": email, "password": password, "nombre": nombre})


def _alta_verificada(api, email: str, password: str = "unaClaveLarga1"):
    """Registra y verifica una cuenta; la deja lista para iniciar sesión."""
    assert _registrar(api, email, password).status_code == 201
    token = _token("verificar?token=")
    assert api.post(f"{API}/verificar", json={"token": token}).status_code == 200
    return token


def _clave_login(email: str) -> str:
    """Clave real del limitador de login: email + origen. `TestClient` siempre
    se presenta como `testclient`."""
    return f"login:{email}:testclient"


def _sesion(db_api, email: str, password: str) -> dict:
    r = db_api.post(f"{API}/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ─────────────── registro ───────────────

def test_registro_crea_cuenta_inactiva_y_envia_verificacion(api):
    r = _registrar(api, "registro.feliz@ejemplo.com", nombre="Ana")

    assert r.status_code == 201, r.text
    assert r.json()["ok"] is True
    assert "verificar?token=" in (_buffer().get("cuerpo") or "")
    assert _buffer()["para"] == "registro.feliz@ejemplo.com"


def test_el_correo_transaccional_no_lleva_enlace_de_baja(api):
    """Nadie debe poder darse de baja del correo que activa su propia cuenta."""
    _registrar(api, "sin.baja@ejemplo.com")

    assert _buffer()["enlace_baja"] is None


def test_quien_se_registra_es_propietario_de_una_organizacion_nueva(api):
    from app.core.db import SessionLocal
    from app.services import usuario_service

    _registrar(api, "propietaria@ejemplo.com")

    db = SessionLocal()
    try:
        u = usuario_service.obtener_por_email(db, "propietaria@ejemplo.com")
        admin = usuario_service.obtener_por_email(db, "admin@seis.local")
        assert u.activo is False
        assert u.email_verificado is False
        assert u.rol == "admin" and u.rol_org == "propietario"
        assert u.es_superadmin is False
        assert u.organizacion_id != admin.organizacion_id
    finally:
        db.close()


def test_registro_con_email_existente_responde_igual_que_un_alta_nueva(api):
    """D5: la respuesta HTTP no distingue los dos casos; el aviso va al titular."""
    from app.core.db import SessionLocal

    nueva = _registrar(api, "duplicada@ejemplo.com", nombre="Titular")
    repetida = _registrar(api, "duplicada@ejemplo.com", password="otraClaveLarga2",
                          nombre="Impostor")

    assert repetida.status_code == nueva.status_code == 201
    assert repetida.json() == nueva.json()
    assert "intentado registrarse" in _buffer()["cuerpo"]
    assert _buffer()["para"] == "duplicada@ejemplo.com"

    db = SessionLocal()
    try:
        assert db.query(models.Usuario).filter_by(
            email="duplicada@ejemplo.com").count() == 1
    finally:
        db.close()


def test_el_registro_repetido_no_toca_la_cuenta_existente(api):
    from app.core.db import SessionLocal
    from app.services import usuario_service

    _alta_verificada(api, "intacta@ejemplo.com", "claveOriginal11")
    _registrar(api, "intacta@ejemplo.com", password="claveDelImpostor9")

    db = SessionLocal()
    try:
        u = usuario_service.obtener_por_email(db, "intacta@ejemplo.com")
        assert usuario_service.autenticar(db, "intacta@ejemplo.com",
                                          "claveOriginal11") is not None
        assert usuario_service.autenticar(db, "intacta@ejemplo.com",
                                          "claveDelImpostor9") is None
        assert u.rol_org == "propietario"
    finally:
        db.close()


@pytest.mark.parametrize("password", ["", "corta", "1234567"])
def test_el_registro_exige_ocho_caracteres_de_contrasena(api, password):
    r = api.post(f"{API}/registro", json={"email": "corta@ejemplo.com",
                                          "password": password})

    assert r.status_code == 422, r.text


def test_el_registro_no_permite_elegir_rol_ni_superadmin(api):
    """`RegistroBody` ignora los campos de privilegio de `UsuarioCrear`."""
    from app.core.db import SessionLocal
    from app.services import usuario_service

    r = api.post(f"{API}/registro", json={
        "email": "escalada@ejemplo.com", "password": "unaClaveLarga1",
        "rol": "admin", "rol_org": "propietario", "es_superadmin": True})

    assert r.status_code == 201, r.text
    db = SessionLocal()
    try:
        assert usuario_service.obtener_por_email(
            db, "escalada@ejemplo.com").es_superadmin is False
    finally:
        db.close()


# ─────────────── verificación ───────────────

def test_sin_verificar_el_login_devuelve_403_y_no_401(api):
    """D6: mentirle a quien acertó su contraseña genera soporte, no seguridad."""
    _registrar(api, "sin.verificar@ejemplo.com", "unaClaveLarga1")

    r = api.post(f"{API}/login", data={"username": "sin.verificar@ejemplo.com",
                                       "password": "unaClaveLarga1"})

    assert r.status_code == 403, r.text
    assert "verificada" in r.json()["detail"].lower()


def test_verificar_activa_la_cuenta_y_habilita_el_login(api):
    _registrar(api, "verificable@ejemplo.com", "unaClaveLarga1")
    token = _token("verificar?token=")

    r = api.post(f"{API}/verificar", json={"token": token})

    assert r.status_code == 200, r.text
    assert api.post(f"{API}/login", data={"username": "verificable@ejemplo.com",
                                          "password": "unaClaveLarga1"}).status_code == 200


def test_el_enlace_de_verificacion_no_se_puede_reutilizar(api):
    """El `jti` queda gastado en `token_consumido` tras el primer uso."""
    token = _alta_verificada(api, "un.solo.uso@ejemplo.com")

    r = api.post(f"{API}/verificar", json={"token": token})

    assert r.status_code == 400, r.text


def test_el_jti_gastado_queda_registrado(api):
    from app.core.db import SessionLocal

    token = _alta_verificada(api, "rastro.jti@ejemplo.com")
    jti = jwt.decode(token, options={"verify_signature": False})["jti"]

    db = SessionLocal()
    try:
        fila = db.get(models.TokenConsumido, jti)
        assert fila is not None and fila.proposito == "verificar"
    finally:
        db.close()


def test_reenviar_verificacion_permite_salir_de_un_enlace_caducado(api):
    _registrar(api, "reenvio@ejemplo.com")
    _vaciar_buffer()

    r = api.post(f"{API}/reenviar-verificacion", json={"email": "reenvio@ejemplo.com"})

    assert r.status_code == 200, r.text
    token = _token("verificar?token=")
    assert api.post(f"{API}/verificar", json={"token": token}).status_code == 200


def test_reenviar_verificacion_no_delata_direcciones(api):
    _vaciar_buffer()
    existente = api.post(f"{API}/reenviar-verificacion",
                         json={"email": "admin@seis.local"})
    inexistente = api.post(f"{API}/reenviar-verificacion",
                           json={"email": "nadie.de.nada@ejemplo.com"})

    assert existente.status_code == inexistente.status_code == 200
    assert existente.json() == inexistente.json()


def test_reenviar_verificacion_no_reenvia_a_una_cuenta_ya_verificada(api):
    """La respuesta es la misma, así que sin mirar el buzón nadie detectaría que
    se quitó la guarda y se empezó a reenviar a cuentas ya activas."""
    _vaciar_buffer()

    api.post(f"{API}/reenviar-verificacion", json={"email": "admin@seis.local"})

    assert _buffer() == {}


# ─────────────── tokens inválidos ───────────────

def test_un_token_de_otro_proposito_no_sirve(api):
    """Un enlace de verificación no puede cambiar una contraseña."""
    cruzado = crear_token_proposito("admin@seis.local", "verificar", horas=1)

    r = api.post(f"{API}/resetear", json={"token": cruzado,
                                          "nueva": "unaClaveLarga1"})

    assert r.status_code == 400, r.text


def test_un_token_caducado_no_sirve(api):
    from app.core.config import get_settings

    ahora = datetime.now(timezone.utc)
    caducado = jwt.encode(
        {"sub": "admin@seis.local", "proposito": "verificar", "jti": "caducado",
         "iat": ahora - timedelta(hours=48), "exp": ahora - timedelta(hours=1)},
        get_settings().jwt_secret, algorithm="HS256")

    r = api.post(f"{API}/verificar", json={"token": caducado})

    assert r.status_code == 400, r.text


def test_un_token_firmado_con_otra_clave_no_sirve(api):
    ahora = datetime.now(timezone.utc)
    ajeno = jwt.encode(
        {"sub": "admin@seis.local", "proposito": "verificar", "jti": "ajeno",
         "iat": ahora, "exp": ahora + timedelta(hours=1)},
        "una-clave-que-no-es-la-del-sistema", algorithm="HS256")

    r = api.post(f"{API}/verificar", json={"token": ajeno})

    assert r.status_code == 400, r.text


@pytest.mark.parametrize("ruta", ["verificar", "resetear"])
def test_un_token_basura_no_sirve(api, ruta):
    cuerpo = {"token": "esto-no-es-un-token"}
    if ruta == "resetear":
        cuerpo["nueva"] = "unaClaveLarga1"

    assert api.post(f"{API}/{ruta}", json=cuerpo).status_code == 400


def test_todos_los_fallos_de_token_dicen_lo_mismo(api):
    """Distinguir «caducado» de «ya usado» filtraría si el enlace existió."""
    gastado = _alta_verificada(api, "mismo.mensaje@ejemplo.com")
    basura = api.post(f"{API}/verificar", json={"token": "xxx"})
    reutilizado = api.post(f"{API}/verificar", json={"token": gastado})

    assert basura.json()["detail"] == reutilizado.json()["detail"]


# ─────────────── recuperación y reseteo ───────────────

def test_recuperar_responde_igual_exista_o_no_la_cuenta(api):
    _alta_verificada(api, "recuperable@ejemplo.com")

    existe = api.post(f"{API}/recuperar", json={"email": "recuperable@ejemplo.com"})
    no_existe = api.post(f"{API}/recuperar", json={"email": "fantasma@ejemplo.com"})

    assert existe.status_code == no_existe.status_code == 200
    assert existe.json() == no_existe.json()


def test_recuperar_no_envia_correo_a_una_direccion_desconocida(api):
    _vaciar_buffer()

    api.post(f"{API}/recuperar", json={"email": "fantasma2@ejemplo.com"})

    assert _buffer().get("para") != "fantasma2@ejemplo.com"


def test_resetear_cambia_la_contrasena_e_invalida_la_anterior(api):
    _alta_verificada(api, "reseteable@ejemplo.com", "claveOriginal11")
    _vaciar_buffer()
    api.post(f"{API}/recuperar", json={"email": "reseteable@ejemplo.com"})
    token = _token("resetear?token=")

    r = api.post(f"{API}/resetear", json={"token": token, "nueva": "claveNueva222"})

    assert r.status_code == 200, r.text
    assert api.post(f"{API}/login", data={"username": "reseteable@ejemplo.com",
                                          "password": "claveNueva222"}).status_code == 200
    assert api.post(f"{API}/login", data={"username": "reseteable@ejemplo.com",
                                          "password": "claveOriginal11"}).status_code == 401


def test_el_enlace_de_reseteo_no_se_puede_reutilizar(api):
    _alta_verificada(api, "reseteo.unico@ejemplo.com", "claveOriginal11")
    _vaciar_buffer()
    api.post(f"{API}/recuperar", json={"email": "reseteo.unico@ejemplo.com"})
    token = _token("resetear?token=")
    assert api.post(f"{API}/resetear",
                    json={"token": token, "nueva": "claveNueva222"}).status_code == 200

    r = api.post(f"{API}/resetear", json={"token": token, "nueva": "otraMas3333"})

    assert r.status_code == 400, r.text


def test_resetear_exige_ocho_caracteres(api):
    _alta_verificada(api, "reseteo.corto@ejemplo.com")
    _vaciar_buffer()
    api.post(f"{API}/recuperar", json={"email": "reseteo.corto@ejemplo.com"})
    token = _token("resetear?token=")

    assert api.post(f"{API}/resetear",
                    json={"token": token, "nueva": "1234567"}).status_code == 422


def test_resetear_desbloquea_el_login(api):
    """Quien demuestra que controla el buzón no debe seguir bloqueado."""
    _alta_verificada(api, "bloqueada@ejemplo.com", "claveOriginal11")
    for _ in range(6):
        api.post(f"{API}/login", data={"username": "bloqueada@ejemplo.com",
                                       "password": "mal"})
    _vaciar_buffer()
    api.post(f"{API}/recuperar", json={"email": "bloqueada@ejemplo.com"})
    token = _token("resetear?token=")

    api.post(f"{API}/resetear", json={"token": token, "nueva": "claveNueva222"})

    assert api.post(f"{API}/login", data={"username": "bloqueada@ejemplo.com",
                                          "password": "claveNueva222"}).status_code == 200


# ─────────────── anti fuerza bruta ───────────────

def test_el_sexto_intento_fallido_devuelve_429(api):
    _alta_verificada(api, "fuerza.bruta@ejemplo.com", "claveOriginal11")

    codigos = [api.post(f"{API}/login",
                        data={"username": "fuerza.bruta@ejemplo.com",
                              "password": "mal"}).status_code for _ in range(5)]
    sexto = api.post(f"{API}/login", data={"username": "fuerza.bruta@ejemplo.com",
                                           "password": "mal"})

    assert codigos == [401] * 5
    assert sexto.status_code == 429, sexto.text


def test_el_bloqueo_ignora_que_la_contrasena_sea_correcta(api):
    _alta_verificada(api, "bloqueo.total@ejemplo.com", "claveOriginal11")
    for _ in range(5):
        api.post(f"{API}/login", data={"username": "bloqueo.total@ejemplo.com",
                                       "password": "mal"})

    r = api.post(f"{API}/login", data={"username": "bloqueo.total@ejemplo.com",
                                       "password": "claveOriginal11"})

    assert r.status_code == 429, r.text


def test_un_acceso_correcto_limpia_el_contador(api):
    from app.core import rate_limit

    _alta_verificada(api, "contador@ejemplo.com", "claveOriginal11")
    for _ in range(4):
        api.post(f"{API}/login", data={"username": "contador@ejemplo.com",
                                       "password": "mal"})

    assert rate_limit.bloqueado(_clave_login("contador@ejemplo.com")) is False  # aún no
    assert api.post(f"{API}/login", data={"username": "contador@ejemplo.com",
                                          "password": "claveOriginal11"}).status_code == 200
    # El acceso correcto tiene que haber borrado los 4 fallos acumulados, no solo
    # dejarlos por debajo del umbral.
    from app.core.rate_limit import _memoria
    assert _clave_login("contador@ejemplo.com") not in _memoria


def test_el_bloqueo_del_login_es_por_email_y_origen(api):
    """Con la clave solo por email, cualquiera dejaba fuera a un tercero a base
    de contraseñas erróneas. Al componerla con el origen, el atacante solo se
    bloquea a sí mismo. (TestClient viaja siempre desde el mismo origen, así que
    aquí se comprueba la forma de la clave, no el aislamiento entre orígenes:
    eso solo es observable con IPs reales, que hoy Docker no conserva.)"""
    from app.core import rate_limit

    _alta_verificada(api, "clave.compuesta@ejemplo.com", "claveOriginal11")
    for _ in range(5):
        api.post(f"{API}/login", data={"username": "clave.compuesta@ejemplo.com",
                                       "password": "mal"})

    assert rate_limit.bloqueado("login:clave.compuesta@ejemplo.com") is False
    assert rate_limit.bloqueado(_clave_login("clave.compuesta@ejemplo.com")) is True


def test_el_bloqueo_de_un_email_no_afecta_a_otro(api):
    _alta_verificada(api, "victima@ejemplo.com", "claveOriginal11")
    for _ in range(6):
        api.post(f"{API}/login", data={"username": "atacada@ejemplo.com",
                                       "password": "mal"})

    r = api.post(f"{API}/login", data={"username": "victima@ejemplo.com",
                                       "password": "claveOriginal11"})

    assert r.status_code == 200, r.text


def test_la_ventana_del_bloqueo_se_cierra_con_el_tiempo(api, monkeypatch):
    """Se envejece el reloj del limitador en vez de dormir de verdad."""
    from app.core import rate_limit
    from app.core.config import get_settings

    _alta_verificada(api, "ventana@ejemplo.com", "claveOriginal11")
    for _ in range(6):
        api.post(f"{API}/login", data={"username": "ventana@ejemplo.com",
                                       "password": "mal"})
    assert rate_limit.bloqueado(_clave_login("ventana@ejemplo.com")) is True

    salto = get_settings().login_ventana_min * 60 + 1
    real = rate_limit._ahora
    monkeypatch.setattr(rate_limit, "_ahora", lambda: real() + salto)

    assert rate_limit.bloqueado(_clave_login("ventana@ejemplo.com")) is False


def test_recuperar_tambien_esta_limitado(api):
    """Sin límite, /recuperar es un cañón de correo contra un buzón ajeno."""
    _alta_verificada(api, "spameable@ejemplo.com")

    codigos = [api.post(f"{API}/recuperar",
                        json={"email": "spameable@ejemplo.com"}).status_code
               for _ in range(6)]

    assert codigos[:5] == [200] * 5
    assert codigos[5] == 429


def test_registro_tambien_esta_limitado(api):
    codigos = [api.post(f"{API}/registro",
                        json={"email": f"masivo{i}@ejemplo.com",
                              "password": "unaClaveLarga1"}).status_code
               for i in range(6)]

    assert codigos[:5] == [201] * 5
    assert codigos[5] == 429


# ─────────────── cambio de contraseña autenticado ───────────────

def test_cambiar_password_con_sesion(api):
    _alta_verificada(api, "cambio@ejemplo.com", "claveOriginal11")
    cabeceras = _sesion(api, "cambio@ejemplo.com", "claveOriginal11")

    r = api.post(f"{API}/cambiar-password", headers=cabeceras,
                 json={"actual": "claveOriginal11", "nueva": "claveNueva222"})

    assert r.status_code == 200, r.text
    assert api.post(f"{API}/login", data={"username": "cambio@ejemplo.com",
                                          "password": "claveNueva222"}).status_code == 200


def test_cambiar_password_exige_la_actual(api):
    _alta_verificada(api, "cambio.malo@ejemplo.com", "claveOriginal11")
    cabeceras = _sesion(api, "cambio.malo@ejemplo.com", "claveOriginal11")

    r = api.post(f"{API}/cambiar-password", headers=cabeceras,
                 json={"actual": "no-es-la-mia", "nueva": "claveNueva222"})

    assert r.status_code == 400, r.text
    assert api.post(f"{API}/login", data={"username": "cambio.malo@ejemplo.com",
                                          "password": "claveOriginal11"}).status_code == 200


def test_cambiar_password_requiere_sesion(api):
    r = api.post(f"{API}/cambiar-password",
                 json={"actual": "x", "nueva": "claveNueva222"})

    assert r.status_code == 401, r.text


# ─────────────── separación entre tokens de sesión y de propósito ───────────────

def test_un_token_de_proposito_no_vale_como_sesion(api):
    """Ambos se firman con el mismo secreto. Sin `tipo`, un enlace de reseteo
    enviado por correo servía además como Bearer de sesión completo — y seguía
    sirviendo después de haberse consumido, porque `token_consumido` solo lo mira
    el camino de un solo uso."""
    token = crear_token_proposito("admin@seis.local", "resetear", horas=1)

    r = api.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 401, r.text


def test_un_token_de_sesion_no_vale_como_enlace_de_proposito(api):
    from app.core.security import crear_token

    sesion = crear_token("admin@seis.local", "admin")

    assert api.post(f"{API}/verificar",
                    json={"token": sesion}).status_code == 400


def test_el_token_de_sesion_declara_su_tipo(api):
    from app.core.security import TIPO_SESION

    r = api.post(f"{API}/login", data={"username": "admin@seis.local",
                                       "password": "admin"})
    payload = jwt.decode(r.json()["access_token"], options={"verify_signature": False})

    assert payload["tipo"] == TIPO_SESION


# ─────────────── auditoría ───────────────

def test_cada_accion_sensible_deja_rastro_en_auditoria(api):
    """CLAUDE.md §6.4: toda acción sensible escribe en `Auditoria`.

    No se parametriza por acción: el escenario hay que montarlo una sola vez,
    porque repetirlo con el mismo email caería en el camino de `/registro`
    duplicado (D5), que no envía enlace de verificación.
    """
    from app.core.db import SessionLocal

    _alta_verificada(api, "auditada@ejemplo.com", "claveOriginal11")
    cabeceras = _sesion(api, "auditada@ejemplo.com", "claveOriginal11")
    api.post(f"{API}/cambiar-password", headers=cabeceras,
             json={"actual": "claveOriginal11", "nueva": "claveNueva222"})

    db = SessionLocal()
    try:
        acciones = {a.accion for a in db.query(models.Auditoria)
                    .filter(models.Auditoria.entidad_id == "auditada@ejemplo.com")}
    finally:
        db.close()
    assert {"registro_self_service", "verificar_email",
            "cambiar_password"} <= acciones, sorted(acciones)


def test_la_auditoria_nunca_guarda_la_contrasena(api):
    from app.core.db import SessionLocal

    _alta_verificada(api, "sin.filtrar@ejemplo.com", "claveSecreta777")
    cabeceras = _sesion(api, "sin.filtrar@ejemplo.com", "claveSecreta777")
    api.post(f"{API}/cambiar-password", headers=cabeceras,
             json={"actual": "claveSecreta777", "nueva": "claveNueva888"})

    db = SessionLocal()
    try:
        filas = db.query(models.Auditoria).filter(
            models.Auditoria.entidad_id == "sin.filtrar@ejemplo.com").all()
        volcado = str([f.delta for f in filas])
        assert "claveSecreta777" not in volcado
        assert "claveNueva888" not in volcado
    finally:
        db.close()


# ─────────────── regresión de la Fase 9 ───────────────

def test_las_altas_administrativas_siguen_naciendo_verificadas(api, headers):
    """Un usuario creado por el superadmin no recibe correo de verificación: si
    naciera sin verificar, quedaría permanentemente fuera por el 403 de D6."""
    r = api.post(f"{API}/usuarios", headers=headers,
                 json={"email": "alta.admin@ejemplo.com", "password": "claveAdmin11",
                       "rol": "analista"})
    assert r.status_code == 201, r.text

    assert api.post(f"{API}/login", data={"username": "alta.admin@ejemplo.com",
                                          "password": "claveAdmin11"}).status_code == 200
