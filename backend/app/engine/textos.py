"""Fase 5J-2a — nombres legibles de los códigos y símbolos que el motor usa por dentro.

El resultado del motor guarda CÓDIGOS (`juridico`, `una_alta`, `comparables_ajustados`,
`posesion_verificada`…) y algunos textos llevan los SÍMBOLOS de la especificación (`C_F`,
`c_v`, `δ_v`, `P_max`…). Los códigos son datos —los leen la interfaz, las reglas y la
persistencia, y la foto del caso dorado (`tests/test_invariante_5h1.py`) los fija—, así que
no se cambian: se traducen aquí al REDACTAR el informe (M14), que es lo que lee una persona
y lo que llega al PDF.

Solo redacción: ninguna función de este módulo interviene en un cálculo. Diccionario
cerrado y explícito, sin reglas generales: una palabra que no está aquí se queda como está
(el test `test_textos_5j2a.py` barre el informe en busca de lo que se haya escapado).
"""
from __future__ import annotations

import re

# Símbolos de la especificación (§ glosario) → su nombre.
SIMBOLOS: dict[str, str] = {
    "C_F": "costes fijos",
    "c_v": "costes proporcionales",
    "δ_v": "descuento de prudencia",
    "P_max": "precio máximo",
    "P_ideal": "precio ideal",
    "P_objetivo": "precio objetivo",
    "P_limite": "precio límite",
    "P_adj": "precio de adjudicación",
    "VS_p": "VS prudente",
}

# Códigos internos → texto con tildes y sin barra baja.
ETIQUETAS: dict[str, str] = {
    # Dimensiones de riesgo (`contracts.Dimension`)
    "juridico": "jurídico", "documental": "documental", "ocupacion": "ocupación",
    "urbanistico": "urbanístico", "tecnico": "técnico", "financiero": "financiero",
    "comercial": "comercial", "liquidez": "liquidez", "mercado": "mercado",
    # Niveles y bandas de riesgo
    "bajo": "bajo", "medio": "medio", "alto": "alto", "muy_alto": "muy alto", "critico": "crítico",
    # Dominancia del riesgo agregado (`riesgos.dominancia`)
    "una_alta": "una dimensión alta", "dos_altas": "dos dimensiones altas",
    "critica_mitigable": "una dimensión crítica mitigable",
    "critica_no_mitigable": "una dimensión crítica no mitigable",
    # Partidas de los costes fijos (M06)
    "reforma": "Reforma", "ocupacion_desalojo": "Ocupación y desalojo",
    "atrasos_comunidad_ibi": "Atrasos de comunidad e IBI", "adquisicion_fija": "Costes fijos de adquisición",
    "tenencia": "Tenencia", "comercializacion": "Comercialización", "contingencia": "Contingencia",
    "cargas_subsistentes": "Cargas subsistentes", "plusvalia_municipal": "Plusvalía municipal",
    # Método de valoración (M03)
    "comparables_ajustados": "comparables ajustados", "sin_comparables": "sin comparables",
    # Fuentes de subasta
    "judicial_boe": "judicial (Portal de Subastas del BOE)", "aeat": "de la Agencia Tributaria (AEAT)",
    "tgss": "de la Seguridad Social (TGSS)", "concursal": "concursal", "banco": "bancaria",
    "notarial": "notarial", "privada": "privada",
    # Estados de ocupación
    "desconocida": "no consta", "vacio": "vacío", "propietario": "ocupada por el propietario",
    "precario": "precario", "arrendado_posterior": "arrendado (contrato posterior)",
    "arrendado_anterior": "arrendado (contrato anterior)", "renta_antigua": "renta antigua",
    # Documentación (carencias del ICI)
    "nota_simple": "nota simple", "cert_cargas": "certificación de cargas",
    "posesion_verificada": "posesión verificada", "avaluo": "avalúo",
    "fotos_interior_o_visita": "fotos interiores o visita", "fotos_exterior": "fotos exteriores",
    "cert_comunidad": "certificado de la comunidad", "recibo_ibi": "recibo del IBI",
    "ite_cee": "ITE y certificado energético", "catastro_conciliado": "Catastro conciliado",
    # Categorías de reglas T2
    "veto": "veto", "semaforo": "semáforo", "puja": "puja",
    # Origen de la base imponible (fiscal.py)
    "precio_pagado": "precio pagado", "valor_referencia": "valor de referencia",
    "valor_declarado": "valor declarado",
}

# Token candidato: palabra (latina o griega) con al menos una barra baja, sin letra, cifra
# ni barra baja pegada a los lados.
_TOKEN = re.compile(r"(?<![\w])([^\W\d_][^\W_]*(?:_[^\W_]+)+)(?![\w])")


def etiqueta(codigo: str | None) -> str:
    """Nombre legible de un código; el propio código si no está en el diccionario."""
    if codigo is None:
        return ""
    return ETIQUETAS.get(codigo, codigo)


def legible(texto: str) -> str:
    """Sustituye en un texto los símbolos y códigos con barra baja por su nombre.
    Las palabras sueltas sin barra baja NO se tocan: «reforma» o «medio» también son
    palabras normales de una frase; para esas, `etiqueta` en el punto que las redacta."""
    def cambio(m: re.Match[str]) -> str:
        t = m.group(1)
        return SIMBOLOS.get(t) or ETIQUETAS.get(t) or t
    return _TOKEN.sub(cambio, texto)
