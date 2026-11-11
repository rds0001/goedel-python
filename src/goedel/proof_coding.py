"""Versioned finite proof transport, with proof validity checked separately.

This JSON-byte transport is not itself the arithmetical Proof_T relation.
Its identities specify exactly which native scoped calculus is replayed.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .natural_deduction import CALCULUS, check_scoped_proof
from .proof import _formulas
from .sequence import sequence_decode, sequence_encode
from .syntax import Expr, _error, _expr, _wire

_FIELDS = {
    "schema_version",
    "calculus",
    "numbering",
    "theory",
    "theory_sha256",
    "assumptions",
    "axioms",
    "conclusion",
    "logic",
    "steps",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def proof_object(
    steps: list[dict[str, Any]],
    assumptions: list[Expr] | tuple[Expr, ...] = (),
    axioms: list[Expr] | tuple[Expr, ...] = (),
    theory: dict[str, Any] | None = None,
    conclusion: Expr | None = None,
    logic: str = "classical",
) -> dict[str, Any]:
    """Construct a version-bound finite proof object, without asserting validity.

    Malformed input is rejected. A well-formed but invalid submitted derivation
    can still be represented and encoded; replay is a separate operation.
    """
    check_scoped_proof(steps, assumptions, axioms, theory, conclusion, logic)
    normalized = []
    for step in steps:
        normalized.append(
            {k: _wire(_expr(v)) if k in {"formula", "term", "template"} else v for k, v in step.items()}
        )
    result = {
        "schema_version": "1.0",
        "calculus": CALCULUS,
        "numbering": "goedel-nat-sequence-v1",
        "theory": theory,
        "theory_sha256": None
        if theory is None
        else hashlib.sha256(_canonical(theory).encode("ascii")).hexdigest(),
        "assumptions": [_wire(a) for a in _formulas(assumptions)],
        "axioms": [_wire(a) for a in _formulas(axioms)],
        "conclusion": None if conclusion is None else _wire(_expr(conclusion)),
        "logic": logic,
        "steps": normalized,
    }
    return json.loads(_canonical(result))


def _proof(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != _FIELDS:
        _error("Proof record fields do not match the versioned schema")
    if (
        record["schema_version"] != "1.0"
        or record["calculus"] != CALCULUS
        or record["numbering"] != "goedel-nat-sequence-v1"
    ):
        _error("Unknown proof schema, calculus or numbering identity")
    expected = proof_object(
        record["steps"],
        record["assumptions"],
        record["axioms"],
        record["theory"],
        record["conclusion"],
        record["logic"],
    )
    if record != expected:
        _error("Noncanonical proof object or mismatched theory identity")
    return expected


def encode_proof(record: dict[str, Any]) -> str:
    """Encode a canonical proof object with transport header [20261106,1]."""
    data = _canonical(_proof(record)).encode("ascii")
    if len(data) > 1000000:
        _error("Proof transport byte budget exceeded", "RESOURCE_LIMIT")
    return sequence_encode(["20261106", "1", *(str(b) for b in data)])


def decode_proof(code: str) -> dict[str, Any]:
    """Decode a proof object and identities; decoding is not proof acceptance."""
    values = sequence_decode(code)
    if len(values) < 2 or values[:2] != ["20261106", "1"]:
        _error("Unknown proof transport header")
    if any(len(v) > 3 or int(v) > 255 for v in values[2:]):
        _error("Proof payload has a non-byte cell")
    data = bytes(int(v) for v in values[2:])

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        if len({k for k, _ in items}) != len(items):
            _error("Duplicate proof JSON keys")
        return dict(items)

    try:
        text = data.decode("ascii")
        record = json.loads(text, object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError):
        _error("Malformed proof JSON bytes")
    except RecursionError:
        _error("Proof JSON nesting budget exceeded", "RESOURCE_LIMIT")
    record = _proof(record)
    if _canonical(record) != text:
        _error("Noncanonical proof JSON payload")
    return record


def check_proof_code(code: str, expected_theory: dict[str, Any] | None = None) -> dict[str, Any]:
    """Decode and independently replay the submitted native scoped proof.

    If expected_theory is supplied it must equal the bound theory exactly.
    A successful result has the same explicit trust scope as check_scoped_proof.
    """
    record = decode_proof(code)
    if expected_theory is not None and record["theory"] != expected_theory:
        _error("Proof belongs to a different theory presentation")
    return check_scoped_proof(
        record["steps"],
        record["assumptions"],
        record["axioms"],
        record["theory"],
        record["conclusion"],
        record["logic"],
    )
