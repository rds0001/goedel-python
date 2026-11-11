"""Exact natural-number register execution and independent transition replay."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .proof import _result
from .sequence import MAX_SEQUENCE_BITS, _decimal, _nat
from .syntax import _error

MACHINE_ID = "goedel-arithmetic-register-v1"
LIMITATION = "This is a finite computation of an explicit register program; runtime exhaustion is not a mathematical negative result or a proof of representability."
_FIELDS = {
    "CONST": {"dst", "value", "next"},
    "COPY": {"dst", "src", "next"},
    "ADD": {"dst", "left", "right", "next"},
    "MUL": {"dst", "left", "right", "next"},
    "SUB": {"dst", "left", "right", "next"},
    "DIVMOD": {"quotient", "remainder", "numerator", "denominator", "next"},
    "JEQ": {"left", "right", "then", "else"},
    "JLT": {"left", "right", "then", "else"},
    "JUMP": {"next"},
    "HALT": set(),
}


def _integer(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _validate_program(program: Any) -> None:
    if not isinstance(program, dict) or set(program) != {
        "id",
        "version",
        "register_count",
        "inputs",
        "output",
        "entry",
        "instructions",
    }:
        _error("Invalid register program envelope")
    if any(not isinstance(program[k], str) or not program[k] for k in ("id", "version")):
        _error("Program identity and version must be nonempty strings")
    count, instructions = program["register_count"], program["instructions"]
    if (
        not _integer(count, 1, 4096)
        or not isinstance(instructions, list)
        or not 1 <= len(instructions) <= 100000
    ):
        _error("Invalid register or instruction count")
    if (
        not isinstance(program["inputs"], list)
        or any(not _integer(i, 0, count - 1) for i in program["inputs"])
        or len(set(program["inputs"])) != len(program["inputs"])
    ):
        _error("Invalid input register layout")
    if not _integer(program["output"], 0, count - 1) or not _integer(
        program["entry"], 0, len(instructions) - 1
    ):
        _error("Invalid program output or entry index")
    for instruction in instructions:
        if (
            not isinstance(instruction, dict)
            or not isinstance(instruction.get("op"), str)
            or instruction["op"] not in _FIELDS
        ):
            _error("Unknown register instruction")
        op = instruction["op"]
        if set(instruction) != {"op"} | _FIELDS[op]:
            _error("Incorrect instruction fields")
        for field, value in instruction.items():
            if field in {"op", "value"}:
                continue
            high = len(instructions) - 1 if field in {"next", "then", "else"} else count - 1
            if not _integer(value, 0, high):
                _error("Invalid instruction operand")
        if op == "CONST":
            _nat(instruction["value"], 4096)
        if op == "DIVMOD" and instruction["quotient"] == instruction["remainder"]:
            _error("DIVMOD output registers must differ")
    if not any(i["op"] == "HALT" for i in instructions):
        _error("A program must include an explicit HALT instruction")


def _inputs(program: dict[str, Any], values: Any) -> list[int]:
    if not isinstance(values, (list, tuple)) or len(values) != len(program["inputs"]):
        _error("Register input arity mismatch")
    result = [_nat(v) for v in values]
    _bits(result)
    return result


def _bits(registers: list[int]) -> None:
    if any(v.bit_length() > MAX_SEQUENCE_BITS for v in registers):
        _error("Register bit budget exceeded", "RESOURCE_LIMIT")


def _initial(program: dict[str, Any], values: list[int]) -> tuple[int, list[int]]:
    registers = [0] * program["register_count"]
    for index, value in zip(program["inputs"], values):
        registers[index] = value
    return program["entry"], registers


def _wire(pc: int, registers: list[int]) -> dict[str, Any]:
    return {"pc": pc, "registers": [_decimal(v) for v in registers]}


def _context(program: dict[str, Any]) -> dict[str, str]:
    data = json.dumps(program, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
    return {"program_sha256": hashlib.sha256(data).hexdigest(), "machine_id": MACHINE_ID}


def run_register_program(
    program: dict[str, Any], inputs: list[str], max_steps: int = 100000, trace: bool = False
) -> dict[str, Any]:
    """Run explicit exact arithmetic instructions within a finite transition budget.

    HALT itself costs no transition. UNKNOWN means budget exhaustion. Optional
    traces include the initial state and every successor, at most 10000 states.
    Operands are read before writes, including when registers alias.
    """
    _validate_program(program)
    values = _inputs(program, inputs)
    if not _integer(max_steps, 1, 1000000) or type(trace) is not bool:
        _error("Invalid register step budget or trace flag")
    pc, registers = _initial(program, values)
    used = 0
    history = [_wire(pc, registers)] if trace else None
    constants = {
        i: _nat(row["value"], 4096) for i, row in enumerate(program["instructions"]) if row["op"] == "CONST"
    }
    while True:
        instruction = program["instructions"][pc]
        op = instruction["op"]
        halted = op == "HALT"
        if halted or used == max_steps:
            break
        if history is not None and len(history) == 10000:
            _error("Register trace budget exceeded", "RESOURCE_LIMIT")
        before = registers
        after = list(before)
        if op == "CONST":
            after[instruction["dst"]] = constants[pc]
        elif op == "COPY":
            after[instruction["dst"]] = before[instruction["src"]]
        elif op in {"ADD", "MUL", "SUB"}:
            left, right = before[instruction["left"]], before[instruction["right"]]
            after[instruction["dst"]] = (
                left + right if op == "ADD" else left * right if op == "MUL" else max(left - right, 0)
            )
        elif op == "DIVMOD":
            numerator, denominator = before[instruction["numerator"]], before[instruction["denominator"]]
            quotient, remainder = divmod(numerator, denominator) if denominator else (0, numerator)
            after[instruction["quotient"]], after[instruction["remainder"]] = quotient, remainder
        if op in {"JEQ", "JLT"}:
            left, right = before[instruction["left"]], before[instruction["right"]]
            condition = left == right if op == "JEQ" else left < right
            pc = instruction["then"] if condition else instruction["else"]
        else:
            pc = instruction["next"]
        # Only addition/multiplication can increase beyond the checked input
        # and constant bounds. All other instructions preserve or lower values.
        if op in {"ADD", "MUL"}:
            _bits([after[instruction["dst"]]])
        registers = after
        used += 1
        if history is not None:
            history.append(_wire(pc, registers))
    return _result(
        "ESTABLISHED" if halted else "UNKNOWN",
        "FINITE_COMPUTATION",
        "register_program_execution",
        [],
        [],
        [LIMITATION],
        history,
        {
            "steps_used": used,
            "halted": halted,
            "output": _decimal(registers[program["output"]]) if halted else None,
            "pc": pc,
            "registers": [_decimal(v) for v in registers],
        },
        _context(program),
    )


def check_register_trace(
    program: dict[str, Any], inputs: list[str], trace: list[dict[str, Any]]
) -> dict[str, Any]:
    """Check submitted transition constraints independently of the execution loop.

    A valid finite prefix is established only as a trace. The halted flag and
    output distinguish a complete computation from an unfinished prefix.
    """
    _validate_program(program)
    values = _inputs(program, inputs)
    if not isinstance(trace, list) or not trace:
        _error("A trace requires its initial state")
    if len(trace) > 10000:
        _error("Register trace budget exceeded", "RESOURCE_LIMIT")
    parsed = []
    for state in trace:
        if (
            not isinstance(state, dict)
            or set(state) != {"pc", "registers"}
            or not _integer(state["pc"], 0, len(program["instructions"]) - 1)
        ):
            _error("Malformed register trace state")
        if not isinstance(state["registers"], list) or len(state["registers"]) != program["register_count"]:
            _error("Trace register arity mismatch")
        registers = [_nat(v) for v in state["registers"]]
        _bits(registers)
        parsed.append((state["pc"], registers))
    checked = 0

    def finish(valid: bool, invalid: int | None = None, reason: str = "VALID") -> dict[str, Any]:
        pc, registers = parsed[-1]
        halted = valid and program["instructions"][pc]["op"] == "HALT"
        return _result(
            "ESTABLISHED" if valid else "REFUTED",
            "FINITE_COMPUTATION",
            "validity_of_submitted_register_trace",
            [],
            [],
            [LIMITATION],
            trace if valid else None,
            {
                "invalid_step": invalid,
                "reason": reason,
                "steps_checked": checked,
                "halted": halted,
                "output": _decimal(registers[program["output"]]) if halted else None,
            },
            _context(program),
        )

    if parsed[0] != _initial(program, values):
        return finish(False, 1, "INITIAL_STATE_MISMATCH")
    for index, ((pc, before), (next_pc, after)) in enumerate(zip(parsed, parsed[1:]), 2):
        instruction = program["instructions"][pc]
        op = instruction["op"]
        if op == "HALT":
            return finish(False, index, "TRANSITION_MISMATCH")
        written: set[int] = set()
        valid = True
        if op in {"CONST", "COPY", "ADD", "MUL", "SUB"}:
            dst = instruction["dst"]
            written.add(dst)
            value = after[dst]
            if op == "CONST":
                valid = value == _nat(instruction["value"], 4096)
            elif op == "COPY":
                valid = value == before[instruction["src"]]
            else:
                left, right = before[instruction["left"]], before[instruction["right"]]
                if op == "ADD":
                    valid = value == left + right
                elif op == "MUL":
                    valid = value == left * right
                else:
                    valid = value == 0 if left < right else value + right == left
        elif op == "DIVMOD":
            q, r = instruction["quotient"], instruction["remainder"]
            written.update((q, r))
            numerator, denominator = before[instruction["numerator"]], before[instruction["denominator"]]
            valid = (
                (after[q] == 0 and after[r] == numerator)
                if denominator == 0
                else after[r] < denominator and denominator * after[q] + after[r] == numerator
            )
        if valid:
            valid = all(after[i] == before[i] for i in range(len(before)) if i not in written)
        if op in {"JEQ", "JLT"}:
            left, right = before[instruction["left"]], before[instruction["right"]]
            condition = left == right if op == "JEQ" else left < right
            target = instruction["then"] if condition else instruction["else"]
        else:
            target = instruction["next"]
        if not valid or next_pc != target:
            return finish(False, index, "TRANSITION_MISMATCH")
        checked += 1
    return finish(True)
