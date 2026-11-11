# A concrete PA proof predicate

The public scoped natural-deduction checker accepts explicitly supplied assumptions
and axioms. The separate `goedel-pa-hilbert-proof-v1` presentation recognizes
classical first-order PA proofs without external premises. Its effective calculus
has the classical implicational axiom schemas, universal instantiation with
free-for checks, quantifier distribution, equality reflexivity and substitution,
all arithmetic induction instances, seven closed Q axioms, modus ponens and
unrestricted generalization of earlier theorems. Its mathematical definition has
no proof-length or execution cutoff.

`hilbert_q_axiom(1..7)` returns the exact normalized Q formulas in indexed variables
x0 and x1. `pa_proof_encode` and `pa_proof_decode` transport a list of records with
`rule`, `formula`, `aux_a` and `aux_b`; all except the rule index are exact natural
decimal strings. Their numerical envelope is
`[20261106,1,N,rule,formula,aux_a,aux_b,0,0,...]`. The two reserved cells must be zero.
The transport budget is 4096 records and the common sequence bit budget. Decoding
alone establishes no inference validity.

```python
import goedel as g

axiom = g.hilbert_q_axiom(4)  # forall x0, x0+0=x0
conclusion = g.arithmetic_dag_encode(axiom)
proof = g.pa_proof_encode([
    {'rule': 14, 'formula': conclusion, 'aux_a': '0', 'aux_b': '0'}
])
assert g.check_pa_proof(proof, conclusion)['status'] == 'ESTABLISHED'
```

`check_pa_proof` executes the actual packaged register program, not an approximate
second proof checker. It returns `ESTABLISHED` for acceptance, `REFUTED` for
rejection of the submitted proof, or `UNKNOWN` if the declared transition budget
ends. Its `CHECKED_DERIVATION` result identifies the exact program, numbering,
calculus, theory presentation and provability formula. A successful finite check
is not a proof of PA's consistency.

| Rule | Schema or inference | aux_a | aux_b |
|---:|---|---|---|
| 1 | A -> (B -> A) | 0 | 0 |
| 2 | (A -> (B -> C)) -> ((A -> B) -> (A -> C)) | 0 | 0 |
| 3 | (not B -> not A) -> (A -> B) | 0 | 0 |
| 4 | (forall i A) -> A[i:=t] | term code t | 0 |
| 5 | (forall i (A -> B)) -> (A -> forall i B), i not free in A | 0 | 0 |
| 6 | t=t | 0 | 0 |
| 7 | s=t -> (A[i:=s] -> A[i:=t]) | formula code A | index i |
| 8 | (A[i:=0] and forall i(A -> A[i:=S(i)])) -> forall i A | 0 | 0 |
| 11–17 | Q axioms 1–7 | 0 | 0 |
| 20 | Modus ponens | earlier line A | earlier line A -> B |
| 21 | Generalization | earlier line A | index i |

All unused auxiliaries are zero. Rule 4 and both substitutions in rule 7 require
the term to be free for the variable; the checker does not silently rename bound
variables. Rule 8 allows free arithmetic parameters; repeated generalization
obtains their universal closure. Generalization is unrestricted here because the
format has no open assumptions; this does not weaken freshness conditions in the
separate natural-deduction checker.

Formula comparison expands num, and, or, exists and bottom into the documented
core syntax and compares literal expanded trees. Sharing is irrelevant, but bound
variable names remain significant. Arithmetic equivalence is not performed:
`num(2)` and `S(S(0))` have the same standard value but distinct binary-Horner
normal forms. A proof of their equality requires actual inference.

`proof_PA_formula(pvar='x0', xvar='x1')` constructs the arithmetic formula saying
that the register checker returns one for proof code pvar and conclusion code
xvar. `provability_formula(xvar='x1', proofvar='x0')` existentially binds the proof
code. `consistency_formula()` constructs the closed formula
`not Pr_PA(nu(code(0=S(0))))`. These are arithmetic DAGs with actual zero,
successor, addition and multiplication operations, not opaque Proof or Pr atoms.
Caller-selected indexed variables are substituted simultaneously and capture-free.

`provability_identity()` binds the exact graph, program, predicate, contradiction,
numbering, calculus and theory presentation. A construction returns syntax,
not its truth. Derivability conditions and correspondence reviews have separate
records; the package never infers them merely from passing finite examples.

`godel_sentence()` performs the full fixed-point construction with
`phi(x)=not Pr_PA(x)` for this actual predicate. It returns the concrete sentence,
its exact numerical code equation and the checked conditional equivalence. It
can require several million decimal digits and appreciable runtime; use
`python examples/arithmetical_godel.py --godel` to print compact hashes rather than
the full witness. Its success does not assert the resulting sentence's truth or
unprovability.

`check_metatheorem(id, assumptions, identity=None)` applies the named catalogue
variant to the exact reviewed representation. For example,
`check_metatheorem('godel_second_hbl', {'consistent': True})` is explicitly
conditional on the caller's consistency assumption. Löb's result uses the separate
`lob` identifier and needs no consistency declaration. The three Gödel I variants,
Rosser and Tarski likewise retain separate hypotheses. Missing review of D2 or a
custom predicate identity yields `UNKNOWN`; caller-written HBL flags cannot grant
reviewed status. Reviewed structural conditions and user assumptions are reported
separately, and no finite computation establishes consistency or soundness.
