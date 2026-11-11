"""The scoped deduction rules applied to arithmetic DAG views without expansion."""

from __future__ import annotations

from typing import Any

from .arithmetic_dag import _dag_info, _variable_index, dag_substitute
from .natural_deduction import _check_scoped_proof
from .syntax import _error


class _Context:
    def __init__(self, dag: dict[str, Any]):
        self.info = _dag_info(dag)
        self.nodes = tuple((n["op"], n["name"], tuple(n["args"])) for n in dag["nodes"])
        self.free_cache: dict[int, set[str]] = {}


class _View:
    def __init__(self, context: _Context, index: int):
        self.context, self.index = context, index

    @property
    def kind(self) -> str:
        op = self.context.nodes[self.index][0]
        return "const" if op == "zero" else "func" if op in {"succ", "add", "mul"} else op

    @property
    def name(self) -> str:
        op, name, _ = self.context.nodes[self.index]
        return "zero" if op == "zero" else "S" if op == "succ" else op if op in {"add", "mul"} else name

    @property
    def args(self) -> tuple[_View, ...]:
        return tuple(_View(self.context, i) for i in self.context.nodes[self.index][2])


def _view_wire(view: _View) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "nodes": [
            {"op": op, "name": name, "args": list(args)}
            for op, name, args in view.context.nodes[: view.index + 1]
        ],
        "root": view.index,
    }


def _view_free(view: _View) -> set[str]:
    context = view.context
    if view.index not in context.free_cache:
        bits = context.info["free"][view.index]
        context.free_cache[view.index] = {
            name for name, mask in context.info["name_bits"].items() if bits & mask
        }
    return context.free_cache[view.index]


def _alpha(left: _View, right: _View) -> bool:
    # Entry environments are empty: identical validated syntax implies alpha equality.
    # Keep this outside the lexical traversal; equal nodes under different binders
    # need not denote alpha-equivalent subexpressions.
    if left.index == right.index and (
        left.context is right.context
        or left.context.nodes[: left.index + 1] == right.context.nodes[: right.index + 1]
    ):
        return True
    stack = [(left.index, right.index, (), (), 0)]
    seen = set()
    while stack:
        lindex, rindex, lenv, renv, depth = stack.pop()
        key = (lindex, rindex, lenv, renv)
        if key in seen:
            continue
        if len(seen) > 800000:
            _error("DAG alpha-comparison context budget exceeded", "RESOURCE_LIMIT")
        seen.add(key)
        lop, lname, largs = left.context.nodes[lindex]
        rop, rname, rargs = right.context.nodes[rindex]
        if lop != rop or len(largs) != len(rargs):
            return False
        le, re = dict(lenv), dict(renv)
        if lop == "var":
            if (lname in le) != (rname in re):
                return False
            if (le[lname] != re[rname]) if lname in le else (lname != rname):
                return False
        elif lop in {"forall", "exists"}:
            depth += 1
            le[lname], re[rname] = depth, depth
        elif lname != rname:
            return False
        left_environment, right_environment = tuple(sorted(le.items())), tuple(sorted(re.items()))
        for la, ra in reversed(list(zip(largs, rargs))):
            stack.append((la, ra, left_environment, right_environment, depth))
    return True


def dag_alpha_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Compare denoted arithmetic DAG syntax up to lexical bound-variable renaming.

    Unreachable nodes and duplicate shared nodes do not affect the expanded-root
    syntax. This is not semantic equivalence or equality of presentation codes.
    """
    lc, rc = _Context(left), _Context(right)
    return _alpha(_View(lc, len(lc.nodes) - 1), _View(rc, len(rc.nodes) - 1))


def check_scoped_dag_proof(
    steps: list[dict[str, Any]],
    assumptions: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    axioms: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    conclusion: dict[str, Any] | None = None,
    logic: str = "classical",
) -> dict[str, Any]:
    """Apply the same scoped FOL rules directly to explicit arithmetic DAGs.

    Formula, term and template fields contain DAG envelopes. Trusted axioms must
    be closed. There is no implicit theory selector. Existing ordinary Expr limits
    are unchanged, and no exponential expansion of shared subtrees is performed.
    """
    contexts: dict[int, tuple[Any, _Context]] = {}
    alpha_cache: dict[tuple[int, int, int, int], bool] = {}

    def expr(value: Any) -> _View:
        if isinstance(value, _View):
            return value
        if id(value) not in contexts:
            contexts[id(value)] = (value, _Context(value))
        context = contexts[id(value)][1]
        return _View(context, len(context.nodes) - 1)

    def formula(value: Any) -> _View:
        view = expr(value)
        if view.context.info["sorts"][view.index] != "formula":
            _error("A formula DAG is required")
        return view

    def formulas(values: Any) -> list[_View]:
        if not isinstance(values, (list, tuple)):
            _error("Formula collection must be a list or tuple")
        if len(values) > 1000:
            _error("Formula collection budget exceeded", "RESOURCE_LIMIT")
        return [formula(v) for v in values]

    def name(value: Any) -> str:
        _variable_index(value)
        return value

    def variable(value: str) -> _View:
        name(value)
        return expr({"schema_version": "1.0", "nodes": [{"op": "var", "name": value, "args": []}], "root": 0})

    def substitute(node: _View, var: str, term: _View) -> _View:
        return expr(dag_substitute(_view_wire(node), var, _view_wire(term)))

    def alpha(left: _View, right: _View) -> bool:
        key = (id(left.context), left.index, id(right.context), right.index)
        if key not in alpha_cache:
            alpha_cache[key] = _alpha(left, right)
        return alpha_cache[key]

    operations = {
        "formula": formula,
        "formulas": formulas,
        "expr": expr,
        "free": _view_free,
        "wire": _view_wire,
        "alpha": alpha,
        "substitute": substitute,
        "variable": variable,
        "name": name,
        "signature": lambda expressions: None,
        "calculus": "goedel-nd-scoped-dag-v1",
        "claim": "validity_of_submitted_scoped_dag_proof",
    }
    return _check_scoped_proof(steps, assumptions, axioms, None, conclusion, logic, operations)
