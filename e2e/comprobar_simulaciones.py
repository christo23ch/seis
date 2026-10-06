"""¿Quedó en la base lo que el navegador vio? (e2e de simulaciones, Fase 5F.7.9)

La pantalla solo demuestra que el frontend pintó algo. Esto cierra el círculo sobre
el SQLite DESECHABLE de la ejecución: procedencia de cada informe, estado de la
simulación y una fila de auditoría por cada escritura del flujo.

Se consulta el fichero directamente y no un endpoint de apoyo: una ruta solo para
tests sería superficie de API en producción sin otro usuario que la prueba.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

RUTA_BD = os.environ["E2E_BD"]
RUTA_IDS = os.environ["E2E_IDS"]

# En Windows la consola usa cp1252 y no puede imprimir «✓»/«✗»: sin esto, el
# comprobador revienta al informar del primer resultado (medido en 5F.7.9).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

fallos: list[str] = []


def comprobar(condicion: bool, descripcion: str) -> None:
    print(f"  {'✓' if condicion else '✗'} {descripcion}")
    if not condicion:
        fallos.append(descripcion)


with open(RUTA_IDS, encoding="utf-8") as fh:
    ids = json.load(fh)

necesarios = ("analisis", "simulacion", "informe1", "informe2")
if not all(ids.get(k) for k in necesarios):
    print(f"  ✗ el navegador no llegó a registrar todos los ids: {ids}")
    sys.exit(1)

con = sqlite3.connect(RUTA_BD)
try:
    def uno(sql: str, *args):
        return con.execute(sql, args).fetchone()

    procedencia1 = uno("SELECT simulacion_id, analisis_id FROM informe WHERE id = ?", ids["informe1"])
    comprobar(procedencia1 is not None and procedencia1[0] == ids["simulacion"],
              "el primer informe guarda simulacion_id = la simulación validada")
    comprobar(procedencia1 is not None and procedencia1[1] == ids["analisis"], "y pertenece al análisis")
    procedencia2 = uno("SELECT simulacion_id FROM informe WHERE id = ?", ids["informe2"])
    comprobar(procedencia2 is not None and procedencia2[0] is None,
              "el segundo informe guarda simulacion_id = NULL (configuración original)")

    sim = uno("SELECT estado, fecha_validacion, analisis_id, usuario FROM simulacion WHERE id = ?", ids["simulacion"])
    comprobar(sim is not None and sim[0] == "validada", "la simulación está «validada»")
    comprobar(sim is not None and sim[1] is not None, "con fecha de validación")
    comprobar(sim is not None and sim[3] is not None and "@" not in sim[3],
              "Simulacion.usuario guarda un id técnico, no un correo")
    puntero = uno("SELECT simulacion_validada_id FROM analisis WHERE id = ?", ids["analisis"])
    comprobar(puntero is not None and puntero[0] is None,
              "el análisis terminó en la configuración original (puntero NULL)")

    def auditorias(entidad: str, entidad_id: str, accion: str) -> int:
        return uno("SELECT COUNT(*) FROM auditoria WHERE entidad = ? AND entidad_id = ? AND accion = ?",
                   entidad, entidad_id, accion)[0]

    # Una fila por cada escritura del recorrido, ni más ni menos.
    esperadas = [
        ("analisis", ids["analisis"], "crear"),
        ("simulacion", ids["simulacion"], "crear"),
        ("simulacion", ids["simulacion"], "validar"),
        ("informe", ids["informe1"], "generar_oficial"),
        ("analisis", ids["analisis"], "volver_configuracion_original"),
        ("informe", ids["informe2"], "generar_oficial"),
    ]
    for entidad, entidad_id, accion in esperadas:
        n = auditorias(entidad, entidad_id, accion)
        comprobar(n == 1, f"auditoría {entidad}/{accion}: {n} fila(s)")
    delta = uno("SELECT delta FROM auditoria WHERE entidad = 'informe' AND entidad_id = ?", ids["informe1"])
    comprobar(delta is not None and json.loads(delta[0]).get("simulacion_id") == ids["simulacion"],
              "la auditoría del primer informe registra su simulación de procedencia")
finally:
    con.close()

print(f"\nFALLOS: {len(fallos)}\n" if fallos else "\nBase de datos: todo correcto.\n")
sys.exit(1 if fallos else 0)
