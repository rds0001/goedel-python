# Reproducing the arithmetic representations

This directory contains the complete numerical source programs, compilers,
numbering specifications and mathematical review records needed to rebuild the
closed-substitution and Hilbert-PA computation graphs. The corresponding Python
and R source distributions contain byte-identical copies of this directory.

Run with Python 3.10 or later; only the standard library is needed:

```sh
python3 build.py --output reproduced
```

The optional developer tool is separate from the R package's native runtime.
Running the R library does not invoke Python.

The builder validates every input file against `manifest.json`, compiles the
source programs, emits their bounded-order and raw arithmetic formula DAGs, and
compares the three canonical fingerprints per artifact. Its output files are
`substitution_representation.json`, `pa_proof_representation.json` and
`build_report.json`. It reproduces program/formula identities; the surrounding
archived review metadata is intentionally not regenerated as an accepted review.
Every generated artifact is labelled `UNREVIEWED_REBUILD`, with
`formal_kernel=false`. Successful hash comparison checks reproducibility and
does not perform a new mathematical or formal-kernel review.

The manifest also binds this builder, the explanatory documents and the archived
reviews. A change to a bound source requires updating the reference and assessing
its mathematical implications independently. Existing independent review records
refer to their original logical source paths beginning `shared/`; those files
are supplied here under the same basenames. These path labels are provenance,
not runtime filesystem dependencies.

The main files are:

- `ARITHMETIC_CODING.md` and `representation_spec.md`: exact coding, register
  transitions, beta traces and definitional arithmetic expansion.
- `arithmetization_programs.py`: explicit code substitution and sequence helpers.
- `compile_register.py`, `compile_register_calls.py`,
  `representation_compiler.py`: source-to-register and register-to-formula tools.
- `pa_proof_programs.py` and `PA_PROOF_PRESENTATION.md`: the complete finite
  Hilbert-PA checker and its precise calculus.
- `pa_transformations.py`, `pa_specialization.py`, `PA_HBL_ARGUMENT.md`: numerical
  proof transformations and the predicate-specific mathematical HBL argument.
- `substitution_review.json`, `call_compiler_review.json`,
  `pa_proof_review.json`, `pa_hbl_review.json`: separately authored mathematical
  reviews with exact hashes and explicit epistemic limits.
- `provability_representation.json`: the packaged predicate identity and its
  links to those mathematical reviews. Public library operations construct
  Proof_PA, Pr_PA and the chosen consistency formula from the generated graph.

A graph describes mathematically arbitrary finite executions; native API budgets
limit an individual computation. A catalogue claim, a finite trace and an
independently reviewed mathematical argument have different evidential scopes.
None of these resources asserts PA's consistency or a formal-kernel replay.
