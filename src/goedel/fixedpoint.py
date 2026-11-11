"""Concrete arithmetical fixed points with an explicit trusted representation premise."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from typing import Any

from .arithmetic_dag import (
    DAG_ID,
    _DAGBuilder,
    _variable_index,
    arithmetic_dag_encode,
    dag_fingerprint,
    dag_substitute,
    dag_substitute_numeral,
    substitute_code,
    validate_arithmetic_dag,
)
from .dag_proofs import check_scoped_dag_proof
from .proof import _result
from .sequence import _decimal
from .syntax import _error

_BUILTIN_SHA = "09ed7e7edbaf7f775e7d320c2ef20488705c8312cc45217c460f1fc914f12ef6"
_LIMITS = [
    "The representation premise is supported by independent mathematical review, not proved by the native deduction checker.",
    "The constructed sentence is not thereby asserted true, unprovable, or a consistency statement.",
]


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def _bundle(representation: Any) -> tuple[dict[str, Any], bool]:
    if representation is None:
        representation = json.loads(
            files("goedel").joinpath("resources/substitution_representation.json").read_text()
        )
    if (
        not isinstance(representation, dict)
        or set(representation) != {"schema_version", "program", "representation", "review"}
        or representation["schema_version"] != "1.0"
    ):
        _error("Unknown substitution representation bundle")
    record, review, program = (
        representation["representation"],
        representation["review"],
        representation["program"],
    )
    if not all(isinstance(v, dict) for v in (record, review, program)):
        _error("Malformed substitution representation records")
    required = {
        "arithmetic_dag",
        "arithmetic_sha256",
        "bounded_dag",
        "bounded_sha256",
        "program_sha256",
        "program_id",
        "inputs",
        "output",
        "machine_id",
    }
    if not required <= set(record):
        _error("Incomplete substitution representation")
    if (
        record["inputs"] != ["x0", "x1", "x2"]
        or record["output"] != "x3"
        or record["program_id"] != "goedel-dag-closed-substitution-v1"
        or record["machine_id"] != "goedel-arithmetic-register-v1"
    ):
        _error("Representation input/output or numbering identity mismatch")
    info = validate_arithmetic_dag(record["arithmetic_dag"])
    if info["root_sort"] != "formula" or info["free_variables"] != ["x0", "x1", "x2", "x3"]:
        _error("Substitution formula has the wrong signature or free variables")
    hashes = {
        "arithmetic_sha256": dag_fingerprint(record["arithmetic_dag"]),
        "bounded_sha256": dag_fingerprint(record["bounded_dag"], True),
        "program_sha256": hashlib.sha256(_canonical(program)).hexdigest(),
    }
    if any(record.get(k) != v or review.get(k) != v for k, v in hashes.items()):
        _error("Representation formula/program/review binding changed")
    reviewed = (
        hashlib.sha256(_canonical(representation)).hexdigest() == _BUILTIN_SHA
        and review.get("status") == "INDEPENDENTLY_CHECKED"
        and review.get("formal_kernel") is False
    )
    return representation, reviewed


def _term(op: str, name: str) -> dict[str, Any]:
    return {"schema_version": "1.0", "nodes": [{"op": op, "name": name, "args": []}], "root": 0}


def _import(builder: _DAGBuilder, dag: dict[str, Any]) -> int:
    mapping = []
    for node in dag["nodes"]:
        mapping.append(builder.node(node["op"], node["name"], [mapping[a] for a in node["args"]]))
    return mapping[dag["root"]]


def fixed_point(phi: dict[str, Any], representation: dict[str, Any] | None = None) -> dict[str, Any]:
    """Construct a real arithmetic fixed point and replay its conditional equivalence.

    Input is an arithmetic formula DAG with exactly one free indexed variable.
    The returned q and m are actual presentation codes satisfying m=SUB(q,i,q).
    ESTABLISHED means the displayed conditional equivalence, with its reviewed
    representation premise still trusted, not proved by the native checker.
    """
    info = validate_arithmetic_dag(phi)
    if info["root_sort"] != "formula" or len(info["free_variables"]) != 1:
        _error("Fixed-point input must be an arithmetic formula with exactly one free variable")
    bundle, reviewed = _bundle(representation)
    record = bundle["representation"]
    sub = record["arithmetic_dag"]
    variable = info["free_variables"][0]
    names = [n["name"] for n in phi["nodes"] + sub["nodes"] if n["op"] in {"var", "forall", "exists"}]
    largest = max((_variable_index(name) for name in names), default=0)
    x, z = "x" + _decimal(largest + 1), "x" + _decimal(largest + 2)
    xterm, zterm = _term("var", x), _term("var", z)
    indexterm = _term("num", x[1:])
    sub_template = sub
    for old, replacement in [("x0", xterm), ("x1", indexterm), ("x2", xterm), ("x3", zterm)]:
        sub_template = dag_substitute(sub_template, old, replacement)
    phi_z = dag_substitute(phi, variable, zterm)
    delta_builder = _DAGBuilder()
    sr, pr = _import(delta_builder, sub_template), _import(delta_builder, phi_z)
    body = delta_builder.node("implies", args=[sr, pr])
    delta = delta_builder.export(delta_builder.node("forall", z, [body]))
    q = arithmetic_dag_encode(delta)
    fixed = dag_substitute_numeral(delta, x, q)
    m = arithmetic_dag_encode(fixed)
    if substitute_code(q, x[1:], q) != m:
        raise RuntimeError("Native fixed-point code equation failed")
    mterm = _term("num", m)
    phi_m = dag_substitute(phi, variable, mterm)
    sz = dag_substitute(sub_template, x, _term("num", q))
    sm = dag_substitute(sz, z, mterm)
    builder = _DAGBuilder()
    zr, mr, szr, smr, pzr, pmr, gr = [
        _import(builder, d) for d in (zterm, mterm, sz, sm, phi_z, phi_m, fixed)
    ]

    def binary(op: str, left: int, right: int) -> int:
        return builder.node(op, args=[left, right])

    def iff(left: int, right: int) -> int:
        return binary("and", binary("implies", left, right), binary("implies", right, left))

    equality = binary("eq", zr, mr)
    premise_root = builder.node("forall", z, [iff(szr, equality)])
    target_root = iff(gr, pmr)
    premise, target = builder.export(premise_root), builder.export(target_root)
    steps = []

    def step(
        rule: str,
        root: int,
        premises: tuple[int, ...] | list[int] = (),
        scope: tuple[int, ...] | list[int] = (),
        **extra: Any,
    ) -> None:
        steps.append(
            {
                "rule": rule,
                "formula": builder.export(root),
                "premises": list(premises),
                "scope": list(scope),
                **extra,
            }
        )

    equal_mm = binary("eq", mr, mr)
    step("axiom", premise_root)
    step("assume", gr, scope=[2])
    step("forall_elim", iff(smr, equal_mm), [1], [2], term=mterm)
    step("and_right", binary("implies", equal_mm, smr), [3], [2])
    step("eq_refl", equal_mm, scope=[2])
    step("mp", smr, [5, 4], [2])
    step("forall_elim", binary("implies", smr, pmr), [2], [2], term=mterm)
    step("mp", pmr, [6, 7], [2])
    step("imp_intro", binary("implies", gr, pmr), [8], discharge=[2])
    step("assume", pmr, scope=[10])
    step("assume", szr, scope=[10, 11])
    step("forall_elim", iff(szr, equality), [1], [10, 11], term=zterm)
    step("and_left", binary("implies", szr, equality), [12], [10, 11])
    step("mp", equality, [11, 13], [10, 11])
    step("eq_symm", binary("eq", mr, zr), [14], [10, 11])
    step("eq_elim", pzr, [15, 10], [10, 11], template=phi_z, variable=z)
    step("imp_intro", binary("implies", szr, pzr), [16], [10], discharge=[11])
    step("forall_intro", gr, [17], [10])
    step("imp_intro", binary("implies", pmr, gr), [18], discharge=[10])
    step("and_intro", target_root, [9, 19])
    checked = check_scoped_dag_proof(steps, axioms=[premise], conclusion=target)
    if checked["status"] != "ESTABLISHED":
        raise RuntimeError(
            "Conditional fixed-point derivation failed native replay: " + str(checked["details"])
        )
    witness = {
        "phi": phi,
        "delta": delta,
        "G": fixed,
        "q": q,
        "m": m,
        "variable": variable,
        "diagonal_variable": x,
        "output_variable": z,
        "numbering_id": DAG_ID,
        "program_sha256": record["program_sha256"],
        "arithmetic_sha256": record["arithmetic_sha256"],
        "representation_instance": premise,
        "target": target,
        "derivation": steps,
        "checked_proof": checked,
        "trusted_premises": [premise],
    }
    return _result(
        "ESTABLISHED" if reviewed else "UNKNOWN",
        "SYMBOLIC_CONSTRUCTION",
        "Conditional fixed-point equivalence under the displayed representation premise",
        [{"kind": "REPRESENTATION_INSTANCE", "formula": premise, "proved_by_native_checker": False}],
        [bundle["review"]],
        _LIMITS,
        witness,
        {
            "representation_reviewed": reviewed,
            "code_equation_checked": True,
            "native_derivation_checked": True,
            "formal_kernel_replay": False,
        },
        {"theory": "PA", "numbering": DAG_ID, "representation_id": record["program_id"]},
        [{"program_sha256": record["program_sha256"], "arithmetic_sha256": record["arithmetic_sha256"]}],
    )
