"""Concrete arithmetic fixed points, exact code equations and explicit trust."""

import copy
import json
import os
from importlib.resources import files

import pytest

import goedel as g
from goedel.fixedpoint import _bundle


@pytest.mark.skipif(
    os.environ.get("GOEDEL_RUN_LARGE_TESTS") != "1" or os.environ.get("CI") == "true",
    reason="Large fixed-point construction requires explicit local opt-in and resource limits",
)
@pytest.mark.parametrize("text", ["x = @zero", "exists y. x = S(y)"])
def test_real_arithmetic_fixedpoints(text):
    phi = g.arithmetic_dag(g.parse_formula(text))
    result = g.fixed_point(phi)
    assert result["status"] == "ESTABLISHED"
    assert result["mode"] == "SYMBOLIC_CONSTRUCTION"
    assert result["details"] == {
        "representation_reviewed": True,
        "code_equation_checked": True,
        "native_derivation_checked": True,
        "formal_kernel_replay": False,
    }
    witness = result["witness"]
    assert len(witness["derivation"]) == 20
    assert witness["checked_proof"]["status"] == "ESTABLISHED"
    assert g.validate_arithmetic_dag(witness["G"])["free_variables"] == []
    assert g.arithmetic_dag_decode(witness["q"]) == witness["delta"]
    assert g.arithmetic_dag_decode(witness["m"]) == witness["G"]
    assert result["assumptions"][0]["formula"] == witness["representation_instance"]
    assert result["assumptions"][0]["proved_by_native_checker"] is False
    assert "conditional" in result["claim"].lower()


def test_representation_binding_and_unverified_input():
    bundle = json.loads(files("goedel").joinpath("resources/substitution_representation.json").read_text())
    assert _bundle(bundle)[1] is True
    unverified = copy.deepcopy(bundle)
    unverified["review"]["status"] = "SOURCE_CHECKED"
    assert _bundle(unverified)[1] is False
    altered = copy.deepcopy(bundle)
    altered["program"]["id"] = "unreviewed-machine"
    with pytest.raises(g.GoedelError):
        _bundle(altered)
    for formula in [g.equal(g.zero(), g.zero()), g.equal(g.variable("x"), g.variable("y"))]:
        with pytest.raises(g.GoedelError):
            g.fixed_point(g.arithmetic_dag(formula))


def test_foreign_machine_identity_is_rejected():
    bundle = json.loads(files("goedel").joinpath("resources/substitution_representation.json").read_text())
    bundle["representation"]["machine_id"] = "foreign-register-machine"
    with pytest.raises(g.GoedelError, match="identity") as caught:
        _bundle(bundle)
    assert caught.value.code == "INVALID_INPUT"
