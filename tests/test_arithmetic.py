"""Independent arithmetic, induction and textual grammar reference cases."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

import goedel as g


def test_arithmetic_signature_and_q_axioms():
    signature = g.arithmetic_language()
    assert signature["constants"] == ["zero"]
    assert signature["functions"] == [
        {"name": "S", "arity": 1},
        {"name": "add", "arity": 2},
        {"name": "mul", "arity": 2},
    ]
    axioms = g.q_axioms()
    assert len(axioms) == 7
    expected = [
        "forall x. !(S(x) = @zero)",
        "forall x. forall y. S(x) = S(y) -> x = y",
        "forall x. !(x = @zero) -> exists y. x = S(y)",
        "forall x. (x + @zero) = x",
        "forall x. forall y. (x + S(y)) = S(x + y)",
        "forall x. (x * @zero) = @zero",
        "forall x. forall y. (x * S(y)) = ((x * y) + x)",
    ]
    assert all(g.alpha_equal(a, g.parse_formula(b)) for a, b in zip(axioms, expected))
    assert all(g.free_variables(a) == [] for a in axioms)


@given(st.integers(min_value=0, max_value=1000000))
def test_numeral_exact_expansion_value(value):
    compact = g.numeral(str(value))
    assert g.numeral_value(compact) == str(value)
    assert g.numeral_value(g.expand_numeral(compact)) == str(value)
    assert g.deserialize(g.serialize(compact)) == compact


def test_numeral_horner_literal_and_arithmetic():
    two = g.successor(g.successor(g.zero()))
    three = g.successor(g.multiply(two, g.successor(g.zero())))
    assert g.expand_numeral(g.numeral("3")) == three
    assert g.numeral_value(g.add(g.numeral("9007199254740993"), g.numeral("7"))) == "9007199254741000"
    assert g.numeral_value(g.multiply(g.numeral("123456789"), g.numeral("987654321"))) == "121932631112635269"
    assert g.numeral_value(g.numeral("9" * 4096)) == "9" * 4096


@pytest.mark.parametrize("value", [True, -1, 1.5, "-1", "00", "01", "1.0", "", " 1", None])
def test_invalid_numerals(value):
    with pytest.raises(g.GoedelError):
        g.numeral(value)


def test_arithmetic_limits_and_signature_errors():
    for action in [
        lambda: g.numeral("1" * 4097),
        lambda: g.expand_numeral(g.numeral("123456"), max_nodes=5),
        lambda: g.numeral_value(g.multiply(g.numeral("9" * 4096), g.numeral("9" * 4096))),
    ]:
        with pytest.raises(g.GoedelError) as caught:
            action()
        assert caught.value.code == "RESOURCE_LIMIT"
    for term in [g.variable("x"), g.constant("c"), g.function_term("f", []), g.bottom()]:
        with pytest.raises(g.GoedelError):
            g.numeral_value(term)


def test_induction_parameter_closure_and_mutations():
    x, y = g.variable("x"), g.variable("y")
    body = g.equal(g.add(x, y), g.add(y, x))
    instance = g.induction_axiom(body, "x")
    expected = g.parse_formula(
        "forall y. (((@zero + y) = (y + @zero)) & (forall x. ((x + y) = (y + x)) -> ((S(x) + y) = (y + S(x))))) -> (forall x. (x + y) = (y + x))"
    )
    assert g.alpha_equal(instance, expected)
    recognition = g.recognize_induction(instance)
    assert recognition["is_instance"] is True
    assert recognition["parameters"] == ["y"]
    assert g.is_axiom(g.arithmetic_theory("PA"), instance)
    assert not g.is_axiom(g.arithmetic_theory("Q"), instance)
    assert not g.is_axiom(g.arithmetic_theory("PA"), g.induction_axiom(body, "x", close=False))
    assert not g.recognize_induction(g.implication(g.bottom(), g.forall("x", body)))["is_instance"]
    assert g.recognize_induction(g.normalize(instance))["is_instance"]
    with pytest.raises(g.GoedelError):
        g.induction_axiom(g.predicate("P", [x]), "x")


def test_theory_extensions_are_closed_explicit_axioms():
    extra = g.equal(g.zero(), g.successor(g.zero()))
    theory = g.arithmetic_theory("Q", [extra])
    assert theory["consistency_status"] == "NOT_ESTABLISHED"
    assert g.is_axiom(theory, extra)
    theory["schemas"] = ["PA_INDUCTION"]
    with pytest.raises(g.GoedelError):
        g.is_axiom(theory, extra)
    for extensions in [[g.equal(g.variable("x"), g.zero())], [extra, extra]]:
        with pytest.raises(g.GoedelError):
            g.arithmetic_theory("PA", extensions)


@pytest.mark.parametrize(
    "text",
    [
        "forall x. exists y. (S(x) = y) -> !(x = y)",
        "P(x,@c) & Q() | !(R()) -> false",
        "(x + 2 * y) = (x + (2 * y))",
        "forall x. ((x * @zero) = @zero)",
        "false() | forall(x)",
    "(forall = 0) & S(x)",
    ],
)
def test_parser_formatter_roundtrip(text):
    node = g.parse_formula(text)
    assert g.parse_formula(g.format_formula(node)) == node


@pytest.mark.parametrize(
    "text", ["", "x + 1", "forall . x=x", "P(x", "x =", "00=0", "P(x);print(1)", "λx", "P() trailing"]
)
def test_parser_rejects_malformed_text(text):
    with pytest.raises(g.GoedelError):
        g.parse_formula(text)


def test_precedence_and_right_associative_implication():
    p, q, r = [g.predicate(name) for name in ["P", "Q", "R"]]
    assert g.parse_formula("P -> Q -> R") == g.implication(p, g.implication(q, r))
    assert g.parse_formula("P | Q & R") == g.disjunction(p, g.conjunction(q, r))
    with pytest.raises(g.GoedelError):
        g.format_formula(g.variable("x"))
