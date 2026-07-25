"""Seguridad: hash de contraseñas (PBKDF2-HMAC, stdlib) y tokens JWT (T4)."""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

_ITERACIONES = 240_000


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


def crear_token(email: str, rol: str) -> str:
    s = get_settings()
    ahora = datetime.now(timezone.utc)
    payload = {"sub": email, "rol": rol, "iat": ahora,
               "exp": ahora + timedelta(hours=s.jwt_exp_horas)}
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decodificar_token(token: str) -> dict:
    """Devuelve el payload o lanza jwt.PyJWTError."""
    return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])


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
