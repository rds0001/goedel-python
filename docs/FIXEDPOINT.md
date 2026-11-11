# Concrete arithmetic fixed points

`fixed_point(phi)` takes an arithmetic DAG formula with exactly one free variable.
It uses the packaged arithmetic representation of closed numerical substitution
to construct an actual diagonal sentence G. The representation is a formula over
zero, successor, addition and multiplication, with ordinary logical operators;
it is not an opaque predicate named Sub. The resource includes the explicit
register program, arithmetic formula and a mathematical correspondence review.
The review records that no proof-assistant kernel replay was performed.

```python
import goedel as g

phi = g.arithmetic_dag(g.parse_formula('x = 0'))
result = g.fixed_point(phi)
assert result['details']['code_equation_checked']
assert result['witness']['checked_proof']['status'] == 'ESTABLISHED'
assert g.validate_arithmetic_dag(result['witness']['G'])['free_variables'] == []
```

The construction produces large exact codes; retain the returned value or print
its lengths and hashes instead of dumping it. Runtime and memory depend strongly
on the formula. Internal node and context limits are not byte or wall-time limits.
Run substantial constructions sequentially in a worker with operating-system
memory and execution-time limits; start with a small formula. The full PA Goedel
sentence is much larger than this example and may exceed a local budget. A
terminated or resource-limited run has no mathematical verdict and does not
refute the fixed-point theorem.

The witness exposes phi, delta, G, the decimal codes `q=code(delta)` and `m=code(G)`,
variable indices, numbering identity, program/formula hashes, the representation
instance, target equivalence, twenty explicit proof steps and their native checker
result. The implementation independently checks the concrete equation
`substitute_code(q, diagonal_variable, q) == m`. Presentation-preserving numbering
is essential: delta and G are not compacted after their codes are chosen.

The displayed premise says that the chosen substitution instance returns exactly
m. From that premise the native scoped DAG checker verifies the logical derivation
of `G iff phi(nu(m))`. The result's `assumptions` and `trusted_premises` expose this
premise. `ESTABLISHED` refers to the conditional construction and reviewed
representation correspondence. The native checker does not itself prove the
arithmetic representation premise in PA. In particular, the output asserts
neither truth nor unprovability of G and does not establish consistency of PA.

A caller may pass a representation bundle explicitly. Formula and program hashes
must match its review record. A caller-written review flag cannot grant the built-in
review status: only the exact pinned resource identity is recognized. An otherwise
valid unreviewed bundle produces `UNKNOWN` together with the conditional witness.
A corrupted binding is an input error.
