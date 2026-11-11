"""Independent small register arithmetic and semantic trace mutations."""

import copy

import pytest

import goedel as g


def program(instructions, registers=4, inputs=None, output=0):
    return {
        "id": "native-test",
        "version": "1.0",
        "register_count": registers,
        "inputs": [0, 1] if inputs is None else inputs,
        "output": output,
        "entry": 0,
        "instructions": instructions,
    }


@pytest.mark.parametrize(
    "op,inputs,expected",
    [
        ("ADD", ["9007199254740993", "7"], "9007199254741000"),
        ("MUL", ["123456789", "987654321"], "121932631112635269"),
        ("SUB", ["7", "10"], "0"),
        ("SUB", ["10", "7"], "3"),
    ],
)
def test_register_arithmetic_and_aliases(op, inputs, expected):
    p = program([{"op": op, "dst": 0, "left": 0, "right": 1, "next": 1}, {"op": "HALT"}])
    answer = g.run_register_program(p, inputs, max_steps=1, trace=True)
    assert answer["status"] == "ESTABLISHED"
    assert answer["details"]["output"] == expected
    assert g.check_register_trace(p, inputs, answer["witness"])["status"] == "ESTABLISHED"
    bad = copy.deepcopy(answer["witness"])
    bad[-1]["registers"][3] = "1"  # changing an unwritten register is not permitted
    assert g.check_register_trace(p, inputs, bad)["status"] == "REFUTED"


@pytest.mark.parametrize("numerator,denominator,q,r", [("17", "5", "3", "2"), ("17", "0", "0", "17")])
def test_total_divmod_with_aliased_destinations(numerator, denominator, q, r):
    p = program(
        [
            {"op": "DIVMOD", "quotient": 0, "remainder": 1, "numerator": 0, "denominator": 1, "next": 1},
            {"op": "HALT"},
        ]
    )
    result = g.run_register_program(p, [numerator, denominator], trace=True)
    assert result["details"]["registers"][:2] == [q, r]
    assert g.check_register_trace(p, [numerator, denominator], result["witness"])["status"] == "ESTABLISHED"


def test_branch_copy_const_jump_and_finite_prefix():
    p = program(
        [
            {"op": "CONST", "dst": 2, "value": "3", "next": 1},
            {"op": "JLT", "left": 0, "right": 2, "then": 2, "else": 4},
            {"op": "COPY", "dst": 0, "src": 2, "next": 3},
            {"op": "JUMP", "next": 4},
            {"op": "JEQ", "left": 0, "right": 2, "then": 5, "else": 0},
            {"op": "HALT"},
        ]
    )
    result = g.run_register_program(p, ["1", "0"], trace=True)
    assert result["details"]["output"] == "3"
    assert result["details"]["steps_used"] == 5
    assert g.check_register_trace(p, ["1", "0"], result["witness"])["details"]["halted"]
    limited = g.run_register_program(p, ["1", "0"], max_steps=2, trace=True)
    assert limited["status"] == "UNKNOWN" and limited["details"]["output"] is None
    prefix = g.check_register_trace(p, ["1", "0"], limited["witness"])
    assert prefix["status"] == "ESTABLISHED" and not prefix["details"]["halted"]
    bad = copy.deepcopy(result["witness"])
    bad[0]["registers"][0] = "2"
    assert g.check_register_trace(p, ["1", "0"], bad)["details"]["reason"] == "INITIAL_STATE_MISMATCH"


def test_register_invalid_instructions_and_trace_after_halt():
    p = program([{"op": "HALT"}])
    result = g.run_register_program(p, ["0", "0"], trace=True)
    assert result["details"]["steps_used"] == 0
    assert g.check_register_trace(p, ["0", "0"], result["witness"] * 2)["status"] == "REFUTED"
    for mutate in [
        lambda p: p.update(entry=1),
        lambda p: p.update(inputs=[0, 0]),
        lambda p: p["instructions"][0].update(op="EXEC"),
    ]:
        bad = copy.deepcopy(p)
        mutate(bad)
        with pytest.raises(g.GoedelError):
            g.run_register_program(bad, ["0", "0"])
