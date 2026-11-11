"""Exact semantics over explicitly supplied, completely interpreted finite domains."""

from __future__ import annotations

import hashlib
import itertools
import json
import re
from typing import Any

from .proof import _formula, _result
from .syntax import TERMS, Expr, _error, _expr, _free, _name

FINITE_LIMIT = "Exact truth concerns only the supplied finite structure, not the natural numbers or consistency of a theory."


def _label(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_]{1,64}", value) is None:
        _error("Domain and world labels must be 1 to 64 ASCII letters, digits or underscores")
    return value


def _labels(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple)) or not values:
        _error("A nonempty finite domain is required")
    if len(values) > 16:
        _error("Finite domain size exceeds 16", "RESOURCE_LIMIT")
    result = [_label(v) for v in values]
    if len(result) != len(set(result)):
        _error("Duplicate domain element")
    return sorted(result)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


class _Budget:
    def __init__(self, maximum: int):
        if type(maximum) is not int or not 1 <= maximum <= 1000000:
            _error("max_steps must be an integer from 1 to 1000000")
        self.maximum, self.used = maximum, 0

    def tick(self) -> None:
        self.used += 1
        if self.used > self.maximum:
            _error("Finite evaluation budget exhausted", "RESOURCE_LIMIT")


def finite_structure(
    domain: list[str],
    constants: dict[str, str] | None = None,
    functions: list[dict[str, Any]] | None = None,
    relations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate a finite structure with total function and relation tables.

    Table records have name, arity and table; each row has args and value. False
    relation rows are explicit. No omitted interpretation receives a default.
    """
    elements = _labels(domain)
    constants = {} if constants is None else constants
    if not isinstance(constants, dict):
        _error("Constant interpretation must be a mapping")
    for name, value in constants.items():
        _name(name)
        if value not in elements:
            _error("Constant value outside domain")

    def tables(records: Any, relation: bool) -> list[dict[str, Any]]:
        records = [] if records is None else records
        if not isinstance(records, (list, tuple)):
            _error("Function and relation interpretations must be lists")
        if len(records) > 256:
            _error("Signature budget exceeded", "RESOURCE_LIMIT")
        seen: set[str] = set()
        result = []
        total = 0
        for record in records:
            if not isinstance(record, dict) or set(record) != {"name", "arity", "table"}:
                _error("Interpretation requires exactly name, arity and table")
            name, arity, rows = record["name"], record["arity"], record["table"]
            _name(name)
            if name in seen:
                _error("Duplicate interpreted symbol")
            seen.add(name)
            if type(arity) is not int or arity < 0:
                _error("Symbol arity must be a nonnegative integer")
            if arity > 16 or len(elements) ** arity > 65536:
                _error("Interpretation table budget exceeded", "RESOURCE_LIMIT")
            if not isinstance(rows, list) or len(rows) != len(elements) ** arity:
                _error("Interpretation table is not total")
            total += len(rows)
            if total > 65536:
                _error("Interpretation table budget exceeded", "RESOURCE_LIMIT")
            indexed: dict[tuple[str, ...], Any] = {}
            for row in rows:
                if not isinstance(row, dict) or set(row) != {"args", "value"}:
                    _error("Table rows require args and value")
                if not isinstance(row["args"], list) or len(row["args"]) != arity:
                    _error("Incorrect table argument arity")
                if any(a not in elements for a in row["args"]):
                    _error("Table argument outside domain")
                args = tuple(row["args"])
                if args in indexed:
                    _error("Duplicate table row")
                value = row["value"]
                if (type(value) is not bool) if relation else (value not in elements):
                    _error("Invalid interpretation value")
                indexed[args] = value
            result.append(
                {
                    "name": name,
                    "arity": arity,
                    "table": [{"args": list(args), "value": indexed[args]} for args in sorted(indexed)],
                }
            )
        return sorted(result, key=lambda r: r["name"])

    return {
        "schema_version": "1.0",
        "domain": elements,
        "constants": dict(sorted(constants.items())),
        "functions": tables(functions, False),
        "relations": tables(relations, True),
    }


def _structure(model: Any) -> dict[str, Any]:
    if (
        not isinstance(model, dict)
        or set(model) != {"schema_version", "domain", "constants", "functions", "relations"}
        or model["schema_version"] != "1.0"
    ):
        _error("Unknown finite structure schema")
    return finite_structure(model["domain"], model["constants"], model["functions"], model["relations"])


class _Evaluator:
    def __init__(self, model: Any, max_steps: int):
        self.model = _structure(model)
        self.budget = _Budget(max_steps)
        self.functions = {
            r["name"]: (r["arity"], {tuple(x["args"]): x["value"] for x in r["table"]})
            for r in self.model["functions"]
        }
        self.relations = {
            r["name"]: (r["arity"], {tuple(x["args"]): x["value"] for x in r["table"]})
            for r in self.model["relations"]
        }

    def assignment(self, node: Expr, assignment: Any) -> dict[str, str]:
        assignment = {} if assignment is None else assignment
        if not isinstance(assignment, dict):
            _error("Assignment must be a mapping")
        for key, value in assignment.items():
            _name(key)
            if value not in self.model["domain"]:
                _error("Assignment value outside domain")
        if not _free(node) <= set(assignment):
            _error("Missing free variable assignment")
        self.signature(node)
        return dict(sorted(assignment.items()))

    def signature(self, node: Expr) -> None:
        if node.kind == "const" and node.name not in self.model["constants"]:
            _error("Uninterpreted constant")
        if node.kind in {"func", "pred"}:
            table = self.functions if node.kind == "func" else self.relations
            if node.name not in table or table[node.name][0] != len(node.args):
                _error("Missing interpretation or symbol arity mismatch")
        if node.kind == "num":
            if "zero" not in self.model["constants"]:
                _error("Numeral interpretation needs zero")
            n = int(node.name)
            if n and ("S" not in self.functions or self.functions["S"][0] != 1):
                _error("Numeral interpretation needs unary S")
            if n > 1 and ("mul" not in self.functions or self.functions["mul"][0] != 2):
                _error("Numeral interpretation needs binary mul")
        for arg in node.args:
            self.signature(arg)

    def term(self, node: Expr, assignment: dict[str, str]) -> str:
        self.budget.tick()
        if node.kind == "var":
            return assignment[node.name]
        if node.kind == "const":
            return self.model["constants"][node.name]
        if node.kind == "num":
            n = int(node.name)
            self.budget.tick()  # zero in the expanded term
            value = self.model["constants"]["zero"]
            if n == 0:
                return value
            self.budget.tick()  # initial S(0)
            value = self.functions["S"][1][(value,)]
            for bit in bin(n)[3:]:
                for _ in range(4):
                    self.budget.tick()  # multiplication and S(S(0))
                two = self.functions["S"][1][(self.functions["S"][1][(self.model["constants"]["zero"],)],)]
                value = self.functions["mul"][1][(two, value)]
                if bit == "1":
                    self.budget.tick()
                    value = self.functions["S"][1][(value,)]
            return value
        values = tuple(self.term(arg, assignment) for arg in node.args)
        return self.functions[node.name][1][values]

    def formula(self, node: Expr, assignment: dict[str, str]) -> tuple[bool, dict[str, str]]:
        self.budget.tick()
        kind = node.kind
        if kind == "bottom":
            return False, assignment
        if kind == "eq":
            return self.term(node.args[0], assignment) == self.term(node.args[1], assignment), assignment
        if kind == "pred":
            return self.relations[node.name][1][
                tuple(self.term(arg, assignment) for arg in node.args)
            ], assignment
        if kind == "not":
            value, witness = self.formula(node.args[0], assignment)
            return not value, witness
        if kind in {"and", "or", "implies"}:
            left, witness = self.formula(node.args[0], assignment)
            if kind == "and" and not left:
                return False, witness
            if (kind == "or" and left) or (kind == "implies" and not left):
                return True, witness
            return self.formula(node.args[1], assignment)
        for element in self.model["domain"]:
            value, witness = self.formula(node.args[0], {**assignment, node.name: element})
            if (kind == "forall" and not value) or (kind == "exists" and value):
                return value, witness
        return kind == "forall", assignment


def evaluate_term(
    term: Expr, model: dict[str, Any], assignment: dict[str, str] | None = None, max_steps: int = 10000
) -> dict[str, Any]:
    """Evaluate a term in an explicit finite structure, with a counted resource budget."""
    node = _expr(term)
    if node.kind not in TERMS:
        _error("A term is required")
    evaluator = _Evaluator(model, max_steps)
    values = evaluator.assignment(node, assignment)
    value = evaluator.term(node, values)
    return _result(
        "ESTABLISHED",
        "FINITE_EXACT",
        "finite_term_value",
        [],
        [],
        [FINITE_LIMIT],
        None,
        {"value": value, "steps_used": evaluator.budget.used},
        {"model_sha256": _digest(evaluator.model)},
    )


def evaluate_formula(
    formula: Expr, model: dict[str, Any], assignment: dict[str, str] | None = None, max_steps: int = 10000
) -> dict[str, Any]:
    """Evaluate a formula and retain its original assignment for exact replay.

    Quantifier-local bindings do not overwrite free input variables in the witness.
    """
    node = _formula(formula)
    evaluator = _Evaluator(model, max_steps)
    values = evaluator.assignment(node, assignment)
    value, _ = evaluator.formula(node, values)
    return _result(
        "ESTABLISHED" if value else "REFUTED",
        "FINITE_EXACT",
        "finite_formula_truth",
        [],
        [],
        [FINITE_LIMIT],
        {"assignment": dict(sorted(values.items()))},
        {"value": value, "steps_used": evaluator.budget.used},
        {"model_sha256": _digest(evaluator.model)},
    )


def finite_model_check(formulas: list[Expr], model: dict[str, Any], max_steps: int = 10000) -> dict[str, Any]:
    """Check every listed formula under all assignments in one finite structure.

    Checking a finite list never checks the entire PA induction schema.
    """
    if not isinstance(formulas, list) or len(formulas) > 1000:
        _error("Provide at most 1000 formulas")
    nodes = [_formula(f) for f in formulas]
    evaluator = _Evaluator(model, max_steps)
    for node in nodes:
        evaluator.signature(node)
    checked = 0
    witness = None
    for i, node in enumerate(nodes, 1):
        names = sorted(_free(node))
        for values in itertools.product(evaluator.model["domain"], repeat=len(names)):
            assignment = dict(zip(names, values))
            value, _ = evaluator.formula(node, assignment)
            if not value:
                witness = {"formula_index": i, "assignment": dict(sorted(assignment.items()))}
                break
        checked += 1
        if witness is not None:
            break
    return _result(
        "ESTABLISHED" if witness is None else "REFUTED",
        "FINITE_EXACT",
        "finite_model_of_list",
        [],
        [],
        [FINITE_LIMIT],
        witness,
        {"checked_formulas": checked, "steps_used": evaluator.budget.used, "value": witness is None},
        {"model_sha256": _digest(evaluator.model)},
    )
