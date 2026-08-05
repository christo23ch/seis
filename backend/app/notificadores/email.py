"""Notificador de email (Fase 12).

Proveedor según EMAIL_PROVIDER: postmark | ses | smtp. Sin proveedor configurado
es honesto: registra en log, guarda el último email en un buffer (accesible desde
tests) y devuelve False sin romper nada.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.text import MIMEText

import httpx

from app import models
from app.core.config import get_settings
from app.notificadores.base import Mensaje, Notificador

log = logging.getLogger("seis.notificadores.email")

# Buffer del último email "enviado" sin proveedor: los tests lo inspeccionan.
ultimo_email: dict | None = None


def _html(mensaje: Mensaje) -> str:
    cuerpo = mensaje.cuerpo.replace("\n", "<br>")
    baja = ""
    if mensaje.enlace_baja:
        baja = (f'<hr><p style="font-size:12px;color:#666">Si no desea recibir más '
                f'comunicaciones, <a href="{mensaje.enlace_baja}">dese de baja aquí</a>.</p>')
    return f"<html><body><p>{cuerpo}</p>{baja}</body></html>"


class NotificadorEmail(Notificador):
    canal = "email"

    def disponible(self) -> bool:
        s = get_settings()
        if s.email_provider == "postmark":
            return bool(s.postmark_token)
        if s.email_provider == "ses":
            return bool(s.ses_region and s.ses_access_key and s.ses_secret_key)
        if s.email_provider == "smtp":
            return bool(s.smtp_host)
        return False

    def enviar(self, usuario: models.Usuario, mensaje: Mensaje) -> bool:
        global ultimo_email
        s = get_settings()
        try:
            if not self.disponible():
                ultimo_email = {"para": usuario.email, "asunto": mensaje.asunto,
                                "cuerpo": mensaje.cuerpo, "enlace_baja": mensaje.enlace_baja}
                log.info("Email sin proveedor configurado (no enviado): para=%s asunto=%s",
                         usuario.email, mensaje.asunto)
                return False
            if s.email_provider == "postmark":
                return self._postmark(usuario.email, mensaje)
            if s.email_provider == "ses":
                return self._ses(usuario.email, mensaje)
            return self._smtp(usuario.email, mensaje)
        except Exception:                                    # noqa: BLE001 — el canal nunca rompe
            log.exception("Fallo enviando email a %s", usuario.email)
            return False

    def _postmark(self, para: str, mensaje: Mensaje) -> bool:
        s = get_settings()
        r = httpx.post(
            "https://api.postmarkapp.com/email",
            headers={"X-Postmark-Server-Token": s.postmark_token},
            json={"From": s.email_from, "To": para, "Subject": mensaje.asunto,
                  "HtmlBody": _html(mensaje), "TextBody": mensaje.cuerpo,
                  "MessageStream": "outbound"},
            timeout=10)
        return r.status_code == 200

    def _ses(self, para: str, mensaje: Mensaje) -> bool:
        # API SES v2 vía boto3 si está instalado; si no, se registra la carencia.
        try:
            import boto3                                     # noqa: PLC0415 — dependencia opcional
        except ImportError:
            log.warning("EMAIL_PROVIDER=ses pero boto3 no está instalado")
            return False
        s = get_settings()
        cliente = boto3.client("sesv2", region_name=s.ses_region,
                               aws_access_key_id=s.ses_access_key,
                               aws_secret_access_key=s.ses_secret_key)
        cliente.send_email(
            FromEmailAddress=s.email_from,
            Destination={"ToAddresses": [para]},
            Content={"Simple": {"Subject": {"Data": mensaje.asunto},
                                "Body": {"Html": {"Data": _html(mensaje)},
                                         "Text": {"Data": mensaje.cuerpo}}}})
        return True

    def _smtp(self, para: str, mensaje: Mensaje) -> bool:
        s = get_settings()
        mime = MIMEText(_html(mensaje), "html", "utf-8")
        mime["Subject"] = mensaje.asunto
        mime["From"] = s.email_from
        mime["To"] = para
        with smtplib.SMTP(s.smtp_host, s.smtp_puerto, timeout=10) as smtp:
            # El contexto es OBLIGATORIO. `starttls()` sin él usa
            # `ssl._create_stdlib_context()`, que trae `verify_mode=CERT_NONE` y
            # `check_hostname=False`: cualquier certificado autofirmado completa
            # el handshake sin protesta. Un atacante con posición de red entre
            # el contenedor y el relay captaría SMTP_USUARIO y SMTP_PASSWORD
            # —`login()` va justo debajo, ya dentro del canal— y el contenido de
            # todos los correos, que incluye los enlaces de verificación y de
            # reseteo de contraseña de la Fase 10: con ellos se toma cualquier
            # cuenta del sistema.
            #
            # Hasta la Fase 11 este camino era inalcanzable bajo Docker, porque
            # las credenciales SMTP no se propagaban al contenedor y
            # `disponible()` devolvía False. El Bloque C′ lo activó al cerrar
            # ese hueco, de modo que el defecto pasó de latente a explotable.
            smtp.starttls(context=ssl.create_default_context())
            if s.smtp_usuario:
                smtp.login(s.smtp_usuario, s.smtp_password)
            smtp.sendmail(s.email_from, [para], mime.as_string())
        return True
