"""Correos transaccionales del alta self-service (Fase 10).

Los tres mensajes de esta fase —verificación, reseteo y aviso de cuenta ya
existente— viajan **sin enlace de baja**. `Mensaje.enlace_baja` nació en la Fase
12 para las comunicaciones comerciales (alertas y digest), donde es obligatorio;
aquí sería un error funcional: nadie debe poder «darse de baja» del correo que
precisamente le permite activar su cuenta o recuperar el acceso.

Tampoco consultan `PreferenciasNotificacion`. Un usuario que apagó las alertas
sigue teniendo derecho a recuperar su contraseña.
"""
from __future__ import annotations

from app import models
from app.core.config import get_settings
from app.core.security import (PROPOSITO_RESETEAR, PROPOSITO_VERIFICAR,
                               crear_token_proposito)
from app.notificadores import Mensaje, obtener_notificadores

# TTL de cada enlace. La verificación es generosa porque el usuario puede leer el
# correo al día siguiente; el reseteo es corto porque es la llave de la cuenta.
HORAS_VERIFICACION = 24
HORAS_RESETEO = 1


def _enviar(usuario: models.Usuario, mensaje: Mensaje) -> bool:
    """Envía por email. Devuelve False sin lanzar si el canal no está configurado."""
    for notificador in obtener_notificadores(["email"]):
        return notificador.enviar(usuario, mensaje)
    return False


def enlace_verificacion(email: str) -> str:
    token = crear_token_proposito(email, PROPOSITO_VERIFICAR, horas=HORAS_VERIFICACION)
    return f"{get_settings().frontend_url}/verificar?token={token}"


def enlace_reseteo(email: str) -> str:
    token = crear_token_proposito(email, PROPOSITO_RESETEAR, horas=HORAS_RESETEO)
    return f"{get_settings().frontend_url}/resetear?token={token}"


def enviar_verificacion(usuario: models.Usuario) -> bool:
    """Correo de activación de cuenta recién registrada."""
    cuerpo = (
        f"Le damos la bienvenida a SEIS.\n\n"
        f"Para activar su cuenta y empezar a analizar subastas, confirme su "
        f"dirección de correo en el siguiente enlace:\n\n"
        f"{enlace_verificacion(usuario.email)}\n\n"
        f"El enlace caduca en {HORAS_VERIFICACION} horas y solo puede usarse una vez.\n"
        f"Si no ha sido usted quien se ha registrado, ignore este mensaje: sin "
        f"confirmar, la cuenta no se activa."
    )
    return _enviar(usuario, Mensaje(asunto="Confirme su cuenta de SEIS",
                                    cuerpo=cuerpo, enlace_baja=None))


def enviar_reseteo(usuario: models.Usuario) -> bool:
    """Correo de restablecimiento de contraseña."""
    cuerpo = (
        f"Hemos recibido una solicitud para restablecer la contraseña de su "
        f"cuenta de SEIS.\n\n"
        f"Puede establecer una contraseña nueva en el siguiente enlace:\n\n"
        f"{enlace_reseteo(usuario.email)}\n\n"
        f"El enlace caduca en {HORAS_RESETEO} hora y solo puede usarse una vez.\n"
        f"Si no ha solicitado el cambio, ignore este mensaje: su contraseña "
        f"actual sigue siendo válida."
    )
    return _enviar(usuario, Mensaje(asunto="Restablecer su contraseña de SEIS",
                                    cuerpo=cuerpo, enlace_baja=None))


def enviar_aviso_cuenta_existente(usuario: models.Usuario) -> bool:
    """Aviso al titular cuando alguien intenta registrarse con su dirección.

    Es la contrapartida de que `POST /auth/registro` responda 201 tanto si la
    cuenta existe como si no: la respuesta HTTP no distingue los dos casos, así
    que quien recibe información sobre el intento es el titular de la dirección,
    nunca quien lo hizo.
    """
    cuerpo = (
        f"Alguien ha intentado registrarse en SEIS con esta dirección de correo, "
        f"que ya tiene una cuenta.\n\n"
        f"No hemos creado ninguna cuenta nueva ni modificado la suya.\n\n"
        f"Si ha sido usted, inicie sesión con normalidad en "
        f"{get_settings().frontend_url}/login\n"
        f"Si no recuerda su contraseña, puede restablecerla en "
        f"{get_settings().frontend_url}/recuperar\n\n"
        f"Si no ha sido usted, no tiene que hacer nada."
    )
    return _enviar(usuario, Mensaje(asunto="Intento de registro en SEIS",
                                    cuerpo=cuerpo, enlace_baja=None))
