# goedel

`goedel` is a native Python library for arithmetic syntax, finite first-order and
modal semantics, exact Goedel numbering, explicit proof checking, bounded proof search and a qualified catalogue
of metamathematical results. Python 3.10 or later is required. There are no runtime
dependencies and no dependency on R.

Install a local source tree with `python -m pip install .`, or install its built
wheel. The local 0.2.0 candidate extends the 0.1.0 syntax and encoding APIs with
concrete Q/PA theory objects, parameterized induction, scoped natural deduction
finite Kripke models, presentation-sensitive arithmetic DAG coding, concrete
conditional fixed points and typed catalogue inference. The R package implements
the same shared contracts.

```python
import goedel as g

x, y = g.variable("x"), g.variable("y")
formula = g.forall("y", g.predicate("R", [x, y]))
changed = g.substitute(formula, "x", y)
assert g.free_variables(changed) == ["y"]
assert changed == g.forall("v0", g.predicate("R", [y, g.variable("v0")]))
assert g.decode(g.encode(changed)) == changed

p, q = g.predicate("P"), g.predicate("Q")
assumptions = [p, g.implication(p, q)]
answer = g.bounded_proof_search(q, assumptions, max_steps=8)
assert answer["status"] == "ESTABLISHED"
assert g.check_proof(answer["witness"], assumptions, conclusion=q)["status"] == "ESTABLISHED"

# A theory name does not silently assert its metamathematical properties.
assert g.check_applicability("rosser", g.theory_context("PA"))["status"] == "UNKNOWN"
variant = g.lookup_statement("rosser")
context = g.theory_context("T", {key: True for key in variant["requirements"]})
assert g.check_applicability("rosser", context)["status"] == "ESTABLISHED"
assert context["consistency_status"] == "NOT_ESTABLISHED"
```

An established applicability result is conditional on the supplied declarations.
It is not a proof that those declarations hold. A valid derivation trusts its
declared assumptions and closed axioms. An exhausted search does not demonstrate
unprovability. Syntax validation, finite computation, catalogue evidence and formal
kernel verification have different meanings; no formal kernel verification is
claimed by this release.

See [the guide](docs/GUIDE.md), [API reference](docs/API.md),
[arithmetic and finite semantics](docs/ARITHMETIC.md), [scoped proof rules](docs/SCOPED_PROOFS.md),
[wire and numbering specification](docs/WIRE.md), [arithmetic DAG coding](docs/ARITHMETIC_CODING.md),
[concrete fixed points](docs/FIXEDPOINT.md), [PA proof predicates](docs/PA_PROVABILITY.md), [register computations](docs/REGISTER_MACHINE.md), [typed catalogue inference](docs/INFERENCE.md), and
[release/testing notes](docs/DEVELOPMENT.md). Scientific sources and exact locators
are embedded in each relevant catalogue record and its source table.

Copyright 2026 RiskDataScience GmbH. Licensed under Apache-2.0. Maintainer:
Dr. Dimitrios Geromichalos, riskdatascience@web.de. The package itself makes no
network requests, performs no telemetry and reads its installed resources without
modifying them. Explicit caller serialization/exports are returned as values.
