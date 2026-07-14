"""T2 — Motor de reglas determinista (§8.2).

Reglas declarativas (dict/YAML) → encadenamiento hacia delante por prioridades
sobre la pizarra de hechos, con trazabilidad de cada disparo (P1, P2).

Expresiones numéricas: subconjunto seguro de Python evaluado sobre el AST con
lista blanca de nodos (números, identificadores → hechos, + − × ÷ y paréntesis).
Jamás se usa eval().
"""
from __future__ import annotations

import ast
import operator as op
from dataclasses import dataclass, field
from typing import Any

_BINOPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv}
_UNARY = {ast.USub: op.neg, ast.UAdd: op.pos}


class ExpresionInsegura(ValueError):
    pass


def _nombre_atributo(node: ast.AST) -> str:
    """Reconstruye 'riesgo.ocupacion.score' desde una cadena de Attribute/Name."""
    partes: list[str] = []
    while isinstance(node, ast.Attribute):
        partes.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        partes.append(node.id)
        return ".".join(reversed(partes))
    raise ExpresionInsegura("identificador no válido en expresión")


def eval_expr(expr: str, hechos: dict[str, Any]) -> float:
    """Evalúa una expresión numérica segura contra la pizarra de hechos."""
    try:
        arbol = ast.parse(expr, mode="eval")
    except SyntaxError as e:                     # pragma: no cover
        raise ExpresionInsegura(f"sintaxis inválida: {expr}") from e

    def _ev(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return _ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, (ast.Name, ast.Attribute)):
            clave = _nombre_atributo(n)
            if clave not in hechos:
                raise KeyError(f"hecho no disponible en expresión: {clave}")
            return float(hechos[clave])
        if isinstance(n, ast.BinOp) and type(n.op) in _BINOPS:
            return _BINOPS[type(n.op)](_ev(n.left), _ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _UNARY:
            return _UNARY[type(n.op)](_ev(n.operand))
        raise ExpresionInsegura(f"nodo no permitido: {type(n).__name__}")

    return _ev(arbol)


_OPS = {
    ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b, "!=": lambda a, b: a != b,
    "in": lambda a, b: a in b, "not_in": lambda a, b: a not in b,
    "is_true": lambda a, b: bool(a) is True, "is_false": lambda a, b: bool(a) is False,
}


@dataclass
class Disparo:
    codigo: str
    version: str
    categoria: str
    efecto: dict
    evidencias: list[str] = field(default_factory=list)


class RuleEngine:
    """Evalúa un catálogo de reglas contra la pizarra. Determinista: orden estable
    por (prioridad, código); iteración hasta punto fijo (máx. 6 pasadas)."""

    def __init__(self, reglas: list[dict]):
        self.reglas = sorted(reglas, key=lambda r: (int(r.get("prioridad", 100)), r["codigo"]))

    # ── condiciones ──────────────────────────────────────────────────────
    def _condicion_ok(self, cond: dict, hechos: dict) -> bool:
        clave = cond["hecho"]
        if clave not in hechos:
            return False                                  # P4: hecho ausente ⇒ la condición no afirma
        actual = hechos[clave]
        operador = cond.get("op", "==")
        if operador not in _OPS:
            raise ExpresionInsegura(f"operador no permitido: {operador}")
        if "expr" in cond:
            objetivo: Any = eval_expr(cond["expr"], hechos)
        else:
            objetivo = cond.get("valor")
        if operador in (">", ">=", "<", "<="):
            try:
                return _OPS[operador](float(actual), float(objetivo))
            except (TypeError, ValueError):
                return False
        return _OPS[operador](actual, objetivo)

    def _bloque_ok(self, cuando: dict, hechos: dict) -> bool:
        if "all" in cuando:
            return all(self._condicion_ok(c, hechos) for c in cuando["all"])
        if "any" in cuando:
            return any(self._condicion_ok(c, hechos) for c in cuando["any"])
        raise ValueError("bloque 'cuando' debe contener all/any")

    # ── evaluación ───────────────────────────────────────────────────────
    def evaluar(self, hechos: dict[str, Any]) -> list[Disparo]:
        disparos: list[Disparo] = []
        disparadas: set[str] = set()
        for _ in range(6):                                # punto fijo acotado
            nuevo = False
            for r in self.reglas:
                if r["codigo"] in disparadas:
                    continue
                if not self._bloque_ok(r["cuando"], hechos):
                    continue
                efecto = dict(r.get("efecto", {}))
                # efectos que afirman hechos: literal o {"expr": "..."} resuelto ahora
                if "hechos" in efecto:
                    for k, v in efecto["hechos"].items():
                        if isinstance(v, dict) and "expr" in v:
                            hechos[k] = eval_expr(v["expr"], hechos)
                        else:
                            hechos[k] = v
                disparos.append(Disparo(
                    codigo=r["codigo"], version=str(r.get("version", "dev")),
                    categoria=r.get("categoria", "regla"), efecto=efecto,
                    evidencias=list(r.get("evidencias", [])),
                ))
                disparadas.add(r["codigo"])
                nuevo = True
            if not nuevo:
                break
        return disparos
