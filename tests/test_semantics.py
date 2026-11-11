"""Finite models with independently tabulated interpretations and counterexamples."""

import copy
import itertools

import pytest

import goedel as g


def model():
    return g.finite_structure(
        ["0", "1"],
        {"zero": "0"},
        [
            {
                "name": "S",
                "arity": 1,
                "table": [{"args": ["0"], "value": "1"}, {"args": ["1"], "value": "0"}],
            },
            {
                "name": "add",
                "arity": 2,
                "table": [
                    {"args": [a, b], "value": str((int(a) + int(b)) % 2)}
                    for a, b in itertools.product("01", repeat=2)
                ],
            },
            {
                "name": "mul",
                "arity": 2,
                "table": [
                    {"args": [a, b], "value": "1" if a == b == "1" else "0"}
                    for a, b in itertools.product("01", repeat=2)
                ],
            },
        ],
        [
            {
                "name": "P",
                "arity": 1,
                "table": [{"args": ["0"], "value": False}, {"args": ["1"], "value": True}],
            }
        ],
    )


def test_finite_truth_quantifiers_and_counterexample():
    structure = model()
    x = g.variable("x")
    false_q1 = g.forall("x", g.negate(g.equal(g.successor(x), g.zero())))
    result = g.evaluate_formula(false_q1, structure)
    assert result["status"] == "REFUTED"
    assert result["witness"] == {"assignment": {}}
    assert result["mode"] == "FINITE_EXACT"
    existential = g.exists("x", g.predicate("P", [x]))
    assert g.evaluate_formula(existential, structure)["witness"] == {"assignment": {}}
    assert g.evaluate_formula(g.forall("x", g.equal(x, x)), structure)["details"]["value"] is True
    assert (
        g.evaluate_term(g.add(g.numeral("9007199254740993"), g.numeral("1")), structure)["details"]["value"]
        == "0"
    )


@pytest.mark.parametrize("left,right", itertools.product([False, True], repeat=2))
def test_all_propositional_connectives_against_truth_table(left, right):
    structure = g.finite_structure(
        ["e"],
        relations=[
            {"name": "P", "arity": 0, "table": [{"args": [], "value": left}]},
            {"name": "Q", "arity": 0, "table": [{"args": [], "value": right}]},
        ],
    )
    p, q = g.predicate("P"), g.predicate("Q")
    for formula, expected in [
        (g.conjunction(p, q), left and right),
        (g.disjunction(p, q), left or right),
        (g.implication(p, q), (not left) or right),
        (g.negate(p), not left),
        (g.bottom(), False),
    ]:
        assert g.evaluate_formula(formula, structure)["details"]["value"] is expected


def test_semantic_substitution_independent_assignments():
    structure = model()
    original = g.forall("y", g.equal(g.add(g.variable("x"), g.variable("y")), g.variable("y")))
    substituted = g.substitute(original, "x", g.variable("y"))
    for value in ["0", "1"]:
        expected = all((int(value) + y) % 2 == y for y in [0, 1])
        assert g.evaluate_formula(substituted, structure, {"y": value})["details"]["value"] == expected
        assert (
            g.evaluate_formula(g.normalize(substituted), structure, {"y": value})["details"]["value"]
            == expected
        )


def test_model_check_list_and_free_assignments():
    structure = model()
    x = g.variable("x")
    result = g.finite_model_check([g.equal(x, x), g.equal(g.successor(x), x)], structure)
    assert result["status"] == "REFUTED"
    assert result["details"]["checked_formulas"] == 2
    assert result["witness"] == {"formula_index": 2, "assignment": {"x": "0"}}
    assert g.finite_model_check([g.equal(x, x)], structure)["status"] == "ESTABLISHED"


def test_missing_interpretation_rejected_even_in_unused_branch():
    structure = model()
    formula = g.implication(g.bottom(), g.predicate("Missing"))
    with pytest.raises(g.GoedelError):
        g.evaluate_formula(formula, structure)


def test_malformed_and_incomplete_structures():
    for mutate in [
        lambda m: m["functions"][0]["table"].pop(),
        lambda m: m["relations"][0]["table"][0].update(value=0),
        lambda m: m["constants"].update(zero="outside"),
    ]:
        structure = copy.deepcopy(model())
        mutate(structure)
        with pytest.raises(g.GoedelError):
            g.evaluate_formula(g.bottom(), structure)
    with pytest.raises(g.GoedelError):
        g.evaluate_formula(g.equal(g.variable("x"), g.zero()), model())
    with pytest.raises(g.GoedelError) as caught:
        g.evaluate_formula(g.forall("x", g.equal(g.variable("x"), g.variable("x"))), model(), max_steps=1)
    assert caught.value.code == "RESOURCE_LIMIT"


def test_numeral_means_horner_term_in_nonarithmetic_structure():
    structure = model()
    # Deliberately alter multiplication. Numeral 2 now differs from S(S(0)).
    for row in next(r for r in structure["functions"] if r["name"] == "mul")["table"]:
        row["value"] = "1"
    assert g.evaluate_term(g.numeral("2"), structure)["details"]["value"] == "1"
    assert g.evaluate_term(g.successor(g.successor(g.zero())), structure)["details"]["value"] == "0"


def test_shadowed_bound_variable_cannot_overwrite_counterexample_assignment():
    structure = g.finite_structure(
        ["a", "b"],
        relations=[
            {
                "name": "P",
                "arity": 1,
                "table": [{"args": ["a"], "value": True}, {"args": ["b"], "value": False}],
            }
        ],
    )
    p = g.predicate("P", [g.variable("x")])
    formula = g.implication(p, g.forall("x", p))
    # Independently: at x=a the antecedent holds but the universal consequent fails.
    # At x=b the implication is true, so b is not a counterexample assignment.
    assert g.evaluate_formula(formula, structure, {"x": "b"})["status"] == "ESTABLISHED"
    checked = g.finite_model_check([formula], structure)
    assert checked["status"] == "REFUTED"
    assert checked["witness"] == {"formula_index": 1, "assignment": {"x": "a"}}
    replay = g.evaluate_formula(formula, structure, checked["witness"]["assignment"])
    assert replay["status"] == "REFUTED"
    assert replay["witness"]["assignment"] == {"x": "a"}
    assert g.evaluate_formula(formula, structure, replay["witness"]["assignment"])["status"] == "REFUTED"
