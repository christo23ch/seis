"""Seguridad: hash de contraseñas (PBKDF2-HMAC, stdlib) y tokens JWT (T4)."""
from __future__ import annotations

import hashlib
import hmac
import os
import uuid
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


def crear_token_proposito(sub: str, proposito: str, horas: float) -> str:
    """Token de un solo uso (Fase 10): verificación de email o reseteo de contraseña.

    Lleva `jti` (identificador único, consumido por usuario_service tras su uso)
    y `proposito`, para que un token de "verificar" no sirva en /auth/resetear ni
    viceversa aunque comparta firma y secreto.
    """
    s = get_settings()
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "proposito": proposito,
        "jti": str(uuid.uuid4()),
        "iat": ahora,
        "exp": ahora + timedelta(hours=horas),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decodificar_token_proposito(token: str, proposito_esperado: str) -> dict:
    """Devuelve el payload si la firma, expiración y propósito son válidos.

    Lanza jwt.PyJWTError (expirado/manipulado) o ValueError (propósito
    equivocado) — ambos deben tratarse como token inválido por el llamador.
    """
    payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    if payload.get("proposito") != proposito_esperado:
        raise ValueError("propósito de token incorrecto")
    return payload
