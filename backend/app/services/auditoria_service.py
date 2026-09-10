"""Único punto por el que se escribe en `auditoria` (Fase 16, hallazgo 1.3).

Antes había 23 construcciones de `models.Auditoria(...)` repartidas por siete
módulos. Ninguna estaba mal, pero el conjunto tenía un problema que no era de
ninguna en particular: **nada impedía que la próxima metiera un dato personal en
`delta`**, y ese campo es JSON libre.

Por qué eso importa más de lo que parece. La limpieza del RGPD
(`borrado_service.anonimizar_auditoria`) actúa **por nombre de columna**: sustituye
`quien` y `entidad_id`. `delta` no puede estar en esa lista, porque su contenido
es arbitrario y no hay forma de saber qué campo de dentro es una persona. De modo
que un correo escrito en `delta` sobreviviría a un borrado que el sistema declara
completo — y el test que deriva las tablas hijas del esquema no lo vería nunca,
porque `auditoria` no tiene clave foránea a `usuario`: la ligadura es por VALOR.

LA GARANTÍA NO ES `auditar()`, ES EL OYENTE. Un embudo solo sirve si todo el
mundo lo usa, y «todo el mundo lo usa» es una afirmación sobre las personas, no
sobre el código: la vigésimo cuarta construcción de `Auditoria(...)` no pasaría
por aquí y nadie se enteraría. De modo que la comprobación se engancha a
`before_insert` del propio modelo: **cubre toda escritura, venga de donde venga,
incluidas las que se escriban dentro de un año sin conocer este módulo.**

`auditar()` sigue siendo la forma preferida porque falla antes —al construir, no
al volcar— y el mensaje sale con más contexto. Pero no es la barrera.

QUÉ CUBRE: que ningún `delta` que llegue a la tabla `auditoria` lleve algo con
forma de dirección de correo. Falla en voz alta si lo lleva.

QUÉ NO CUBRE, y se dice aquí, junto al mecanismo, y no en un documento aparte
(ADR-0014):

- **No detecta otros datos personales.** Un teléfono, un DNI, una dirección
  postal o un nombre pasan sin más. Solo se busca la forma del correo, que es el
  identificador que este sistema usa de hecho para nombrar personas.
- **No mira `quien` ni `entidad_id`.** Ahí el correo es LEGÍTIMO —es el actor— y
  lo seudonimiza el borrado. Vetarlo aquí rompería la auditoría.
- **No cubre `UPDATE`.** Solo `before_insert`. Nadie actualiza filas de auditoría
  hoy salvo la anonimización del borrado, que escribe seudónimos; si alguna fase
  empieza a editar `delta`, esto no lo verá.
- **No cubre escrituras que no pasen por el ORM.** Un `INSERT` en SQL crudo o una
  migración que rellene `auditoria` se lo salta. Hoy no existe ninguna.
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app import models
from app.core.datos_personales import (DatoPersonalEnAuditoria, buscar_correo,
                                       mensaje_de_veto)

def auditar(db: Session, *, quien: str | None, entidad: str, entidad_id: str,
            accion: str, delta: dict | None = None) -> models.Auditoria:
    """Añade una fila de auditoría a la sesión. NO hace commit.

    Lanza `DatoPersonalEnAuditoria` si `delta` lleva algo con forma de correo.
    Lanzar y no limpiar es deliberado: limpiar en silencio dejaría al autor
    creyendo que su dato se guardó, y el problema volvería en la fila siguiente.
    """
    delta = delta or {}
    donde = buscar_correo(delta)
    if donde is not None:
        # Se comprueba aquí ADEMÁS del oyente del modelo: así falla al construir
        # y no al volcar la sesión, que es donde el error resulta legible.
        raise DatoPersonalEnAuditoria(mensaje_de_veto(accion, donde))
    fila = models.Auditoria(quien=quien, entidad=entidad, entidad_id=entidad_id,
                            accion=accion, delta=delta)
    db.add(fila)
    return fila
