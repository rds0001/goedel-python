"""Checking and bounded search in an explicitly limited deduction fragment."""
from __future__ import annotations

from typing import Any

from .syntax import (
    FORMULAS,
    TERMS,
    Expr,
    _error,
    _expr,
    _free,
    _wire,
    alpha_equal,
    normalize,
    serialize,
    substitute,
)

CALCULUS = "goedel-nd-fragment-v1"
PROOF_LIMIT = "Assumptions and closed axioms are trusted; the checker is not a formally verified kernel."
SEARCH_LIMIT = "Finite closure under modus ponens and conjunction projection; failure is not unprovability."
RULE_COUNTS = {"assumption": 0, "axiom": 0, "mp": 2, "and_intro": 2,
               "and_left": 1, "and_right": 1, "forall_elim": 1, "forall_intro": 1}


def _formula(value: Any) -> Expr:
    expr = _expr(value)
    if expr.kind not in FORMULAS:
        _error("A formula is required")
    return expr


def _formulas(values: Any) -> list[Expr]:
    if not isinstance(values, (list, tuple)):
        _error("Formula collection must be a list or tuple")
    if len(values) > 1000:
        _error("Formula collection budget exceeded", "RESOURCE_LIMIT")
    return [_formula(v) for v in values]


def _joint_signature(values: list[Expr]) -> None:
    arities: dict[tuple[str, str], int] = {}

    def walk(node: Expr) -> None:
        if node.kind in {"func", "pred"}:
            key = (node.kind, node.name)
            if key in arities and arities[key] != len(node.args):
                _error("Inconsistent symbol arity across proof context")
            arities[key] = len(node.args)
        for arg in node.args:
            walk(arg)

    for value in values:
        walk(value)


def _result(status: str, mode: str, claim: str, assumptions: Any,
            evidence: list[Any], limitations: list[str], witness: Any,
            details: dict[str, Any], context: Any = None,
            dependencies: Any = None) -> dict[str, Any]:
    return {"status": status, "mode": mode, "claim": claim,
            "context": {} if context is None else context, "assumptions": assumptions,
            "evidence": evidence, "dependencies": [] if dependencies is None else dependencies,
            "limitations": limitations, "witness": witness, "details": details}


def check_proof(steps: list[dict[str, Any]], assumptions: list[Expr] | tuple[Expr, ...] = (),
                axioms: list[Expr] | tuple[Expr, ...] = (),
                conclusion: Expr | None = None) -> dict[str, Any]:
    """Validate a finite submitted derivation relative to explicit trusted premises.

    Steps use one-based earlier indices. REFUTED concerns the submitted proof's
    validity, never the truth of its formula. Malformed data raise GoedelError.
    """
    declared, fixed = _formulas(assumptions), _formulas(axioms)
    if any(_free(axiom) for axiom in fixed):
        _error("Explicit axioms must be closed formulas")
    target = None if conclusion is None else _formula(conclusion)
    if not isinstance(steps, list):
        _error("Proof steps must be a list")
    if len(steps) > 256:
        _error("Proof step budget exceeded", "RESOURCE_LIMIT")
    parsed: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict) or not {"rule", "formula", "premises"} <= set(step):
            _error("Each step requires rule, formula and premises")
        rule = step["rule"]
        if not isinstance(rule, str) or rule not in RULE_COUNTS:
            _error("Unsupported proof rule")
        allowed = {"rule", "formula", "premises"} | ({"term"} if rule == "forall_elim" else set())
        if set(step) != allowed:
            _error("Unexpected or missing proof-step field")
        if not isinstance(step["premises"], list) or any(type(i) is not int for i in step["premises"]):
            _error("Premises must be an array of integer indices")
        record = {"rule": rule, "formula": _formula(step["formula"]), "premises": list(step["premises"])}
        if rule == "forall_elim":
            record["term"] = _expr(step["term"])
            if record["term"].kind not in TERMS:
                _error("Universal elimination requires a term")
        parsed.append(record)
    all_exprs = declared + fixed + [p["formula"] for p in parsed]
    all_exprs += [p["term"] for p in parsed if "term" in p]
    if target is not None:
        all_exprs.append(target)
    _joint_signature(all_exprs)
    evidence = [{"kind": "NATIVE_RULE_CHECK", "calculus": CALCULUS,
                 "axioms": [_wire(a) for a in fixed]}]

    def result(status: str, invalid_step: int | None, reason: str) -> dict[str, Any]:
        witness = None
        if status == "ESTABLISHED":
            witness = [{"rule": p["rule"], "formula": _wire(p["formula"]), "premises": p["premises"],
                        **({"term": _wire(p["term"])} if "term" in p else {})} for p in parsed]
        return _result(status, "CHECKED_DERIVATION", "validity_of_submitted_proof",
                       [_wire(a) for a in declared], evidence, [PROOF_LIMIT], witness,
                       {"invalid_step": invalid_step, "reason": reason})

    if not parsed:
        return result("REFUTED", None, "EMPTY_PROOF")
    assumption_free = set().union(*(_free(a) for a in declared))
    for index, step in enumerate(parsed, 1):
        rule, formula, refs = step["rule"], step["formula"], step["premises"]
        if len(refs) != RULE_COUNTS[rule] or any(i < 1 or i >= index for i in refs):
            return result("REFUTED", index, "RULE_MISMATCH")
        premises = [parsed[i - 1]["formula"] for i in refs]
        valid = False
        if rule == "assumption":
            valid = any(alpha_equal(formula, a) for a in declared)
        elif rule == "axiom":
            valid = any(alpha_equal(formula, a) for a in fixed)
        elif rule == "mp":
            first, second = premises
            valid = second.kind == "implies" and alpha_equal(first, second.args[0]) and alpha_equal(formula, second.args[1])
        elif rule == "and_intro":
            valid = (formula.kind == "and" and alpha_equal(formula.args[0], premises[0])
                     and alpha_equal(formula.args[1], premises[1]))
        elif rule in {"and_left", "and_right"}:
            premise = premises[0]
            valid = premise.kind == "and" and alpha_equal(formula, premise.args[0 if rule == "and_left" else 1])
        elif rule == "forall_elim":
            premise = premises[0]
            valid = premise.kind == "forall" and alpha_equal(formula, substitute(premise.args[0], premise.name, step["term"]))
        elif rule == "forall_intro":
            valid = (formula.kind == "forall" and formula.name not in assumption_free
                     and alpha_equal(formula.args[0], premises[0]))
        if not valid:
            return result("REFUTED", index, "RULE_MISMATCH")
    if target is not None and not alpha_equal(parsed[-1]["formula"], target):
        return result("REFUTED", len(parsed), "CONCLUSION_MISMATCH")
    return result("ESTABLISHED", None, "VALID")


def bounded_proof_search(goal: Expr, assumptions: list[Expr] | tuple[Expr, ...] = (),
                         max_steps: int = 64) -> dict[str, Any]:
    """Finite deterministic closure under MP and conjunction projections only."""
    target, declared = _formula(goal), _formulas(assumptions)
    if type(max_steps) is not int or not 1 <= max_steps <= 256:
        _error("max_steps must be an integer from 1 to 256")
    _joint_signature([target, *declared])
    facts: list[Expr] = []
    steps: list[dict[str, Any]] = []
    seen: set[str] = set()
    termination: str | None = None

    def add(formula: Expr, rule: str, premises: list[int]) -> bool:
        nonlocal termination
        key = serialize(normalize(formula))
        if key in seen:
            return False
        if len(steps) == max_steps:
            termination = "BOUND_EXHAUSTED"
            return False
        seen.add(key)
        facts.append(formula)
        steps.append({"rule": rule, "formula": formula, "premises": premises})
        if alpha_equal(formula, target):
            termination = "GOAL_FOUND"
        return True

    for assumption in declared:
        add(assumption, "assumption", [])
        if termination:
            break
    while termination is None:
        changed = False
        snapshot = list(enumerate(facts, 1))
        for i, formula in snapshot:
            if formula.kind == "and":
                for rule, child in zip(("and_left", "and_right"), formula.args):
                    changed = add(child, rule, [i]) or changed
                    if termination:
                        break
            if termination:
                break
        if termination:
            break
        snapshot = list(enumerate(facts, 1))
        for i, first in snapshot:
            for j, second in snapshot:
                if second.kind == "implies" and alpha_equal(first, second.args[0]):
                    changed = add(second.args[1], "mp", [i, j]) or changed
                    if termination:
                        break
            if termination:
                break
        if not changed and not termination:
            termination = "SEARCH_SPACE_EXHAUSTED"
    witness = None
    if termination == "GOAL_FOUND":
        checked = check_proof(steps, declared, conclusion=target)
        if checked["status"] != "ESTABLISHED":
            raise RuntimeError("Internal search witness failed independent proof checking")
        witness = checked["witness"]
    return _result("ESTABLISHED" if termination == "GOAL_FOUND" else "UNKNOWN",
                   "BOUNDED_SEARCH", "bounded_derivability", [_wire(a) for a in declared],
                   [], [SEARCH_LIMIT], witness,
                   {"termination_reason": termination, "steps_used": len(steps)})
