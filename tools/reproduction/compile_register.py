"""Build a natural-number register program from a restricted imperative source.

Build-time tool, not a runtime language bridge. The source language has local
natural-number variables, literal constants, +, saturating -, *, //, %, comparison,
if, while, and nonrecursive, pure, inlined function calls. Native integer division
by zero has the IR's explicit convention q=0, r=n. No external calls or oracle
instructions can be compiled. Source and emitted program hashes bind evidence.
"""
from __future__ import annotations
import ast
import hashlib
import json


class Compiler:
    def __init__(self, source: str):
        tree = ast.parse(source)
        self.functions = {}
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue
            if not isinstance(node, ast.FunctionDef) or node.decorator_list:
                raise ValueError("Only pure function definitions are permitted")
            if node.name in self.functions:
                raise ValueError("Duplicate function")
            self.functions[node.name] = node
        self.source = source
        self.code = []
        self.registers = {}
        self.calls = []
        self.temporary = 0
        for function in self.functions.values():
            self.check_flow(function.body, {a.arg for a in function.args.args})
            if not self.returns(function.body):
                raise ValueError(f"Function {function.name} may fall through without returning")

    @staticmethod
    def returns(nodes):
        for node in nodes:
            if isinstance(node, ast.Return):
                return True
            if isinstance(node, ast.If) and Compiler.returns(node.body) and Compiler.returns(node.orelse):
                return True
        return False

    def check_flow(self, nodes, assigned):
        assigned = set(assigned)
        def reads(expr):
            if isinstance(expr, ast.Call):
                for arg in expr.args:
                    reads(arg)
            elif isinstance(expr, ast.Name):
                if expr.id not in assigned:
                    raise ValueError(f"Variable {expr.id} may be read before assignment")
            else:
                for child in ast.iter_child_nodes(expr):
                    reads(child)
        for node in nodes:
            if isinstance(node, ast.Assign):
                reads(node.value)
                for target in node.targets:
                    for item in ast.walk(target):
                        if isinstance(item, ast.Name):
                            assigned.add(item.id)
            elif isinstance(node, ast.If):
                reads(node.test)
                left = self.check_flow(node.body, assigned)
                right = self.check_flow(node.orelse, assigned)
                if self.returns(node.body):
                    assigned = right
                elif self.returns(node.orelse):
                    assigned = left
                else:
                    assigned = left & right
            elif isinstance(node, ast.While):
                reads(node.test)
                self.check_flow(node.body, assigned)
            elif isinstance(node, ast.Return):
                reads(node.value)
                return assigned
        return assigned

    def reg(self, scope, name):
        key = (scope, name)
        if key not in self.registers:
            self.registers[key] = len(self.registers)
        return self.registers[key]

    def temp(self):
        self.temporary += 1
        return self.reg("$temporary", str(self.temporary))

    def emit(self, op, **args):
        index = len(self.code)
        self.code.append({"op": op, **args})
        if op not in ("HALT", "JEQ", "JLT", "JUMP"):
            self.code[-1]["next"] = index + 1
        return index

    def expression(self, node, scope):
        if isinstance(node, ast.Name):
            if (scope, node.id) not in self.registers:
                raise ValueError(f"Unassigned variable {scope}:{node.id}")
            return self.reg(scope, node.id)
        if isinstance(node, ast.Constant) and type(node.value) is int and node.value >= 0:
            dst = self.temp()
            self.emit("CONST", dst=dst, value=str(node.value))
            return dst
        if isinstance(node, ast.BinOp):
            left, right = self.expression(node.left, scope), self.expression(node.right, scope)
            dst = self.temp()
            ops = {ast.Add: "ADD", ast.Sub: "SUB", ast.Mult: "MUL"}
            if type(node.op) in ops:
                self.emit(ops[type(node.op)], dst=dst, left=left, right=right)
            elif isinstance(node.op, (ast.FloorDiv, ast.Mod)):
                other = self.temp()
                q, r = (dst, other) if isinstance(node.op, ast.FloorDiv) else (other, dst)
                self.emit("DIVMOD", quotient=q, remainder=r, numerator=left, denominator=right)
            else:
                raise ValueError("Unsupported arithmetic operation")
            return dst
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            args = [self.expression(arg, scope) for arg in node.args]
            outputs = self.call(node.func.id, args)
            if len(outputs) != 1:
                raise ValueError("Tuple result used as scalar")
            return outputs[0]
        raise ValueError(f"Unsupported expression {ast.dump(node)}")

    def branch(self, node, scope):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            raise ValueError("A simple comparison is required")
        left = self.expression(node.left, scope)
        right = self.expression(node.comparators[0], scope)
        op = node.ops[0]
        flip = isinstance(op, (ast.NotEq, ast.GtE, ast.LtE))
        if isinstance(op, (ast.Gt, ast.LtE)):
            left, right = right, left
        if isinstance(op, (ast.Eq, ast.NotEq)):
            kind = "JEQ"
        elif isinstance(op, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
            kind = "JLT"
        else:
            raise ValueError("Unsupported comparison")
        return self.emit(kind, left=left, right=right, **{"then": -1, "else": -1}), flip

    def statements(self, nodes, scope, outputs, returns):
        for node in nodes:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    src = self.expression(node.value, scope)
                    self.emit("COPY", dst=self.reg(scope, target.id), src=src)
                elif isinstance(target, ast.Tuple) and all(isinstance(n, ast.Name) for n in target.elts):
                    if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and not node.value.keywords:
                        values = self.call(node.value.func.id, [self.expression(a, scope) for a in node.value.args])
                    elif isinstance(node.value, ast.Tuple):
                        values = [self.expression(a, scope) for a in node.value.elts]
                    else:
                        raise ValueError("Tuple assignment requires tuple or function")
                    if len(values) != len(target.elts):
                        raise ValueError("Tuple length mismatch")
                    saved = [self.temp() for _ in values]
                    for dst, src in zip(saved, values):
                        self.emit("COPY", dst=dst, src=src)
                    for name, src in zip(target.elts, saved):
                        self.emit("COPY", dst=self.reg(scope, name.id), src=src)
                else:
                    raise ValueError("Only local scalar/tuple assignment permitted")
            elif isinstance(node, ast.If):
                cond, flip = self.branch(node.test, scope)
                self.code[cond]["else" if flip else "then"] = len(self.code)
                self.statements(node.body, scope, outputs, returns)
                jump = self.emit("JUMP", next=-1)
                self.code[cond]["then" if flip else "else"] = len(self.code)
                self.statements(node.orelse, scope, outputs, returns)
                self.code[jump]["next"] = len(self.code)
            elif isinstance(node, ast.While) and not node.orelse:
                start = len(self.code)
                cond, flip = self.branch(node.test, scope)
                self.code[cond]["else" if flip else "then"] = len(self.code)
                self.statements(node.body, scope, outputs, returns)
                self.emit("JUMP", next=start)
                self.code[cond]["then" if flip else "else"] = len(self.code)
            elif isinstance(node, ast.Return):
                values = node.value.elts if isinstance(node.value, ast.Tuple) else [node.value]
                regs = [self.expression(value, scope) for value in values]
                if len(regs) != len(outputs):
                    raise ValueError("Inconsistent return arity")
                for dst, src in zip(outputs, regs):
                    self.emit("COPY", dst=dst, src=src)
                returns.append(self.emit("JUMP", next=-1))
            else:
                raise ValueError(f"Unsupported statement {ast.dump(node)}")

    def call(self, name, args):
        if name in self.calls or name not in self.functions:
            raise ValueError("Recursion and external calls are forbidden")
        function = self.functions[name]
        if (function.args.defaults or function.args.kwonlyargs or function.args.vararg or
                function.args.kwarg or function.args.posonlyargs or len(function.args.args) != len(args)):
            raise ValueError("Only positional calls of matching arity permitted")
        result_nodes = [n for n in ast.walk(function) if isinstance(n, ast.Return)]
        if not result_nodes:
            raise ValueError("Function must return a value")
        result = result_nodes[0].value
        arity = len(result.elts) if isinstance(result, ast.Tuple) else 1
        outputs = [self.temp() for _ in range(arity)]
        for param, src in zip(function.args.args, args):
            self.emit("COPY", dst=self.reg(name, param.arg), src=src)
        self.calls.append(name)
        returns = []
        self.statements(function.body, name, outputs, returns)
        for index in returns:
            self.code[index]["next"] = len(self.code)
        self.calls.pop()
        return outputs

    def compile(self, function, identifier, version="1.0"):
        fn = self.functions[function]
        inputs = [self.reg("$inputs", a.arg) for a in fn.args.args]
        outputs = self.call(function, inputs)
        if len(outputs) != 1:
            raise ValueError("Program entry must return one natural number")
        self.emit("HALT")
        return {"id": identifier, "version": version, "register_count": len(self.registers),
                "inputs": inputs, "output": outputs[0], "entry": 0,
                "instructions": self.code}


def compile_source(source, function, identifier, version="1.0"):
    """Compile a pure natural-number source function to an inspectable IR table."""
    return Compiler(source).compile(function, identifier, version)


def source_digest(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def run(program, inputs, max_steps=1000000):
    """Independent build-tool interpreter; product runtimes have their own copies."""
    regs = [0] * program["register_count"]
    if len(inputs) != len(program["inputs"]) or any(type(x) is not int or x < 0 for x in inputs):
        raise ValueError("Natural input tuple required")
    for register, value in zip(program["inputs"], inputs):
        regs[register] = value
    pc = program["entry"]
    for steps in range(max_steps + 1):
        ins = program["instructions"][pc]
        op = ins["op"]
        if op == "HALT":
            return regs[program["output"]], steps
        if steps == max_steps:
            raise RuntimeError("RESOURCE_LIMIT")
        if op == "CONST":
            regs[ins["dst"]] = int(ins["value"])
        elif op == "COPY":
            regs[ins["dst"]] = regs[ins["src"]]
        elif op in {"ADD", "SUB", "MUL"}:
            a, b = regs[ins["left"]], regs[ins["right"]]
            regs[ins["dst"]] = a + b if op == "ADD" else max(a-b, 0) if op == "SUB" else a*b
        elif op == "DIVMOD":
            a, b = regs[ins["numerator"]], regs[ins["denominator"]]
            q, r = divmod(a, b) if b else (0, a)
            regs[ins["quotient"]], regs[ins["remainder"]] = q, r
        if op in {"JEQ", "JLT"}:
            a, b = regs[ins["left"]], regs[ins["right"]]
            cond = a == b if op == "JEQ" else a < b
            pc = ins["then"] if cond else ins["else"]
        else:
            pc = ins["next"]
    raise AssertionError("unreachable")


def allocate_registers(program):
    """Color the exact CFG's live-register interference graph.

    Operands are read before destinations are assigned. A destination may reuse
    a dead operand. The two DIVMOD destinations and all input registers remain
    distinct. This optimization changes no control flow or arithmetic operation.
    """
    instructions = program['instructions']
    uses, definitions, successors = [], [], []
    for ins in instructions:
        op = ins['op']
        use, defined = set(), set()
        if op == 'COPY':
            use.add(ins['src'])
        if op in {'ADD', 'MUL', 'SUB', 'JEQ', 'JLT'}:
            use.update((ins['left'], ins['right']))
        if op == 'DIVMOD':
            use.update((ins['numerator'], ins['denominator']))
            defined.update((ins['quotient'], ins['remainder']))
        if op in {'CONST', 'COPY', 'ADD', 'MUL', 'SUB'}:
            defined.add(ins['dst'])
        if op == 'HALT':
            use.add(program['output'])
        successors.append([] if op == 'HALT' else [ins['then'], ins['else']] if op in {'JEQ', 'JLT'} else [ins['next']])
        uses.append(use)
        definitions.append(defined)
    live_in = [set() for _ in instructions]
    live_out = [set() for _ in instructions]
    changed = True
    while changed:
        changed = False
        for pc in range(len(instructions)-1, -1, -1):
            out = set().union(*(live_in[s] for s in successors[pc]))
            incoming = uses[pc] | (out - definitions[pc])
            if incoming != live_in[pc] or out != live_out[pc]:
                changed = True
                live_in[pc], live_out[pc] = incoming, out
    edges = [set() for _ in range(program['register_count'])]
    def join(a, b):
        if a != b:
            edges[a].add(b)
            edges[b].add(a)
    for pc in range(len(instructions)):
        for a in definitions[pc]:
            for b in live_out[pc] | definitions[pc]:
                join(a, b)
        for a in uses[pc]:
            for b in uses[pc]:
                join(a, b)
    for a in program['inputs']:
        for b in program['inputs']:
            join(a, b)
    # Initial inputs may be live alongside registers whose initial value is zero.
    for a in live_in[program['entry']]:
        for b in live_in[program['entry']] | set(program['inputs']):
            join(a, b)
    colors = {}
    for old in sorted(range(len(edges)), key=lambda r: (-len(edges[r]), r)):
        occupied = {colors[n] for n in edges[old] if n in colors}
        color = 0
        while color in occupied:
            color += 1
        colors[old] = color
    result = json.loads(json.dumps(program))
    result['register_count'] = max(colors.values()) + 1
    result['inputs'] = [colors[r] for r in program['inputs']]
    result['output'] = colors[program['output']]
    for ins in result['instructions']:
        for field in set(ins) - {'op', 'next', 'then', 'else', 'value'}:
            ins[field] = colors[ins[field]]
    return result
