"""Autenticación y alta self-service.

Los endpoints que añade la Fase 10 son **públicos** salvo `/cambiar-password`.
Dos criterios los gobiernan y conviene leerlos antes de tocar nada:

* **No revelan si una dirección tiene cuenta.** `/registro` responde 201 y
  `/recuperar` responde 200 exista o no el email. Quien recibe información sobre
  lo ocurrido es siempre el titular de la dirección, por correo, nunca quien hizo
  la petición. Es el mismo criterio que CLAUDE.md §4 impone a los recursos ajenos
  (404 y no 403) y que la Fase 12 ya aplica en `/notificaciones/baja`.
* **Todo fallo de token dice exactamente lo mismo.** Inválido, caducado, con el
  propósito cambiado o ya gastado producen el mismo 400 y el mismo texto.
"""
from __future__ import annotations

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_current_user, require_superadmin
from app.core import rate_limit
from app.core.db import get_db
from app.core.security import (PROPOSITO_RESETEAR, PROPOSITO_VERIFICAR,
                               crear_token, decodificar_token_proposito,
                               verify_password)
from app.services import registro_service, usuario_service

router = APIRouter(prefix="/auth", tags=["auth"])

# Longitud mínima de contraseña. Se valida en Pydantic para que el rechazo llegue
# antes de tocar la base de datos; el frontend la replica solo por comodidad.
MIN_PASSWORD = 8
# Tope defensivo: acota la entrada de campos que se procesan antes de tocar la
# base de datos. PBKDF2 no se dispara con claves largas, pero una entrada sin
# límite no tiene por qué llegar al servicio.
MAX_PASSWORD = 200
MAX_TOKEN = 2000

MENSAJE_ENLACE_INVALIDO = "El enlace no es válido, ha caducado o ya se ha utilizado"
MENSAJE_DEMASIADOS_INTENTOS = (
    "Demasiados intentos. Espere unos minutos antes de volver a probar.")
MENSAJE_SIN_VERIFICAR = (
    "Su cuenta aún no está verificada. Revise su correo y confirme la dirección "
    "para poder entrar.")
# Texto único del alta, del reenvío y de la recuperación: es lo que hace que la
# respuesta sea indistinguible exista o no la cuenta.
MENSAJE_NEUTRO = (
    "Si la dirección es válida, recibirá un correo para continuar. Revise "
    "también la carpeta de correo no deseado.")


class UsuarioCrear(BaseModel):
    email: EmailStr
    password: str
    nombre: str | None = None
    rol: str = "analista"
    organizacion_id: str | None = None       # superadmin: org destino (por defecto, la suya)
    rol_org: str = "miembro"
    es_superadmin: bool = False


class RegistroBody(BaseModel):
    """Entrada del alta pública.

    Deliberadamente **no** reutiliza `UsuarioCrear`: aquel expone `rol`,
    `rol_org` y `es_superadmin` como campos de entrada, y aceptarlos en un
    endpoint sin autenticar sería regalar una escalada de privilegios. Quien se
    registra acaba siempre como propietario de una organización nueva y nunca
    como superadministrador de plataforma.
    """
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD, max_length=MAX_PASSWORD)
    # `nombre` acota a 80 porque esa es la anchura de `usuario.nombre`: sin el
    # tope, un valor más largo abortaría la transacción en PostgreSQL y saldría
    # como un 500 en vez de como el 422 que corresponde a una entrada inválida.
    nombre: str | None = Field(default=None, max_length=80)


class EmailBody(BaseModel):
    """Dirección a buscar en `/recuperar` y `/reenviar-verificacion`.

    Aquí el campo es `str` y **no** `EmailStr`, al contrario que en el alta. En
    estos dos endpoints la dirección es solo una clave de búsqueda: si no existe,
    no pasa nada. Exigir sintaxis de email introduciría un segundo código de
    respuesta —422— que rompería la propiedad que estos endpoints prometen
    («200 siempre»), y de hecho dejaba fuera al administrador sembrado, cuya
    dirección `admin@seis.local` rechaza `email-validator` por ser `.local` un
    dominio de uso especial (RFC 6762). El límite de longitud está para acotar la
    entrada, no para validarla.
    """
    email: str = Field(min_length=3, max_length=200)


class TokenBody(BaseModel):
    token: str = Field(max_length=MAX_TOKEN)


class ResetearBody(BaseModel):
    token: str = Field(max_length=MAX_TOKEN)
    nueva: str = Field(min_length=MIN_PASSWORD, max_length=MAX_PASSWORD)


class CambiarPasswordBody(BaseModel):
    actual: str = Field(max_length=MAX_PASSWORD)
    nueva: str = Field(min_length=MIN_PASSWORD, max_length=MAX_PASSWORD)


class RespuestaSimple(BaseModel):
    ok: bool
    mensaje: str


def _ip(request: Request) -> str:
    """IP del cliente, para limitar por origen los endpoints que envían correo.

    Se usa `request.client.host` y **no** `X-Forwarded-For`: esa cabecera la
    puede escribir cualquiera, de modo que fiarse de ella sin una lista de
    proxies de confianza permitiría tanto evadir el límite rotando el valor como
    envenenar el contador de un tercero.

    **Limitación medida (Fase 10, pendiente de la Fase 11).** Bajo `docker
    compose`, el reenvío del puerto publicado no conserva la IP de origen: se
    comprobó que todas las peticiones externas llegan con la de la pasarela
    (`172.18.0.1`), de modo que los límites por IP de `/registro` y
    `/reenviar-verificacion` se comportan como un único cupo global en vez de uno
    por cliente. No es un agujero de seguridad —el límite sigue frenando el
    abuso—, pero sí un tope de capacidad: 5 altas cada 15 minutos en todo el
    sitio. La solución pertenece a la infraestructura, no a este módulo: proxy
    inverso delante, uvicorn con `--proxy-headers` y `--forwarded-allow-ips`
    acotado a ese proxy, y solo entonces `X-Forwarded-For` pasa a ser fiable.
    """
    return request.client.host if request.client else "desconocida"


def _clave_login(email: str, ip: str) -> str:
    """Clave del limitador de login: por email **y** por origen.

    Con la clave solo por email, cualquiera podía dejar bloqueada la cuenta de un
    tercero enviando cinco contraseñas erróneas, y repitiéndolo cada ventana la
    dejaba inaccesible de forma indefinida —el bloqueo se comprueba antes que la
    contraseña, así que ni el titular legítimo entraba—. No hacía falta ni que la
    cuenta existiera. Al componer la clave con el origen, el atacante solo se
    bloquea a sí mismo contra esa cuenta.

    La protección contra fuerza bruta no se resiente: quien la ejerce viene de un
    origen concreto y sigue agotando sus cinco intentos.

    **Su efecto completo depende de la Fase 11.** Bajo el `docker compose` actual
    todas las peticiones externas comparten la IP de la pasarela, de modo que hoy
    esta clave se comporta como la anterior; deja de hacerlo en cuanto haya un
    proxy inverso que conserve el origen real.
    """
    return f"login:{email.strip().lower()}:{ip}"


def _exigir_no_bloqueado(clave: str) -> None:
    if rate_limit.bloqueado(clave):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            MENSAJE_DEMASIADOS_INTENTOS)


def _consumir_token(db: Session, token: str, proposito: str) -> str:
    """Valida un token de un solo uso y devuelve su `sub`.

    Reclama el `jti` **antes** de que el llamante aplique ningún efecto, y la
    exclusión la impone la clave primaria de `token_consumido`, no una lectura
    previa. Todos los caminos de fallo lanzan el mismo 400 con el mismo texto.
    """
    try:
        payload = decodificar_token_proposito(token, proposito)
    except pyjwt.PyJWTError:
        raise HTTPException(400, MENSAJE_ENLACE_INVALIDO)
    jti, sub = payload.get("jti"), payload.get("sub")
    if not jti or not sub:
        raise HTTPException(400, MENSAJE_ENLACE_INVALIDO)
    if not usuario_service.marcar_jti(db, jti, proposito):
        raise HTTPException(400, MENSAJE_ENLACE_INVALIDO)
    return sub


@router.post("/login")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)) -> dict:
    clave = _clave_login(form.username, _ip(request))
    _exigir_no_bloqueado(clave)
    user, motivo = usuario_service.autenticar_con_motivo(db, form.username,
                                                         form.password)
    if user is None:
        # Solo «sin verificar» cambia el código de estado. Una cuenta desactivada
        # por su propietario sigue devolviendo el 401 genérico que fijó la Fase 9
        # (`test_propietario_activa_desactiva_miembro_propio`): ahí la opacidad es
        # deliberada —quien fue dado de baja no tiene por qué saber si su cuenta
        # existe todavía— y no es un caso que el titular pueda resolver solo.
        # El motivo solo existe cuando la contraseña era correcta, así que este
        # camino no cuenta como intento de fuerza bruta ni acerca al bloqueo:
        # quien acierta la clave no la está adivinando.
        if motivo == usuario_service.MOTIVO_SIN_VERIFICAR:
            raise HTTPException(status.HTTP_403_FORBIDDEN, MENSAJE_SIN_VERIFICAR)
        if motivo is None:
            rate_limit.registrar_intento(clave)
        raise HTTPException(401, "Email o contraseña incorrectos")
    rate_limit.limpiar(clave)
    return {"access_token": crear_token(user.email, user.rol),
            "token_type": "bearer", "rol": user.rol, "nombre": user.nombre}


@router.get("/me")
def me(user: models.Usuario = Depends(get_current_user),
       db: Session = Depends(get_db)) -> dict:
    org = (usuario_service.obtener_organizacion(db, user.organizacion_id)
           if user.organizacion_id else None)
    return {"email": user.email, "nombre": user.nombre, "rol": user.rol,
            "organizacion_id": user.organizacion_id,
            "organizacion_nombre": org.nombre if org else None,
            "rol_org": user.rol_org, "es_superadmin": user.es_superadmin}


@router.post("/usuarios", status_code=201)
def crear_usuario(body: UsuarioCrear, db: Session = Depends(get_db),
                  admin: models.Usuario = Depends(require_superadmin)) -> dict:
    try:
        u = usuario_service.crear_usuario(
            db, body.email, body.password, body.nombre, body.rol,
            organizacion_id=body.organizacion_id or admin.organizacion_id,
            rol_org=body.rol_org, es_superadmin=body.es_superadmin)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"email": u.email, "rol": u.rol, "organizacion_id": u.organizacion_id}


# ─────────────── Alta self-service (Fase 10) ───────────────

@router.post("/registro", status_code=201, response_model=RespuestaSimple)
def registro(body: RegistroBody, request: Request,
             db: Session = Depends(get_db)) -> RespuestaSimple:
    """Alta pública. Responde 201 exista o no la cuenta.

    Si la dirección ya está registrada no se crea nada y se avisa por correo a su
    titular, el único con derecho a enterarse del intento.
    """
    clave = f"registro:{_ip(request)}"
    _exigir_no_bloqueado(clave)
    rate_limit.registrar_intento(clave)

    usuario = usuario_service.registrar_usuario(db, body.email, body.password,
                                                body.nombre)
    if usuario is None:
        existente = usuario_service.obtener_por_email(db, body.email)
        if existente is not None:
            registro_service.enviar_aviso_cuenta_existente(existente)
    else:
        registro_service.enviar_verificacion(usuario)
    return RespuestaSimple(ok=True, mensaje=MENSAJE_NEUTRO)


@router.post("/verificar", response_model=RespuestaSimple)
def verificar(body: TokenBody, db: Session = Depends(get_db)) -> RespuestaSimple:
    """Confirma la dirección y activa la cuenta. Un solo uso."""
    email = _consumir_token(db, body.token, PROPOSITO_VERIFICAR)
    if usuario_service.verificar_email(db, email) is None:
        raise HTTPException(400, MENSAJE_ENLACE_INVALIDO)
    return RespuestaSimple(ok=True,
                           mensaje="Cuenta verificada. Ya puede iniciar sesión.")


@router.post("/reenviar-verificacion", response_model=RespuestaSimple)
def reenviar_verificacion(body: EmailBody, request: Request,
                          db: Session = Depends(get_db)) -> RespuestaSimple:
    """Reenvía el correo de activación.

    Sin esto, un enlace caducado a las 24 h dejaría la cuenta muerta y sin salida:
    no puede entrar porque no está verificada, y no puede verificarse porque su
    único enlace expiró.
    """
    # Dos claves, como en `/recuperar`: por origen y **por destinatario**. Sin la
    # segunda, quien dispusiera de varios orígenes podría llenar la bandeja de una
    # cuenta real no verificada a base de reenvíos.
    por_origen = f"reenviar:{_ip(request)}"
    por_destino = f"reenviar-destino:{body.email.strip().lower()}"
    _exigir_no_bloqueado(por_origen)
    _exigir_no_bloqueado(por_destino)
    rate_limit.registrar_intento(por_origen)
    rate_limit.registrar_intento(por_destino)

    usuario = usuario_service.obtener_por_email(db, body.email)
    if usuario is not None and not usuario.email_verificado:
        registro_service.enviar_verificacion(usuario)
    return RespuestaSimple(ok=True, mensaje=MENSAJE_NEUTRO)


@router.post("/recuperar", response_model=RespuestaSimple)
def recuperar(body: EmailBody, db: Session = Depends(get_db)) -> RespuestaSimple:
    """Solicita el restablecimiento. Responde 200 exista o no la cuenta."""
    clave = f"recuperar:{body.email.strip().lower()}"
    _exigir_no_bloqueado(clave)
    rate_limit.registrar_intento(clave)

    usuario = usuario_service.obtener_por_email(db, body.email)
    if usuario is not None:
        registro_service.enviar_reseteo(usuario)
    return RespuestaSimple(ok=True, mensaje=MENSAJE_NEUTRO)


@router.post("/resetear", response_model=RespuestaSimple)
def resetear(body: ResetearBody, request: Request,
             db: Session = Depends(get_db)) -> RespuestaSimple:
    """Fija una contraseña nueva a partir del enlace firmado. Un solo uso."""
    email = _consumir_token(db, body.token, PROPOSITO_RESETEAR)
    usuario = usuario_service.obtener_por_email(db, email)
    if usuario is None:
        raise HTTPException(400, MENSAJE_ENLACE_INVALIDO)
    usuario_service.cambiar_password(db, usuario, body.nueva)
    # Quien acaba de demostrar que controla el buzón no debe seguir arrastrando
    # el bloqueo de sus intentos fallidos previos. Se limpia el contador de su
    # propio origen, que es justamente desde donde vuelve a intentar entrar.
    rate_limit.limpiar(_clave_login(usuario.email, _ip(request)))
    return RespuestaSimple(ok=True,
                           mensaje="Contraseña actualizada. Ya puede iniciar sesión.")


@router.post("/cambiar-password", response_model=RespuestaSimple)
def cambiar_password(body: CambiarPasswordBody,
                     user: models.Usuario = Depends(get_current_user),
                     db: Session = Depends(get_db)) -> RespuestaSimple:
    """Cambio de contraseña con sesión iniciada.

    Antes de la Fase 10 no existía ninguno: quien recibía una contraseña temporal
    de su propietario no tenía forma de cambiarla jamás.
    """
    if not verify_password(body.actual, user.hash_pwd):
        raise HTTPException(400, "La contraseña actual no es correcta")
    usuario_service.cambiar_password(db, user, body.nueva)
    return RespuestaSimple(ok=True, mensaje="Contraseña actualizada correctamente.")
