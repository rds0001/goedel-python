# HBL argument for the concrete Hilbert-PA representation

Status: **independently reviewed mathematical argument**; see `pa_hbl_review.json`. This file
is an argument about the exact versioned programs and generated formulas bound
by `pa_hbl_evidence_draft.json`. It is not a proof-assistant replay and must not
be labelled FORMALLY_VERIFIED. The source author and the independent reviewer are distinct; the separate
review binds the concrete program, predicate, argument and sources.

## 1. Fixed objects and the claim

Let H be precisely the calculus in `PA_PROOF_PRESENTATION.md`. Its theorem set
is ordinary classical PA: the seven Q axioms and all induction instances, with
first-order equality logic, modus ponens and generalization. Open parameter
instances of induction and their universal closures are interderivable by the
specified generalization and universal-elimination rules. There are no assumed
premises in an H proof.

Let `Check(p,a)` be the output-one relation of the exact total numerical program
`check_pa_proof`. Let `G(p,a,r)` be its generated **raw arithmetic graph**, using
the bound program, register-machine semantics and beta-trace compiler. Define

    Proof(p,a) := G(p,a,nu_H(1))
    Pr(a)      := exists p Proof(p,a).

Here `nu_H` is the specified binary Horner numeral; its value1 is literally S0.
The graph has input slots x0=p,x1=a and output x2=r. Constructing Proof must
capture-freely replace that free output with S0; constructing Pr must quantify
only the proof input, with the required fresh/bound-name hygiene. These are
syntactic recipe requirements, not an instruction to insert a new predicate
symbol or an interpreter call into a formula.

For each sentence A, choose its actual well-typed DAG presentation code a and
write `Pr[A]` for the raw arithmetic sentence `Pr(nu_H(a))`. The claims are the
three complete schemes, not a finite list of sample sentences:

    D1: if PA proves A, then PA proves Pr[A].
    D2: PA proves Pr[A -> B] -> (Pr[A] -> Pr[B]).
    D3: PA proves Pr[A] -> Pr[Pr[A]].

In D3 the inner raw sentence has its own actual presentation code. No two
presentation numbers are identified merely because their formulas are equal.
No consistency assumption is needed for these three derivability schemes.
Consistency is an additional assumption when deriving unprovability of the
chosen consistency sentence from them.

## 2. Internal correspondence, not only standard-number agreement

The bridge used below is the PA theorem, in a conservative definitional
extension by primitive-recursive functions,

    PA proves forall p,a (Proof(p,a) <-> Check(p,a)).                 (IC)

The function notation on the right can be eliminated to ordinary arithmetic.
The claim is specifically about this checker and compiler. It does not follow
for an arbitrary recursive predicate just because its standard extension is
the desired set. The following invariants supply a proof of (IC).

The finite-sequence push/pop equations are inverse on valid cells, with an
explicit sentinel. Each parser checks its header, every required cell and the
exact final tail. Node sorts are established by induction over backward child
references. Normalization maintains a table assigning each original node its
expanded root; its copy rules are the displayed connective definitions and the
exact Horner recurrence. The NUM1 final-root copy preserves this invariant even
when the preparatory literal-two node is unreachable. These facts prove the
normalization lemma in PA by induction over the record index and numeral bits.

For a normalized node j define its expanded size recursively by
`W(j)=1+sum W(child)`. Backward references make the table definition primitive
recursive. In `pa_same` the sum of sizes of pending expression pairs decreases
when a pair is processed and its children are queued. The same ranking, with
the carried blocking flag, proves `pa_sub_equal`. The free-variable and free-for
traversals have the analogous pending-size invariant and stop precisely at a
binder for the substituted variable. The two-phase canonical traversal has at
most twice the expanded occurrence count. These rankings give termination and
the stated structural meanings in PA, including nonstandard internal inputs;
they are not just induction over externally observed standard traces.

All normalization loops have primitive-recursive bounds. For an input natural
code c, record count and decoded labels are at most c. Each numeral contributes
at most a constant plus twice its label in new records; consequently a crude
quadratic bound in c suffices for normalized node count. An expanded binary tree
of R nodes has at most `2^(R+1)` occurrences. Iterated cell construction has a
primitive-recursive bound obtained by primitive recursion on its bounded number
of iterations. Nested record traversals, comparison stacks and proof-line loops
therefore also admit primitive-recursive bounds. This supplies bounded-recursion
implementations and PA-proofs of totality; it does not appeal to totality of an
arbitrary while program.

The proof checker loop invariant says: after k lines, the stored normalized
formulas are exactly the first k decoded lines and each is an H axiom or follows
from the specified earlier lines. Each rule case is precisely the condition in
the presentation: both free-for checks for Leibniz, the absent-free-variable
condition for universal distribution, the induction substitution equalities,
and strictly earlier MP/GEN references are retained. The final normalized target
comparison is independent of all preceding rule checks. This proves, in PA,
that Check is the characteristic relation of those finite H derivations.

Source-to-IR correspondence uses explicit instruction simulation and the
acyclic-call selector invariant; register allocation preserves every live value.
Each arithmetic instruction formula describes its deterministic transition,
including subtraction saturation and the specified division-by-zero branch.
The preservation conjunction includes every unwritten register. These are
finite syntactic cases, so their arithmetic verifications combine in PA by
induction over execution length. The checked primitive-recursive bounds supply
a complete terminating execution for every pair of checker inputs.

The beta relation is uniquely the appropriate Euclidean remainder. Its bounded
extraction variables omit no remainder or quotient. Conversely, a finite trace
with L cells and largest value A has a beta encoding: take `c=(A+1)L!`; its
moduli `1+(i+1)c` are larger than every cell and pairwise coprime. For i<j, a
common divisor is coprime to c, divides j-i, and thus divides c, so is1. Finite
CRT and its induction proof are available in PA. The graph's initial/final
conditions and its transition conjunct now prove both implications of (IC).
A purported longer run cannot continue from HALT. No trace-length API bound is
inserted into this argument or the represented predicate.

These are mathematical PA-internal induction arguments. No serialized PA proof
of (IC) or external formal kernel replay is claimed by this draft. Independent
review must examine these invariants and the bound source hashes, rather than
substituting finite test success for them.

## 3. D1: a particular accepted proof gives an arithmetic proof

Take an actual finite H proof p of A. Its total checker computation ends in1.
The finite true computation facts have numeralwise PA proofs. Beta existence
encodes the trace, or equivalently the numeral instance of (IC) identifies the
accepted checker result. Thus PA proves `Proof(nu_H(p),nu_H(a))`; existential
introduction proves `Pr(nu_H(a))`. This is the external derivability rule D1.
It asserts neither that every input code is a proof nor that PA is consistent.

## 4. D2: the exact numerical MP transformer

`join_pa_mp(p,q,b)` in `pa_transformations.py` decodes the row structures, retains
p's n rows, appends q's m rows, then appends

    [20,b,n,n+m,0,0].

In q's rows it increases both references of rule20 by n and only aux_a of rule21
by n. It does **not** change the GEN variable in aux_b, the term/formula witnesses
of rules4/7, or any other auxiliary field. Malformed row structures yield0.
The routine does not itself establish its input proof premises.

Assume Check(p,a)=1 and Check(q,imp(a,b))=1, where imp constructs an implication
presentation whose normalized children are the normalized a and b. Induct over
the appended q rows. Axiom rows are unchanged. An MP/GEN row points to the same
normalized predecessor formulas at shifted indices; those indices are still
strictly earlier. The new last row uses p's last normalized formula and q's last
implication to derive the normalized b. Therefore PA proves the uniform closure

    Check(p,a) and Check(q,imp(a,b)) ->
      Check(join_pa_mp(p,q,b),b).

This induction is about the specified finite data transformation, not a semantic
assumption that provability respects modus ponens. Using (IC) and existential
introduction/elimination gives D2. The same proof, with primitive-recursive
formula-code functions as parameters, supplies the uniform D2 used below.
Normalization permits different presentations of the same antecedent; it never
permits an arbitrary logically equivalent or numerically equal antecedent.

## 5. Auxiliary unary/core quotation for the uniform theorem

A direct appeal to a unary-numeral theorem with Horner substitution would be
incorrect: `nu_H(n+1)` is not literally `S(nu_H(n))`. The productive convention is
unchanged. For the mathematical uniform argument use a separate auxiliary
quotation:

* `u(n)=S^n(0)`, built by `pa_unary_term` without NUM macros.
* `C(F)` is the sequence code of the **unshared, postorder core tree** of F,
  after the explicit connective/Horner normalization. The core syntax has
  literal binder indices and no NUM/and/or/exists/bottom constructors.
* Before applying the uniform theorem, regard formulas as that ordinary core
  syntax. C is injective on core syntax trees. `pa_core_canonical` computes C
  from an arbitrary presentation; it is deliberately a normalization map,
  rather than an injective map on all input presentations.

The two-phase canonical traversal emits children before their parent, duplicates
all shared occurrences, and omits unreachable nodes. Its stack invariant proves
that two outputs coincide exactly when their normalized trees coincide. The
standard constructor, substitution and formula-predicate functions for C are
primitive recursive, and their identities are PA-provable by structural
induction. In particular unary insertion obeys the literal successor identity
required by the auxiliary uniform quotation. The unshared representation is a
mathematical proof device; native APIs need not materialize enormous unary trees.

The implemented transformer `specialize_pa_forall(p,U,t)` handles any closed
term t. It extracts U's universal body and substitutes t by a two-copy structural
construction. The original body nodes are retained, the normalized term nodes
are appended, and transformed body nodes follow them. Matching variables receive
the term-root record; a binder for that variable retains its original child;
all other children refer to transformed body nodes. Induction on original node
index proves closed-term substitution; no capture is possible. The final
instance is canonicalized to C. The transformer then appends a rule4 universal
elimination axiom with the exact term witness and an MP using p's last line.
Thus PA proves, uniformly in p,U,t satisfying the displayed syntactic premises,

    Check(p,U) and ClosedTerm(t) and U=forall i F ->
      Check(specialize_pa_forall(p,U,t), C(F[t/i])).                 (UI*)

This says nothing about invalid or mismatched input proofs. `generalize_pa`
provides the corresponding append-GEN transformation. Both algorithms are
explicit natural-number sources in `pa_specialization.py`, with the same
primitive-recursive rankings and PA structural proofs as above.

Suppose PA proves `forall x1...xk F`. Fix such a proof. Iterate (UI*) using
u(n1),...,u(nk). Each replacement is closed. PA proves that for **all** parameter
values the resulting proof checks against `C(F[u(n1)/x1,...,u(nk)/xk])`.
By (IC), this establishes D1-uniform for Phi(z)=Pr(z) and the auxiliary unary/core
quotation. If a starting theorem has free parameters, apply the explicit GEN
transformation first to obtain its closure. No whole-proof substitution routine
or undeclared assumption is needed.

D2-uniform follows from the same join transformer applied to the canonical codes
of F and G after unary insertion. Canonical implication construction commutes
with insertion by a syntactic induction; target normalization handles the
presentation of the newly built implication. Thus the **same** predicate Phi
satisfies the two uniform conditions under a single consistent unary quotation.
This step does not replace Pr by a predicate merely agreeing on standard numbers.

## 6. Formalized Sigma1 completeness and D3

The imported mathematical result is the schematic implication from uniform D1
and uniform D2 to uniform Sigma1 completeness, with ordinary unary numerals.
Kurahashi, *A note on derivability conditions*, arXiv:1902.00895v3, Definition2.12
and Theorem2.18, states this result. Section2 specifies unary numerals; Lemma3.2
explains why their syntactic successor behavior matters. We use precisely the
auxiliary convention of section5. The paper's consistency convention creates no
extra consistency claim here: in the inconsistent case every target arithmetic
scheme is already provable by explosion; in the consistent case the stated
schematic implication applies. The derivability argument itself uses no
assertion that PA is consistent.

Consequently, for every Sigma1 sentence chi in ordinary arithmetic notation,

    PA proves chi -> Pr(u(C(chi))).                                (S1C)

Only this mathematical implication is imported. No imported Lean/Coq program
certifies our checker, source compiler, numbering or graph. The checked
correspondences and uniform hypotheses above are necessary for this application.

Fix the actual presentation code a of A and let

    sigma := Pr(nu_H(a));      b := actual_code(sigma).

The beta graph has an existential prefix over a bounded-order matrix, and adding
its existential proof quantifier preserves that class. Exact expansion of order
and bounded quantifiers produces the raw arithmetic formula sigma. The usual
PA arithmetical-hierarchy/definitional-normal-form theorem therefore supplies a
Sigma1 representative chi with

    PA proves chi <-> sigma.                                      (E)

Here bounded-order notation has its standard arithmetic meaning. Its definitional
extension is conservative, and normal-form conversion is an arithmetic theorem;
the raw expanded AST is **not** declared literally prenex Sigma1. The explicit
bounded DAG and its capture-free translation are the inputs to this step.

Now derive the required D3 without changing any syntactic identity silently:

1. From sigma obtain chi using (E).
2. Apply (S1C) to chi, obtaining Pr(u(C(chi))).
3. For the fixed natural C(chi), PA proves the closed arithmetic equality
   `u(C(chi))=nu_H(C(chi))`. Equality substitution gives Pr(nu_H(C(chi))).
   This is a PA arithmetic proof about two terms with the **same** value;
   it is not an equality-reflexivity check or a code-identity assertion.
4. Since PA proves chi -> sigma, D1 and D2 imply
   `Pr(nu_H(C(chi))) -> Pr(nu_H(C(sigma)))`. If its implication has another
   presentation, use the exact target-normalization invariant below.
5. C(sigma) and b have the same normalized tree. The checker compares only that
   tree at its final target test. PA therefore proves, uniformly in p,
   `Check(p,C(sigma)) <-> Check(p,b)`. With (IC) and existential quantification,
   `Pr(nu_H(C(sigma))) <-> Pr(nu_H(b))` follows.

The conclusion is `sigma -> Pr(nu_H(b))`, exactly D3. In step5 the **numbers**
C(sigma) and b can differ. They are not set equal: the proven target-invariance
property relates the two provability statements. Conversely step3 changes only
two arithmetic terms denoting one fixed number. These two justifications must
never be conflated.

For completeness, the fixed numeral equality in step3 is provable by evaluation
of the finite closed Horner term with the Q addition/multiplication recursions,
ending in its unary numeral. No uniform equality shortcut is built into the
checker. Native checks that reject `num(2)=S(S(0))` as reflexivity remain correct;
a longer arithmetic derivation is needed for that true equation.

## 7. Evidence and limits

The proof uses the actual source/presentation internal correctness theorem,
explicit universal-instantiation and MP transformations, the verified unary/core
quotation convention, the cited uniform completeness theorem, and an explicit
PA equivalence to a Sigma1 representative. These are the mathematical premises
an independent reviewer must assess. Merely calling the checker recursive or
noting its behavior on finitely many examples would establish none of them.

Runtime limits affect the feasibility of producing particular traces, unary
auxiliary objects or expanded trees; they do not truncate the represented proof
relation. The user-facing HBL result must bind the theory, numbering, checker,
compiler, graph and this reviewed argument. Other theories, modified predicates,
normalizations or compiler versions require another review. This draft proves
no consistency of PA, no completeness of arithmetic truth and no successful
formal-kernel replay. Its independent mathematical review is recorded in `pa_hbl_review.json`;
that status is not formal verification and applies only to the bound artifacts.
