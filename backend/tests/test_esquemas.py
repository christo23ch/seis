"""Fallo de familia: valores por defecto que esquivan su propia validación.

Viene de un caso concreto de la Fase 14. `RegistroBody` declaraba

    acepta_terminos: bool = False

con un `@field_validator` que rechaza el `False`. Parecía obligatorio y no lo
era: **Pydantic v2 no valida los valores por defecto**, así que un cliente que
no enviara el campo pasaba la validación con «no acepta» y creaba la cuenta
igual. El validador estaba escrito, se leía bien y no se ejecutaba nunca.

Lo delató que la suite entera siguiera en verde después de añadirlo, cuando
debería haberse puesto roja. Es decir: lo delató el verde, no un rojo.

Este test convierte aquel hallazgo en una barrera. Recorre TODOS los esquemas
Pydantic del proyecto y comprueba que cada valor por defecto pasaría la
validación de su propio campo. Cubre las tres formas de la misma familia:
`@field_validator`, restricciones de `Field` (`min_length`, `gt`…) y el propio
tipo declarado.

Se recorre el paquete en vez de enumerar esquemas a propósito: un esquema nuevo
queda cubierto sin que nadie tenga que acordarse, que es la única forma de que
una barrera siga sirviendo dentro de un año.

Comprobado por mutación: devolver el defecto a `acepta_terminos` pone este test
en rojo nombrando el campo.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil

from pydantic import BaseModel
from pydantic_core import PydanticUndefined


def _todos_los_esquemas() -> dict[str, type[BaseModel]]:
    import app

    esquemas: dict[str, type[BaseModel]] = {}
    for modulo in pkgutil.walk_packages(app.__path__, "app."):
        try:
            cargado = importlib.import_module(modulo.name)
        except Exception:                       # noqa: BLE001
            # Un módulo que no importa es problema de otro test; aquí saltarlo
            # es preferible a que este falle por una causa que no vigila.
            continue
        for obj in vars(cargado).values():
            if (inspect.isclass(obj) and issubclass(obj, BaseModel)
                    and obj is not BaseModel):
                esquemas[f"{obj.__module__}.{obj.__name__}"] = obj
    return esquemas


def test_ningun_valor_por_defecto_esquiva_su_propia_validacion():
    esquemas = _todos_los_esquemas()
    assert len(esquemas) > 20, (
        f"solo se han encontrado {len(esquemas)} esquemas: el recorrido del "
        "paquete se ha roto y este test no está vigilando casi nada")

    sospechosos = []
    for ruta, esquema in sorted(esquemas.items()):
        for campo, info in esquema.model_fields.items():
            if info.default is PydanticUndefined and info.default_factory is None:
                continue                        # obligatorio de verdad: nada que mirar
            defecto = (info.default if info.default is not PydanticUndefined
                       else info.default_factory())
            try:
                # `validate_assignment` sí ejecuta los validadores del campo,
                # que es justo lo que la construcción con defecto se salta.
                esquema.__pydantic_validator__.validate_assignment(
                    esquema.model_construct(), campo, defecto)
            except Exception as e:              # noqa: BLE001
                sospechosos.append(f"  · {ruta}.{campo} = {defecto!r} → {type(e).__name__}")

    assert not sospechosos, (
        "Estos campos tienen un valor por defecto que NO pasaría su propia "
        "validación, de modo que la restricción parece aplicarse y no se aplica:\n"
        + "\n".join(sospechosos)
        + "\n\nSi el campo es obligatorio, quítele el valor por defecto: así "
          "faltar produce un 422 en vez de un valor inventado. Si el defecto es "
          "legítimo, es la restricción la que sobra.")
