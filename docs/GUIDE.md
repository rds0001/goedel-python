# Mathematical scope and use

The syntax is first-order syntax with equality and the connectives negation,
conjunction, disjunction, implication, universal/existential quantification and
falsum. Terms contain variables, constants and function applications. Expressions
are finite immutable trees. No default structure, truth assignment or ambient
arithmetical theory is silently attached to a formula.

Free variables are determined by lexical quantifier scope. Substitution affects
only free occurrences. A conflicting binder is renamed to the first available
v0, v1, ... name, with shadowing preserved. Alpha-normalization is purely syntactic:
it does not identify classically equivalent formulas such as double negations.
A structural fingerprint hashes the original canonical syntax, not alpha classes.

The checker accepts a finite natural-deduction fragment with assumption, closed
axiom, modus ponens, conjunction introduction/projections and universal
introduction/elimination. Premise references are one-based earlier step indices.
For universal introduction the bound variable must not be free in any declared
assumption. All explicit axioms must be closed. Formulas across a proof share
consistent predicate/function arities. Axioms are trusted input, not validated
mathematical theorems. There is no implication discharge, existential rule, induction
rule or complete first-order decision procedure in this initial fragment.

A proof result concerns validity of the submitted derivation relative to its
premises. REFUTED does not mean its final formula is false. Malformed payloads
raise a structured error instead. A successful proof result is CHECKED_DERIVATION,
not FORMAL_KERNEL: the Python implementation is part of the trusted computing base.

Bounded search repeatedly closes the given assumptions under conjunction
projection and modus ponens only. The step limit counts admitted assumptions and
derived formulas; alpha-equivalent duplicates are skipped. Within a round,
conjunctions are scanned in insertion order, left projection before right;
then modus-ponens pairs are scanned in insertion order. A found witness is passed
through the separate checker. BOUND_EXHAUSTED and SEARCH_SPACE_EXHAUSTED both return
UNKNOWN about the requested derivability problem.

The catalogue distinguishes Goedel's original consistency and omega-consistency
variants, a Sigma-1-soundness variant, Rosser's refinement, the second theorem under
specified derivability conditions, Loeb, Tarski and related results. These are
carefully delimited literature records; they are not executable general theorem
provers. Context keys are explicit assumptions. The name PA alone supplies none.
Every requirement has to be declared true for conditional applicability. Missing
requirements yield UNKNOWN; explicitly violated requirements yield NOT_APPLICABLE.
DRAFT, withdrawn or otherwise unreviewed evidence never enables applicability.
An explicit consistent=false together with omega_consistent=true or
sigma1_sound=true is reported as INCONSISTENT_CONTEXT, without generalizing this
small contradiction detector into a consistency decision algorithm.

`relation_graph()` exposes only direct typed edges. REQUIRES edges express
conceptual dependencies, not logical implications. Arbitrary graph paths are not
converted into mathematical proofs. A catalogue source or successfully checked
catalogue path could not establish the premises it assumes.

Not included in 0.1.0: general surface-language parser, automatic enumeration of
Q/PA axiom schemes, constructive arithmetical diagonalization, external proof
assistant replay, unbounded search, higher-order logic, inferred consistency,
and transitive theorem inference. The catalogue can describe these concepts
without pretending to calculate them.
