"""Typed propositional modal syntax and finite Kripke semantics."""

from __future__ import annotations

import itertools
import json
from dataclasses import dataclass
from typing import Any

from .proof import _result
from .semantics import _Budget, _digest, _labels
from .syntax import _error, _name

MODAL_LIMIT = "This result concerns the specified finite Kripke model or frame, not arithmetic provability or general GL completeness."
_ARITIES = {"atom": 0, "bottom": 0, "not": 1, "box": 1, "diamond": 1, "and": 2, "or": 2, "implies": 2}


@dataclass(frozen=True, slots=True)
class ModalExpr:
    """Immutable modal syntax, distinct from first-order expressions."""

    kind: str
    name: str = ""
    args: tuple[ModalExpr, ...] = ()

    def __post_init__(self) -> None:
        _validate_modal(self)


def _mw(node: ModalExpr) -> dict[str, Any]:
    return {"args": [_mw(a) for a in node.args], "kind": node.kind, "name": node.name}


def _validate_modal(node: Any) -> None:
    count = 0
    active: set[int] = set()

    def walk(e: Any, depth: int) -> None:
        nonlocal count
        count += 1
        if depth > 64 or count > 1000:
            _error("Modal syntax budget exceeded", "RESOURCE_LIMIT")
        if (
            not isinstance(e, ModalExpr)
            or not isinstance(e.args, tuple)
            or not isinstance(e.kind, str)
            or e.kind not in _ARITIES
        ):
            _error("A valid modal expression is required")
        if id(e) in active:
            _error("Cyclic modal expression")
        if len(e.args) != _ARITIES[e.kind]:
            _error("Modal arity mismatch")
        if e.kind == "atom":
            _name(e.name)
        elif e.name != "":
            _error("Logical modal names must be empty")
        active.add(id(e))
        for a in e.args:
            walk(a, depth + 1)
        active.remove(id(e))

    walk(node, 1)
    if len(json.dumps(_mw(node), sort_keys=True, separators=(",", ":"))) > 65536:
        _error("Modal serialization budget exceeded", "RESOURCE_LIMIT")


def _modal(value: Any, depth: int = 1) -> ModalExpr:
    if depth > 64:
        _error("Modal syntax depth exceeded", "RESOURCE_LIMIT")
    if isinstance(value, ModalExpr):
        _validate_modal(value)
        return value
    if (
        not isinstance(value, dict)
        or set(value) != {"args", "kind", "name"}
        or not isinstance(value["args"], list)
    ):
        _error("Modal wire expression requires exactly args, kind and name")
    if not isinstance(value["kind"], str) or value["kind"] not in _ARITIES or len(value["args"]) != _ARITIES[value["kind"]]:
        _error("Modal arity or kind mismatch")
    return ModalExpr(value["kind"], value["name"], tuple(_modal(a, depth + 1) for a in value["args"]))


def modal_atom(name: str) -> ModalExpr:
    """Construct a propositional modal atom."""
    return ModalExpr("atom", name)


def modal_bottom() -> ModalExpr:
    """Construct modal falsum."""
    return ModalExpr("bottom")


def modal_negate(formula: ModalExpr) -> ModalExpr:
    """Construct modal negation."""
    return ModalExpr("not", "", (_modal(formula),))


def modal_conjunction(left: ModalExpr, right: ModalExpr) -> ModalExpr:
    """Construct modal conjunction."""
    return ModalExpr("and", "", (_modal(left), _modal(right)))


def modal_disjunction(left: ModalExpr, right: ModalExpr) -> ModalExpr:
    """Construct modal disjunction."""
    return ModalExpr("or", "", (_modal(left), _modal(right)))


def modal_implication(left: ModalExpr, right: ModalExpr) -> ModalExpr:
    """Construct material implication between modal formulas."""
    return ModalExpr("implies", "", (_modal(left), _modal(right)))


def modal_box(formula: ModalExpr) -> ModalExpr:
    """Construct the necessity modality."""
    return ModalExpr("box", "", (_modal(formula),))


def modal_diamond(formula: ModalExpr) -> ModalExpr:
    """Construct the possibility modality."""
    return ModalExpr("diamond", "", (_modal(formula),))


def kripke_model(
    worlds: list[str], edges: list[list[str]], valuation: dict[str, list[str]] | None = None
) -> dict[str, Any]:
    """Build an explicit finite Kripke model; listed atoms have complete valuations."""
    nodes = _labels(worlds)
    if not isinstance(edges, list):
        _error("Edges must be a list of ordered world pairs")
    pairs: set[tuple[str, str]] = set()
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2 or any(w not in nodes for w in edge):
            _error("Invalid accessibility edge")
        pair = tuple(edge)
        if pair in pairs:
            _error("Duplicate accessibility edge")
        pairs.add(pair)
    valuation = {} if valuation is None else valuation
    if not isinstance(valuation, dict):
        _error("Valuation must map atoms to lists of true worlds")
    normalized = {}
    for atom, true_worlds in valuation.items():
        _name(atom)
        if (
            not isinstance(true_worlds, (list, tuple))
            or any(w not in nodes for w in true_worlds)
            or len(set(true_worlds)) != len(true_worlds)
        ):
            _error("Invalid atom valuation")
        normalized[atom] = sorted(true_worlds)
    return {
        "schema_version": "1.0",
        "worlds": nodes,
        "edges": [list(pair) for pair in sorted(pairs)],
        "valuation": dict(sorted(normalized.items())),
    }


def _model(model: Any) -> dict[str, Any]:
    if (
        not isinstance(model, dict)
        or set(model) != {"schema_version", "worlds", "edges", "valuation"}
        or model["schema_version"] != "1.0"
    ):
        _error("Unknown Kripke model schema")
    return kripke_model(model["worlds"], model["edges"], model["valuation"])


def frame_check(model: dict[str, Any]) -> dict[str, bool]:
    """Decide reflexivity, irreflexivity, transitivity and acyclicity of a finite frame."""
    model = _model(model)
    worlds = model["worlds"]
    edges = {tuple(e) for e in model["edges"]}
    reach = set(edges)
    for mid in worlds:
        for source in worlds:
            for target in worlds:
                if (source, mid) in reach and (mid, target) in reach:
                    reach.add((source, target))
    return {
        "reflexive": all((w, w) in edges for w in worlds),
        "irreflexive": all((w, w) not in edges for w in worlds),
        "transitive": all((a, c) in edges for a, b in edges for b2, c in edges if b == b2),
        "acyclic": all((w, w) not in reach for w in worlds),
    }


def _atoms(node: ModalExpr) -> set[str]:
    result = {node.name} if node.kind == "atom" else set()
    for arg in node.args:
        result.update(_atoms(arg))
    return result


def _truth(node: ModalExpr, model: dict[str, Any], world: str, budget: _Budget) -> bool:
    budget.tick()
    if node.kind == "atom":
        return world in model["valuation"][node.name]
    if node.kind == "bottom":
        return False
    if node.kind == "not":
        return not _truth(node.args[0], model, world, budget)
    if node.kind == "and":
        return _truth(node.args[0], model, world, budget) and _truth(node.args[1], model, world, budget)
    if node.kind == "or":
        return _truth(node.args[0], model, world, budget) or _truth(node.args[1], model, world, budget)
    if node.kind == "implies":
        return not _truth(node.args[0], model, world, budget) or _truth(node.args[1], model, world, budget)
    successors = [b for a, b in model["edges"] if a == world]
    if node.kind == "box":
        return all(_truth(node.args[0], model, target, budget) for target in successors)
    return any(_truth(node.args[0], model, target, budget) for target in successors)


def evaluate_modal(
    formula: ModalExpr, model: dict[str, Any], world: str, max_steps: int = 10000
) -> dict[str, Any]:
    """Evaluate a modal formula at one world of a complete finite model."""
    node, structure = _modal(formula), _model(model)
    if world not in structure["worlds"]:
        _error("Evaluation world outside frame")
    if not _atoms(node) <= set(structure["valuation"]):
        _error("Missing atom valuation")
    budget = _Budget(max_steps)
    value = _truth(node, structure, world, budget)
    return _result(
        "ESTABLISHED" if value else "REFUTED",
        "FINITE_EXACT",
        "finite_modal_truth",
        [],
        [],
        [MODAL_LIMIT],
        None,
        {"value": value, "world": world, "steps_used": budget.used},
        {"model_sha256": _digest(structure)},
    )


def validate_modal_frame(
    formula: ModalExpr, worlds: list[str], edges: list[list[str]], max_valuations: int = 4096
) -> dict[str, Any]:
    """Exhaust all valuations of a formula's atoms on a specific finite frame.

    The first countermodel is returned. Insufficient resources raise RESOURCE_LIMIT
    rather than asserting validity from a partially checked set of valuations.
    """
    node = _modal(formula)
    structure = kripke_model(worlds, edges)
    if type(max_valuations) is not int or not 1 <= max_valuations <= 65536:
        _error("max_valuations must be an integer from 1 to 65536")
    atoms = sorted(_atoms(node))
    size = len(atoms) * len(structure["worlds"])
    if size > 16 or 2**size > max_valuations:
        _error("Modal valuation budget exceeded", "RESOURCE_LIMIT")
    budget = _Budget(1000000)
    checked, checked_worlds = 0, 0
    witness = None
    for bits in itertools.product((False, True), repeat=size):
        width = len(structure["worlds"])
        structure["valuation"] = {
            atom: [w for j, w in enumerate(structure["worlds"]) if bits[i * width + j]]
            for i, atom in enumerate(atoms)
        }
        checked += 1
        for world in structure["worlds"]:
            checked_worlds += 1
            if not _truth(node, structure, world, budget):
                witness = {"world": world, "valuation": structure["valuation"]}
                break
        if witness is not None:
            break
    return _result(
        "ESTABLISHED" if witness is None else "REFUTED",
        "FINITE_EXACT",
        "finite_frame_validity",
        [],
        [],
        [MODAL_LIMIT],
        witness,
        {"valuations_checked": checked, "worlds_checked": checked_worlds},
        {"frame_sha256": _digest({"worlds": structure["worlds"], "edges": structure["edges"]})},
    )
