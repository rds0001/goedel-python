"""Independent examples and invariant tests; no implementation-generated oracles."""
import dataclasses
import hashlib
import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import goedel as g


def test_constructors_and_wire():
    x, zero = g.variable("x"), g.constant("zero")
    successor = g.function_term("S", [x])
    assert g.serialize(x) == '{"args":[],"kind":"var","name":"x"}'
    assert g.validate_expr(g.equal(successor, zero))
    assert g.validate_expr(g.negate(g.bottom()))
    assert g.validate_expr(g.disjunction(g.predicate("A"), g.predicate("B")))
    assert g.validate_expr(g.exists("x", g.equal(x, zero)))
    assert g.bound_variables(g.forall("x", g.exists("y", g.predicate("R", [x, g.variable("y")])))) == ["x", "y"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        x.name = "z"


@pytest.mark.parametrize("name", ["", "a b", "κ", "a" * 65, "x\n", 1, None, "1x"])
def test_bad_names(name):
    with pytest.raises(g.GoedelError, match="Names") as exc:
        g.variable(name)
    assert exc.value.code == "INVALID_INPUT"


@pytest.mark.parametrize("factory", [
    lambda: g.negate(g.variable("x")),
    lambda: g.equal(g.predicate("P"), g.variable("x")),
    lambda: g.function_term("f", [g.predicate("P")]),
    lambda: g.predicate("P", [g.predicate("Q")]),
    lambda: g.conjunction(g.predicate("P"), g.predicate("P", [g.variable("x")])),
    lambda: g.Expr("strange"),
    lambda: g.Expr("bottom", "x"),
    lambda: g.Expr("not"),
    lambda: g.Expr("var", "x", []),
])
def test_wrong_types_and_arities(factory):
    with pytest.raises(g.GoedelError):
        factory()


def test_capture_avoidance_shadowing_and_determinism():
    x, y = g.variable("x"), g.variable("y")
    source = g.forall("y", g.predicate("R", [x, y]))
    expected = g.forall("v0", g.predicate("R", [y, g.variable("v0")]))
    assert g.substitute(source, "x", y) == expected
    assert g.free_variables(expected) == ["y"]
    assert g.substitute(g.forall("x", g.predicate("P", [x])), "x", y) == g.forall("x", g.predicate("P", [x]))
    assert g.substitute(g.forall("y", g.predicate("P", [y])), "x", y) == g.forall("y", g.predicate("P", [y]))
    nested = g.forall("y", g.conjunction(g.predicate("P", [x]), g.forall("y", g.predicate("Q", [y]))))
    changed = g.substitute(nested, "x", y)
    assert changed == g.forall("v0", g.conjunction(g.predicate("P", [y]), g.forall("y", g.predicate("Q", [y]))))
    with pytest.raises(g.GoedelError):
        g.substitute(source, "x", g.bottom())


def test_alpha_normalization_preserves_free_variables():
    x, y, v0 = g.variable("x"), g.variable("y"), g.variable("v0")
    a = g.forall("x", g.predicate("R", [x, v0]))
    b = g.forall("y", g.predicate("R", [y, v0]))
    assert g.alpha_equal(a, b)
    assert g.normalize(a) == g.forall("v1", g.predicate("R", [g.variable("v1"), v0]))
    assert not g.alpha_equal(g.forall("x", g.predicate("R", [x, y])), g.forall("y", g.predicate("R", [x, y])))
    assert g.fingerprint(a) != g.fingerprint(b)


def test_independent_byte_numbering():
    expr = g.variable("x")
    wire = b'{"args":[],"kind":"var","name":"x"}'
    expected = 256 ** len(wire) + sum(byte * 256 ** (len(wire) - index - 1) for index, byte in enumerate(wire))
    assert g.encode(expr) == str(expected)
    assert expected > 2**53
    assert g.decode(str(expected)) == expr
    assert g.fingerprint(expr) == hashlib.sha256(wire).hexdigest()
    assert g.numbering()["id"] == "goedel-json-byte-v1"
    noncanonical = str(int.from_bytes(b'\x01' + b' {"args":[],"kind":"var","name":"x"}', "big"))
    with pytest.raises(g.GoedelError, match="canonical"):
        g.decode(noncanonical)


@pytest.mark.parametrize("code", ["0", "01", "-1", "1.5", 2, True, "1", "256", "512", str(int.from_bytes(b'\x01\xff', 'big'))])
def test_invalid_codes(code):
    with pytest.raises(g.GoedelError):
        g.decode(code)


@pytest.mark.parametrize("text", ["null", "[]", "NaN", '{"args":[],"kind":"var","name":"x","extra":1}', '{"args":[],"kind":"var","name":"x","name":"y"}', '{"args":{},"kind":"var","name":"x"}', "{"])
def test_malformed_wire(text):
    with pytest.raises(g.GoedelError):
        g.deserialize(text)


def test_resource_limits():
    expr = g.predicate("P")
    for _ in range(63):
        expr = g.negate(expr)
    with pytest.raises(g.GoedelError) as exc:
        g.negate(expr)
    assert exc.value.code == "RESOURCE_LIMIT"
    with pytest.raises(g.GoedelError) as exc:
        g.encode(expr)
    assert exc.value.code == "RESOURCE_LIMIT"
    with pytest.raises(g.GoedelError):
        g.decode("1" * 2501)
    with pytest.raises(g.GoedelError):
        g.deserialize(" " * 65537)
    with pytest.raises(g.GoedelError):
        g.predicate("P", [g.variable("x")] * 1000)
    with pytest.raises(g.GoedelError) as exc:
        g.predicate("P", [g.constant("a" * 64)] * 900)
    assert exc.value.code == "RESOURCE_LIMIT"
    cycle = {"kind": "not", "name": "", "args": []}
    cycle["args"].append(cycle)
    with pytest.raises(g.GoedelError, match="Cyclic"):
        g.validate_expr(cycle)


names = st.sampled_from(["x", "y", "z", "v0", "v1"])
terms = st.recursive(names.map(g.variable), lambda children: st.lists(children, min_size=1, max_size=1).map(lambda args: g.function_term("f", args)), max_leaves=5)
formulas = st.recursive(terms.map(lambda t: g.predicate("P", [t])), lambda children: st.one_of(children.map(g.negate), st.tuples(names, children).map(lambda pair: g.forall(*pair)), st.tuples(children, children).map(lambda pair: g.conjunction(*pair))), max_leaves=6)


@settings(max_examples=60, deadline=None)
@given(formulas)
def test_roundtrip_and_alpha_invariants(expr):
    assert g.deserialize(g.serialize(expr)) == expr
    assert g.normalize(g.normalize(expr)) == g.normalize(expr)
    assert g.free_variables(g.normalize(expr)) == g.free_variables(expr)
    assert g.alpha_equal(expr, g.normalize(expr))
    if len(g.serialize(expr)) <= 1024:
        assert g.decode(g.encode(expr)) == expr


@settings(max_examples=50, deadline=None)
@given(formulas, names, terms)
def test_substitution_free_variable_law(expr, name, term):
    before = set(g.free_variables(expr))
    expected = (before - {name}) | (set(g.free_variables(term)) if name in before else set())
    assert set(g.free_variables(g.substitute(expr, name, term))) == expected


def test_reject_nonexpression_inputs():
    for value in [None, 1, True, [], {"kind": "var"}]:
        with pytest.raises(g.GoedelError):
            g.validate_expr(value)
    assert g.deserialize(json.dumps({"name": "x", "kind": "var", "args": []})) == g.variable("x")
