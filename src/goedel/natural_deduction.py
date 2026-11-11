"""Finite first-order natural deduction with explicit scope opening and discharge."""

from __future__ import annotations

from typing import Any

from .arithmetic import arithmetic_theory, is_axiom
from .proof import _formula, _formulas, _joint_signature, _result
from .syntax import TERMS, Expr, _error, _expr, _free, _name, _wire, alpha_equal, substitute, variable

CALCULUS = "goedel-nd-scoped-v1"
LIMITATION = "Declared assumptions, closed axioms and the selected theory presentation are trusted; this native checker is not a formally verified kernel."
_COUNTS = {
    "assume": 0,
    "assumption": 0,
    "axiom": 0,
    "reiterate": 1,
    "mp": 2,
    "and_intro": 2,
    "and_left": 1,
    "and_right": 1,
    "or_left": 1,
    "or_right": 1,
    "or_elim": 3,
    "false_elim": 1,
    "not_elim": 2,
    "not_intro": 1,
    "imp_intro": 1,
    "classical": 1,
    "forall_elim": 1,
    "forall_intro": 1,
    "exists_intro": 1,
    "exists_elim": 2,
    "eq_refl": 0,
    "eq_symm": 1,
    "eq_trans": 2,
    "eq_elim": 2,
}
_CLOSING = {"imp_intro", "not_intro", "classical", "exists_elim"}
_EXPR_OPS = {
    "formula": _formula,
    "formulas": _formulas,
    "expr": _expr,
    "free": _free,
    "wire": _wire,
    "alpha": alpha_equal,
    "substitute": substitute,
    "variable": variable,
    "name": _name,
    "signature": _joint_signature,
    "calculus": CALCULUS,
    "claim": "validity_of_submitted_scoped_proof",
}


def _check_scoped_proof(
    steps: list[dict[str, Any]],
    assumptions: list[Expr] | tuple[Expr, ...] = (),
    axioms: list[Expr] | tuple[Expr, ...] = (),
    theory: dict[str, Any] | None = None,
    conclusion: Expr | None = None,
    logic: str = "classical",
    _adapter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check a submitted scoped derivation in the documented finite FOL calculus.

    Every step has rule, formula, premises and scope. Scope entries are the
    one-based indices of open ``assume`` steps. Closing rules pop exactly the
    final scope; discharged lines are inaccessible thereafter. The mathematical
    calculus permits arbitrary finite proofs; this API caps submissions at 4096
    steps as an operational limit.
    """
    operations = _EXPR_OPS if _adapter is None else _adapter
    _formula, _formulas, _expr = (operations[k] for k in ("formula", "formulas", "expr"))
    _free, _wire, alpha_equal = (operations[k] for k in ("free", "wire", "alpha"))
    substitute, variable, _name = (operations[k] for k in ("substitute", "variable", "name"))
    _joint_signature = operations["signature"]
    declared, fixed = _formulas(assumptions), _formulas(axioms)
    if any(_free(a) for a in fixed):
        _error("Explicit axioms must be closed")
    if not isinstance(logic, str) or logic not in {"classical", "intuitionistic"}:
        _error("Logic must be classical or intuitionistic")
    if theory is not None:
        if (
            not isinstance(theory, dict)
            or not isinstance(theory.get("id"), str)
            or theory["id"] not in {"Q", "PA"}
        ):
            _error("Unknown arithmetic theory")
        if theory != arithmetic_theory(theory["id"], theory.get("extensions", [])):
            _error("Modified arithmetic theory presentation")
    target = None if conclusion is None else _formula(conclusion)
    if not isinstance(steps, list):
        _error("Proof steps must be a list")
    if len(steps) > 4096:
        _error("Proof step budget exceeded", "RESOURCE_LIMIT")
    parsed = []
    for step in steps:
        if not isinstance(step, dict) or not {"rule", "formula", "premises", "scope"} <= set(step):
            _error("A scoped step requires rule, formula, premises and scope")
        rule = step["rule"]
        if not isinstance(rule, str) or rule not in _COUNTS:
            _error("Unknown scoped proof rule")
        extra = set()
        if rule in _CLOSING:
            extra.add("discharge")
        if rule in {"forall_elim", "exists_intro"}:
            extra.add("term")
        if rule in {"eq_elim", "exists_elim"}:
            extra.add("variable")
        if rule == "eq_elim":
            extra.add("template")
        if set(step) != {"rule", "formula", "premises", "scope"} | extra:
            _error("Unexpected or missing scoped step field")
        for field in {"premises", "scope"} | ({"discharge"} if rule in _CLOSING else set()):
            if not isinstance(step[field], list) or any(type(i) is not int for i in step[field]):
                _error("Step references and scopes must be integer arrays")
        record = {
            "rule": rule,
            "formula": _formula(step["formula"]),
            "premises": list(step["premises"]),
            "scope": list(step["scope"]),
        }
        if "discharge" in extra:
            record["discharge"] = list(step["discharge"])
        if "term" in extra:
            record["term"] = _expr(step["term"])
            if record["term"].kind not in TERMS:
                _error("Term witness required")
        if "variable" in extra:
            record["variable"] = _name(step["variable"])
        if "template" in extra:
            record["template"] = _formula(step["template"])
        parsed.append(record)
    expressions = declared + fixed + [p["formula"] for p in parsed]
    expressions += [p[k] for p in parsed for k in ("term", "template") if k in p]
    if theory is not None:
        expressions += [_expr(a) for a in theory["axioms"] + theory["extensions"]]
    if target is not None:
        expressions.append(target)
    _joint_signature(expressions)
    current: list[int] = []
    closed: set[int] = set()
    supports: list[set[int]] = []
    dependencies: list[dict[str, Any]] = []

    def finish(status: str, invalid: int | None, reason: str) -> dict[str, Any]:
        witness = None
        if status == "ESTABLISHED":
            witness = [
                {k: _wire(v) if k in {"formula", "term", "template"} else v for k, v in step.items()}
                for step in parsed
            ]
        return _result(
            status,
            "CHECKED_DERIVATION",
            operations["claim"],
            [_wire(a) for a in declared],
            [
                {
                    "kind": "NATIVE_RULE_CHECK",
                    "calculus": operations["calculus"],
                    "axioms": [_wire(a) for a in fixed],
                    "theory": theory,
                }
            ],
            [LIMITATION],
            witness,
            {
                "invalid_step": invalid,
                "reason": reason,
                "steps_checked": len(supports),
                "open_scopes": list(current),
            },
            {"logic": logic},
            dependencies,
        )

    def accessible(reference: int, scope: list[int]) -> bool:
        origin = parsed[reference - 1]["scope"]
        return origin == scope[: len(origin)] and not (set(origin) & closed)

    if not parsed:
        return finish("REFUTED", None, "EMPTY_PROOF")
    for index, step in enumerate(parsed, 1):
        rule, formula, refs, scope = step["rule"], step["formula"], step["premises"], step["scope"]
        if len(refs) != _COUNTS[rule] or any(i < 1 or i >= index for i in refs):
            return finish("REFUTED", index, "RULE_MISMATCH")
        if rule == "assume":
            valid_scope = scope == current + [index]
        elif rule in _CLOSING:
            valid_scope = bool(current) and scope == current[:-1] and step["discharge"] == current[-1:]
            if valid_scope:
                endpoint = refs[-1]
                valid_scope = parsed[endpoint - 1]["scope"] == current and accessible(endpoint, current)
                if rule == "exists_elim":
                    valid_scope = valid_scope and accessible(refs[0], scope)
        else:
            valid_scope = scope == current and all(accessible(i, current) for i in refs)
        if not valid_scope:
            return finish("REFUTED", index, "RULE_MISMATCH")
        premises = [parsed[i - 1]["formula"] for i in refs]
        support: set[int] = set().union(*(supports[i - 1] for i in refs))
        valid = False
        if rule == "assume":
            valid, support = True, {index}
        elif rule == "assumption":
            valid = any(alpha_equal(formula, a) for a in declared)
        elif rule == "axiom":
            valid = any(alpha_equal(formula, a) for a in fixed)
            if not valid and theory is not None:
                # Non-arithmetic formulas cannot be axioms of the fixed signature.
                try:
                    valid = is_axiom(theory, formula)
                except ValueError as exc:
                    if getattr(exc, "code", None) == "RESOURCE_LIMIT":
                        raise
                    valid = False
        elif rule == "reiterate":
            valid = alpha_equal(formula, premises[0])
        elif rule == "mp":
            valid = (
                premises[1].kind == "implies"
                and alpha_equal(premises[0], premises[1].args[0])
                and alpha_equal(formula, premises[1].args[1])
            )
        elif rule == "and_intro":
            valid = formula.kind == "and" and all(alpha_equal(a, b) for a, b in zip(formula.args, premises))
        elif rule in {"and_left", "and_right"}:
            valid = premises[0].kind == "and" and alpha_equal(formula, premises[0].args[rule == "and_right"])
        elif rule in {"or_left", "or_right"}:
            valid = formula.kind == "or" and alpha_equal(premises[0], formula.args[rule == "or_right"])
        elif rule == "or_elim":
            disj, left, right = premises
            valid = (
                disj.kind == "or"
                and left.kind == right.kind == "implies"
                and alpha_equal(disj.args[0], left.args[0])
                and alpha_equal(disj.args[1], right.args[0])
                and alpha_equal(formula, left.args[1])
                and alpha_equal(formula, right.args[1])
            )
        elif rule == "false_elim":
            valid = premises[0].kind == "bottom"
        elif rule == "not_elim":
            valid = (
                formula.kind == "bottom"
                and premises[1].kind == "not"
                and alpha_equal(premises[0], premises[1].args[0])
            )
        elif rule in {"imp_intro", "not_intro", "classical"}:
            opening = parsed[current[-1] - 1]["formula"]
            if rule == "imp_intro":
                valid = (
                    formula.kind == "implies"
                    and alpha_equal(formula.args[0], opening)
                    and alpha_equal(formula.args[1], premises[0])
                )
            elif rule == "not_intro":
                valid = (
                    formula.kind == "not"
                    and premises[0].kind == "bottom"
                    and alpha_equal(formula.args[0], opening)
                )
            else:
                valid = (
                    logic == "classical"
                    and opening.kind == "not"
                    and premises[0].kind == "bottom"
                    and alpha_equal(formula, opening.args[0])
                )
        elif rule == "forall_elim":
            prem = premises[0]
            valid = prem.kind == "forall" and alpha_equal(
                formula, substitute(prem.args[0], prem.name, step["term"])
            )
        elif rule == "forall_intro":
            open_formulas = declared + [parsed[i - 1]["formula"] for i in current]
            valid = (
                formula.kind == "forall"
                and all(formula.name not in _free(a) for a in open_formulas)
                and alpha_equal(formula.args[0], premises[0])
            )
        elif rule == "exists_intro":
            valid = formula.kind == "exists" and alpha_equal(
                premises[0], substitute(formula.args[0], formula.name, step["term"])
            )
        elif rule == "exists_elim":
            quantified, endpoint = premises
            opening = parsed[current[-1] - 1]["formula"]
            name = step["variable"]
            forbidden = declared + [parsed[i - 1]["formula"] for i in scope] + [formula, quantified]
            valid = (
                quantified.kind == "exists"
                and alpha_equal(endpoint, formula)
                and all(name not in _free(a) for a in forbidden)
                and alpha_equal(opening, substitute(quantified.args[0], quantified.name, variable(name)))
            )
        elif rule == "eq_refl":
            valid = formula.kind == "eq" and alpha_equal(formula.args[0], formula.args[1])
        elif rule == "eq_symm":
            valid = (
                formula.kind == premises[0].kind == "eq"
                and alpha_equal(formula.args[0], premises[0].args[1])
                and alpha_equal(formula.args[1], premises[0].args[0])
            )
        elif rule == "eq_trans":
            left, right = premises
            valid = (
                formula.kind == left.kind == right.kind == "eq"
                and alpha_equal(left.args[1], right.args[0])
                and alpha_equal(formula.args[0], left.args[0])
                and alpha_equal(formula.args[1], right.args[1])
            )
        elif rule == "eq_elim":
            equality, premise = premises
            valid = (
                equality.kind == "eq"
                and alpha_equal(premise, substitute(step["template"], step["variable"], equality.args[0]))
                and alpha_equal(formula, substitute(step["template"], step["variable"], equality.args[1]))
            )
        if not valid:
            return finish("REFUTED", index, "RULE_MISMATCH")
        if rule == "assume":
            current = scope
        elif rule in _CLOSING:
            discharged = current[-1]
            support.discard(discharged)
            closed.add(discharged)
            current = scope
        supports.append(support)
        dependencies.append({"step": index, "local_assumptions": sorted(support)})
    if current:
        return finish("REFUTED", len(parsed), "UNCLOSED_SCOPE")
    if target is not None and not alpha_equal(target, parsed[-1]["formula"]):
        return finish("REFUTED", len(parsed), "CONCLUSION_MISMATCH")
    return finish("ESTABLISHED", None, "VALID")


def check_scoped_proof(
    steps: list[dict[str, Any]],
    assumptions: list[Expr] | tuple[Expr, ...] = (),
    axioms: list[Expr] | tuple[Expr, ...] = (),
    theory: dict[str, Any] | None = None,
    conclusion: Expr | None = None,
    logic: str = "classical",
) -> dict[str, Any]:
    """Check finite scoped first-order deduction with explicit discharge and eigenvariables.

    Step fields and all rules are specified in SCOPED_PROOFS.md. The 4096-step
    submission limit is operational; validity trusts declared premises and is
    not formal verification of this checker. Malformed inputs raise GoedelError;
    REFUTED concerns the submitted derivation, never its conclusion's truth.
    """
    return _check_scoped_proof(steps, assumptions, axioms, theory, conclusion, logic)
