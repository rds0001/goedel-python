"""Explicit arithmetic formulas and finite checks for a fixed PA presentation."""

from __future__ import annotations

import copy
import hashlib
import json
from functools import lru_cache
from importlib.resources import files
from typing import Any

from .arithmetic_dag import (
    DAG_ID,
    _DAGBuilder,
    _variable_index,
    arithmetic_dag_decode,
    arithmetic_dag_encode,
    dag_fingerprint,
    dag_substitute,
    validate_arithmetic_dag,
)
from .proof import _result
from .register_machine import run_register_program
from .sequence import _decimal, _nat, _natural_text, sequence_decode, sequence_encode
from .syntax import _error


@lru_cache(maxsize=1)
def _representation() -> dict[str, Any]:
    """Load the exact packaged mathematical program and graph, checking their binding."""
    raw = files("goedel").joinpath("resources/pa_proof_representation.json").read_bytes()
    bundle = json.loads(raw)
    representation = bundle["representation"]
    program = bundle["program"]
    encoded = json.dumps(program, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if (
        representation["program_sha256"] != "1d56c2d284c57619bcb667d2ebc2811cc2e89cdead029d2a3af5a2ac5727fe51"
        or representation["arithmetic_sha256"]
        != "00712f13ebd539d4082ecd64dba420034901c84d0a4acae277d1735a9b33442d"
        or bundle["schema_version"] != "1.0"
        or program["id"] != "goedel-pa-hilbert-proof-v1"
        or hashlib.sha256(encoded).hexdigest() != representation["program_sha256"]
        or dag_fingerprint(representation["arithmetic_dag"]) != representation["arithmetic_sha256"]
        or representation["inputs"] != ["x0", "x1"]
        or representation["output"] != "x2"
    ):
        _error("PA program and arithmetic representation identity mismatch")
    statistics = validate_arithmetic_dag(representation["arithmetic_dag"])
    if statistics["root_sort"] != "formula" or statistics["free_variables"] != ["x0", "x1", "x2"]:
        _error("PA representation must have exactly its declared input and output variables")
    return bundle


def _atom(op: str, name: str = "") -> dict[str, Any]:
    return {"schema_version": "1.0", "nodes": [{"op": op, "name": name, "args": []}], "root": 0}


def _import(builder: _DAGBuilder, graph: dict[str, Any]) -> int:
    mapping = []
    for node in graph["nodes"]:
        mapping.append(builder.node(node["op"], node["name"], [mapping[a] for a in node["args"]]))
    return mapping[graph["root"]]


def proof_PA_formula(pvar: str = "x0", xvar: str = "x1") -> dict[str, Any]:
    """Build the arithmetic graph accepting proof code pvar and conclusion code xvar.

    Variables are indexed DAG names and must differ. Compiler-bound variables are
    renamed capture-free. No opaque proof predicate or execution budget occurs in
    the returned mathematical formula.
    """
    _variable_index(pvar)
    _variable_index(xvar)
    if pvar == xvar:
        _error("Proof and conclusion variables must differ")
    graph = _representation()["representation"]["arithmetic_dag"]
    # Rename both inputs through fresh variables before choosing caller names.
    indices = [_variable_index(n["name"]) for n in graph["nodes"] if n["op"] in {"var", "forall", "exists"}]
    fresh = max([*indices, _variable_index(pvar), _variable_index(xvar)]) + 1
    ptmp, xtmp = "x" + _decimal(fresh), "x" + _decimal(fresh + 1)
    for name, replacement in [
        ("x0", _atom("var", ptmp)),
        ("x1", _atom("var", xtmp)),
        ("x2", _atom("num", "1")),
        (ptmp, _atom("var", pvar)),
        (xtmp, _atom("var", xvar)),
    ]:
        graph = dag_substitute(graph, name, replacement)
    return graph


def provability_formula(xvar: str = "x1", proofvar: str = "x0") -> dict[str, Any]:
    """Build exists proofvar Proof_PA(proofvar,xvar) for the fixed PA presentation."""
    graph = proof_PA_formula(proofvar, xvar)
    builder = _DAGBuilder()
    body = _import(builder, graph)
    return builder.export(builder.node("exists", proofvar, [body]))


def _contradiction() -> dict[str, Any]:
    builder = _DAGBuilder()
    zero = builder.node("zero", "", [])
    successor = builder.node("succ", "", [zero])
    return builder.export(builder.node("eq", "", [zero, successor]))


def consistency_formula() -> dict[str, Any]:
    """Build not Pr_PA(nu(code(0=S(0)))); this construction asserts no consistency."""
    contradiction_code = arithmetic_dag_encode(_contradiction())
    formula = dag_substitute(provability_formula(), "x1", _atom("num", contradiction_code))
    builder = _DAGBuilder()
    return builder.export(builder.node("not", "", [_import(builder, formula)]))


@lru_cache(maxsize=1)
def _identity() -> dict[str, Any]:
    bundle = _representation()
    representation = bundle["representation"]
    return {
        "schema_version": "1.0",
        "theory_id": "PA",
        "theory_presentation": "goedel-pa-hilbert-theory-v1",
        "calculus_id": "goedel-pa-hilbert-proof-v1",
        "numbering_id": DAG_ID,
        "program_sha256": representation["program_sha256"],
        "graph_sha256": representation["arithmetic_sha256"],
        "proof_numbering_id": "goedel-pa-hilbert-proof-sequence-v1",
        "predicate_sha256": dag_fingerprint(provability_formula()),
        "contradiction_code": arithmetic_dag_encode(_contradiction()),
    }


def provability_identity() -> dict[str, Any]:
    """Return the exact installed provability identity; review flags are not assumptions."""
    return copy.deepcopy(_identity())


def check_pa_proof(proof_code: str, conclusion_code: str, max_steps: int = 1000000) -> dict[str, Any]:
    """Execute the exact PA Hilbert checker within a declared finite step budget.

    ESTABLISHED validates the submitted proof, REFUTED rejects it, and UNKNOWN
    reports budget exhaustion. No result asserts consistency of PA.
    """
    bundle = _representation()
    answer = run_register_program(bundle["program"], [proof_code, conclusion_code], max_steps=max_steps)
    details = answer["details"]
    if not details["halted"]:
        status, reason = "UNKNOWN", "STEP_LIMIT"
    elif details["output"] == "1":
        status, reason = "ESTABLISHED", "VALID"
    elif details["output"] == "0":
        status, reason = "REFUTED", "INVALID_PROOF"
    else:
        raise RuntimeError("The PA proof checker returned a non-boolean output")
    identity = provability_identity()
    return _result(
        status,
        "CHECKED_DERIVATION",
        "Validity of submitted PA Hilbert proof",
        [],
        [{"kind": "NATIVE_REGISTER_CHECK", "program_sha256": identity["program_sha256"]}],
        [
            "This validates one submitted finite proof under the fixed PA calculus. It does not establish PA consistency; budget exhaustion is not unprovability."
        ],
        None,
        {
            "reason": reason,
            "steps_used": details["steps_used"],
            "halted": details["halted"],
            "output": details["output"],
        },
        context=copy.deepcopy(identity),
    )


_Q_CODES = (
    "500916525028717704190487132685665064192049151",
    "34128533460435954929216433013749539833340190205358723760417406975",
    "659269241530276489251887774916317243209608597141772127334720066388438037764767743",
    "7303094192337005764632264550179605053439",
    "2133033341277245731431407528563156690439727583356260119625072639",
    "7303104576930742177100635445239058792447",
    "8532133365108982925472268923064903045895990360676493062035210239",
)


def hilbert_q_axiom(index: int) -> dict[str, Any]:
    """Return Q axiom 1..7 in the exact normalized Hilbert presentation.

    Bound variable indices are literally x0/x1. These codes are the explicit
    patterns used by the mathematical checker; arbitrary renamings are not
    silently treated as axiom instances by that checker.
    """
    if type(index) is not int or not 1 <= index <= 7:
        _error("Q axiom index must be an integer from 1 to 7")
    return arithmetic_dag_decode(_Q_CODES[index - 1])


def _proof_steps(steps: Any) -> None:
    if not isinstance(steps, list) or not steps:
        _error("A PA proof envelope requires at least one step")
    if len(steps) > 4096:
        _error("PA proof transport step budget exceeded", "RESOURCE_LIMIT")
    for step in steps:
        if not isinstance(step, dict) or set(step) != {"rule", "formula", "aux_a", "aux_b"}:
            _error("Malformed PA proof step")
        if type(step["rule"]) is not int or not 0 <= step["rule"] <= 2147483647:
            _error("PA rule transport field must be an integer from 0 to 2147483647")
        for name in ("formula", "aux_a", "aux_b"):
            _natural_text(step[name])


def pa_proof_encode(steps: list[dict[str, Any]]) -> str:
    """Encode a PA Hilbert proof envelope without certifying inference validity."""
    _proof_steps(steps)
    cells = ["20261106", "1", str(len(steps))]
    for step in steps:
        cells.extend([str(step["rule"]), step["formula"], step["aux_a"], step["aux_b"], "0", "0"])
    return sequence_encode(cells)


def pa_proof_decode(code: str) -> list[dict[str, Any]]:
    """Decode structural PA proof fields; only check_pa_proof checks the logic."""
    cells = sequence_decode(code, max_items=24579)
    if len(cells) < 3 or cells[:2] != ["20261106", "1"]:
        _error("Unknown PA proof transport magic or version")
    count = _nat(cells[2])
    if not 1 <= count <= 4096 or len(cells) != 3 + 6 * count:
        _error("Incorrect PA proof record count")
    steps = []
    for i in range(count):
        rule, formula, a, b, c, d = cells[3 + 6 * i : 9 + 6 * i]
        if c != "0" or d != "0":
            _error("Reserved PA proof fields must be zero")
        steps.append({"rule": _nat(rule), "formula": formula, "aux_a": a, "aux_b": b})
    _proof_steps(steps)
    return steps
