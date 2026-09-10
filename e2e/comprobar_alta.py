"""¿Llegó el alta a la base de datos, con sus consentimientos?

La pantalla de «Revise su correo» solo demuestra que el frontend no reventó. Lo
que cierra el círculo es esto: que exista la fila, y que los consentimientos
—incluido el «no» a las comerciales— estén guardados con su versión.

Se consulta el SQLite desechable directamente y no un endpoint de apoyo: una
ruta que dijera si un correo está registrado sería el oráculo de enumeración que
`/registro` evita a propósito respondiendo 201 exista o no la cuenta.
"""
from __future__ import annotations

import os
import sqlite3
import sys

RUTA_BD = os.environ.get("E2E_BD", "/tmp/e2e-seis.db")
RUTA_EMAIL = os.environ.get("E2E_EMAIL_FICHERO", "/tmp/e2e-email.txt")

fallos: list[str] = []


def comprobar(condicion: bool, descripcion: str) -> None:
    print(f"  {'✓' if condicion else '✗'} {descripcion}")
    if not condicion:
        fallos.append(descripcion)


with open(RUTA_EMAIL) as fh:
    email = fh.read().strip()

con = sqlite3.connect(RUTA_BD)
try:
    fila = con.execute("SELECT id, activo, email_verificado FROM usuario WHERE email = ?",
                       (email,)).fetchone()
    comprobar(fila is not None, f"la cuenta {email} existe en la base de datos")
    if fila is None:
        raise SystemExit(1)

    usuario_id, activo, verificado = fila
    # Nace inactiva y sin verificar: hasta que su titular demuestre que controla
    # la dirección, la cuenta no sirve para nada.
    comprobar(not activo, "la cuenta nace inactiva")
    comprobar(not verificado, "la cuenta nace sin verificar")

    consentimientos = dict(con.execute(
        "SELECT tipo, otorgado FROM consentimiento WHERE usuario_id = ?",
        (usuario_id,)).fetchall())
    comprobar(consentimientos.get("terminos") == 1, "«términos» guardado como aceptado")
    comprobar(consentimientos.get("privacidad") == 1, "«privacidad» guardado como aceptado")
    comprobar(consentimientos.get("comunicaciones_comerciales") == 0,
              "el «no» a las comerciales también quedó guardado")

    versiones = [v for (v,) in con.execute(
        "SELECT version FROM consentimiento WHERE usuario_id = ?", (usuario_id,))]
    comprobar(bool(versiones) and all(versiones),
              "cada consentimiento guarda la versión del texto aceptado")
finally:
    con.close()

print(f"\nFALLOS: {len(fallos)}\n" if fallos else "\nBase de datos: todo correcto.\n")
sys.exit(1 if fallos else 0)
