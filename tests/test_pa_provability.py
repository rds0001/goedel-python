"""Native replay of explicit Hilbert examples and arithmetic predicate identities."""

import pytest

import goedel as g


def record(rule, formula, a="0", b="0"):
    return {"rule": rule, "formula": g.arithmetic_dag_encode(formula), "aux_a": a, "aux_b": b}


@pytest.mark.parametrize("index", range(1, 8))
def test_seven_literal_hilbert_axioms(index):
    axiom = g.hilbert_q_axiom(index)
    step = record(10 + index, axiom)
    code = g.pa_proof_encode([step])
    assert g.pa_proof_decode(code) == [step]
    result = g.check_pa_proof(code, step["formula"])
    assert result["status"] == "ESTABLISHED"
    assert result["mode"] == "CHECKED_DERIVATION"
    assert result["details"]["output"] == "1"
    assert not result["assumptions"]


def test_wrong_conclusion_unknown_rule_and_unused_aux_rejected():
    step = record(14, g.hilbert_q_axiom(4))
    target = step["formula"]
    code = g.pa_proof_encode([step])
    other = g.arithmetic_dag_encode(g.hilbert_q_axiom(6))
    assert g.check_pa_proof(code, other)["status"] == "REFUTED"
    for patch in [{"rule": 0}, {"rule": 9}, {"aux_a": "1"}, {"aux_b": "1"}]:
        broken = dict(step, **patch)
        assert g.check_pa_proof(g.pa_proof_encode([broken]), target)["status"] == "REFUTED"
    assert g.check_pa_proof(code, target, max_steps=1)["status"] == "UNKNOWN"
    assert g.check_pa_proof("0", target)["status"] == "REFUTED"


def test_reflexivity_and_generalization_without_assumptions():
    reflexive = g.arithmetic_dag(g.parse_formula("x = x"))
    x = g.validate_arithmetic_dag(reflexive)["free_variables"][0]
    general = {
        "schema_version": "1.0",
        "nodes": [*reflexive["nodes"], {"op": "forall", "name": x, "args": [reflexive["root"]]}],
        "root": len(reflexive["nodes"]),
    }
    steps = [record(6, reflexive), record(21, general, "1", x[1:])]
    assert g.check_pa_proof(g.pa_proof_encode(steps), steps[-1]["formula"])["status"] == "ESTABLISHED"
    # A reference to the current line is never a proof of the generalized formula.
    steps[-1]["aux_a"] = "2"
    assert g.check_pa_proof(g.pa_proof_encode(steps), steps[-1]["formula"])["status"] == "REFUTED"


def test_proof_transport_structure_is_not_logical_validity():
    code = g.pa_proof_encode([{"rule": 123, "formula": "0", "aux_a": "0", "aux_b": "0"}])
    assert g.pa_proof_decode(code)[0]["rule"] == 123
    assert g.check_pa_proof(code, "0")["status"] == "REFUTED"
    bad = g.sequence_encode(["20261106", "1", "1", "6", "0", "0", "0", "1", "0"])
    with pytest.raises(g.GoedelError):
        g.pa_proof_decode(bad)
    for steps in [
        [],
        [{"rule": True, "formula": "0", "aux_a": "0", "aux_b": "0"}],
        [{"rule": 6, "formula": "00", "aux_a": "0", "aux_b": "0"}],
    ]:
        with pytest.raises(g.GoedelError):
            g.pa_proof_encode(steps)
    with pytest.raises(g.GoedelError):
        g.hilbert_q_axiom(0)


def test_actual_arithmetic_proof_and_provability_formulas():
    graph = g.proof_PA_formula("x3", "x0")  # x3 conflicts with a compiler binder.
    assert g.validate_arithmetic_dag(graph)["free_variables"] == ["x0", "x3"]
    assert {n["op"] for n in graph["nodes"]} <= {
        "zero",
        "num",
        "var",
        "succ",
        "add",
        "mul",
        "eq",
        "not",
        "and",
        "or",
        "implies",
        "forall",
        "exists",
        "bottom",
    }
    provability = g.provability_formula()
    assert g.validate_arithmetic_dag(provability)["free_variables"] == ["x1"]
    consistency = g.consistency_formula()
    assert g.validate_arithmetic_dag(consistency)["free_variables"] == []
    identity = g.provability_identity()
    assert identity["predicate_sha256"] == g.dag_fingerprint(provability)
    assert identity["contradiction_code"] == "2156323289736949647085695664127"
    assert identity["theory_id"] == "PA"
    identity["theory_id"] = "MUTATED"
    assert g.provability_identity()["theory_id"] == "PA"
    with pytest.raises(g.GoedelError):
        g.proof_PA_formula("x0", "x0")
