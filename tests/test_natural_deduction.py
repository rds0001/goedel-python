"""Hand-derived FOL proofs, scope mutations and eigenvariable counterexamples."""

import copy

import pytest

import goedel as g


def step(rule, formula, premises=None, scope=None, **extra):
    return {
        "rule": rule,
        "formula": formula,
        "premises": [] if premises is None else premises,
        "scope": [] if scope is None else scope,
        **extra,
    }


def test_identity_discharge_and_closed_scope_mutation():
    a = g.predicate("A")
    steps = [
        step("assume", a, scope=[1]),
        step("reiterate", a, [1], [1]),
        step("imp_intro", g.implication(a, a), [2], discharge=[1]),
    ]
    result = g.check_scoped_proof(steps)
    assert result["status"] == "ESTABLISHED"
    assert result["dependencies"] == [
        {"step": 1, "local_assumptions": [1]},
        {"step": 2, "local_assumptions": [1]},
        {"step": 3, "local_assumptions": []},
    ]
    assert g.check_scoped_proof(result["witness"])["status"] == "ESTABLISHED"
    assert g.check_scoped_proof(steps + [step("reiterate", a, [1])])["status"] == "REFUTED"
    assert g.check_scoped_proof(steps[:2])["details"]["reason"] == "UNCLOSED_SCOPE"
    changed = copy.deepcopy(steps)
    changed[2]["discharge"] = [2]
    assert g.check_scoped_proof(changed)["status"] == "REFUTED"


def test_nested_scope_discharge():
    a, b = g.predicate("A"), g.predicate("B")
    steps = [
        step("assume", a, scope=[1]),
        step("assume", b, scope=[1, 2]),
        step("reiterate", a, [1], [1, 2]),
        step("imp_intro", g.implication(b, a), [3], [1], discharge=[2]),
        step("imp_intro", g.implication(a, g.implication(b, a)), [4], discharge=[1]),
    ]
    assert g.check_scoped_proof(steps)["status"] == "ESTABLISHED"
    changed = copy.deepcopy(steps)
    changed[3]["scope"] = []
    assert g.check_scoped_proof(changed)["status"] == "REFUTED"


def test_propositional_rules_independently():
    a, b, c = [g.predicate(n) for n in ["A", "B", "C"]]
    cases = [
        ("mp", [a, g.implication(a, b)], b),
        ("and_intro", [a, b], g.conjunction(a, b)),
        ("and_left", [g.conjunction(a, b)], a),
        ("and_right", [g.conjunction(a, b)], b),
        ("or_left", [a], g.disjunction(a, b)),
        ("or_right", [b], g.disjunction(a, b)),
        ("or_elim", [g.disjunction(a, b), g.implication(a, c), g.implication(b, c)], c),
        ("false_elim", [g.bottom()], a),
        ("not_elim", [a, g.negate(a)], g.bottom()),
    ]
    for rule, premises, target in cases:
        steps = [step("assumption", p) for p in premises]
        steps.append(step(rule, target, list(range(1, len(premises) + 1))))
        assert g.check_scoped_proof(steps, assumptions=premises)["status"] == "ESTABLISHED", rule
        changed = copy.deepcopy(steps)
        changed[-1]["formula"] = g.predicate("Wrong")
        if rule != "false_elim":  # Explosion deliberately permits any formula.
            assert g.check_scoped_proof(changed, assumptions=premises)["status"] == "REFUTED", rule


def test_negation_and_classical_rule():
    a = g.predicate("A")
    steps = [
        step("assume", a, scope=[1]),
        step("assumption", g.negate(a), scope=[1]),
        step("not_elim", g.bottom(), [1, 2], [1]),
        step("not_intro", g.negate(a), [3], discharge=[1]),
    ]
    assert g.check_scoped_proof(steps, [g.negate(a)], logic="intuitionistic")["status"] == "ESTABLISHED"
    classical = [
        step("assume", g.negate(a), scope=[1]),
        step("assumption", g.negate(g.negate(a)), scope=[1]),
        step("not_elim", g.bottom(), [1, 2], [1]),
        step("classical", a, [3], discharge=[1]),
    ]
    assert g.check_scoped_proof(classical, [g.negate(g.negate(a))])["status"] == "ESTABLISHED"
    assert (
        g.check_scoped_proof(classical, [g.negate(g.negate(a))], logic="intuitionistic")["status"]
        == "REFUTED"
    )


def test_equality_and_quantifier_rules():
    x, y, z = [g.variable(n) for n in ["x", "y", "z"]]
    reflexive = [
        step("eq_refl", g.equal(x, x)),
        step("forall_intro", g.forall("x", g.equal(x, x)), [1]),
        step("forall_elim", g.equal(g.zero(), g.zero()), [2], term=g.zero()),
    ]
    assert g.check_scoped_proof(reflexive)["status"] == "ESTABLISHED"
    assert g.check_scoped_proof(reflexive, [g.predicate("P", [x])])["status"] == "REFUTED"
    eqs = [g.equal(x, y), g.equal(y, z)]
    chain = [
        step("assumption", eqs[0]),
        step("assumption", eqs[1]),
        step("eq_trans", g.equal(x, z), [1, 2]),
        step("eq_symm", g.equal(z, x), [3]),
    ]
    assert g.check_scoped_proof(chain, eqs)["status"] == "ESTABLISHED"
    px = g.predicate("P", [x])
    substitution = [
        step("assumption", g.equal(x, y)),
        step("assumption", px),
        step("eq_elim", g.predicate("P", [y]), [1, 2], variable="z", template=g.predicate("P", [z])),
    ]
    assert g.check_scoped_proof(substitution, [g.equal(x, y), px])["status"] == "ESTABLISHED"
    exists = [step("eq_refl", g.equal(x, x)), step("exists_intro", g.exists("z", g.equal(z, x)), [1], term=x)]
    assert g.check_scoped_proof(exists)["status"] == "ESTABLISHED"


def test_existential_elimination_eigenvariable():
    x, a = g.variable("x"), g.variable("a")
    q = g.predicate("Q")
    ex = g.exists("x", g.predicate("P", [x]))
    universal = g.forall("x", g.implication(g.predicate("P", [x]), q))
    pa = g.predicate("P", [a])
    steps = [
        step("assumption", ex),
        step("assumption", universal),
        step("assume", pa, scope=[3]),
        step("forall_elim", g.implication(pa, q), [2], [3], term=a),
        step("mp", q, [3, 4], [3]),
        step("exists_elim", q, [1, 5], discharge=[3], variable="a"),
    ]
    result = g.check_scoped_proof(steps, [ex, universal])
    assert result["status"] == "ESTABLISHED"
    assert result["dependencies"][-1]["local_assumptions"] == []
    assert g.check_scoped_proof(steps, [ex, universal, g.predicate("R", [a])])["status"] == "REFUTED"
    changed = copy.deepcopy(steps)
    changed[-1]["variable"] = "x"
    assert g.check_scoped_proof(changed, [ex, universal])["status"] == "REFUTED"
    # The invalid inference exists x P(x) => P(a) violates eigenvariable freshness.
    bad = [
        step("assumption", ex),
        step("assume", pa, scope=[2]),
        step("exists_elim", pa, [1, 2], discharge=[2], variable="a"),
    ]
    assert g.check_scoped_proof(bad, [ex])["status"] == "REFUTED"


def test_theory_axioms_and_explicit_trust():
    q1 = g.q_axioms()[0]
    assert (
        g.check_scoped_proof([step("axiom", q1)], theory=g.arithmetic_theory("Q"))["status"] == "ESTABLISHED"
    )
    induction = g.induction_axiom(g.equal(g.variable("x"), g.variable("x")), "x")
    assert (
        g.check_scoped_proof([step("axiom", induction)], theory=g.arithmetic_theory("PA"))["status"]
        == "ESTABLISHED"
    )
    assert (
        g.check_scoped_proof([step("axiom", induction)], theory=g.arithmetic_theory("Q"))["status"]
        == "REFUTED"
    )
    p = g.predicate("P")
    assert g.check_scoped_proof([step("axiom", p)], axioms=[p])["status"] == "ESTABLISHED"


def test_malformed_rule_indices_and_shared_signature():
    a = g.predicate("A")
    assert g.check_scoped_proof([])["details"]["reason"] == "EMPTY_PROOF"
    assert g.check_scoped_proof([step("reiterate", a, [1])])["status"] == "REFUTED"
    assert (
        g.check_scoped_proof([step("assumption", a)], [a], conclusion=g.bottom())["details"]["reason"]
        == "CONCLUSION_MISMATCH"
    )
    for bad in [step("unknown", a), step("assumption", a, extra=True), step("reiterate", a, [True])]:
        with pytest.raises(g.GoedelError):
            g.check_scoped_proof([bad])
    with pytest.raises(g.GoedelError):
        g.check_scoped_proof([step("assumption", g.predicate("P"))], [g.predicate("P", [g.zero()])])
