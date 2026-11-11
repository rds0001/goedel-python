import json
from importlib.resources import files

import pytest

import goedel as g

CASES = json.loads(files("goedel").joinpath("resources/reference_cases.json").read_text())["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_independent_reference(case):
    operation = case["operation"]
    function_name = {"search": "bounded_proof_search", "decode_error": "decode", "validate_error": "validate_expr"}.get(operation, operation)
    if operation == "applicability":
        actual = g.check_applicability(case["arguments"][0], g.theory_context("T", case["arguments"][1]))["status"]
    elif operation.endswith("_error"):
        with pytest.raises(g.GoedelError) as exc:
            getattr(g, function_name)(*case["arguments"])
        actual = exc.value.code
    else:
        actual = getattr(g, function_name)(*case["arguments"])
        if isinstance(actual, g.Expr):
            actual = json.loads(g.serialize(actual))
        elif operation in {"search", "check_proof"}:
            actual = actual["status"]
    assert actual == case["expected"]
