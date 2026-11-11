# Effective Hilbert presentation of PA, version 1.0

`goedel-pa-hilbert-proof-v1` recognizes finite proofs without external premises.
It is a concrete presentation of classical first-order PA with equality. It is
separate from the user-facing scoped natural-deduction calculus. Neither its
existence nor a successful finite proof check establishes PA's consistency.

The complete natural-number algorithm is `pa_proof_programs.py`, compiled after
`arithmetization_programs.py`. Its only operations are explicit integer arithmetic,
loops, conditions and inlined pure functions; it contains no proof or substitution
oracle. Mathematical checking has no time, node, proof-length or integer cutoff.
A public runtime may impose explicit resource budgets without changing this
mathematical predicate.

## Definitional syntax

Input expressions use the versioned arithmetic DAG presentation numbering in
`ARITHMETIC_CODING.md`. Both term and formula codes are accepted by normalization;
proof lines and the target must be formulas. The normalizer validates every
record and expands the following definitions into the core signature:

- `and(A,B)` is `not(implies(A,not(B)))`.
- `or(A,B)` is `implies(not(A),B)`.
- `exists(i,A)` is `not(forall(i,not(A)))`.
- `bottom` is `not(eq(zero,zero))`.
- `num(n)` is exactly the binary Horner term specified by the numbering, including
  `nu(1)=S(0)` and `nu(2)=S(S(0))*S(0)`.

The core uses `zero,S,add,mul,eq,not,implies,forall`. Every comparison then compares
the expanded syntax tree, with exact variable indices. DAG sharing and unreachable
records are immaterial to this comparison. No arithmetic evaluation, alpha
conversion, general logical equivalence or truth decision occurs. For example,
`num(2)` and `S(S(0))` have equal standard values but different normal forms; their
equality is not an equality-reflexivity instance.

Proof checking admits this explicit definitional conversion throughout. Thus a
proof concluding presentation `a` can check against presentation `b` exactly when
the two expanded trees agree. This is a conservative notation convention, not a
new axiom identifying arbitrary arithmetically equal terms.

## Proof coding

Use the same injective finite natural-sequence codec as arithmetic syntax:

    [20261106,1,N, line1...,lineN...]
    line = [rule, formula_code, aux_a, aux_b, aux_c, aux_d]

Here `N>=1`, every line has exactly six cells, and the input must end exactly after
line N. Indices referring to proof lines are one-based and strictly earlier than
the current line. Reserved `aux_c,aux_d` must both be zero. All unused auxiliary
fields must be zero. Malformed syntax or an invalid derivation returns natural
zero. A valid derivation of the target returns natural one.

| Rule | Axiom or inference | aux_a | aux_b |
|---:|---|---|---|
|1|A -> (B -> A)|0|0|
|2|(A -> (B -> C)) -> ((A -> B) -> (A -> C))|0|0|
|3|(not B -> not A) -> (A -> B)|0|0|
|4|(forall i A) -> A[i:=t], with t free for i in A|term code t|0|
|5|(forall i (A -> B)) -> (A -> forall i B), i not free in A|0|0|
|6|t=t|0|0|
|7|s=t -> (A[i:=s] -> A[i:=t]), both terms free for i in A|formula code A|variable index i|
|8|Induction, as below|0|0|
|11..17|The seven closed Q axioms below|0|0|
|20|Modus ponens: from A and A -> B conclude B|line of A|line of A -> B|
|21|Generalization: from A conclude forall i A|line of A|variable index i|

A, B and C range over arbitrary arithmetic formulas, including formulas with
free variables. There are no open assumptions in this Hilbert proof format, so
generalization has no undischarged-assumption side condition. Its use does not
justify generalizing an assumption in the separate scoped calculus.

The equality schema ranges over all arithmetic formulas; its two free-for checks
are essential. Substitution matching blocks traversal at a binder for i and
otherwise changes just free occurrences. The free-for test rejects any path on
which a different binder would capture a free variable of the replacement term.
No renaming is performed by this checker; a user can supply a suitably renamed
formula and prove the corresponding alpha variant with the logical calculus.

## Arithmetic axioms and induction

Q axioms use the literal variable indices x0 and x1 in this proof presentation:

1. forall x0 not(S(x0)=0).
2. forall x0 forall x1 (S(x0)=S(x1) -> x0=x1).
3. forall x0 (not(x0=0) -> exists x1 (x0=S(x1))).
4. forall x0 (x0+0=x0).
5. forall x0 forall x1 (x0+S(x1)=S(x0+x1)).
6. forall x0 (x0*0=0).
7. forall x0 forall x1 (x0*S(x1)=(x0*x1)+x0).

Other variable names or term instances can be derived using universal elimination
and generalization. The product's descriptive Q axiom API may choose other bound
names; translating that notation does not change the theory.

Rule8 recognizes each open parameter instance

    (A[i:=0] and forall i (A -> A[i:=S(i)])) -> forall i A.

All arithmetic A and variable indices i are permitted. The outer parameter
closure is derived by repeated generalization. This open-schema presentation and
the usual schema of universal closures generate the same PA theorems: universal
elimination yields each open instance from its closure; generalization yields
the closure from the open instance. This distinction must not be confused with
an external assumption or a restriction to a finite list of induction instances.

## Verification scope

Source tests, compiled-program tests and a separately reviewed source/IR/formula
correspondence are distinct artifacts. A graph for this checker represents the
acceptance of **every mathematically finite proof**, regardless of executable API
budgets. Successful finite tests alone do not certify the general correspondence,
the completeness of the logical calculus, formalized Sigma1 completeness, or the
Hilbert-Bernays-Lob conditions. Those require their own mathematical review and,
if claimed, actual formal-kernel replay.
