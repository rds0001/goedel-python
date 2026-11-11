"""Independent natural-code literals and lexical DAG substitution checks."""

import copy
import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

import goedel as g


@pytest.mark.parametrize(
    "values,code",
    [
        ([], "1"),
        (["0"], "5"),
        (["1"], "19"),
        (["2"], "27"),
        (["3"], "71"),
        (["4"], "87"),
        (["0", "0"], "21"),
        (["0", "1"], "77"),
        (["1", "0"], "83"),
        (["2", "0"], "91"),
    ],
)
def test_sequence_independently_computed_literals(values, code):
    assert g.sequence_encode(values) == code
    assert g.sequence_decode(code) == values


@given(st.lists(st.integers(min_value=0, max_value=10**20).map(str), max_size=20))
def test_sequence_roundtrip(values):
    assert g.sequence_decode(g.sequence_encode(values)) == values


def test_sequence_invalid_and_operational_budgets():
    for code in ["0", "2", "3", "4", "6", "7", "01", "-1"]:
        with pytest.raises(g.GoedelError):
            g.sequence_decode(code)
    for action in [
        lambda: g.sequence_encode(["0"], max_items=0),
        lambda: g.sequence_encode(["1"], max_bits=4),
        lambda: g.sequence_decode("19", max_bits=4),
    ]:
        with pytest.raises(g.GoedelError) as caught:
            action()
        assert caught.value.code == "RESOURCE_LIMIT"


def test_exact_dag_cells_and_index_mapping():
    dag = g.arithmetic_dag(g.equal(g.variable("x"), g.zero()))
    assert dag == {
        "schema_version": "1.0",
        "nodes": [
            {"op": "var", "name": "x376", "args": []},
            {"op": "zero", "name": "", "args": []},
            {"op": "eq", "name": "", "args": [0, 1]},
        ],
        "root": 2,
    }
    code = g.arithmetic_dag_encode(dag)
    assert g.sequence_decode(code) == [
        "20261105",
        "1",
        "3",
        "1",
        "376",
        "0",
        "0",
        "2",
        "0",
        "0",
        "0",
        "6",
        "0",
        "1",
        "2",
    ]
    assert g.arithmetic_dag_decode(code) == dag
    assert g.validate_arithmetic_dag(dag) == {
        "nodes": 3,
        "root_sort": "formula",
        "expanded_nodes": "3",
        "free_variables": ["x376"],
    }
    assert json.loads(g.serialize_arithmetic_dag(dag)) == dag
    assert len(g.dag_fingerprint(dag)) == 64
    assert g.arithmetic_dag(g.variable("x0"))["nodes"][0]["name"] == "x96304"


def test_exact_terms_and_exponential_sharing():
    term = g.arithmetic_dag(g.numeral("9007199254740993"))
    assert g.validate_arithmetic_dag(term)["root_sort"] == "term"
    assert g.arithmetic_dag_decode(g.arithmetic_dag_encode(term)) == term
    nodes = [{"op": "zero", "name": "", "args": []}]
    for i in range(1, 100):
        nodes.append({"op": "add", "name": "", "args": [i - 1, i - 1]})
    dag = {"schema_version": "1.0", "nodes": nodes, "root": 99}
    assert g.validate_arithmetic_dag(dag)["expanded_nodes"] == str(2**100 - 1)


def test_closed_substitution_exact_two_copy_presentation_and_binding():
    x = g.variable("x")
    original = g.arithmetic_dag(g.conjunction(g.equal(x, g.zero()), g.forall("x", g.equal(x, x))))
    changed = g.dag_substitute_numeral(original, "x376", "7")
    count = len(original["nodes"])
    assert changed["nodes"][:count] == original["nodes"]
    assert changed["root"] == 2 * count - 1
    assert g.validate_arithmetic_dag(changed)["free_variables"] == []
    expected = g.arithmetic_dag(
        g.conjunction(g.equal(g.numeral("7"), g.zero()), g.forall("x", g.equal(x, x)))
    )
    assert g.dag_alpha_equal(changed, expected)
    assert (
        g.arithmetic_dag_decode(g.substitute_code(g.arithmetic_dag_encode(original), "376", "7")) == changed
    )
    assert g.substitute_code("0", "0", "7") == "0"
    assert g.substitute_code(g.sequence_encode(["1", "2"]), "0", "7") == "0"


def test_general_capture_avoiding_dag_substitution():
    x, y = g.variable("x"), g.variable("y")
    original = g.arithmetic_dag(g.forall("y", g.equal(x, y)))
    changed = g.dag_substitute(original, "x376", g.arithmetic_dag(y))
    assert g.validate_arithmetic_dag(changed)["free_variables"] == ["x377"]
    assert changed["nodes"][-1]["name"] == "x378"
    expected = g.arithmetic_dag(g.substitute(g.forall("y", g.equal(x, y)), "x", y))
    assert g.dag_alpha_equal(changed, expected)
    assert not g.dag_alpha_equal(original, changed)


def test_malformed_dag_codes_totalize_but_not_resource_errors():
    valid = g.arithmetic_dag(g.equal(g.zero(), g.zero()))
    for mutation in [
        lambda d: d["nodes"][-1].update(args=[1, 1]),
        lambda d: d["nodes"][0].update(name="not_empty"),
        lambda d: d.update(root=0),
    ]:
        bad = copy.deepcopy(valid)
        mutation(bad)
        with pytest.raises(g.GoedelError):
            g.validate_arithmetic_dag(bad)
    cells = ["20261105", "1", "1", "2", "1", "0", "0"]
    assert g.substitute_code(g.sequence_encode(cells), "0", "0") == "0"
    with pytest.raises(g.GoedelError):
        g.substitute_code("01", "0", "0")


def test_scoped_dag_proof_reuses_native_rules_and_binders():
    x, y = g.variable("x"), g.variable("y")
    reflexive = g.arithmetic_dag(g.equal(x, x))
    universal = g.arithmetic_dag(g.forall("x", g.equal(x, x)))
    constant = g.arithmetic_dag(g.zero())
    instantiated = g.arithmetic_dag(g.equal(g.zero(), g.zero()))
    steps = [
        {"rule": "eq_refl", "formula": reflexive, "premises": [], "scope": []},
        {"rule": "forall_intro", "formula": universal, "premises": [1], "scope": []},
        {"rule": "forall_elim", "formula": instantiated, "premises": [2], "scope": [], "term": constant},
    ]
    result = g.check_scoped_dag_proof(steps)
    assert result["status"] == "ESTABLISHED"
    assert g.check_scoped_dag_proof(result["witness"])["status"] == "ESTABLISHED"
    assert g.check_scoped_dag_proof(steps, [g.arithmetic_dag(g.equal(x, y))])["status"] == "REFUTED"
    bad = copy.deepcopy(steps)
    bad[-1]["formula"] = g.arithmetic_dag(g.bottom())
    assert g.check_scoped_dag_proof(bad)["status"] == "REFUTED"


def test_proof_transport_is_distinct_from_proof_validity():
    theory = g.arithmetic_theory("PA")
    steps = [{"rule": "axiom", "formula": g.q_axioms()[0], "premises": [], "scope": []}]
    proof = g.proof_object(steps, theory=theory)
    code = g.encode_proof(proof)
    assert g.decode_proof(code) == proof
    assert g.check_proof_code(code, expected_theory=theory)["status"] == "ESTABLISHED"
    with pytest.raises(g.GoedelError):
        g.check_proof_code(code, expected_theory=g.arithmetic_theory("Q"))
    invalid = g.proof_object(
        [{"rule": "eq_refl", "formula": g.equal(g.zero(), g.numeral("1")), "premises": [], "scope": []}]
    )
    assert g.check_proof_code(g.encode_proof(invalid))["status"] == "REFUTED"
    invalid["calculus"] = "other"
    with pytest.raises(g.GoedelError):
        g.encode_proof(invalid)


@pytest.mark.parametrize("binder", ["bforall", "bexists"])
def test_substitution_in_bound_renames_shadowing_binder(binder):
    original = {"schema_version": "1.0", "nodes": [
        {"op": "var", "name": "x0", "args": []},
        {"op": "var", "name": "x1", "args": []},
        {"op": "eq", "name": "", "args": [1, 1]},
        {"op": binder, "name": "x1", "args": [0, 2]},
    ], "root": 3}
    replacement = {"schema_version": "1.0", "nodes": [{"op": "var", "name": "x1", "args": []}], "root": 0}
    result = g.dag_substitute(original, "x0", replacement)
    assert g.validate_arithmetic_dag(result, bounded=True)["free_variables"] == ["x1"]
    bound, body = result["nodes"][-1]["args"]
    assert result["nodes"][-1]["name"] == "x2"
    assert result["nodes"][bound] == {"op": "var", "name": "x1", "args": []}
    assert all(result["nodes"][a]["name"] == "x2" for a in result["nodes"][body]["args"])
