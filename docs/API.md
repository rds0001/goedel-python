# Public Python API

The APIs share exact mathematical contracts with the independent R package.

See [syntax and results](GUIDE.md), [arithmetic and semantics](ARITHMETIC.md), [scoped proofs](SCOPED_PROOFS.md), [DAG coding](ARITHMETIC_CODING.md), [fixed points](FIXEDPOINT.md), [PA provability](PA_PROVABILITY.md), [register computations](REGISTER_MACHINE.md), and [catalogue inference](INFERENCE.md).

## Expr

```python
Expr(kind: 'str', name: 'str' = '', args: 'tuple[Expr, ...]' = ()) -> None
```

Immutable typed expression. Prefer the named constructors.

## GoedelError

```python
GoedelError(code: 'str', message: 'str')
```

A structured input or resource error; ``code`` identifies its category.

## ModalExpr

```python
ModalExpr(kind: 'str', name: 'str' = '', args: 'tuple[ModalExpr, ...]' = ()) -> None
```

Immutable modal syntax, distinct from first-order expressions.

## add

```python
add(left: 'Expr', right: 'Expr') -> 'Expr'
```

Construct arithmetic addition, without evaluating it.

## alpha_equal

```python
alpha_equal(left: 'Expr', right: 'Expr') -> 'bool'
```

Compare bound-variable renamings only; not semantic equivalence.

## arithmetic_dag

```python
arithmetic_dag(expr: 'Expr') -> 'dict[str, Any]'
```

Convert ordinary arithmetic syntax to a shared DAG with injective variable indices.

An ordinary variable name maps to x followed by the natural number whose
bytes are 0x01 then that ASCII name. Already-indexed compiler DAGs are separate
inputs and must not pass through this conversion again.

## arithmetic_dag_decode

```python
arithmetic_dag_decode(code: 'str') -> 'dict[str, Any]'
```

Decode and validate a DAG presentation, without proving its formula.

## arithmetic_dag_encode

```python
arithmetic_dag_encode(dag: 'dict[str, Any]') -> 'str'
```

Encode a base-signature DAG as versioned natural-number cells.

Header [20261105,1,N], then four cells [tag,name,left,right] per node.
Numeric child references are one-based; zero denotes an absent child.

## arithmetic_language

```python
arithmetic_language() -> 'dict[str, Any]'
```

Return the versioned first-order arithmetic signature and numeral convention.

## arithmetic_theory

```python
arithmetic_theory(name: 'str' = 'PA', extensions: 'list[Expr] | tuple[Expr, ...]' = ()) -> 'dict[str, Any]'
```

Describe executable Q or PA axiom membership plus explicit closed extensions.

PA uses all seven Q axioms plus induction; the predecessor axiom is redundant
in this presentation. Extensions are declared axioms, not proved conclusions.

## bottom

```python
bottom() -> 'Expr'
```

Construct the falsum formula, not a proof of a contradiction.

## bound_variables

```python
bound_variables(expr: 'Expr') -> 'list[str]'
```

Return sorted distinct names appearing in quantifier binders.

## bounded_proof_search

```python
bounded_proof_search(goal: 'Expr', assumptions: 'list[Expr] | tuple[Expr, ...]' = (), max_steps: 'int' = 64) -> 'dict[str, Any]'
```

Finite deterministic closure under MP and conjunction projections only.

## catalogue_graph

```python
catalogue_graph(adapter: 'str' = 'records')
```

Export typed data; optional NetworkX conversion preserves all attributes.

## catalogue_manifest

```python
catalogue_manifest() -> 'dict[str, str]'
```

Return catalogue/schema versions and the packaged resource's byte hash.

## catalogue_topics

```python
catalogue_topics() -> 'list[dict[str, Any]]'
```

Return the twelve-family inventory, distinguishing coverage from verification.

## check_applicability

```python
check_applicability(id: 'str', context: 'dict[str, Any]') -> 'dict[str, Any]'
```

Check declared conditions of one reviewed variant without certifying them.

## check_derivation

```python
check_derivation(witness: 'dict[str, Any]', context: 'dict[str, Any] | None' = None) -> 'dict[str, Any]'
```

Independently replay rule applications and identity/hash-bound premises.

## check_metatheorem

```python
check_metatheorem(id: 'str', assumptions: 'dict[str, bool]', identity: 'dict[str, Any] | None' = None) -> 'dict[str, Any]'
```

Check a named variant against the exact reviewed PA predicate and declarations.

User consistency, soundness and standard-model declarations remain assumptions.
User-written HBL flags cannot replace an independent representation review.
A custom identity is not silently promoted to the built-in identity.

## check_pa_proof

```python
check_pa_proof(proof_code: 'str', conclusion_code: 'str', max_steps: 'int' = 1000000) -> 'dict[str, Any]'
```

Execute the exact PA Hilbert checker within a declared finite step budget.

ESTABLISHED validates the submitted proof, REFUTED rejects it, and UNKNOWN
reports budget exhaustion. No result asserts consistency of PA.

## check_proof

```python
check_proof(steps: 'list[dict[str, Any]]', assumptions: 'list[Expr] | tuple[Expr, ...]' = (), axioms: 'list[Expr] | tuple[Expr, ...]' = (), conclusion: 'Expr | None' = None) -> 'dict[str, Any]'
```

Validate a finite submitted derivation relative to explicit trusted premises.

Steps use one-based earlier indices. REFUTED concerns the submitted proof's
validity, never the truth of its formula. Malformed data raise GoedelError.

## check_proof_code

```python
check_proof_code(code: 'str', expected_theory: 'dict[str, Any] | None' = None) -> 'dict[str, Any]'
```

Decode and independently replay the submitted native scoped proof.

If expected_theory is supplied it must equal the bound theory exactly.
A successful result has the same explicit trust scope as check_scoped_proof.

## check_register_trace

```python
check_register_trace(program: 'dict[str, Any]', inputs: 'list[str]', trace: 'list[dict[str, Any]]') -> 'dict[str, Any]'
```

Check submitted transition constraints independently of the execution loop.

A valid finite prefix is established only as a trace. The halted flag and
output distinguish a complete computation from an unfinished prefix.

## check_scoped_dag_proof

```python
check_scoped_dag_proof(steps: 'list[dict[str, Any]]', assumptions: 'list[dict[str, Any]] | tuple[dict[str, Any], ...]' = (), axioms: 'list[dict[str, Any]] | tuple[dict[str, Any], ...]' = (), conclusion: 'dict[str, Any] | None' = None, logic: 'str' = 'classical') -> 'dict[str, Any]'
```

Apply the same scoped FOL rules directly to explicit arithmetic DAGs.

Formula, term and template fields contain DAG envelopes. Trusted axioms must
be closed. There is no implicit theory selector. Existing ordinary Expr limits
are unchanged, and no exponential expansion of shared subtrees is performed.

## check_scoped_proof

```python
check_scoped_proof(steps: 'list[dict[str, Any]]', assumptions: 'list[Expr] | tuple[Expr, ...]' = (), axioms: 'list[Expr] | tuple[Expr, ...]' = (), theory: 'dict[str, Any] | None' = None, conclusion: 'Expr | None' = None, logic: 'str' = 'classical') -> 'dict[str, Any]'
```

Check finite scoped first-order deduction with explicit discharge and eigenvariables.

Step fields and all rules are specified in SCOPED_PROOFS.md. The 4096-step
submission limit is operational; validity trusts declared premises and is
not formal verification of this checker. Malformed inputs raise GoedelError;
REFUTED concerns the submitted derivation, never its conclusion's truth.

## conjunction

```python
conjunction(left: 'Expr', right: 'Expr') -> 'Expr'
```

Construct a binary conjunction.

## consistency_formula

```python
consistency_formula() -> 'dict[str, Any]'
```

Build not Pr_PA(nu(code(0=S(0)))); this construction asserts no consistency.

## constant

```python
constant(name: 'str') -> 'Expr'
```

Construct a named constant term without asserting an interpretation.

## dag_alpha_equal

```python
dag_alpha_equal(left: 'dict[str, Any]', right: 'dict[str, Any]') -> 'bool'
```

Compare denoted arithmetic DAG syntax up to lexical bound-variable renaming.

Unreachable nodes and duplicate shared nodes do not affect the expanded-root
syntax. This is not semantic equivalence or equality of presentation codes.

## dag_fingerprint

```python
dag_fingerprint(dag: 'dict[str, Any]', bounded: 'bool' = False) -> 'str'
```

Hash the exact DAG presentation; this is not a semantic-equivalence hash.

## dag_substitute

```python
dag_substitute(dag: 'dict[str, Any]', variable: 'str', term_dag: 'dict[str, Any]') -> 'dict[str, Any]'
```

Capture-avoiding substitution of a DAG term for free indexed variables.

Conflicting binders are renamed above every index in both inputs, in preorder.
The output is a hash-consed reachable presentation; unlike the dedicated
two-copy numeral substitution, it does not preserve presentation numbering.

## dag_substitute_numeral

```python
dag_substitute_numeral(dag: 'dict[str, Any]', variable: 'str', value: 'str') -> 'dict[str, Any]'
```

Substitute a closed compact numeral using the specified two-copy presentation.

Original nodes remain unchanged. New matching variables become numeral nodes;
a matching binder retains its original children, so substitution stops there.
No alpha-renaming is needed because the substituted numeral is closed.

## decode

```python
decode(code: 'str') -> 'Expr'
```

Invert encode, rejecting noncanonical codes and codes outside its image.

## decode_proof

```python
decode_proof(code: 'str') -> 'dict[str, Any]'
```

Decode a proof object and identities; decoding is not proof acceptance.

## definition

```python
definition(id: 'str') -> 'dict[str, Any]'
```

Return one definition; a definition is not an existence proof.

## deserialize

```python
deserialize(text: 'str') -> 'Expr'
```

Parse a wire expression without eval, rejecting duplicate fields.

## disjunction

```python
disjunction(left: 'Expr', right: 'Expr') -> 'Expr'
```

Construct a binary disjunction.

## encode

```python
encode(expr: 'Expr') -> 'str'
```

Inject canonical syntax bytes into a positive integer, returned as decimal text.

## encode_proof

```python
encode_proof(record: 'dict[str, Any]') -> 'str'
```

Encode a canonical proof object with transport header [20261106,1].

## equal

```python
equal(left: 'Expr', right: 'Expr') -> 'Expr'
```

Construct equality of two terms, without deciding it.

## evaluate_formula

```python
evaluate_formula(formula: 'Expr', model: 'dict[str, Any]', assignment: 'dict[str, str] | None' = None, max_steps: 'int' = 10000) -> 'dict[str, Any]'
```

Evaluate a formula and retain its original assignment for exact replay.

Quantifier-local bindings do not overwrite free input variables in the witness.

## evaluate_modal

```python
evaluate_modal(formula: 'ModalExpr', model: 'dict[str, Any]', world: 'str', max_steps: 'int' = 10000) -> 'dict[str, Any]'
```

Evaluate a modal formula at one world of a complete finite model.

## evaluate_term

```python
evaluate_term(term: 'Expr', model: 'dict[str, Any]', assignment: 'dict[str, str] | None' = None, max_steps: 'int' = 10000) -> 'dict[str, Any]'
```

Evaluate a term in an explicit finite structure, with a counted resource budget.

## exists

```python
exists(variable: 'str', body: 'Expr') -> 'Expr'
```

Existentially bind a named variable in a formula.

## expand_numeral

```python
expand_numeral(term: 'Expr', max_nodes: 'int' = 1000) -> 'Expr'
```

Replace numeral abbreviations by actual binary Horner arithmetic terms.

nu(0)=0, nu(1)=S0, nu(2k)=2*nu(k), nu(2k+1)=S(2*nu(k)).
Existing expression depth and node limits still apply.

## explain_derivation

```python
explain_derivation(witness: 'dict[str, Any]') -> 'list[dict[str, Any]]'
```

Return validated step explanations, retaining unverified declaration labels.

## fingerprint

```python
fingerprint(expr: 'Expr') -> 'str'
```

SHA-256 of canonical bytes; distinct alpha-equivalent syntax may hash differently.

## finite_model_check

```python
finite_model_check(formulas: 'list[Expr]', model: 'dict[str, Any]', max_steps: 'int' = 10000) -> 'dict[str, Any]'
```

Check every listed formula under all assignments in one finite structure.

Checking a finite list never checks the entire PA induction schema.

## finite_structure

```python
finite_structure(domain: 'list[str]', constants: 'dict[str, str] | None' = None, functions: 'list[dict[str, Any]] | None' = None, relations: 'list[dict[str, Any]] | None' = None) -> 'dict[str, Any]'
```

Validate a finite structure with total function and relation tables.

Table records have name, arity and table; each row has args and value. False
relation rows are explicit. No omitted interpretation receives a default.

## fixed_point

```python
fixed_point(phi: 'dict[str, Any]', representation: 'dict[str, Any] | None' = None) -> 'dict[str, Any]'
```

Construct a real arithmetic fixed point and replay its conditional equivalence.

Input is an arithmetic formula DAG with exactly one free indexed variable.
The returned q and m are actual presentation codes satisfying m=SUB(q,i,q).
ESTABLISHED means the displayed conditional equivalence, with its reviewed
representation premise still trusted, not proved by the native checker.

## forall

```python
forall(variable: 'str', body: 'Expr') -> 'Expr'
```

Universally bind a named variable in a formula.

## format_formula

```python
format_formula(expr: 'Expr') -> 'str'
```

Format a formula as deterministic ASCII notation accepted by parse_formula.

## frame_check

```python
frame_check(model: 'dict[str, Any]') -> 'dict[str, bool]'
```

Decide reflexivity, irreflexivity, transitivity and acyclicity of a finite frame.

## free_variables

```python
free_variables(expr: 'Expr') -> 'list[str]'
```

Return sorted distinct free variable names.

## function_term

```python
function_term(name: 'str', args: 'list[Expr] | tuple[Expr, ...]' = ()) -> 'Expr'
```

Construct a function-symbol application to terms.

## godel_sentence

```python
godel_sentence() -> 'dict[str, Any]'
```

Construct the actual fixed point of not Pr_PA(x), retaining its trusted premise.

The result verifies a conditional equivalence. Unprovability or truth of the
sentence requires separate metatheorem hypotheses and is not asserted here.
Exact codes can contain millions of digits within explicit DAG/sequence limits.

## hilbert_q_axiom

```python
hilbert_q_axiom(index: 'int') -> 'dict[str, Any]'
```

Return Q axiom 1..7 in the exact normalized Hilbert presentation.

Bound variable indices are literally x0/x1. These codes are the explicit
patterns used by the mathematical checker; arbitrary renamings are not
silently treated as axiom instances by that checker.

## implication

```python
implication(left: 'Expr', right: 'Expr') -> 'Expr'
```

Construct a binary implication.

## induction_axiom

```python
induction_axiom(body: 'Expr', variable: 'str', close: 'bool' = True) -> 'Expr'
```

Construct a PA induction instance, optionally closing all free parameters.

## infer

```python
infer(property: 'str', value: 'bool', context: 'dict[str, Any]', max_steps: 'int' = 256) -> 'dict[str, Any]'
```

Find a finite typed rule chain; failure means UNKNOWN, never unprovability.

## inference_context

```python
inference_context(theory: 'str', assumptions: 'dict[str, bool] | None' = None, metatheory: 'str' = 'ordinary_classical_metamathematics', predicate_identity: 'dict[str, Any] | None' = None) -> 'dict[str, Any]'
```

Bind declarations to explicit theory, metatheory and optional predicate identities.

## is_axiom

```python
is_axiom(theory: 'dict[str, Any]', formula: 'Expr') -> 'bool'
```

Decide membership in the declared built-in arithmetic axiom presentation.

## kripke_model

```python
kripke_model(worlds: 'list[str]', edges: 'list[list[str]]', valuation: 'dict[str, list[str]] | None' = None) -> 'dict[str, Any]'
```

Build an explicit finite Kripke model; listed atoms have complete valuations.

## list_definitions

```python
list_definitions() -> 'list[str]'
```

Return sorted catalogue definition identifiers.

## list_inference_rules

```python
list_inference_rules() -> 'list[dict[str, Any]]'
```

List rules with hypotheses, polarity, provenance and review status.

## list_statements

```python
list_statements() -> 'list[str]'
```

Return sorted catalogue statement identifiers.

## lookup_statement

```python
lookup_statement(id: 'str') -> 'dict[str, Any]'
```

Return an independent copy of one statement, including its evidence and limits.

## modal_atom

```python
modal_atom(name: 'str') -> 'ModalExpr'
```

Construct a propositional modal atom.

## modal_bottom

```python
modal_bottom() -> 'ModalExpr'
```

Construct modal falsum.

## modal_box

```python
modal_box(formula: 'ModalExpr') -> 'ModalExpr'
```

Construct the necessity modality.

## modal_conjunction

```python
modal_conjunction(left: 'ModalExpr', right: 'ModalExpr') -> 'ModalExpr'
```

Construct modal conjunction.

## modal_diamond

```python
modal_diamond(formula: 'ModalExpr') -> 'ModalExpr'
```

Construct the possibility modality.

## modal_disjunction

```python
modal_disjunction(left: 'ModalExpr', right: 'ModalExpr') -> 'ModalExpr'
```

Construct modal disjunction.

## modal_implication

```python
modal_implication(left: 'ModalExpr', right: 'ModalExpr') -> 'ModalExpr'
```

Construct material implication between modal formulas.

## modal_negate

```python
modal_negate(formula: 'ModalExpr') -> 'ModalExpr'
```

Construct modal negation.

## multiply

```python
multiply(left: 'Expr', right: 'Expr') -> 'Expr'
```

Construct arithmetic multiplication, without evaluating it.

## negate

```python
negate(formula: 'Expr') -> 'Expr'
```

Construct negation of a formula.

## normalize

```python
normalize(expr: 'Expr') -> 'Expr'
```

Canonical alpha-renaming of bound variables, preserving free names.

## numbering

```python
numbering() -> 'dict[str, Any]'
```

Describe the exact, versioned finite byte numbering used by encode/decode.

## numeral

```python
numeral(value: 'str | int') -> 'Expr'
```

Construct an exact compact numeral from decimal text or a Python integer.

## numeral_value

```python
numeral_value(term: 'Expr') -> 'str'
```

Evaluate a closed arithmetic term in the natural numbers, exactly.

This finite term evaluation does not decide quantified arithmetic truth.
The returned value has at most 4096 decimal digits.

## pa_proof_decode

```python
pa_proof_decode(code: 'str') -> 'list[dict[str, Any]]'
```

Decode structural PA proof fields; only check_pa_proof checks the logic.

## pa_proof_encode

```python
pa_proof_encode(steps: 'list[dict[str, Any]]') -> 'str'
```

Encode a PA Hilbert proof envelope without certifying inference validity.

## parse_formula

```python
parse_formula(text: 'str') -> 'Expr'
```

Parse documented ASCII first-order notation without executing input text.

## predicate

```python
predicate(name: 'str', args: 'list[Expr] | tuple[Expr, ...]' = ()) -> 'Expr'
```

Construct an atomic formula, allowing nullary predicates.

## proof_PA_formula

```python
proof_PA_formula(pvar: 'str' = 'x0', xvar: 'str' = 'x1') -> 'dict[str, Any]'
```

Build the arithmetic graph accepting proof code pvar and conclusion code xvar.

Variables are indexed DAG names and must differ. Compiler-bound variables are
renamed capture-free. No opaque proof predicate or execution budget occurs in
the returned mathematical formula.

## proof_object

```python
proof_object(steps: 'list[dict[str, Any]]', assumptions: 'list[Expr] | tuple[Expr, ...]' = (), axioms: 'list[Expr] | tuple[Expr, ...]' = (), theory: 'dict[str, Any] | None' = None, conclusion: 'Expr | None' = None, logic: 'str' = 'classical') -> 'dict[str, Any]'
```

Construct a version-bound finite proof object, without asserting validity.

Malformed input is rejected. A well-formed but invalid submitted derivation
can still be represented and encoded; replay is a separate operation.

## provability_formula

```python
provability_formula(xvar: 'str' = 'x1', proofvar: 'str' = 'x0') -> 'dict[str, Any]'
```

Build exists proofvar Proof_PA(proofvar,xvar) for the fixed PA presentation.

## provability_identity

```python
provability_identity() -> 'dict[str, Any]'
```

Return the exact installed provability identity; review flags are not assumptions.

## q_axioms

```python
q_axioms() -> 'list[Expr]'
```

Return the seven closed Robinson-Q axioms in the documented Q1--Q7 order.

## recognize_induction

```python
recognize_induction(formula: 'Expr') -> 'dict[str, Any]'
```

Recognize exact PA induction syntax up to bound-variable renaming.

Open instances and full universal closures are recognized. Axiom membership
additionally requires closure; malformed or foreign syntax is rejected.

## relation_graph

```python
relation_graph() -> 'dict[str, Any]'
```

Return direct typed catalogue edges only; reachability is not a derivation.

## run_register_program

```python
run_register_program(program: 'dict[str, Any]', inputs: 'list[str]', max_steps: 'int' = 100000, trace: 'bool' = False) -> 'dict[str, Any]'
```

Run explicit exact arithmetic instructions within a finite transition budget.

HALT itself costs no transition. UNKNOWN means budget exhaustion. Optional
traces include the initial state and every successor, at most 10000 states.
Operands are read before writes, including when registers alias.

## search_catalogue

```python
search_catalogue(query: 'str', topic: 'str | None' = None) -> 'list[dict[str, Any]]'
```

Search record text and optional topic using deterministic ASCII case folding.

## sequence_decode

```python
sequence_decode(code: 'str', max_items: 'int' = 1000000, max_bits: 'int' = 16000000) -> 'list[str]'
```

Invert sequence_encode; malformed cells and an absent sentinel are errors.

## sequence_encode

```python
sequence_encode(values: 'list[str]', max_items: 'int' = 1000000, max_bits: 'int' = 16000000) -> 'str'
```

Encode a sequence of canonical natural decimal strings injectively.

For v=a+1 and k=bit_length(v), the low 2k-bit cell is
(2**k-1)+2**(k+1)*(v-2**(k-1)). The remaining sequence follows above it.

## serialize

```python
serialize(expr: 'Expr') -> 'str'
```

Canonical compact ASCII JSON, with keys args, kind, name in that order.

## serialize_arithmetic_dag

```python
serialize_arithmetic_dag(dag: 'dict[str, Any]', bounded: 'bool' = False) -> 'str'
```

Return canonical compact ASCII JSON for a validated arithmetic DAG.

## substitute

```python
substitute(expr: 'Expr', variable: 'str', term: 'Expr') -> 'Expr'
```

Capture-avoiding substitution for free occurrences with deterministic renaming.

## substitute_code

```python
substitute_code(code: 'str', variable_index: 'str', value: 'str') -> 'str'
```

Totalized code substitution: invalid natural DAG codes map to zero.

Non-natural input strings are malformed inputs. Operational resource limits
remain RESOURCE_LIMIT and are never silently totalized to mathematical zero.

## successor

```python
successor(term: 'Expr') -> 'Expr'
```

Construct the arithmetic successor term S(term).

## theory_context

```python
theory_context(name: 'str', assumptions: 'dict[str, bool] | None' = None) -> 'dict[str, Any]'
```

Declare a named theory context; no declaration establishes its consistency.

## validate_arithmetic_dag

```python
validate_arithmetic_dag(dag: 'dict[str, Any]', bounded: 'bool' = False) -> 'dict[str, Any]'
```

Validate term/formula DAG syntax, lexical free variables and exact expansion size.

Limits: 200000 shared nodes, 4096 indexed variable names, 16384 bits in the
expansion-count statistic. The bounded profile additionally permits lt,
bexists and bforall as explicit conservative notation.

## validate_expr

```python
validate_expr(expr: 'Expr | dict[str, Any]') -> 'bool'
```

Validate a complete expression, including cross-node arities and hard limits.

## validate_modal_frame

```python
validate_modal_frame(formula: 'ModalExpr', worlds: 'list[str]', edges: 'list[list[str]]', max_valuations: 'int' = 4096) -> 'dict[str, Any]'
```

Exhaust all valuations of a formula's atoms on a specific finite frame.

The first countermodel is returned. Insufficient resources raise RESOURCE_LIMIT
rather than asserting validity from a partially checked set of valuations.

## variable

```python
variable(name: 'str') -> 'Expr'
```

Construct a free variable occurrence; binding is determined by its parents.

## zero

```python
zero() -> 'Expr'
```

Construct the arithmetic zero symbol.
