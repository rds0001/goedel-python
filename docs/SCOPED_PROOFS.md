# Scoped first-order natural deduction

`check_scoped_proof(steps, assumptions=(), axioms=(), theory=None,
conclusion=None, logic="classical")` checks the finite calculus
`goedel-nd-scoped-v1`. It complements the unchanged `check_proof` fragment.
Each step has exactly `rule`, `formula`, `premises` and `scope`, plus the
rule-specific fields below. References are one-based earlier step indices.

A scope is the list of currently open `assume` indices. Opening a subproof appends
that step's own index. Closing rules discharge exactly the last open scope. An
ordinary reference must come from the current scope or an accessible ancestor;
closed branches cannot be reused. A final proof must have empty scope.

```python
import goedel as g
p = g.predicate("P")
steps = [
    {"rule": "assume", "formula": p, "premises": [], "scope": [1]},
    {"rule": "reiterate", "formula": p, "premises": [1], "scope": [1]},
    {"rule": "imp_intro", "formula": g.implication(p, p), "premises": [2],
     "scope": [], "discharge": [1]},
]
result = g.check_scoped_proof(steps)
assert result["status"] == "ESTABLISHED"
assert g.check_scoped_proof(result["witness"])["status"] == "ESTABLISHED"
```

| Rule | Ordered premises | Extra fields and condition |
|---|---|---|
| `assume` | none | Open a local assumption |
| `assumption` | none | Match an explicitly declared assumption |
| `axiom` | none | Match a closed supplied axiom or the selected Q/PA presentation |
| `reiterate` | A | Repeat A in an accessible scope |
| `mp` | A, A → B | Conclude B |
| `and_intro` | A, B | Conclude A ∧ B |
| `and_left`, `and_right` | A ∧ B | Conclude A or B |
| `or_left`, `or_right` | A, respectively B | Conclude A ∨ B |
| `or_elim` | A ∨ B, A → C, B → C | Conclude C; the implications may be closed subproofs |
| `false_elim` | ⊥ | Conclude any formula |
| `not_elim` | A, ¬A | Conclude ⊥ |
| `imp_intro` | branch endpoint B | `discharge:[i]`; opening i is A, conclude A → B |
| `not_intro` | branch endpoint ⊥ | `discharge:[i]`; opening i is A, conclude ¬A |
| `classical` | branch endpoint ⊥ | `discharge:[i]`; opening i is ¬A, conclude A; classical logic only |
| `forall_elim` | ∀x A | `term`; conclude capture-avoiding A[x:=term] |
| `forall_intro` | A | Conclude ∀x A; x is free in no declared or open assumption |
| `exists_intro` | A[x:=term] | `term`; conclude ∃x A |
| `exists_elim` | ∃x A, branch endpoint C | `discharge:[i], variable:a`; opening i is A[x:=a]; a is free in neither the existential premise, C, nor any remaining assumption |
| `eq_refl` | none | Conclude t=t |
| `eq_symm` | t=u | Conclude u=t |
| `eq_trans` | t=u, u=v | Conclude t=v |
| `eq_elim` | t=u, F[z:=t] | `template:F, variable:z`; conclude F[z:=u] using capture-avoiding substitution |

The endpoint of a closing rule belongs to the exact current child scope. An
existential premise must be accessible in the parent scope. The result records
the actual local assumption dependencies of every accepted step. Discharge removes
the relevant assumption from that support. Freshness checks conservatively inspect
all declared and open assumptions, including unused ones.

The checker rejects inconsistent symbol arities across the complete submission.
Malformed payloads raise `INVALID_INPUT`; an incorrectly applied rule returns
`REFUTED` about this submitted proof, not about its conclusion's truth. A finite
submission may contain at most 4096 steps. This is an API resource limit, not part
of the mathematical definition of the calculus. Native checking is trusted
software, not `FORMAL_KERNEL` verification. Declared assumptions, explicit axioms
and the theory presentation remain visible in the returned evidence.

The existing `bounded_proof_search` continues to search only finite MP/projection
closure and rechecks its witness using the original checker. Exhaustion gives
`UNKNOWN`; it is never an assertion of unprovability or consistency.
