"""Identity-bound, conditional metatheorem applicability without assumed soundness."""

from __future__ import annotations

import copy
import hashlib
import json
from importlib.resources import files
from typing import Any

from .arithmetic_dag import _DAGBuilder
from .catalogue import lookup_statement, theory_context
from .fixedpoint import fixed_point
from .pa_provability import _import, provability_formula, provability_identity
from .proof import _result
from .syntax import _error

_RESOURCE_SHA = "faae76a30fa713fb151a6ca8cb535c3aeafbd0fcdd2c80f1e4fb6d09a3e2a607"
_STRUCTURAL = (
    "classical_first_order",
    "decidable_axiom_set",
    "diagonal_lemma_available",
    "effective_axiomatized",
    "effective_language",
    "extends_pa",
    "provability_predicate_fixed",
    "standard_arithmetization",
)
_LIMIT = (
    "Applicability is conditional on user declarations; no consistency or soundness assumption is proved."
)


def _review() -> tuple[dict[str, Any], bool]:
    raw = files("goedel").joinpath("resources/provability_representation.json").read_bytes()
    bundle = json.loads(raw)
    pinned = hashlib.sha256(raw).hexdigest() == _RESOURCE_SHA
    references = bundle.get("resource_refs", {})
    expected = {"pa_proof_representation.json", "substitution_representation.json"}
    if not isinstance(references, dict) or set(references) != expected:
        return bundle, False
    for name in sorted(expected):
        try:
            dependency = files("goedel").joinpath("resources/" + name).read_bytes()
        except FileNotFoundError:
            return bundle, False
        pinned = pinned and hashlib.sha256(dependency).hexdigest() == references[name]
    return bundle, pinned


def check_metatheorem(
    id: str, assumptions: dict[str, bool], identity: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Check a named variant against the exact reviewed PA predicate and declarations.

    User consistency, soundness and standard-model declarations remain assumptions.
    User-written HBL flags cannot replace an independent representation review.
    A custom identity is not silently promoted to the built-in identity.
    """
    record = lookup_statement(id)
    declared = theory_context("PA", assumptions)["assumptions"]
    if identity is not None and not isinstance(identity, dict):
        _error("Predicate identity must be an explicit record or None")
    builtin = provability_identity()
    supplied = copy.deepcopy(builtin if identity is None else identity)
    bundle, pinned = _review()
    matched = supplied == builtin and bundle.get("identity") == builtin
    proof_review = bundle.get("proof_review", bundle.get("review", {}))
    representation_reviewed = pinned and matched and proof_review.get("status") == "INDEPENDENTLY_CHECKED"
    hbl_review = bundle.get("hbl_review", {})
    conditions = hbl_review.get("conditions", {})
    states = {
        name: "REVIEWED"
        if (
            representation_reviewed
            and hbl_review.get("status") == "INDEPENDENTLY_CHECKED"
            and hbl_review.get("predicate_identity") == builtin
            and conditions.get(name, {}).get("status") == "INDEPENDENTLY_CHECKED"
        )
        else "OPEN"
        for name in ("D1", "D2", "D3")
    }
    known = {name: True for name in _STRUCTURAL} if representation_reviewed else {}
    known.update({name: True for name, state in states.items() if state == "REVIEWED"})
    if all(state == "REVIEWED" for state in states.values()):
        known["hbl_conditions"] = True
    structural_conflicts = sorted(name for name in known if declared.get(name) is False)
    effective = dict(declared)
    # These protected claims require the matching review, never just a declaration.
    protected = {"hbl_conditions", "provability_predicate_fixed", "D1", "D2", "D3"}
    for name in protected:
        effective.pop(name, None)
    effective.update(known)
    requirements = sorted(record["requirements"])
    missing = {name for name in requirements if name not in effective}
    violated = {name for name in requirements if effective.get(name) is False}
    if "hbl_conditions" in requirements:
        missing.update(name for name, state in states.items() if state == "OPEN")
    inconsistent = bool(structural_conflicts) or (
        declared.get("consistent") is False
        and any(declared.get(name) is True for name in ("omega_consistent", "sigma1_sound"))
    )
    evidence = record["evidence"]
    statement_reviewed = (
        evidence.get("kind") == "LITERATURE_RESULT"
        and evidence.get("review_status") == "REVIEWED"
        and evidence.get("verification_status") in {"INDEPENDENTLY_CHECKED", "FORMALLY_VERIFIED"}
    )
    if inconsistent:
        status = "INCONSISTENT_CONTEXT"
    elif not matched or not representation_reviewed or not statement_reviewed:
        status = "UNKNOWN"
    elif violated:
        status = "NOT_APPLICABLE"
    elif missing:
        status = "UNKNOWN"
    else:
        status = "ESTABLISHED"
    representation_status = "INDEPENDENTLY_CHECKED" if representation_reviewed else "PENDING"
    context = {
        "theory_id": supplied.get("theory_id", "UNSPECIFIED"),
        "metatheory_id": "ordinary_classical_metamathematics",
        "level": "META",
        "predicate_identity": supplied,
    }
    return _result(
        status,
        "CATALOGUE_INFERENCE",
        "Conditional metatheorem applicability: " + id,
        declared,
        [
            copy.deepcopy(evidence),
            {
                "kind": "REPRESENTATION_REVIEW",
                "status": representation_status,
                "predicate_identity": supplied,
            },
        ],
        [*record["limitations"], _LIMIT],
        None,
        {
            "statement_id": id,
            "identity_status": "MATCH" if matched else "UNREVIEWED_IDENTITY",
            "missing_requirements": sorted(missing),
            "violated_requirements": sorted(violated | set(structural_conflicts)),
            "representation_review": representation_status,
            "hbl_conditions": states,
        },
        context=context,
        dependencies=requirements,
    )


def godel_sentence() -> dict[str, Any]:
    """Construct the actual fixed point of not Pr_PA(x), retaining its trusted premise.

    The result verifies a conditional equivalence. Unprovability or truth of the
    sentence requires separate metatheorem hypotheses and is not asserted here.
    Exact codes can contain millions of digits within explicit DAG/sequence limits.
    """
    builder = _DAGBuilder()
    predicate = _import(builder, provability_formula())
    phi = builder.export(builder.node("not", "", [predicate]))
    return fixed_point(phi)
