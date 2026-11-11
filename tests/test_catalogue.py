import copy

import pytest

import goedel as g
from goedel import catalogue


def test_catalogue_inventory_and_public_metadata():
    statements = g.list_statements()
    definitions = g.list_definitions()
    assert statements == sorted(statements) and len(statements) >= 8
    assert definitions == sorted(definitions) and definitions
    for identifier in statements:
        record = g.lookup_statement(identifier)
        assert record["id"] == identifier
        assert record["requirements"]
        assert record["evidence"]["kind"] == "LITERATURE_RESULT"
    for identifier in definitions:
        assert g.definition(identifier)["id"] == identifier
    graph = g.relation_graph()
    assert graph["nodes"] == statements
    assert isinstance(graph["edges"], list)
    manifest = g.catalogue_manifest()
    assert manifest["catalogue_version"] == "0.2.0"
    assert len(manifest["sha256"]) == 64
    for lookup in [g.lookup_statement, g.definition]:
        with pytest.raises(g.GoedelError):
            lookup("does_not_exist")


def test_theory_declarations_never_certify_consistency():
    context = g.theory_context("PA", {"consistent": True})
    assert context["consistency_status"] == "NOT_ESTABLISHED"
    context["assumptions"]["consistent"] = False
    assert g.theory_context("PA", {"consistent": True})["assumptions"]["consistent"] is True
    for values in [{"consistent": 1}, {1: True}, {"": True}, [], {"consistent": None}]:
        with pytest.raises(g.GoedelError):
            g.theory_context("T", values)
    with pytest.raises(g.GoedelError):
        g.theory_context("")


def test_live_catalogue_missing_and_violated_conditions():
    for identifier in g.list_statements():
        record = g.lookup_statement(identifier)
        assert g.check_applicability(identifier, g.theory_context("PA"))["status"] == "UNKNOWN"
        values = {key: True for key in record["requirements"]}
        full = g.check_applicability(identifier, g.theory_context("T", values))
        active = record["evidence"]["review_status"] == "REVIEWED" and record["evidence"]["verification_status"] == "INDEPENDENTLY_CHECKED"
        assert full["status"] == ("ESTABLISHED" if active else "UNKNOWN")
        assert full["context"]["consistency_status"] == "NOT_ESTABLISHED"
        assert "conditional" in " ".join(full["limitations"])


def test_draft_withdrawn_and_promoted_evidence_guards(monkeypatch):
    fixture = {"id": "fixture", "requirements": ["consistent", "effective"],
               "evidence": {"kind": "LITERATURE_RESULT", "review_status": "REVIEWED",
                            "verification_status": "INDEPENDENTLY_CHECKED"}, "limitations": []}
    monkeypatch.setattr(catalogue, "lookup_statement", lambda _: copy.deepcopy(fixture))
    assert g.check_applicability("fixture", g.theory_context("T", {"consistent": True, "effective": True}))["status"] == "ESTABLISHED"
    assert g.check_applicability("fixture", g.theory_context("T", {"consistent": False}))["status"] == "NOT_APPLICABLE"
    assert g.check_applicability("fixture", g.theory_context("T", {"consistent": True}))["details"]["missing_requirements"] == ["effective"]
    fixture["evidence"]["review_status"] = "DRAFT"
    assert g.check_applicability("fixture", g.theory_context("T", {"consistent": True, "effective": True}))["status"] == "UNKNOWN"
    fixture["evidence"]["review_status"] = "WITHDRAWN"
    assert g.check_applicability("fixture", g.theory_context("T", {"consistent": True, "effective": True}))["status"] == "UNKNOWN"
    assert g.check_applicability("fixture", g.theory_context("T", {"consistent": False, "omega_consistent": True}))["status"] == "INCONSISTENT_CONTEXT"
    assert g.check_applicability("fixture", g.theory_context("T", {"consistent": False, "sigma1_sound": True}))["status"] == "INCONSISTENT_CONTEXT"
    context = g.theory_context("T")
    context["consistency_status"] = "PROVED"
    with pytest.raises(g.GoedelError):
        g.check_applicability("fixture", context)
