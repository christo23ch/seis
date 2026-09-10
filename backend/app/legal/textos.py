"""Textos legales y sus versiones (Fase 14, RGPD).

**HUECO DELIBERADO: los textos NO están escritos.** Los redacta un abogado; aquí
solo está la estructura que los sostiene, con marcadores que no se pueden
confundir con texto real.

Lo que sí es definitivo es el mecanismo: cada texto tiene una **versión**, y el
consentimiento se guarda contra esa versión. Sin eso, publicar una política
nueva convertiría retroactivamente los consentimientos anteriores en
consentimientos a un texto que nadie leyó — que es precisamente lo que el RGPD
no admite.

CÓMO SE PUBLICA UNA VERSIÓN NUEVA, cuando lleguen los textos:

1. Se sustituye el cuerpo y **se sube la versión** en la misma edición. Cambiar
   el texto sin subir la versión es el único error de aquí que no tiene arreglo
   después: los consentimientos ya guardados apuntarían a un texto que ya no
   existe y no habría forma de saber cuál firmó cada cual.
2. `VERSION_VIGENTE` pasa a la nueva.
3. Los consentimientos anteriores **no se tocan**: son la prueba de lo que se
   aceptó entonces. Si el cambio es sustancial, hay que volver a pedirlos.

Un test comprueba que ningún texto marcado como pendiente pueda publicarse como
definitivo por descuido.
"""
from __future__ import annotations

from dataclasses import dataclass

# Tipos de consentimiento. `obligatorio` distingue lo que es condición del
# servicio de lo que no: marcar como obligatorio algo que no lo es convierte el
# consentimiento en no libre, y un consentimiento no libre no es consentimiento.
TERMINOS = "terminos"
PRIVACIDAD = "privacidad"
COMUNICACIONES_COMERCIALES = "comunicaciones_comerciales"

MARCADOR_PENDIENTE = "«PENDIENTE DE REDACCIÓN LEGAL»"


@dataclass(frozen=True)
class TextoLegal:
    tipo: str
    version: str
    titulo: str
    cuerpo: str
    obligatorio: bool

    @property
    def pendiente(self) -> bool:
        """¿Sigue siendo un marcador y no un texto de verdad?"""
        return MARCADOR_PENDIENTE in self.cuerpo


# Versión inicial. Sube a «2» cuando lleguen los textos reales, y a partir de ahí
# una por cada cambio sustancial.
VERSION_VIGENTE = "1"

TEXTOS: dict[str, TextoLegal] = {
    TERMINOS: TextoLegal(
        tipo=TERMINOS, version=VERSION_VIGENTE,
        titulo="Condiciones del servicio",
        cuerpo=f"{MARCADOR_PENDIENTE}\n\nAquí van las condiciones del servicio.",
        obligatorio=True),
    PRIVACIDAD: TextoLegal(
        tipo=PRIVACIDAD, version=VERSION_VIGENTE,
        titulo="Política de privacidad",
        cuerpo=(f"{MARCADOR_PENDIENTE}\n\nAquí van responsable del tratamiento, "
                "finalidades, base jurídica, plazos de conservación, "
                "destinatarios y cómo ejercer los derechos."),
        obligatorio=True),
    COMUNICACIONES_COMERCIALES: TextoLegal(
        tipo=COMUNICACIONES_COMERCIALES, version=VERSION_VIGENTE,
        titulo="Comunicaciones comerciales",
        cuerpo=(f"{MARCADOR_PENDIENTE}\n\nEnvío de novedades del producto. "
                "Se puede retirar en cualquier momento."),
        # NO obligatorio, y esto es la parte que no se puede tocar sin pensarlo:
        # condicionar el alta a aceptar publicidad haría que el consentimiento no
        # fuera libre, y entonces no vale como consentimiento.
        obligatorio=False),
}

OBLIGATORIOS = tuple(t for t, texto in TEXTOS.items() if texto.obligatorio)
TIPOS_VALIDOS = tuple(TEXTOS)


def hay_textos_pendientes() -> bool:
    """¿Queda algún texto sin redactar? Lo usan los tests y el arranque."""
    return any(t.pendiente for t in TEXTOS.values())
