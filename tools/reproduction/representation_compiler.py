"""Build arithmetic formula DAGs from the versioned register-machine IR.

This is a development/build tool, not a Python runtime dependency of the R
library. Generated formulas contain no program-execution or proof oracles.
The syntactic correspondence check is not a proof-assistant certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
MACHINE_ID = "goedel-arithmetic-register-v1"
COMPILER_ID = "goedel-beta-trace-compiler-v1"
ARITHMETIC_OPS = {"zero", "var", "succ", "add", "mul", "eq", "not", "and", "or", "implies", "exists", "forall"}
BOUNDED_OPS = ARITHMETIC_OPS | {"num", "lt", "bexists", "bforall"}
INSTRUCTION_FIELDS = {
    "CONST": {"op", "dst", "value", "next"},
    "COPY": {"op", "dst", "src", "next"},
    "ADD": {"op", "dst", "left", "right", "next"},
    "MUL": {"op", "dst", "left", "right", "next"},
    "SUB": {"op", "dst", "left", "right", "next"},
    "DIVMOD": {"op", "quotient", "remainder", "numerator", "denominator", "next"},
    "JEQ": {"op", "left", "right", "then", "else"},
    "JLT": {"op", "left", "right", "then", "else"},
    "JUMP": {"op", "next"},
    "HALT": {"op"},
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _integer(value: Any, name: str, lower: int, upper: int) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"{name} must be an integer in {lower}..{upper}")
    return value


def validate_program(program: dict[str, Any]) -> None:
    required = {"id", "version", "register_count", "inputs", "output", "entry", "instructions"}
    if not isinstance(program, dict) or set(program) != required:
        raise ValueError("Program fields must exactly match the versioned program schema")
    if any(not isinstance(program[k], str) or not program[k] for k in ("id", "version")):
        raise ValueError("Program id/version must be nonempty strings")
    count = _integer(program["register_count"], "register_count", 1, 4096)
    instructions = program["instructions"]
    if not isinstance(instructions, list) or not 1 <= len(instructions) <= 100000:
        raise ValueError("Program must contain 1..100000 instructions")
    if not isinstance(program["inputs"], list):
        raise ValueError("inputs must be an array")
    for value in program["inputs"]:
        _integer(value, "input register", 0, count - 1)
    if len(program["inputs"]) != len(set(program["inputs"])):
        raise ValueError("Input registers must be distinct")
    _integer(program["output"], "output register", 0, count - 1)
    _integer(program["entry"], "entry pc", 0, len(instructions) - 1)
    for instruction in instructions:
        if not isinstance(instruction, dict) or instruction.get("op") not in INSTRUCTION_FIELDS:
            raise ValueError("Unknown instruction")
        if set(instruction) != INSTRUCTION_FIELDS[instruction["op"]]:
            raise ValueError("Missing or extra instruction fields")
        for key, value in instruction.items():
            if key in {"op", "value"}:
                continue
            if key in {"next", "then", "else"}:
                _integer(value, "jump target", 0, len(instructions) - 1)
            else:
                _integer(value, "register", 0, count - 1)
        if instruction["op"] == "CONST":
            value = instruction["value"]
            if not isinstance(value, str) or re.fullmatch(r"0|[1-9][0-9]*", value) is None:
                raise ValueError("CONST value must be canonical decimal text")
            if len(value) > 4096:
                raise ValueError("Build resource limit: constant exceeds 4096 digits")
        if instruction["op"] == "DIVMOD" and instruction["quotient"] == instruction["remainder"]:
            raise ValueError("DIVMOD destinations must be distinct")
    if not any(i["op"] == "HALT" for i in instructions):
        raise ValueError("Program must contain an explicit HALT instruction")


class FormulaDAG:
    """Explicit lexical arithmetic syntax with shared subexpressions.

    Child references always point backward. Sharing means literal expression
    expansion, not an additional arithmetic function or predicate symbol.
    """

    def __init__(self, first_fresh: int = 0):
        self.nodes: list[dict[str, Any]] = []
        self.index: dict[tuple[Any, ...], int] = {}
        self.next_fresh = first_fresh

    def node(self, op: str, *args: int, name: str = "") -> int:
        key = (op, name, *args)
        if key not in self.index:
            self.index[key] = len(self.nodes)
            self.nodes.append({"op": op, "name": name, "args": list(args)})
        return self.index[key]

    def var(self, name: str) -> int:
        return self.node("var", name=name)

    def fresh(self) -> str:
        name = f"x{self.next_fresh}"
        self.next_fresh += 1
        return name

    def numeral(self, number: int, compact: bool = False) -> int:
        if type(number) is not int or number < 0:
            raise ValueError("Numeral value must be a natural number")
        if compact:
            return self.node("num", name=decimal_nat(number))
        zero = self.node("zero")
        if number == 0:
            return zero
        one = self.node("succ", zero)
        two = self.node("succ", one)
        result = one
        for bit in bin(number)[3:]:
            result = self.node("mul", two, result)
            if bit == "1":
                result = self.node("succ", result)
        return result

    def all(self, items: list[int]) -> int:
        if not items:
            return self.node("eq", self.numeral(0), self.numeral(0))
        while len(items) > 1:
            items = [self.node("and", *items[i:i + 2]) if i + 1 < len(items) else items[i]
                     for i in range(0, len(items), 2)]
        return items[0]

    def any(self, items: list[int]) -> int:
        if not items:
            return self.node("not", self.all([]))
        while len(items) > 1:
            items = [self.node("or", *items[i:i + 2]) if i + 1 < len(items) else items[i]
                     for i in range(0, len(items), 2)]
        return items[0]

    def quantify(self, op: str, name: str, body: int, bound: int | None = None) -> int:
        return self.node(op, *((body,) if bound is None else (bound, body)), name=name)

    def beta(self, b: int, c: int, i: int, r: int) -> int:
        q_name = self.fresh()
        q = self.var(q_name)
        one = self.numeral(1)
        modulus = self.node("add", one, self.node("mul", self.node("add", i, one), c))
        matrix = self.node("eq", b, self.node("add", self.node("mul", q, modulus), r))
        quotient = self.quantify("bexists", q_name, matrix, self.node("add", b, one))
        return self.all([self.node("lt", r, modulus), quotient])

    def export(self, root: int) -> dict[str, Any]:
        # Drop unreachable builder nodes and renumber topologically.
        reachable = {root}
        stack = [root]
        while stack:
            for child in self.nodes[stack.pop()]["args"]:
                if child not in reachable:
                    reachable.add(child)
                    stack.append(child)
        mapping = {old: new for new, old in enumerate(sorted(reachable))}
        nodes = [{**self.nodes[old], "args": [mapping[a] for a in self.nodes[old]["args"]]}
                 for old in sorted(reachable)]
        return {"schema_version": SCHEMA_VERSION, "nodes": nodes, "root": mapping[root]}


def validate_dag(dag: dict[str, Any], bounded: bool = False) -> dict[str, Any]:
    if set(dag) != {"schema_version", "nodes", "root"} or dag["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Invalid arithmetic DAG envelope")
    nodes = dag["nodes"]
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("DAG must contain nodes")
    types: list[str] = []
    free: list[set[str]] = []
    expanded_counts: list[int] = []
    allowed = BOUNDED_OPS if bounded else ARITHMETIC_OPS
    arity = {"zero": 0, "var": 0, "num": 0, "succ": 1, "add": 2, "mul": 2,
             "eq": 2, "lt": 2, "not": 1, "and": 2, "or": 2,
             "implies": 2, "exists": 1, "forall": 1, "bexists": 2, "bforall": 2}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict) or set(node) != {"op", "name", "args"}:
            raise ValueError("Invalid DAG node")
        op, name, args = node["op"], node["name"], node["args"]
        if op not in allowed or not isinstance(args, list) or len(args) != arity[op]:
            raise ValueError("Invalid DAG operation/arity")
        if any(type(a) is not int or not 0 <= a < index for a in args):
            raise ValueError("DAG references must point to earlier nodes")
        if op in {"var", "exists", "forall", "bexists", "bforall"}:
            if not isinstance(name, str) or re.fullmatch(r"x(?:0|[1-9][0-9]*)", name) is None:
                raise ValueError("Variables must have natural indexed names x0,x1,...")
        elif op == "num":
            if not isinstance(name, str) or re.fullmatch(r"0|[1-9][0-9]*", name) is None:
                raise ValueError("NUM abbreviation must contain canonical decimal text")
        elif name != "":
            raise ValueError("Only variables and binders have names")
        wanted = (["term"] * len(args) if op in {"succ", "add", "mul", "eq", "lt"}
                  else ["term", "formula"] if op in {"bexists", "bforall"}
                  else ["formula"] * len(args))
        if [types[a] for a in args] != wanted:
            raise ValueError("DAG term/formula sort mismatch")
        types.append("term" if op in {"zero", "var", "num", "succ", "add", "mul"} else "formula")
        variables = set().union(*(free[a] for a in args))
        if op == "var":
            variables.add(name)
        elif op in {"exists", "forall"}:
            variables.discard(name)
        elif op in {"bexists", "bforall"}:
            if name in free[args[0]]:
                raise ValueError("Bounded variable occurs in its own bound")
            variables.discard(name)
        free.append(variables)
        expanded_counts.append(1 + sum(expanded_counts[a] for a in args))
    root = _integer(dag["root"], "DAG root", 0, len(nodes) - 1)
    if types[root] != "formula":
        raise ValueError("Arithmetic graph root must be a formula")
    return {"nodes": len(nodes), "expanded_nodes": str(expanded_counts[root]),
            "free_variables": sorted(free[root], key=lambda n: int(n[1:]))}


def expand_bounded_dag(source: dict[str, Any]) -> dict[str, Any]:
    """Eliminate < and bounded-quantifier macros by exact lexical expansion."""
    validate_dag(source, bounded=True)
    largest = max((int(n["name"][1:]) for n in source["nodes"]
                   if n["op"] in {"var", "exists", "forall", "bexists", "bforall"}), default=-1)
    target = FormulaDAG(largest + 1)
    mapping: list[int] = []

    def less(left: int, right: int) -> int:
        name = target.fresh()
        equation = target.node("eq", right, target.node("add", left, target.node("succ", target.var(name))))
        return target.quantify("exists", name, equation)

    for node in source["nodes"]:
        op, name = node["op"], node["name"]
        args = [mapping[a] for a in node["args"]]
        if op == "num":
            result = target.numeral(parse_nat(name))
        elif op == "lt":
            result = less(*args)
        elif op in {"bexists", "bforall"}:
            guard = less(target.var(name), args[0])
            body = target.node("and" if op == "bexists" else "implies", guard, args[1])
            result = target.quantify("exists" if op == "bexists" else "forall", name, body)
        else:
            result = target.node(op, *args, name=name)
        mapping.append(result)
    result = target.export(mapping[source["root"]])
    validate_dag(result)
    return result


def bounded_sigma_one_record(dag: dict[str, Any]) -> dict[str, Any]:
    """Check existential prefix plus bounded matrix in PA's order notation.

    This is a syntax/correspondence record. It neither verifies HBL nor asserts
    that the completely expanded base-signature AST is literally prenex Sigma1.
    """
    validate_dag(dag, bounded=True)
    nodes, root = dag["nodes"], dag["root"]
    prefix = []
    while nodes[root]["op"] == "exists":
        prefix.append(nodes[root]["name"])
        root = nodes[root]["args"][0]
    seen = set()
    stack = [root]
    while stack:
        index = stack.pop()
        if index in seen:
            continue
        seen.add(index)
        if nodes[index]["op"] in {"exists", "forall"}:
            raise ValueError("Unbounded quantifier inside the proposed bounded matrix")
        stack.extend(nodes[index]["args"])
    return {"classification": "SIGMA_1_IN_BOUNDED_ORDER_NOTATION", "existential_prefix": prefix,
            "matrix_unbounded_quantifiers": 0,
            "base_signature_relation": "EXACT_DEFINITIONAL_EXPANSION",
            "order_definition": "a < b iff exists d (b = a + S(d))",
            "claim_scope": "Syntactic bounded form and exact expansion; no formal-kernel or HBL certification."}


def _preservation_tree(builder: FormulaDAG, before: list[int], after: list[int]):
    """Share the unchanged-register conjunction, rebuilding O(log R) per write."""
    equalities = [builder.node("eq", a, b) for a, b in zip(after, before)]
    cache: dict[tuple[int, int], int] = {}

    def full(lo: int, hi: int) -> int:
        key = (lo, hi)
        if key not in cache:
            if hi == lo:
                cache[key] = builder.all([])
            elif hi == lo + 1:
                cache[key] = equalities[lo]
            else:
                mid = (lo + hi) // 2
                cache[key] = builder.node("and", full(lo, mid), full(mid, hi))
        return cache[key]

    full(0, len(before))

    def exclude(changed: set[int], lo: int = 0, hi: int = len(before)) -> int:
        if not any(lo <= i < hi for i in changed):
            return full(lo, hi)
        if hi == lo + 1:
            return builder.all([])
        mid = (lo + hi) // 2
        return builder.node("and", exclude(changed, lo, mid), exclude(changed, mid, hi))

    return exclude


def decimal_nat(value: int) -> str:
    """Exact decimal conversion without changing Python's process-wide limits."""
    if value == 0:
        return "0"
    chunks = []
    while value:
        value, remainder = divmod(value, 1_000_000_000)
        chunks.append(remainder)
    return str(chunks[-1]) + "".join(f"{x:09d}" for x in reversed(chunks[:-1]))


def parse_nat(text: str) -> int:
    if not isinstance(text, str) or re.fullmatch(r"0|[1-9][0-9]*", text) is None:
        raise ValueError("Expected canonical decimal natural number")
    value = 0
    for offset in range(0, len(text), 9):
        chunk = text[offset:offset + 9]
        value = value * 10 ** len(chunk) + int(chunk)
    return value


def _instruction_condition(builder: FormulaDAG, instruction: dict[str, Any], pc: int,
                           before_pc: int, after_pc: int, before: list[int], after: list[int],
                           preserve) -> int:
    op = instruction["op"]
    if op == "HALT":
        return builder.any([])
    terms = [builder.node("eq", before_pc, builder.numeral(pc))]
    changed: set[int] = set()
    if op in {"CONST", "COPY", "ADD", "MUL"}:
        changed = {instruction["dst"]}
        if op == "CONST":
            rhs = builder.numeral(parse_nat(instruction["value"]), compact=True)
        elif op == "COPY":
            rhs = before[instruction["src"]]
        else:
            rhs = builder.node(op.lower(), before[instruction["left"]], before[instruction["right"]])
        terms.append(builder.node("eq", after[instruction["dst"]], rhs))
    elif op == "SUB":
        changed = {instruction["dst"]}
        a, b, r = before[instruction["left"]], before[instruction["right"]], after[instruction["dst"]]
        terms.append(builder.any([
            builder.all([builder.node("lt", a, b), builder.node("eq", r, builder.numeral(0))]),
            builder.node("eq", a, builder.node("add", r, b)),
        ]))
    elif op == "DIVMOD":
        changed = {instruction["quotient"], instruction["remainder"]}
        a, d = before[instruction["numerator"]], before[instruction["denominator"]]
        q, r = after[instruction["quotient"]], after[instruction["remainder"]]
        zero = builder.numeral(0)
        is_zero = builder.node("eq", d, zero)
        terms.append(builder.any([
            builder.all([is_zero, builder.node("eq", q, zero), builder.node("eq", r, a)]),
            builder.all([builder.node("not", is_zero), builder.node("lt", r, d),
                         builder.node("eq", a, builder.node("add", builder.node("mul", d, q), r))]),
        ]))
    if op in {"JEQ", "JLT"}:
        test = builder.node("eq" if op == "JEQ" else "lt", before[instruction["left"]], before[instruction["right"]])
        terms.append(builder.any([
            builder.all([test, builder.node("eq", after_pc, builder.numeral(instruction["then"]))]),
            builder.all([builder.node("not", test), builder.node("eq", after_pc, builder.numeral(instruction["else"]))]),
        ]))
    else:
        terms.append(builder.node("eq", after_pc, builder.numeral(instruction["next"])))
    terms.append(preserve(changed))
    return builder.all(terms)


def compile_step(program: dict[str, Any]) -> dict[str, Any]:
    """Compile the finite transition relation, useful for independent local tests."""
    validate_program(program)
    count = program["register_count"]
    builder = FormulaDAG(2 * count + 2)
    before_pc, after_pc = builder.var("x0"), builder.var("x1")
    before = [builder.var(f"x{i + 2}") for i in range(count)]
    after = [builder.var(f"x{i + count + 2}") for i in range(count)]
    preserve = _preservation_tree(builder, before, after)
    conditions = [_instruction_condition(builder, instruction, pc, before_pc, after_pc, before, after, preserve)
                  for pc, instruction in enumerate(program["instructions"]) if instruction["op"] != "HALT"]
    dag = builder.export(builder.any(conditions))
    validate_dag(dag, bounded=True)
    return {"dag": dag, "before_pc": "x0", "after_pc": "x1",
            "before": [f"x{i + 2}" for i in range(count)],
            "after": [f"x{i + count + 2}" for i in range(count)]}


def compile_program(program: dict[str, Any]) -> dict[str, Any]:
    validate_program(program)
    arity = len(program["inputs"])
    builder = FormulaDAG(arity + 1)
    inputs = [builder.var(f"x{i}") for i in range(arity)]
    output = builder.var(f"x{arity}")
    length_name, b_name, c_name, t_name = [builder.fresh() for _ in range(4)]
    length, b, c, t = [builder.var(name) for name in (length_name, b_name, c_name, t_name)]
    zero, one = builder.numeral(0), builder.numeral(1)
    width = program["register_count"] + 1
    before_names = [builder.fresh() for _ in range(width)]
    after_names = [builder.fresh() for _ in range(width)]
    before = [builder.var(name) for name in before_names]
    after = [builder.var(name) for name in after_names]
    preserve = _preservation_tree(builder, before[1:], after[1:])
    row = builder.node("mul", builder.numeral(width), t)
    next_row = builder.node("mul", builder.numeral(width), builder.node("add", t, one))
    cells = [builder.beta(b, c, builder.node("add", row, builder.numeral(i)), before[i]) for i in range(width)]
    cells += [builder.beta(b, c, builder.node("add", next_row, builder.numeral(i)), after[i]) for i in range(width)]
    conditions = [_instruction_condition(builder, instruction, pc, before[0], after[0], before[1:], after[1:], preserve)
                  for pc, instruction in enumerate(program["instructions"]) if instruction["op"] != "HALT"]
    transition = builder.all(cells + [builder.any(conditions)])
    bound = builder.node("add", b, one)
    for name in reversed(before_names + after_names):
        transition = builder.quantify("bexists", name, transition, bound)
    transitions = builder.quantify("bforall", t_name, transition, length)
    initial_values = [builder.numeral(program["entry"])] + [zero] * program["register_count"]
    for register, value in zip(program["inputs"], inputs):
        initial_values[register + 1] = value
    initial = builder.all([builder.beta(b, c, builder.numeral(i), value) for i, value in enumerate(initial_values)])
    final_pc_name = builder.fresh()
    final_pc = builder.var(final_pc_name)
    final_row = builder.node("mul", builder.numeral(width), length)
    halt_choices = [builder.node("eq", final_pc, builder.numeral(pc))
                    for pc, instruction in enumerate(program["instructions"]) if instruction["op"] == "HALT"]
    final = builder.all([
        builder.beta(b, c, final_row, final_pc), builder.any(halt_choices),
        builder.beta(b, c, builder.node("add", final_row, builder.numeral(program["output"] + 1)), output),
    ])
    final = builder.quantify("bexists", final_pc_name, final, bound)
    root = builder.all([initial, final, transitions])
    for name in reversed((length_name, b_name, c_name)):
        root = builder.quantify("exists", name, root)
    bounded = builder.export(root)
    expanded = expand_bounded_dag(bounded)
    bounded_info, expanded_info = validate_dag(bounded, True), validate_dag(expanded)
    expected_free = [f"x{i}" for i in range(arity + 1)]
    # A graph may not depend on an unused input or always-fixed output, but its
    # construction binds them all explicitly through initial/final beta cells.
    if bounded_info["free_variables"] != expected_free or expanded_info["free_variables"] != expected_free:
        raise ValueError("Compiler produced unexpected free variables")
    return {"schema_version": SCHEMA_VERSION, "machine_id": MACHINE_ID, "compiler_id": COMPILER_ID,
            "program_id": program["id"], "program_version": program["version"], "program_sha256": digest(program),
            "inputs": expected_free[:-1], "output": expected_free[-1],
            "bounded_dag": bounded, "arithmetic_dag": expanded,
            "bounded_sha256": digest(bounded), "arithmetic_sha256": digest(expanded),
            "bounded_statistics": bounded_info, "arithmetic_statistics": expanded_info,
            "hierarchy": bounded_sigma_one_record(bounded),
            "correspondence": {"kind": "DEFINITIONAL_EXPANSION", "checked": True,
                               "formal_kernel_replay": False, "program_semantic_correctness_certified": False}}


def verify_compilation(program: dict[str, Any], bundle: dict[str, Any]) -> bool:
    """Recompute the artifact, detecting altered programs, macros, or formula nodes."""
    return bundle == compile_program(program)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("programs", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    document = json.loads(args.programs.read_text())
    if document["schema_version"] != SCHEMA_VERSION or document["machine_id"] != MACHINE_ID:
        raise ValueError("Program bundle version mismatch")
    output = {"schema_version": SCHEMA_VERSION, "machine_id": MACHINE_ID,
              "programs": [compile_program(p) for p in document["programs"]]}
    args.output.write_bytes(canonical(output) + b"\n")
    print(json.dumps({"programs": len(output["programs"]), "output": str(args.output),
                      "formula_dag_nodes": [len(p["arithmetic_dag"]["nodes"]) for p in output["programs"]]}))


if __name__ == "__main__":
    main()
