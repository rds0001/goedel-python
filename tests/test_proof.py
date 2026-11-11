import copy

import pytest

import goedel as g


def step(rule, formula, premises=(), **extra):
    return {"rule": rule, "formula": formula, "premises": list(premises), **extra}


def test_mp_and_mutations():
    p, q = g.predicate("P"), g.predicate("Q")
    assumptions = [p, g.implication(p, q)]
    proof = [step("assumption", p), step("assumption", assumptions[1]), step("mp", q, [1, 2])]
    result = g.check_proof(proof, assumptions, conclusion=q)
    assert result["status"] == "ESTABLISHED"
    assert result["mode"] == "CHECKED_DERIVATION"
    assert g.check_proof(result["witness"], assumptions, conclusion=q)["status"] == "ESTABLISHED"
    for refs in ([2, 1], [1, 3], [0, 2], [1, 99], [1]):
        mutated = copy.deepcopy(proof)
        mutated[-1]["premises"] = refs
        answer = g.check_proof(mutated, assumptions)
        assert answer["status"] == "REFUTED"
        assert answer["claim"] == "validity_of_submitted_proof"
        assert answer["details"]["invalid_step"] == 3
    assert g.check_proof(proof, assumptions, conclusion=p)["details"]["reason"] == "CONCLUSION_MISMATCH"


def test_conjunction_and_closed_axioms():
    p, q = g.predicate("P"), g.predicate("Q")
    proof = [step("axiom", p), step("axiom", q), step("and_intro", g.conjunction(p, q), [1, 2]),
             step("and_left", p, [3]), step("and_right", q, [3])]
    assert g.check_proof(proof, axioms=[p, q])["status"] == "ESTABLISHED"
    assert g.check_proof([step("axiom", p)])["status"] == "REFUTED"
    with pytest.raises(g.GoedelError, match="closed"):
        g.check_proof([], axioms=[g.predicate("P", [g.variable("x")])])


def test_quantifier_rules_side_conditions_and_capture():
    x, y = g.variable("x"), g.variable("y")
    universal = g.forall("x", g.forall("y", g.predicate("R", [x, y])))
    instance = g.forall("v0", g.predicate("R", [y, g.variable("v0")]))
    good = [step("axiom", universal), step("forall_elim", instance, [1], term=y)]
    assert g.check_proof(good, axioms=[universal])["status"] == "ESTABLISHED"
    bad = [step("axiom", universal), step("forall_elim", g.forall("y", g.predicate("R", [y, y])), [1], term=y)]
    assert g.check_proof(bad, axioms=[universal])["status"] == "REFUTED"
    px = g.predicate("P", [x])
    assert g.check_proof([step("assumption", px), step("forall_intro", g.forall("x", px), [1])], [px])["status"] == "REFUTED"
    p = g.predicate("P")
    assert g.check_proof([step("axiom", p), step("forall_intro", g.forall("x", p), [1])], axioms=[p])["status"] == "ESTABLISHED"


def test_malformed_proofs_are_input_errors():
    p = g.predicate("P")
    for value in [None, {}, [step("magic", p)], [{"rule": "assumption", "formula": p}],
                  [step("assumption", p, [True])], [step("assumption", p, extra=True)],
                  [step("forall_elim", p, [1])], [step("assumption", g.variable("x"))]]:
        with pytest.raises(g.GoedelError):
            g.check_proof(value)
    with pytest.raises(g.GoedelError) as exc:
        g.check_proof([step("assumption", p)] * 257, [p])
    assert exc.value.code == "RESOURCE_LIMIT"
    assert g.check_proof([])["details"]["reason"] == "EMPTY_PROOF"


def test_joint_signatures():
    p, px = g.predicate("P"), g.predicate("P", [g.variable("x")])
    with pytest.raises(g.GoedelError, match="arity"):
        g.check_proof([step("assumption", p)], [p, px])
    with pytest.raises(g.GoedelError, match="arity"):
        g.bounded_proof_search(px, [p])


def test_search_success_and_rechecked_witness():
    p, q, r = (g.predicate(n) for n in ("P", "Q", "R"))
    assumptions = [g.conjunction(p, g.implication(p, q)), g.implication(q, r)]
    found = g.bounded_proof_search(r, assumptions)
    assert found["status"] == "ESTABLISHED"
    assert found["details"]["termination_reason"] == "GOAL_FOUND"
    assert g.check_proof(found["witness"], assumptions, conclusion=r)["status"] == "ESTABLISHED"
    assert found == g.bounded_proof_search(r, assumptions)


def test_search_limits_not_unprovability():
    p, q = g.predicate("P"), g.predicate("Q")
    budget = g.bounded_proof_search(q, [p, g.implication(p, q)], max_steps=2)
    assert budget["status"] == "UNKNOWN"
    assert budget["details"]["termination_reason"] == "BOUND_EXHAUSTED"
    exhausted = g.bounded_proof_search(q, [p], max_steps=1)
    assert exhausted["status"] == "UNKNOWN"
    assert exhausted["details"]["termination_reason"] == "SEARCH_SPACE_EXHAUSTED"
    assert g.bounded_proof_search(p)["status"] == "UNKNOWN"
    assert g.bounded_proof_search(p, [p], max_steps=1)["status"] == "ESTABLISHED"
    for limit in [0, -1, 257, True, 2.0, "2"]:
        with pytest.raises(g.GoedelError):
            g.bounded_proof_search(p, max_steps=limit)


def test_invalid_conjunction_does_not_construct_out_of_budget_intermediate():
    p = g.predicate("P")
    for _ in range(63):
        p = g.negate(p)
    proof = [step("assumption", p), step("assumption", g.bottom()), step("and_intro", g.bottom(), [1, 2])]
    assert g.check_proof(proof, [p, g.bottom()])["status"] == "REFUTED"
