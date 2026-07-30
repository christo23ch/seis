"""Seguridad: hash de contraseñas (PBKDF2-HMAC, stdlib) y tokens JWT (T4)."""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

_ITERACIONES = 240_000

# Propósitos de los tokens firmados (Fase 10). Nombrarlos evita que un literal
# mal escrito en un endpoint acepte en silencio un token de otro propósito.
# El propósito "baja" (Fase 12) sigue escrito a mano en su propio módulo.
PROPOSITO_VERIFICAR = "verificar"
PROPOSITO_RESETEAR = "resetear"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERACIONES)
    return f"pbkdf2_sha256${_ITERACIONES}${salt.hex()}${dk.hex()}"


def verify_password(password: str, almacenado: str) -> bool:
    try:
        _algo, iters, salt_hex, hash_hex = almacenado.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


# Marca de audiencia del token de sesión. Los tokens de propósito
# (`crear_token_proposito`) NO la llevan, y `decodificar_token` la exige.
TIPO_SESION = "sesion"


def crear_token(email: str, rol: str) -> str:
    s = get_settings()
    ahora = datetime.now(timezone.utc)
    payload = {"sub": email, "rol": rol, "tipo": TIPO_SESION, "iat": ahora,
               "exp": ahora + timedelta(hours=s.jwt_exp_horas)}
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decodificar_token(token: str) -> dict:
    """Devuelve el payload de un token **de sesión**, o lanza jwt.PyJWTError.

    Exige `tipo == "sesion"` para cerrar una confusión de audiencia real: los
    tokens de propósito se firman con **el mismo `jwt_secret`** que los de
    sesión, y hasta la Fase 10 esta función era un `jwt.decode` genérico. Eso
    hacía que un enlace de verificación (24 h) o de reseteo (1 h) enviado por
    correo valiera además como Bearer de sesión completo en cualquier endpoint
    protegido por `get_current_user`, heredando el rol real de la cuenta —y
    seguía valiendo **después** de haberse consumido, porque `token_consumido`
    solo lo consulta el camino de un solo uso, nunca la autenticación.

    Quien se hiciera con la URL de uno de esos correos (buzón comprometido, log
    de proxy con la query string, escáner corporativo de enlaces) no obtenía solo
    una acción de un solo uso: obtenía la sesión.

    La comprobación es una lista blanca, no una negra: un token sin `tipo` se
    rechaza. El precio es que los tokens emitidos antes de este cambio dejan de
    servir, es decir, un cierre de sesión único en el despliegue.
    """
    payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    if payload.get("tipo") != TIPO_SESION:
        raise jwt.InvalidTokenError("El token no es un token de sesión")
    return payload


def crear_token_proposito(sub: str, proposito: str, horas: int) -> str:
    """Token firmado de propósito único (Fase 12: "baja"; Fase 10 lo reutilizará).

    Incluye `jti` para permitir el marcado de un solo uso cuando el propósito
    lo exija. El propósito viaja en el payload y se verifica al decodificar.
    """
    import uuid
    s = get_settings()
    ahora = datetime.now(timezone.utc)
    payload = {"sub": sub, "proposito": proposito, "jti": str(uuid.uuid4()),
               "iat": ahora, "exp": ahora + timedelta(hours=horas)}
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decodificar_token_proposito(token: str, proposito: str) -> dict:
    """Decodifica y exige que el propósito coincida; lanza jwt.PyJWTError si no."""
    payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    if payload.get("proposito") != proposito:
        raise jwt.InvalidTokenError("Propósito del token incorrecto")
    return payload
