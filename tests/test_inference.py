"""Independent typed-chain examples and semantic witness mutations."""

import copy

import pytest

import goedel as g
from goedel import inference as module


def test_predicate_theory_must_match_the_query_theory():
    flags = dict(
        classical_first_order=True,
        consistent=True,
        diagonal_lemma_available=True,
        extends_pa=True,
        hbl_conditions=True,
        provability_predicate_fixed=True,
    )
    identity = g.provability_identity()
    pa = g.inference_context("PA", flags, predicate_identity=identity)
    assert g.infer("proves_own_consistency", False, pa)["status"] == "ESTABLISHED"
    extension = g.inference_context("PA_plus_ConPA", flags, predicate_identity=identity)
    assert g.infer("proves_own_consistency", False, extension)["status"] == "UNKNOWN"


@pytest.mark.parametrize(
    "mutation", ["source_only_rule", "draft_statement", "missing_statement", "new_requirement"]
)
def test_rule_and_literature_withdrawal_invalidates_search_and_replay(monkeypatch, mutation):
    flags = dict(
        classical_first_order=True,
        consistent=True,
        extends_pa=True,
        decidable_axiom_set=True,
        standard_arithmetization=True,
    )
    context = g.inference_context("T", flags)
    witness = g.infer("syntactically_complete", False, context)["witness"]
    data, hash_ = module._rules()
    catalogue, payload = module._catalogue()
    if mutation == "source_only_rule":
        for rule in data["rules"]:
            rule["verification_status"] = "SOURCE_CHECKED"
        monkeypatch.setattr(module, "_rules", lambda: (data, hash_))
    elif mutation == "missing_statement":
        catalogue["statements"] = [s for s in catalogue["statements"] if s["id"] != "rosser"]
    else:
        row = next(s for s in catalogue["statements"] if s["id"] == "rosser")
        if mutation == "draft_statement":
            row["evidence"]["review_status"] = "DRAFT"
        else:
            row["requirements"].append("additional_unsupported_hypothesis")
    monkeypatch.setattr(module, "_catalogue", lambda: (catalogue, payload))
    assert g.infer("syntactically_complete", False, context)["status"] == "UNKNOWN"
    assert g.check_derivation(witness)["status"] == "REFUTED"


def test_nonstring_rule_reference_is_rejected_without_python_type_error():
    context = g.inference_context(
        "T", dict(classical_first_order=True, extends_pa=True, omega_consistent=True)
    )
    witness = g.infer("consistent", True, context)["witness"]
    witness["steps"][-1]["rule"] = []
    assert g.check_derivation(witness)["status"] == "REFUTED"


def declared_context():
    return g.inference_context("T", {"consistent": True})


def test_declared_fact_replay_is_conditional():
    result = g.infer("consistent", True, declared_context())
    assert result["status"] == "ESTABLISHED"
    assert result["mode"] == "CATALOGUE_INFERENCE"
    assert result["dependencies"] == [
        {"property": "consistent", "value": True, "source": "DECLARED_NOT_VERIFIED"}
    ]
    assert g.check_derivation(result["witness"])["status"] == "ESTABLISHED"
    explanation = g.explain_derivation(result["witness"])
    assert explanation[0]["explanation"] == "User declaration; not independently verified."


@pytest.mark.parametrize(
    "mutation",
    [
        "theory",
        "metatheory",
        "level",
        "polarity",
        "undeclared",
        "stale_catalogue",
        "stale_rules",
        "forward_reference",
    ],
)
def test_invalid_witnesses_do_not_establish_facts(mutation):
    witness = copy.deepcopy(g.infer("consistent", True, declared_context())["witness"])
    fact = witness["steps"][0]["fact"]
    if mutation == "theory":
        fact["theory_id"] = "OTHER"
    elif mutation == "metatheory":
        fact["metatheory_id"] = "OTHER"
    elif mutation == "level":
        fact["level"] = "OBJECT"
    elif mutation == "polarity":
        fact["value"] = False
    elif mutation == "undeclared":
        fact["property"] = "omega_consistent"
    elif mutation == "stale_catalogue":
        witness["catalogue_sha256"] = "0" * 64
    elif mutation == "stale_rules":
        witness["rules_sha256"] = "0" * 64
    else:
        witness["steps"][0]["premises"] = [1]
    assert g.check_derivation(witness)["status"] == "REFUTED"
    with pytest.raises(g.GoedelError):
        g.explain_derivation(witness)


def test_expected_context_is_checked():
    witness = g.infer("consistent", True, declared_context())["witness"]
    assert (
        g.check_derivation(witness, g.inference_context("Other", {"consistent": True}))["status"] == "REFUTED"
    )


def test_no_reverse_rule_or_unprovability_claim():
    result = g.infer("omega_consistent", True, declared_context())
    assert result["status"] == "UNKNOWN"
    assert result["details"]["reason"] == "NO_SUPPORTED_DERIVATION"
    assert g.infer("consistent", True, g.inference_context("T", {}))["status"] == "UNKNOWN"


def test_unreviewed_rules_are_never_promoted(monkeypatch):
    data, hash_ = module._rules()
    for rule in data["rules"]:
        rule["review_status"] = "DRAFT"
    monkeypatch.setattr(module, "_rules", lambda: (data, hash_))
    context = g.inference_context(
        "T", {"omega_consistent": True, "extends_pa": True, "classical_first_order": True}
    )
    assert g.infer("consistent", True, context)["status"] == "UNKNOWN"


def test_twelve_topics_and_search_are_explicit():
    assert len(g.catalogue_topics()) == 12
    assert any(r["id"] == "consistency_formula" for r in g.search_catalogue("Con_Pr"))
    assert g.search_catalogue("CON_PR") == g.search_catalogue("con_pr")
    assert all("metatheory" in r["topic_ids"] for r in g.search_catalogue("", topic="metatheory"))
    with pytest.raises(g.GoedelError):
        g.search_catalogue("", topic="bogus")
    assert len(g.list_inference_rules()) >= 5


def test_graph_types_are_not_implications():
    data = g.catalogue_graph()
    assert {"REQUIRES", "RULE_PREMISE", "RULE_CONCLUSION"} <= {e["kind"] for e in data["edges"]}
    assert len({n["id"] for n in data["nodes"]}) == len(data["nodes"])
    nx = pytest.importorskip("networkx")
    graph = g.catalogue_graph("networkx")
    assert isinstance(graph, nx.MultiDiGraph)
    assert graph.number_of_nodes() == len(data["nodes"])
    for edge in data["edges"]:
        assert graph[edge["source"]][edge["target"]][edge["id"]] == edge


def test_reviewed_three_step_chain_and_polarity():
    context = g.inference_context(
        "T",
        {
            "classical_first_order": True,
            "extends_pa": True,
            "omega_consistent": True,
            "decidable_axiom_set": True,
            "standard_arithmetization": True,
        },
    )
    result = g.infer("syntactically_complete", False, context)
    assert result["status"] == "ESTABLISHED"
    assert [s["rule"] for s in result["witness"]["steps"] if s["source"] == "RULE"] == [
        "omega_to_sigma1",
        "sigma1_to_consistent",
        "rosser_incomplete",
    ]
    assert g.check_derivation(result["witness"], context)["status"] == "ESTABLISHED"
    assert g.infer("syntactically_complete", True, context)["status"] == "UNKNOWN"
    # A rule with the opposite polarity is not a rule with the same name.
    witness = copy.deepcopy(result["witness"])
    witness["steps"][-1]["fact"]["value"] = True
    assert g.check_derivation(witness)["status"] == "REFUTED"
    wrong_assumptions = dict(context["assumptions"], consistent=False)
    assert (
        g.infer("syntactically_complete", False, g.inference_context("T", wrong_assumptions))["status"]
        == "INCONSISTENT_CONTEXT"
    )


def test_derivation_may_not_skip_a_required_hypothesis():
    context = g.inference_context(
        "T",
        {
            "classical_first_order": True,
            "extends_pa": True,
            "omega_consistent": True,
        },
    )
    result = g.infer("consistent", True, context)
    witness = copy.deepcopy(result["witness"])
    witness["steps"][-1]["premises"].pop()
    assert g.check_derivation(witness)["status"] == "REFUTED"
    assert g.infer("consistent", True, context, max_steps=3)["status"] == "UNKNOWN"
