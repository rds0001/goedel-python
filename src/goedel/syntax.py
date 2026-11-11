"""Finite first-order syntax with explicit binders and exact byte numbering."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

MAX_DEPTH = 64
MAX_NODES = 1000
MAX_SERIALIZED_BYTES = 65536
MAX_CODE_BYTES = 1024
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")
TERMS = frozenset({"var", "const", "func", "num"})
FORMULAS = frozenset({"pred", "eq", "not", "and", "or", "implies", "forall", "exists", "bottom"})
BINDERS = frozenset({"forall", "exists"})


class GoedelError(ValueError):
    """A structured input or resource error; ``code`` identifies its category."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _error(message: str, code: str = "INVALID_INPUT") -> None:
    raise GoedelError(code, message)


def _name(name: Any) -> str:
    if not isinstance(name, str) or NAME.fullmatch(name) is None:
        _error("Names must match [A-Za-z][A-Za-z0-9_]* and contain at most 64 ASCII characters")
    return name


@dataclass(frozen=True, slots=True)
class Expr:
    """Immutable typed expression. Prefer the named constructors."""

    kind: str
    name: str = ""
    args: tuple[Expr, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.args, tuple):
            _error("Expr.args must be a tuple")
        _validate(self)


def _validate(expr: Any) -> None:
    arities: dict[tuple[str, str], int] = {}
    count = 0
    active: set[int] = set()

    def walk(node: Any, depth: int) -> str:
        nonlocal count
        count += 1
        if depth > MAX_DEPTH or count > MAX_NODES:
            _error("Expression depth or node budget exceeded", "RESOURCE_LIMIT")
        if not isinstance(node, Expr):
            _error("An Expr is required")
        if id(node) in active:
            _error("Cyclic expression")
        active.add(id(node))
        if not isinstance(node.kind, str) or node.kind not in TERMS | FORMULAS:
            _error("Unknown expression kind")
        if not isinstance(node.args, tuple):
            _error("Expression arguments must be a tuple")
        if node.kind == "num":
            if not isinstance(node.name, str) or re.fullmatch(r"0|[1-9][0-9]*", node.name) is None:
                _error("Numerals require canonical nonnegative decimal text")
            if len(node.name) > 4096:
                _error("Numeral digit budget exceeded", "RESOURCE_LIMIT")
        elif node.kind in {"var", "const", "func", "pred"} | BINDERS:
            _name(node.name)
        elif node.name != "":
            _error("Logical node name must be empty")
        arity = len(node.args)
        expected = {"var": 0, "const": 0, "num": 0, "eq": 2, "not": 1, "and": 2,
                    "or": 2, "implies": 2, "forall": 1, "exists": 1, "bottom": 0}
        if node.kind in expected and arity != expected[node.kind]:
            _error("Incorrect expression arity")
        if node.kind in {"func", "pred"}:
            key = (node.kind, node.name)
            if key in arities and arities[key] != arity:
                _error("Inconsistent symbol arity")
            arities[key] = arity
        children = [walk(child, depth + 1) for child in node.args]
        expected_types = TERMS if node.kind in {"func", "pred", "eq"} else FORMULAS
        if any(child not in expected_types for child in children):
            _error("Term/formula position mismatch")
        active.remove(id(node))
        return node.kind

    walk(expr, 1)
    payload = json.dumps(_wire(expr), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    if len(payload.encode("utf-8")) > MAX_SERIALIZED_BYTES:
        _error("Serialized expression byte budget exceeded", "RESOURCE_LIMIT")


def _expr(value: Any) -> Expr:
    if isinstance(value, Expr):
        _validate(value)
        return value
    return _from_wire(value)


def _from_wire(value: Any) -> Expr:
    active: set[int] = set()
    count = 0

    def walk(node: Any, depth: int) -> Expr:
        nonlocal count
        count += 1
        if depth > MAX_DEPTH or count > MAX_NODES:
            _error("Expression depth or node budget exceeded", "RESOURCE_LIMIT")
        if not isinstance(node, dict) or set(node) != {"args", "kind", "name"}:
            _error("Wire nodes require exactly args, kind and name")
        if id(node) in active:
            _error("Cyclic expression")
        if not isinstance(node["args"], list):
            _error("Wire args must be an array")
        active.add(id(node))
        children = tuple(walk(arg, depth + 1) for arg in node["args"])
        active.remove(id(node))
        return Expr(node["kind"], node["name"], children)

    return walk(value, 1)


def _wire(expr: Expr) -> dict[str, Any]:
    return {"args": [_wire(a) for a in expr.args], "kind": expr.kind, "name": expr.name}


def validate_expr(expr: Expr | dict[str, Any]) -> bool:
    """Validate a complete expression, including cross-node arities and hard limits."""
    _expr(expr)
    return True


def variable(name: str) -> Expr:
    """Construct a free variable occurrence; binding is determined by its parents."""
    return Expr("var", name)


def constant(name: str) -> Expr:
    """Construct a named constant term without asserting an interpretation."""
    return Expr("const", name)


def _arguments(args: list[Expr] | tuple[Expr, ...]) -> tuple[Expr, ...]:
    if not isinstance(args, (list, tuple)):
        _error("Arguments must be a list or tuple")
    return tuple(_expr(a) for a in args)


def function_term(name: str, args: list[Expr] | tuple[Expr, ...] = ()) -> Expr:
    """Construct a function-symbol application to terms."""
    return Expr("func", name, _arguments(args))


def predicate(name: str, args: list[Expr] | tuple[Expr, ...] = ()) -> Expr:
    """Construct an atomic formula, allowing nullary predicates."""
    return Expr("pred", name, _arguments(args))


def equal(left: Expr, right: Expr) -> Expr:
    """Construct equality of two terms, without deciding it."""
    return Expr("eq", "", (_expr(left), _expr(right)))


def negate(formula: Expr) -> Expr:
    """Construct negation of a formula."""
    return Expr("not", "", (_expr(formula),))


def conjunction(left: Expr, right: Expr) -> Expr:
    """Construct a binary conjunction."""
    return Expr("and", "", (_expr(left), _expr(right)))


def disjunction(left: Expr, right: Expr) -> Expr:
    """Construct a binary disjunction."""
    return Expr("or", "", (_expr(left), _expr(right)))


def implication(left: Expr, right: Expr) -> Expr:
    """Construct a binary implication."""
    return Expr("implies", "", (_expr(left), _expr(right)))


def forall(variable: str, body: Expr) -> Expr:
    """Universally bind a named variable in a formula."""
    return Expr("forall", variable, (_expr(body),))


def exists(variable: str, body: Expr) -> Expr:
    """Existentially bind a named variable in a formula."""
    return Expr("exists", variable, (_expr(body),))


def bottom() -> Expr:
    """Construct the falsum formula, not a proof of a contradiction."""
    return Expr("bottom")


def _free(expr: Expr, bound: frozenset[str] = frozenset()) -> set[str]:
    if expr.kind == "var":
        return set() if expr.name in bound else {expr.name}
    if expr.kind in BINDERS:
        bound = bound | {expr.name}
    result: set[str] = set()
    for arg in expr.args:
        result.update(_free(arg, bound))
    return result


def free_variables(expr: Expr) -> list[str]:
    """Return sorted distinct free variable names."""
    return sorted(_free(_expr(expr)))


def _all_names(expr: Expr) -> set[str]:
    return ({expr.name} if expr.name else set()).union(*(_all_names(a) for a in expr.args))


def bound_variables(expr: Expr) -> list[str]:
    """Return sorted distinct names appearing in quantifier binders."""
    node = _expr(expr)
    result: set[str] = set()

    def walk(e: Expr) -> None:
        if e.kind in BINDERS:
            result.add(e.name)
        for a in e.args:
            walk(a)

    walk(node)
    return sorted(result)


def substitute(expr: Expr, variable: str, term: Expr) -> Expr:
    """Capture-avoiding substitution for free occurrences with deterministic renaming."""
    node, replacement = _expr(expr), _expr(term)
    _name(variable)
    if replacement.kind not in TERMS:
        _error("Substitution requires a term")
    forbidden = _all_names(node) | _all_names(replacement) | {variable}
    replacement_free = _free(replacement)
    next_index = 0

    def fresh() -> str:
        nonlocal next_index
        while f"v{next_index}" in forbidden:
            next_index += 1
        name = f"v{next_index}"
        forbidden.add(name)
        next_index += 1
        return name

    def rename(e: Expr, old: str, new: str) -> Expr:
        if e.kind == "var" and e.name == old:
            return Expr("var", new)
        if e.kind in BINDERS and e.name == old:
            return e
        return Expr(e.kind, e.name, tuple(rename(a, old, new) for a in e.args))

    def walk(e: Expr) -> Expr:
        if e.kind == "var":
            return replacement if e.name == variable else e
        if e.kind in BINDERS:
            if e.name == variable:
                return e
            body = e.args[0]
            if variable not in _free(body):
                return e
            binder = e.name
            if binder in replacement_free:
                new_name = fresh()
                body = rename(body, binder, new_name)
                binder = new_name
            return Expr(e.kind, binder, (walk(body),))
        return Expr(e.kind, e.name, tuple(walk(a) for a in e.args))

    return walk(node)


def normalize(expr: Expr) -> Expr:
    """Canonical alpha-renaming of bound variables, preserving free names."""
    node = _expr(expr)
    forbidden = _free(node)
    next_index = 0

    def walk(e: Expr, environment: dict[str, str]) -> Expr:
        nonlocal next_index
        if e.kind == "var":
            return Expr("var", environment.get(e.name, e.name))
        if e.kind in BINDERS:
            while f"v{next_index}" in forbidden:
                next_index += 1
            binder = f"v{next_index}"
            next_index += 1
            return Expr(e.kind, binder, (walk(e.args[0], {**environment, e.name: binder}),))
        return Expr(e.kind, e.name, tuple(walk(a, environment) for a in e.args))

    return walk(node, {})


def alpha_equal(left: Expr, right: Expr) -> bool:
    """Compare bound-variable renamings only; not semantic equivalence."""
    return normalize(left) == normalize(right)


def serialize(expr: Expr) -> str:
    """Canonical compact ASCII JSON, with keys args, kind, name in that order."""
    text = json.dumps(_wire(_expr(expr)), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    if len(text.encode("utf-8")) > MAX_SERIALIZED_BYTES:
        _error("Serialized expression byte budget exceeded", "RESOURCE_LIMIT")
    return text


def deserialize(text: str) -> Expr:
    """Parse a wire expression without eval, rejecting duplicate fields."""
    if not isinstance(text, str):
        _error("Serialized expression must be text")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeError:
        _error("Invalid Unicode input")
    if size > MAX_SERIALIZED_BYTES:
        _error("Serialized expression byte budget exceeded", "RESOURCE_LIMIT")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [key for key, _ in items]
        if len(keys) != len(set(keys)):
            _error("Duplicate JSON keys")
        return dict(items)

    try:
        value = json.loads(text, object_pairs_hook=pairs)
    except (ValueError, TypeError) as exc:
        if isinstance(exc, GoedelError):
            raise
        _error("Malformed JSON")
    except RecursionError:
        _error("JSON nesting exceeds resource limit", "RESOURCE_LIMIT")
    return _from_wire(value)


def fingerprint(expr: Expr) -> str:
    """SHA-256 of canonical bytes; distinct alpha-equivalent syntax may hash differently."""
    return hashlib.sha256(serialize(expr).encode("utf-8")).hexdigest()


def numbering() -> dict[str, Any]:
    """Describe the exact, versioned finite byte numbering used by encode/decode."""
    return {"id": "goedel-json-byte-v1", "version": "1.0", "max_bytes": MAX_CODE_BYTES,
            "description": "Sentinel-prefixed base-256 canonical JSON bytes; exact decimal string."}


def encode(expr: Expr) -> str:
    """Inject canonical syntax bytes into a positive integer, returned as decimal text."""
    data = serialize(expr).encode("utf-8")
    if len(data) > MAX_CODE_BYTES:
        _error("Numbering byte budget exceeded", "RESOURCE_LIMIT")
    return str(int.from_bytes(b"\x01" + data, "big"))


def decode(code: str) -> Expr:
    """Invert encode, rejecting noncanonical codes and codes outside its image."""
    if not isinstance(code, str) or re.fullmatch(r"[1-9][0-9]*", code) is None:
        _error("Code must be canonical positive decimal text")
    if len(code) > 2500:
        _error("Numbering digit budget exceeded", "RESOURCE_LIMIT")
    number = int(code)
    payload = number.to_bytes((number.bit_length() + 7) // 8, "big")
    if len(payload) > MAX_CODE_BYTES + 1:
        _error("Numbering byte budget exceeded", "RESOURCE_LIMIT")
    if payload[0] != 1:
        _error("Missing numbering sentinel")
    try:
        text = payload[1:].decode("utf-8")
    except UnicodeError:
        _error("Numbering payload is not UTF-8")
    expr = deserialize(text)
    if serialize(expr) != text:
        _error("Numbering payload is not canonical syntax")
    return expr
