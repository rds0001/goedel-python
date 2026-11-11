# Arithmetic, finite models and modal examples

The arithmetic signature has constant `zero`, successor `S`, addition `add` and
multiplication `mul`, with equality as logical identity. Public constructors
`zero`, `successor`, `add` and `multiply` build terms; they do not prove equations.
`arithmetic_language()` returns its versioned machine-readable description.

```python
import goedel as g
x, y = g.variable("x"), g.variable("y")
body = g.equal(g.add(x, y), g.add(y, x))
instance = g.induction_axiom(body, "x")
assert g.free_variables(instance) == []
assert g.recognize_induction(instance)["parameters"] == ["y"]
assert g.is_axiom(g.arithmetic_theory("PA"), instance)
assert not g.is_axiom(g.arithmetic_theory("Q"), instance)
assert g.parse_formula(g.format_formula(instance)) == instance
```

`q_axioms()` returns seven universally closed formulas in order: successor is
nonzero; successor is injective; every nonzero object is a successor; addition's
zero and successor equations; multiplication's zero and successor equations.
PA here uses all seven Q axioms plus the unrestricted arithmetic induction schema.
The predecessor axiom is redundant in this PA presentation. An induction instance
is `(phi(0) & forall x (phi(x) -> phi(S(x)))) -> forall x phi(x)`. Other free
variables are parameters; the default universally closes them in sorted order.
`close=False` constructs an open instance. `recognize_induction` accepts open
instances or full parameter closures up to alpha-renaming. `is_axiom` requires a
closed formula, including for explicitly declared theory extensions. Every theory
still has `consistency_status="NOT_ESTABLISHED"`.

Compact `numeral("9007199254740993")` uses the term node `num` with exact decimal
text and no arguments. It is a documented abbreviation for a particular arithmetic
term, not an additional uninterpreted constant. `expand_numeral` uses
`nu(0)=0`, `nu(1)=S(0)`, `nu(2k)=S(S(0))*nu(k)` and
`nu(2k+1)=S(S(S(0))*nu(k))`. Expansion is bounded by the existing 64-level,
1000-node expression limits and an optional smaller `max_nodes`. Compact literals
allow at most 4096 decimal digits. `numeral_value` evaluates a closed arithmetic
term exactly in the natural numbers, with the same digit bound on its result.
It does not evaluate arbitrary quantified arithmetic sentences.

The ASCII parser supports decimal numerals; variable names; constants `@c`;
function applications `f(x,@c)`; predicates `P(x)` and `P()`; equality; `false`;
`!`, `&`, `|`, `->`; and `forall x.` / `exists x.`. Multiplication binds more
tightly than addition; conjunction binds more tightly than disjunction, which
binds more tightly than right-associative implication. Quantifiers extend over
the formula following the dot. The formatter inserts explicit parentheses and
preserves the difference between `@zero` and the numeral abbreviation `0`.
Parsing performs no code execution and accepts at most 65536 characters and
5000 tokens, subject also to expression limits.

## Explicit finite structures

`finite_structure(domain, constants, functions, relations)` requires a nonempty
domain of at most 16 unique ASCII labels. Constants map names to labels. Each
function or relation record has `name`, integer `arity`, and a complete `table`.
Rows have `args` and `value`. Relations include explicit false rows. Missing
symbols, wrong arities and partial tables are errors, even in a branch that a
short-circuit evaluator would not visit. Each collection has at most 256 symbols
and 65536 table rows. Domains, symbols and rows are canonicalized deterministically.

```python
model = g.finite_structure(["0", "1"], {"zero": "0"}, [
    {"name": "S", "arity": 1, "table": [
        {"args": ["0"], "value": "1"},
        {"args": ["1"], "value": "0"},
    ]}
])
answer = g.evaluate_formula(g.q_axioms()[0], model)
assert answer["status"] == "REFUTED"
assert answer["witness"]["assignment"] == {}  # the checked axiom is a sentence
```

`evaluate_term` returns a domain element. `evaluate_formula` returns finite truth
and the replayable original assignment. Both return `FINITE_EXACT` results bound to the model
hash. An assignment must cover every free variable. Quantifiers iterate over the
sorted domain; logical connectives short-circuit from left to right. Every visited
formula/term node costs one step. A numeral costs its abbreviation visit plus the
nodes in its Horner expansion, evaluated without constructing that expansion.
The default is 10000 steps, with an explicit maximum of 1000000.

`finite_model_check` tests each supplied formula under every finite assignment,
returning the first counterexample and its one-based formula index. It checks
only the supplied list, never all PA induction instances. Numerals in arbitrary
finite structures mean their specific Horner terms: without arithmetic axioms,
these need not equal unary successor numerals. No integer-modulo-domain shortcut
is used.

## Modal semantics

Modal expressions have their own immutable `ModalExpr` type and constructors
`modal_atom`, `modal_bottom`, `modal_negate`, `modal_conjunction`,
`modal_disjunction`, `modal_implication`, `modal_box` and `modal_diamond`.
They are separate from arithmetic formulas. `kripke_model(worlds, edges,
valuation)` requires explicit accessibility pairs and, for each used atom, the
complete list of worlds where it is true. `frame_check` decides four finite frame
properties: reflexivity, irreflexivity, transitivity and acyclicity.

```python
p = g.modal_atom("p")
loeb = g.modal_implication(
    g.modal_box(g.modal_implication(g.modal_box(p), p)), g.modal_box(p))
countermodel = g.kripke_model(["w"], [["w", "w"]], {"p": []})
assert g.evaluate_modal(loeb, countermodel, "w")["status"] == "REFUTED"
closure = [["0", "1"], ["1", "2"], ["0", "2"]]
assert g.validate_modal_frame(loeb, ["0", "1", "2"], closure)["status"] == "ESTABLISHED"
```

`validate_modal_frame` enumerates all valuations of the formula's atoms and all
worlds, returning a concrete countermodel on failure. Its default valuation limit
is 4096, maximum 65536, with a shared million-step evaluation budget. Insufficient
resources raise `RESOURCE_LIMIT`; incomplete enumeration never proves validity.
The example checks eight valuations on one frame. It does not prove GL
completeness or identify modal validity with arithmetic provability.

Finite semantic witnesses retain the original input assignment (or the enumerated
free-variable assignment for model checking), so passing that assignment back to
`evaluate_formula` reproduces the result. Quantifier-local bindings are not flattened
into this assignment; in particular a shadowed binder cannot overwrite a free input.
