"""Reviewed literature records, explicit declarations, and conditional applicability."""
from __future__ import annotations

import copy
import hashlib
import json
from importlib.resources import files
from typing import Any

from .proof import _result
from .syntax import _error

APPLICABILITY_LIMIT = "Applicability is conditional on declarations; assumptions are not verified."


def _catalogue() -> tuple[dict[str, Any], bytes]:
    payload = files("goedel").joinpath("resources/catalogue.json").read_bytes()
    return json.loads(payload), payload


def theory_context(name: str, assumptions: dict[str, bool] | None = None) -> dict[str, Any]:
    """Declare a named theory context; no declaration establishes its consistency."""
    if not isinstance(name, str) or not name or len(name) > 128:
        _error("Theory name must be nonempty text of at most 128 characters")
    values = {} if assumptions is None else assumptions
    if not isinstance(values, dict) or any(not isinstance(k, str) or not k or type(v) is not bool for k, v in values.items()):
        _error("Context assumptions require nonempty string keys and boolean values")
    if len(values) > 1000:
        _error("Context assumption budget exceeded", "RESOURCE_LIMIT")
    return {"id": name, "assumptions": dict(sorted(values.items())), "consistency_status": "NOT_ESTABLISHED"}


def _context(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"id", "assumptions", "consistency_status"}:
        _error("Invalid theory context fields")
    if value["consistency_status"] != "NOT_ESTABLISHED":
        _error("Declared context cannot certify consistency")
    return theory_context(value["id"], value["assumptions"])


def list_statements() -> list[str]:
    """Return sorted catalogue statement identifiers."""
    data, _ = _catalogue()
    return sorted(s["id"] for s in data["statements"])


def lookup_statement(id: str) -> dict[str, Any]:
    """Return an independent copy of one statement, including its evidence and limits."""
    data, _ = _catalogue()
    for record in data["statements"]:
        if record["id"] == id:
            return copy.deepcopy(record)
    _error("Unknown statement identifier")


def list_definitions() -> list[str]:
    """Return sorted catalogue definition identifiers."""
    data, _ = _catalogue()
    return sorted(s["id"] for s in data["definitions"])


def definition(id: str) -> dict[str, Any]:
    """Return one definition; a definition is not an existence proof."""
    data, _ = _catalogue()
    for record in data["definitions"]:
        if record["id"] == id:
            return copy.deepcopy(record)
    _error("Unknown definition identifier")


def check_applicability(id: str, context: dict[str, Any]) -> dict[str, Any]:
    """Check declared conditions of one reviewed variant without certifying them."""
    record, checked_context = lookup_statement(id), _context(context)
    declared = checked_context["assumptions"]
    requirements = sorted(record["requirements"])
    missing = sorted(key for key in requirements if key not in declared)
    violated = sorted(key for key in requirements if declared.get(key) is False)
    evidence = record["evidence"]
    inconsistent = (declared.get("consistent") is False and
                    any(declared.get(key) is True for key in ("omega_consistent", "sigma1_sound")))
    reviewed = (evidence.get("kind") == "LITERATURE_RESULT" and
                evidence.get("review_status") == "REVIEWED" and
                evidence.get("verification_status") in {"INDEPENDENTLY_CHECKED", "FORMALLY_VERIFIED"})
    if inconsistent:
        status = "INCONSISTENT_CONTEXT"
    elif not reviewed:
        status = "UNKNOWN"
    elif violated:
        status = "NOT_APPLICABLE"
    elif missing:
        status = "UNKNOWN"
    else:
        status = "ESTABLISHED"
    return _result(status, "CATALOGUE", id, declared, [copy.deepcopy(evidence)],
                   [*record["limitations"], APPLICABILITY_LIMIT], None,
                   {"missing_requirements": missing, "violated_requirements": violated},
                   context=checked_context, dependencies=requirements)


def relation_graph() -> dict[str, Any]:
    """Return direct typed catalogue edges only; reachability is not a derivation."""
    data, _ = _catalogue()
    return {"nodes": sorted(s["id"] for s in data["statements"]),
            "edges": copy.deepcopy(sorted(data["relations"], key=lambda edge: edge["id"]))}


def catalogue_manifest() -> dict[str, str]:
    """Return catalogue/schema versions and the packaged resource's byte hash."""
    data, payload = _catalogue()
    return {"schema_version": data["schema_version"], "catalogue_version": data["catalogue_version"],
            "sha256": hashlib.sha256(payload).hexdigest()}
