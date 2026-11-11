# Arithmetic DAGs, numerical sequences and proof transport

`Expr` remains the small-tree interface, with the original depth, node and byte
limits. `arithmetic_dag(expr)` converts an arithmetic term or formula to an
explicit directed acyclic graph. A graph has `schema_version`, `nodes`, and `root`;
each node has `op`, `name`, and an `args` array of earlier zero-based node indices.
The root is the final node. Valid operations are zero, num, var, succ, add, mul,
eq, not, and, or, implies, forall, exists and bottom. `num` is the documented
binary Horner abbreviation from [the arithmetic guide](ARITHMETIC.md).

DAG variables have names `xN`, where N is a canonical natural decimal string.
Conversion from an ordinary variable name is injective: prefix its ASCII bytes
with byte 1, interpret the bytes as a big-endian natural, and prepend `x`.
Compiler-generated DAG names are already indexed and are not converted again.
`validate_arithmetic_dag` reports the root sort, expanded node count and free
variables without expanding shared subtrees. The expanded-node count unshares
literal syntax; a num or bounded-syntax abbreviation still counts as one node,
without expanding its definition. Limits are 200000 graph nodes,
4096 distinct variable indices, 4096 digits per variable index, 5000000 digits
per numeral and 16384 bits for the expanded-node count. This larger representation
does not change the original `Expr` limits.

`dag_substitute` performs general capture-avoiding substitution and may compact
its resulting graph. `dag_alpha_equal` compares denoted syntax up to bound-variable
renaming; it does not compare arithmetic meanings. In contrast,
`dag_fingerprint` and `serialize_arithmetic_dag` preserve the exact presentation,
including sharing and unused nodes. Distinct presentations can denote the same
formula while having different numbers.

```python
import goedel as g

term = g.arithmetic_dag(g.parse_formula('x = 0'))
assert g.validate_arithmetic_dag(term)['root_sort'] == 'formula'
assert g.arithmetic_dag_decode(g.arithmetic_dag_encode(term)) == term
```

The natural-sequence code uses `E([])=1`. To prepend a natural `a` to a tail
code `s`, let `v=a+1`, `k=bit_length(v)` and

```
block = (2**k - 1) + 2**(k+1) * (v - 2**(k-1))
E(a :: tail) = 2**(2*k) * s + block
```

Reading from the least significant bit gives k ones, a zero and k-1 payload
bits. Thus the cell boundaries are unambiguous. `sequence_encode` and
`sequence_decode` use decimal strings for exact numbers; for example `[] -> 1`,
`[0] -> 5`, `[1] -> 19`, `[2] -> 27`, `[0,1] -> 77`. Neither language uses floating
point to hold these codes. Budgets are 1000000 cells and 16000000 code bits.

The arithmetic code is the sequence `[20261105,1,N,record_0,...,record_(N-1)]`,
with four cells per record: operation tag, numeric label, left child, right child.
Tags 0 through 13 correspond to num, var, zero, succ, add, mul, eq, not, and, or,
implies, forall, exists and bottom. Child references are one-based, with zero
meaning absent. The label is the numeral value or variable/binder index; it is
zero for other operations. The root is the last record, with no extra root cell.

`dag_substitute_numeral` implements the versioned presentation transformation
used by `substitute_code`: keep N original nodes, then append N transformed nodes.
A free matching variable becomes the numeral; a matching binder keeps its original
child; other child indices move forward by N. The root becomes index `2*N-1`.
`substitute_code` maps malformed natural syntax codes to `"0"`; malformed decimal
input and resource exhaustion remain explicit errors. It never treats exhaustion
as a successful mathematical substitution. This transformation's exact identity
is used by the representation bundle and [fixed-point construction](FIXEDPOINT.md).

`proof_object`, `encode_proof`, `decode_proof` and `check_proof_code` provide a
separate portable envelope for scoped natural-deduction proofs. The envelope binds
the calculus, logic, theory and its SHA-256 hash, assumptions, explicit axioms,
conclusion and all rule steps. Its numerical code is the sequence
`[20261106,1,*canonical_JSON_bytes]`. Decode checks the envelope, not proof validity;
`check_proof_code` independently replays the submitted inference steps. This JSON
transport must not be identified with the arithmetized mathematical predicate
`Proof_PA`.

`check_scoped_dag_proof` checks the same scoped inference rules as
`check_scoped_proof`, using DAG formulas, terms and templates. It avoids expanding
trees and has no implicit theory argument: theory axioms must be explicitly
supplied. Its evidence identifies the distinct `goedel-nd-scoped-dag-v1` calculus.
