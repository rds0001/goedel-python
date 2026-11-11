# Typed catalogue inference

The catalogue records definitions, precisely scoped theorem variants, source
locators and review states. `catalogue_topics` lists documentary topic coverage;
`search_catalogue` searches definitions and statements, optionally within a topic.
`catalogue_graph` returns graph data by default. Its optional NetworkX export
requires the `graph` extra; core use has no runtime dependency.

`inference_context` binds declarations to a theory, metatheory, META level and
optional exact provability representation. `infer` finds a finite chain of
reviewed rules; `check_derivation` independently replays its explicit witness.
`explain_derivation` first checks that witness before describing the chain.

```python
import goedel as g

context = g.inference_context('T', {
    'classical_first_order': True, 'extends_pa': True,
    'omega_consistent': True,
})
answer = g.infer('consistent', True, context)
assert answer['status'] == 'ESTABLISHED'
assert g.check_derivation(answer['witness'], context)['status'] == 'ESTABLISHED'
```

This chain uses omega-consistency to infer Sigma1-soundness and then ordinary
consistency. All conclusions are conditional on the declarations. The replay
establishes the chain's validity, not the mathematical truth of its starting
assumptions. Rule premises include polarity, level, theory, metatheory and
predicate identity, so changing one cannot silently reuse an earlier result.
The witness also binds exact catalogue and rule resource hashes.

The five explicit rules concern the consistency hierarchy, Rosser incompleteness,
effective completeness and predicate-specific second incompleteness. Missing
premises or an exhausted finite search produce `UNKNOWN`; contradictory supplied
or inferred properties produce `INCONSISTENT_CONTEXT`. General REQUIRES graph
edges are not inference rules. A predicate-specific rule additionally requires
an independently reviewed exact representation whose derivability conditions
were reviewed; caller-written flags cannot substitute for that identity.
The context theory must equal the theory named by that representation. A reviewed
PA predicate therefore cannot silently become a predicate for a stronger theory.
Rules also require independent evidence for their current linked literature
records. Withdrawing a record or adding an unsupported hypothesis disables both
new inference and replay of dependent chains.

The public catalogue review record distinguishes independently checked definitions
and rule arguments from source-only candidates and formal verification. A topic's
reviewed definition inventory does not claim complete theorem coverage, completed
software workflows or formal-kernel verification.
