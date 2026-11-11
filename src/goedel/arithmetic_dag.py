"""Explicit arithmetic formula DAGs and presentation-sensitive natural codes.

Sharing denotes repeated literal subexpressions. It never introduces an oracle,
and lexical binding is still determined by the enclosing quantifier path.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .arithmetic import _arithmetic
from .sequence import _decimal, _nat, _natural_text, sequence_decode, sequence_encode
from .syntax import Expr, GoedelError, _error

DAG_ID = "goedel-arithmetic-dag-v1"
TAGS = [
    "num",
    "var",
    "zero",
    "succ",
    "add",
    "mul",
    "eq",
    "not",
    "and",
    "or",
    "implies",
    "forall",
    "exists",
    "bottom",
]
_ARITY = {
    "num": 0,
    "var": 0,
    "zero": 0,
    "succ": 1,
    "add": 2,
    "mul": 2,
    "eq": 2,
    "not": 1,
    "and": 2,
    "or": 2,
    "implies": 2,
    "forall": 1,
    "exists": 1,
    "bottom": 0,
    "lt": 2,
    "bexists": 2,
    "bforall": 2,
}
_TERMS = {"num", "var", "zero", "succ", "add", "mul"}
_NAMED = {"var", "forall", "exists", "bforall", "bexists"}
MAX_DAG_NODES = 200000


def _variable_index(name: Any) -> int:
    if not isinstance(name, str) or re.fullmatch(r"x(?:0|[1-9][0-9]*)", name) is None:
        _error("DAG variable names must be x followed by a canonical natural number")
    return _nat(name[1:], 4096)


def _dag_info(dag: dict[str, Any], bounded: bool = False, formula: bool = False) -> dict[str, Any]:
    """Validate topological arithmetic syntax and return exact expansion statistics.

    The root is the final node and must be a formula. The bounded profile also
    permits the explicit definitional macros lt, bexists and bforall. Numeric
    indices avoid name-dependent alpha-normalization or hidden renumbering.
    """
    if type(bounded) is not bool:
        _error("bounded must be boolean")
    if (
        not isinstance(dag, dict)
        or set(dag) != {"schema_version", "nodes", "root"}
        or dag["schema_version"] != "1.0"
    ):
        _error("Unknown arithmetic DAG schema")
    nodes = dag["nodes"]
    if not isinstance(nodes, list) or not nodes:
        _error("DAG must have a nonempty node array")
    if len(nodes) > MAX_DAG_NODES:
        _error("Arithmetic DAG node budget exceeded", "RESOURCE_LIMIT")
    if type(dag["root"]) is not int or dag["root"] != len(nodes) - 1:
        _error("DAG root must be the final node")
    allowed = set(TAGS) | ({"lt", "bexists", "bforall"} if bounded else set())
    sorts, counts, free = [], [], []
    name_bits: dict[str, int] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict) or set(node) != {"op", "name", "args"}:
            _error("DAG nodes require exactly op, name and args")
        op, name, args = node["op"], node["name"], node["args"]
        if (
            not isinstance(op, str)
            or op not in allowed
            or not isinstance(args, list)
            or len(args) != _ARITY[op]
        ):
            _error("DAG operation or arity mismatch")
        if any(type(a) is not int or not 0 <= a < index for a in args):
            _error("DAG references must point to earlier nodes")
        if op in _NAMED:
            _variable_index(name)
            if name not in name_bits:
                if len(name_bits) == 4096:
                    _error("DAG variable inventory budget exceeded", "RESOURCE_LIMIT")
                name_bits[name] = 1 << len(name_bits)
        elif op == "num":
            _natural_text(name)
        elif name != "":
            _error("Only variables, binders and numerals carry names")
        expected = (
            ["term"] * len(args)
            if op in {"succ", "add", "mul", "eq", "lt"}
            else ["term", "formula"]
            if op in {"bexists", "bforall"}
            else ["formula"] * len(args)
        )
        if [sorts[a] for a in args] != expected:
            _error("DAG term/formula sort mismatch")
        sorts.append("term" if op in _TERMS else "formula")
        variables = 0
        for arg in args:
            variables |= free[arg]
        if op == "var":
            variables |= name_bits[name]
        elif op in {"forall", "exists"}:
            variables &= ~name_bits[name]
        elif op in {"bforall", "bexists"}:
            if free[args[0]] & name_bits[name]:
                _error("Bound variable occurs in its own bound")
            variables &= ~name_bits[name]
        free.append(variables)
        count = 1 + sum(counts[a] for a in args)
        if count.bit_length() > 16384:
            _error("DAG expansion-count budget exceeded", "RESOURCE_LIMIT")
        counts.append(count)
    if formula and sorts[-1] != "formula":
        _error("DAG root must be a formula")
    return {
        "statistics": {
            "nodes": len(nodes),
            "root_sort": sorts[-1],
            "expanded_nodes": _decimal(counts[-1]),
            "free_variables": sorted(
                (n for n, bit in name_bits.items() if free[-1] & bit), key=_variable_index
            ),
        },
        "sorts": sorts,
        "free": free,
        "name_bits": name_bits,
    }


def validate_arithmetic_dag(dag: dict[str, Any], bounded: bool = False) -> dict[str, Any]:
    """Validate term/formula DAG syntax, lexical free variables and exact expansion size.

    Limits: 200000 shared nodes, 4096 indexed variable names, 16384 bits in the
    expansion-count statistic. The bounded profile additionally permits lt,
    bexists and bforall as explicit conservative notation.
    """
    return _dag_info(dag, bounded)["statistics"]


class _DAGBuilder:
    def __init__(self) -> None:
        self.nodes: list[dict[str, Any]] = []
        self.index: dict[tuple[Any, ...], int] = {}

    def node(self, op: str, name: str = "", args: list[int] | tuple[int, ...] = ()) -> int:
        key = (op, name, *args)
        if key not in self.index:
            if len(self.nodes) == MAX_DAG_NODES:
                _error("Arithmetic DAG node budget exceeded", "RESOURCE_LIMIT")
            self.index[key] = len(self.nodes)
            self.nodes.append({"op": op, "name": name, "args": list(args)})
        return self.index[key]

    def export(self, root: int) -> dict[str, Any]:
        seen = set()
        stack = [root]
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            stack.extend(self.nodes[i]["args"])
        mapping = {old: new for new, old in enumerate(sorted(seen))}
        return {
            "schema_version": "1.0",
            "nodes": [
                {
                    "op": self.nodes[i]["op"],
                    "name": self.nodes[i]["name"],
                    "args": [mapping[a] for a in self.nodes[i]["args"]],
                }
                for i in sorted(seen)
            ],
            "root": mapping[root],
        }


def dag_substitute(dag: dict[str, Any], variable: str, term_dag: dict[str, Any]) -> dict[str, Any]:
    """Capture-avoiding substitution of a DAG term for free indexed variables.

    Conflicting binders are renamed above every index in both inputs, in preorder.
    The output is a hash-consed reachable presentation; unlike the dedicated
    two-copy numeral substitution, it does not preserve presentation numbering.
    """
    info, replacement_info = _dag_info(dag, True), _dag_info(term_dag, True, False)
    _variable_index(variable)
    if replacement_info["sorts"][-1] != "term":
        _error("Replacement DAG must have a term root")
    builder = _DAGBuilder()
    mapping = []
    for node in term_dag["nodes"]:
        mapping.append(builder.node(node["op"], node["name"], [mapping[a] for a in node["args"]]))
    replacement = mapping[-1]
    replacement_free = set(replacement_info["statistics"]["free_variables"])
    all_names = set(info["name_bits"]) | set(replacement_info["name_bits"])
    last = max((_variable_index(name) for name in all_names), default=0)
    # Keys carry lexical environments: sharing a node under two binders does not
    # make its bound occurrences interchangeable.
    root_key = (dag["root"], (), True)
    stack = [(root_key, None)]
    done: dict[tuple[Any, ...], int] = {}
    pending: dict[tuple[Any, ...], tuple[str, list[tuple[Any, ...]]]] = {}
    while stack:
        key, staged = stack.pop()
        if key in done:
            continue
        index, environment, active = key
        node = dag["nodes"][index]
        if staged:
            name, children = pending.pop(key)
            done[key] = builder.node(node["op"], name, [done[child] for child in children])
            continue
        env = dict(environment)
        if node["op"] == "var":
            done[key] = (
                replacement
                if active and node["name"] == variable
                else builder.node("var", env.get(node["name"], node["name"]))
            )
            continue
        binder = node["op"] in {"forall", "exists", "bforall", "bexists"}
        new_name = node["name"]
        if binder:
            body = node["args"][-1]
            affected = info["free"][body]
            if node["op"] in {"bforall", "bexists"}:
                # The binder does not scope over its bound. Substitution into
                # that bound must still preserve the no-own-variable invariant.
                affected |= info["free"][node["args"][0]]
            variable_free = bool(affected & info["name_bits"].get(variable, 0))
            if active and node["name"] != variable and node["name"] in replacement_free and variable_free:
                last += 1
                new_name = "x" + _decimal(last)
        children = []
        for offset, child in enumerate(node["args"]):
            child_env, child_active = dict(env), active
            if binder and offset == len(node["args"]) - 1:
                if new_name == node["name"]:
                    child_env.pop(node["name"], None)
                else:
                    child_env[node["name"]] = new_name
                if node["name"] == variable:
                    child_active = False
            children.append((child, tuple(sorted(child_env.items())), child_active))
        if len(done) + len(pending) > MAX_DAG_NODES * 4:
            _error("DAG lexical transformation budget exceeded", "RESOURCE_LIMIT")
        pending[key] = (new_name, children)
        stack.append((key, True))
        stack.extend((child, None) for child in reversed(children))
    result = builder.export(done[root_key])
    validate_arithmetic_dag(result, True)
    return result


def arithmetic_dag(expr: Expr) -> dict[str, Any]:
    """Convert ordinary arithmetic syntax to a shared DAG with injective variable indices.

    An ordinary variable name maps to x followed by the natural number whose
    bytes are 0x01 then that ASCII name. Already-indexed compiler DAGs are separate
    inputs and must not pass through this conversion again.
    """
    node = _arithmetic(expr)
    nodes: list[dict[str, Any]] = []
    index: dict[tuple[Any, ...], int] = {}

    def walk(e: Expr) -> int:
        op = (
            "zero"
            if e.kind == "const"
            else {"S": "succ", "add": "add", "mul": "mul"}[e.name]
            if e.kind == "func"
            else e.kind
        )
        name = (
            "x" + _decimal(int.from_bytes(b"\x01" + e.name.encode("ascii"), "big"))
            if e.kind in {"var", "forall", "exists"}
            else e.name
            if e.kind == "num"
            else ""
        )
        args = [walk(a) for a in e.args]
        key = (op, name, *args)
        if key not in index:
            index[key] = len(nodes)
            nodes.append({"op": op, "name": name, "args": args})
        return index[key]

    root = walk(node)
    result = {"schema_version": "1.0", "nodes": nodes, "root": root}
    validate_arithmetic_dag(result)
    return result


def serialize_arithmetic_dag(dag: dict[str, Any], bounded: bool = False) -> str:
    """Return canonical compact ASCII JSON for a validated arithmetic DAG."""
    validate_arithmetic_dag(dag, bounded)
    return json.dumps(dag, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def dag_fingerprint(dag: dict[str, Any], bounded: bool = False) -> str:
    """Hash the exact DAG presentation; this is not a semantic-equivalence hash."""
    return hashlib.sha256(serialize_arithmetic_dag(dag, bounded).encode("ascii")).hexdigest()


def arithmetic_dag_encode(dag: dict[str, Any]) -> str:
    """Encode a base-signature DAG as versioned natural-number cells.

    Header [20261105,1,N], then four cells [tag,name,left,right] per node.
    Numeric child references are one-based; zero denotes an absent child.
    """
    validate_arithmetic_dag(dag)
    cells = ["20261105", "1", str(len(dag["nodes"]))]
    for node in dag["nodes"]:
        op, name, args = node["op"], node["name"], node["args"]
        name_code = name if op == "num" else name[1:] if op in _NAMED else "0"
        cells.extend(
            [
                str(TAGS.index(op)),
                name_code,
                str(args[0] + 1) if args else "0",
                str(args[1] + 1) if len(args) == 2 else "0",
            ]
        )
    return sequence_encode(cells)


def arithmetic_dag_decode(code: str) -> dict[str, Any]:
    """Decode and validate a DAG presentation, without proving its formula."""
    cells = sequence_decode(code)
    if len(cells) < 3 or cells[:2] != ["20261105", "1"]:
        _error("Unknown DAG numbering header")
    count = _nat(cells[2])
    if count > MAX_DAG_NODES:
        _error("Arithmetic DAG node budget exceeded", "RESOURCE_LIMIT")
    if count == 0 or len(cells) != 3 + 4 * count:
        _error("Incorrect DAG cell count")
    nodes = []
    for index in range(count):
        tag, name, left, right = cells[3 + 4 * index : 7 + 4 * index]
        number = _nat(tag)
        if number >= len(TAGS):
            _error("Unknown DAG tag")
        op = TAGS[number]
        arity = _ARITY[op]
        lref, rref = _nat(left), _nat(right)
        if (
            (arity == 0 and (lref or rref))
            or (arity == 1 and (not lref or rref))
            or (arity == 2 and (not lref or not rref))
        ):
            _error("Noncanonical child fields")
        if op not in {"var", "forall", "exists", "num"} and name != "0":
            _error("Noncanonical logical name field")
        node_name = "x" + name if op in _NAMED else name if op == "num" else ""
        nodes.append({"op": op, "name": node_name, "args": [lref - 1, rref - 1][:arity]})
    result = {"schema_version": "1.0", "nodes": nodes, "root": count - 1}
    validate_arithmetic_dag(result)
    return result


def dag_substitute_numeral(dag: dict[str, Any], variable: str, value: str) -> dict[str, Any]:
    """Substitute a closed compact numeral using the specified two-copy presentation.

    Original nodes remain unchanged. New matching variables become numeral nodes;
    a matching binder retains its original children, so substitution stops there.
    No alpha-renaming is needed because the substituted numeral is closed.
    """
    validate_arithmetic_dag(dag)
    _variable_index(variable)
    _natural_text(value)
    count = len(dag["nodes"])
    if 2 * count > MAX_DAG_NODES:
        _error("Substituted DAG node budget exceeded", "RESOURCE_LIMIT")
    original = [{"op": n["op"], "name": n["name"], "args": list(n["args"])} for n in dag["nodes"]]
    changed = []
    for node in original:
        if node["op"] == "var" and node["name"] == variable:
            changed.append({"op": "num", "name": value, "args": []})
        elif node["op"] in {"forall", "exists"} and node["name"] == variable:
            changed.append({**node, "args": list(node["args"])})
        else:
            changed.append({**node, "args": [a + count for a in node["args"]]})
    result = {"schema_version": "1.0", "nodes": original + changed, "root": 2 * count - 1}
    validate_arithmetic_dag(result)
    return result


def substitute_code(code: str, variable_index: str, value: str) -> str:
    """Totalized code substitution: invalid natural DAG codes map to zero.

    Non-natural input strings are malformed inputs. Operational resource limits
    remain RESOURCE_LIMIT and are never silently totalized to mathematical zero.
    """
    _natural_text(code)
    _natural_text(variable_index, 4096)
    _natural_text(value)
    try:
        dag = arithmetic_dag_decode(code)
    except GoedelError as exc:
        if exc.code == "RESOURCE_LIMIT":
            raise
        return "0"
    return arithmetic_dag_encode(dag_substitute_numeral(dag, "x" + variable_index, value))
