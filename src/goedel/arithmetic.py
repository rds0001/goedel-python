"""Concrete arithmetic syntax, compact numerals, Q and the PA induction schema.

Numeral nodes abbreviate the documented binary Horner term. They are never
uninterpreted numeric constants or assertions about a theory's consistency.
"""

from __future__ import annotations

import re
from typing import Any

from .syntax import (
    BINDERS,
    FORMULAS,
    TERMS,
    Expr,
    _error,
    _expr,
    _free,
    _name,
    _wire,
    alpha_equal,
    conjunction,
    constant,
    equal,
    exists,
    forall,
    function_term,
    implication,
    negate,
    substitute,
    variable,
)


def arithmetic_language() -> dict[str, Any]:
    """Return the versioned first-order arithmetic signature and numeral convention."""
    return {
        "id": "goedel-arithmetic-v1",
        "constants": ["zero"],
        "functions": [{"name": "S", "arity": 1}, {"name": "add", "arity": 2}, {"name": "mul", "arity": 2}],
        "relations": [],
        "equality": True,
        "numerals": "binary-horner-v1",
    }


def zero() -> Expr:
    """Construct the arithmetic zero symbol."""
    return constant("zero")


def successor(term: Expr) -> Expr:
    """Construct the arithmetic successor term S(term)."""
    return function_term("S", [term])


def add(left: Expr, right: Expr) -> Expr:
    """Construct arithmetic addition, without evaluating it."""
    return function_term("add", [left, right])


def multiply(left: Expr, right: Expr) -> Expr:
    """Construct arithmetic multiplication, without evaluating it."""
    return function_term("mul", [left, right])


def numeral(value: str | int) -> Expr:
    """Construct an exact compact numeral from decimal text or a Python integer."""
    if type(value) is int:
        if value < 0:
            _error("Numerals are nonnegative")
        if value.bit_length() > 13607:
            _error("Numeral digit budget exceeded", "RESOURCE_LIMIT")
        value = str(value)
    if not isinstance(value, str):
        _error("Numeral value must be canonical decimal text or an integer")
    return Expr("num", value)


def _arithmetic(expr: Expr) -> Expr:
    node = _expr(expr)

    def walk(e: Expr) -> None:
        if e.kind == "const" and e.name != "zero":
            _error("Foreign constant in arithmetic signature")
        if e.kind == "func" and {"S": 1, "add": 2, "mul": 2}.get(e.name) != len(e.args):
            _error("Foreign function or arity in arithmetic signature")
        if e.kind == "pred":
            _error("Arithmetic signature has equality and no predicate symbols")
        for arg in e.args:
            walk(arg)

    walk(node)
    return node


def numeral_value(term: Expr) -> str:
    """Evaluate a closed arithmetic term in the natural numbers, exactly.

    This finite term evaluation does not decide quantified arithmetic truth.
    The returned value has at most 4096 decimal digits.
    """
    node = _arithmetic(term)
    if node.kind not in TERMS or _free(node):
        _error("A closed arithmetic term is required")

    def walk(e: Expr) -> int:
        if e.kind == "num":
            value = int(e.name)
        elif e.kind == "const":
            value = 0
        else:
            args = [walk(arg) for arg in e.args]
            value = args[0] + 1 if e.name == "S" else (sum(args) if e.name == "add" else args[0] * args[1])
        if value.bit_length() > 13607:
            _error("Arithmetic value budget exceeded", "RESOURCE_LIMIT")
        return value

    result = str(walk(node))
    if len(result) > 4096:
        _error("Arithmetic value budget exceeded", "RESOURCE_LIMIT")
    return result


def expand_numeral(term: Expr, max_nodes: int = 1000) -> Expr:
    """Replace numeral abbreviations by actual binary Horner arithmetic terms.

    nu(0)=0, nu(1)=S0, nu(2k)=2*nu(k), nu(2k+1)=S(2*nu(k)).
    Existing expression depth and node limits still apply.
    """
    if type(max_nodes) is not int or not 1 <= max_nodes <= 1000:
        _error("max_nodes must be an integer from 1 to 1000")
    node = _expr(term)
    used = 0

    def reserve(amount: int) -> None:
        nonlocal used
        used += amount
        if used > max_nodes:
            _error("Numeral expansion budget exceeded", "RESOURCE_LIMIT")

    def build(n: int) -> Expr:
        if n == 0:
            reserve(1)
            return zero()
        reserve(2)
        result = successor(zero())
        for bit in bin(n)[3:]:
            reserve(4 + (bit == "1"))
            result = multiply(successor(successor(zero())), result)
            if bit == "1":
                result = successor(result)
        return result

    def walk(e: Expr) -> Expr:
        if e.kind == "num":
            return build(int(e.name))
        reserve(1)
        return Expr(e.kind, e.name, tuple(walk(a) for a in e.args))

    return walk(node)


def q_axioms() -> list[Expr]:
    """Return the seven closed Robinson-Q axioms in the documented Q1--Q7 order."""
    x, y = variable("x"), variable("y")
    return [
        forall("x", negate(equal(successor(x), zero()))),
        forall("x", forall("y", implication(equal(successor(x), successor(y)), equal(x, y)))),
        forall("x", implication(negate(equal(x, zero())), exists("y", equal(x, successor(y))))),
        forall("x", equal(add(x, zero()), x)),
        forall("x", forall("y", equal(add(x, successor(y)), successor(add(x, y))))),
        forall("x", equal(multiply(x, zero()), zero())),
        forall("x", forall("y", equal(multiply(x, successor(y)), add(multiply(x, y), x)))),
    ]


def induction_axiom(body: Expr, variable: str, close: bool = True) -> Expr:
    """Construct a PA induction instance, optionally closing all free parameters."""
    node = _arithmetic(body)
    _name(variable)
    if node.kind not in FORMULAS or type(close) is not bool:
        _error("Induction requires an arithmetic formula and a boolean close flag")
    base = substitute(node, variable, zero())
    step = forall(variable, implication(node, substitute(node, variable, successor(Expr("var", variable)))))
    result = implication(conjunction(base, step), forall(variable, node))
    if close:
        for parameter in reversed(sorted(_free(node) - {variable})):
            result = forall(parameter, result)
    return result


def recognize_induction(formula: Expr) -> dict[str, Any]:
    """Recognize exact PA induction syntax up to bound-variable renaming.

    Open instances and full universal closures are recognized. Axiom membership
    additionally requires closure; malformed or foreign syntax is rejected.
    """
    node = _arithmetic(formula)
    if node.kind not in FORMULAS:
        _error("An arithmetic formula is required")
    missing = {"is_instance": False, "variable": None, "body": None, "parameters": []}
    outer: list[str] = []
    core = node
    while core.kind == "forall":
        outer.append(core.name)
        core = core.args[0]
    if core.kind != "implies" or core.args[1].kind != "forall":
        return missing
    binder, body = core.args[1].name, core.args[1].args[0]
    parameters = sorted(_free(body) - {binder})
    if outer and (len(set(outer)) != len(outer) or set(outer) != set(parameters)):
        return missing
    if not alpha_equal(core, induction_axiom(body, binder, close=False)):
        return missing
    return {"is_instance": True, "variable": binder, "body": _wire(body), "parameters": parameters}


def arithmetic_theory(name: str = "PA", extensions: list[Expr] | tuple[Expr, ...] = ()) -> dict[str, Any]:
    """Describe executable Q or PA axiom membership plus explicit closed extensions.

    PA uses all seven Q axioms plus induction; the predecessor axiom is redundant
    in this presentation. Extensions are declared axioms, not proved conclusions.
    """
    if not isinstance(name, str) or name not in {"Q", "PA"} or not isinstance(extensions, (list, tuple)):
        _error("Theory must be Q or PA, with a list of closed arithmetic extensions")
    extra = [_arithmetic(e) for e in extensions]
    if any(e.kind not in FORMULAS or _free(e) for e in extra):
        _error("Extensions must be closed arithmetic formulas")
    if len(extra) > 256:
        _error("Theory extension budget exceeded", "RESOURCE_LIMIT")
    if any(alpha_equal(e, prior) for i, e in enumerate(extra) for prior in extra[:i]):
        _error("Duplicate theory extension")
    return {
        "id": name,
        "version": "1.0",
        "signature": arithmetic_language(),
        "logic": "CLASSICAL_FOL_EQUALITY",
        "axioms": [_wire(a) for a in q_axioms()],
        "schemas": ["PA_INDUCTION"] if name == "PA" else [],
        "presentation": {"kind": "DECIDABLE", "id": f"goedel-{name}-v1"},
        "extensions": [_wire(e) for e in extra],
        "consistency_status": "NOT_ESTABLISHED",
    }


def is_axiom(theory: dict[str, Any], formula: Expr) -> bool:
    """Decide membership in the declared built-in arithmetic axiom presentation."""
    if not isinstance(theory, dict) or not isinstance(theory.get("id"), str) or theory["id"] not in {"Q", "PA"}:
        _error("A built-in arithmetic theory is required")
    expected = arithmetic_theory(theory["id"], theory.get("extensions", []))
    if theory != expected:
        _error("Theory presentation was modified or has an unknown version")
    node = _arithmetic(formula)
    if node.kind not in FORMULAS:
        _error("A formula is required")
    if _free(node):
        return False
    if any(alpha_equal(node, a) for a in expected["axioms"] + expected["extensions"]):
        return True
    return theory["id"] == "PA" and recognize_induction(node)["is_instance"]


_TOKEN = re.compile(r"\s*(->|[A-Za-z][A-Za-z0-9_]*|0|[1-9][0-9]*|[@(),.=!&|+*])")


def parse_formula(text: str) -> Expr:
    """Parse documented ASCII first-order notation without executing input text."""
    if not isinstance(text, str):
        _error("Formula text must be a string")
    if len(text) > 65536:
        _error("Parser input budget exceeded", "RESOURCE_LIMIT")
    tokens: list[str] = []
    position = 0
    while position < len(text):
        if text[position:].isspace():
            break
        match = _TOKEN.match(text, position)
        if match is None:
            _error("Unrecognized formula token")
        tokens.append(match[1])
        position = match.end()
    if len(tokens) > 5000:
        _error("Parser token budget exceeded", "RESOURCE_LIMIT")
    index = 0

    def peek() -> str:
        return tokens[index] if index < len(tokens) else ""

    def take(token: str | None = None) -> str:
        nonlocal index
        value = peek()
        if not value or (token is not None and value != token):
            _error("Unexpected formula token")
        index += 1
        return value

    def term(level: int = 0) -> Expr:
        if level == 0:
            result = term(1)
            while peek() == "+":
                take()
                result = add(result, term(1))
            return result
        if level == 1:
            result = term(2)
            while peek() == "*":
                take()
                result = multiply(result, term(2))
            return result
        value = take()
        if value == "(":
            result = term()
            take(")")
            return result
        if value == "@":
            return constant(take())
        if value.isdecimal():
            return numeral(value)
        _name(value)
        if peek() != "(":
            return variable(value)
        take("(")
        args: list[Expr] = []
        if peek() != ")":
            args.append(term())
            while peek() == ",":
                take()
                args.append(term())
        take(")")
        return function_term(value, args)

    def formula(level: int = 0) -> Expr:
        nonlocal index
        if level < 3:
            op = ("->", "|", "&")[level]
            kind = ("implies", "or", "and")[level]
            result = formula(level + 1)
            while peek() == op:
                take()
                result = Expr(kind, "", (result, formula(level if level == 0 else level + 1)))
            return result
        if peek() == "!":
            take()
            return negate(formula(3))
        if peek() in {"forall", "exists"} and index + 2 < len(tokens) and tokens[index + 2] == ".":
            binder, name = take(), take()
            take(".")
            return Expr(binder, _name(name), (formula(),))
        if peek() == "false" and (index + 1 == len(tokens) or tokens[index + 1] not in {"(", "="}):
            take()
            return Expr("bottom")
        start = index
        if peek() == "(":
            try:
                left = term()
                if peek() == "=":
                    take()
                    return equal(left, term())
            except ValueError as exc:
                if getattr(exc, "code", None) == "RESOURCE_LIMIT":
                    raise
            index = start
            take("(")
            result = formula()
            take(")")
            return result
        start = index
        left = term()
        if peek() == "=":
            take()
            return equal(left, term())
        if left.kind == "var":
            return Expr("pred", left.name)
        if left.kind == "func" and tokens[start] == left.name and start + 1 < len(tokens) and tokens[start + 1] == "(":
            depth = 0
            closing = None
            for cursor in range(start + 1, index):
                depth += tokens[cursor] == "("
                depth -= tokens[cursor] == ")"
                if depth == 0:
                    closing = cursor
                    break
            if closing == index - 1:
                return Expr("pred", left.name, left.args)
        _error("A formula requires equality or a predicate")

    try:
        result = formula()
    except RecursionError:
        _error("Parser nesting budget exceeded", "RESOURCE_LIMIT")
    if index != len(tokens):
        _error("Trailing formula tokens")
    return result


def format_formula(expr: Expr) -> str:
    """Format a formula as deterministic ASCII notation accepted by parse_formula."""
    node = _expr(expr)
    if node.kind not in FORMULAS:
        _error("A formula is required")

    def walk(e: Expr) -> str:
        if e.kind in {"var", "num"}:
            return e.name
        if e.kind == "const":
            return "@" + e.name
        args = [walk(a) for a in e.args]
        if e.kind == "func" and e.name in {"add", "mul"} and len(args) == 2:
            return f"({args[0]} {'+' if e.name == 'add' else '*'} {args[1]})"
        if e.kind in {"func", "pred"}:
            return e.name + "(" + ",".join(args) + ")"
        if e.kind == "bottom":
            return "false"
        if e.kind in BINDERS:
            return f"({e.kind} {e.name}. {args[0]})"
        if e.kind == "not":
            return "!(" + args[0] + ")"
        operator = {"eq": "=", "and": "&", "or": "|", "implies": "->"}[e.kind]
        return f"({args[0]} {operator} {args[1]})"

    return walk(node)
