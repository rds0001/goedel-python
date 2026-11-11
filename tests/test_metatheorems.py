"""Identity, polarity and reviewed-schema guards for distinct metatheorems."""

import copy

import pytest

import goedel as g
from goedel import metatheorems as module


def test_conditional_second_and_loeb_are_distinct():
    second = g.check_metatheorem("godel_second_hbl", {"consistent": True})
    loeb = g.check_metatheorem("lob", {})
    assert second["status"] == loeb["status"] == "ESTABLISHED"
    assert second["assumptions"] == {"consistent": True}
    assert loeb["assumptions"] == {}
    assert second["details"]["statement_id"] != loeb["details"]["statement_id"]
    assert second["mode"] == "CATALOGUE_INFERENCE"
    assert second["details"]["hbl_conditions"] == {"D1": "REVIEWED", "D2": "REVIEWED", "D3": "REVIEWED"}
    assert g.check_metatheorem("godel_second_hbl", {})["status"] == "UNKNOWN"
    assert g.check_metatheorem("godel_second_hbl", {"consistent": False})["status"] == "NOT_APPLICABLE"


@pytest.mark.parametrize(
    "id,missing,provided",
    [
        ("godel_first_consistency", "consistent", {"consistent": True}),
        ("godel_first_omega", "omega_consistent", {"omega_consistent": True}),
        ("godel_first_sigma1", "sigma1_sound", {"sigma1_sound": True}),
        ("rosser", "consistent", {"consistent": True}),
        ("tarski", "standard_naturals", {"standard_naturals": True}),
    ],
)
def test_no_automatic_consistency_soundness_or_standard_model(id, missing, provided):
    unknown = g.check_metatheorem(id, {})
    assert unknown["status"] == "UNKNOWN"
    assert missing in unknown["details"]["missing_requirements"]
    assert g.check_metatheorem(id, provided)["status"] == "ESTABLISHED"


def test_custom_identity_cannot_gain_hbl_by_user_flags():
    identity = g.provability_identity()
    identity["predicate_sha256"] = "0" * 64
    result = g.check_metatheorem(
        "godel_second_hbl",
        {
            "consistent": True,
            "hbl_conditions": True,
            "D1": True,
            "D2": True,
            "D3": True,
            "provability_predicate_fixed": True,
        },
        identity,
    )
    assert result["status"] == "UNKNOWN"
    assert result["details"]["identity_status"] == "UNREVIEWED_IDENTITY"
    assert result["details"]["representation_review"] == "PENDING"
    assert result["details"]["hbl_conditions"]["D2"] == "OPEN"


def test_missing_d2_and_wrong_review_identity_fail_closed(monkeypatch):
    original, pinned = module._review()
    assert pinned
    for mutation in ("missing_d2", "wrong_predicate", "source_only"):
        bundle = copy.deepcopy(original)
        if mutation == "missing_d2":
            del bundle["hbl_review"]["conditions"]["D2"]
        elif mutation == "wrong_predicate":
            bundle["hbl_review"]["predicate_identity"]["predicate_sha256"] = "0" * 64
        else:
            bundle["hbl_review"]["conditions"]["D2"]["status"] = "SOURCE_CHECKED"
        monkeypatch.setattr(module, "_review", lambda: (bundle, True))
        result = g.check_metatheorem("lob", {"hbl_conditions": True, "D2": True})
        assert result["status"] == "UNKNOWN"
        assert "D2" in result["details"]["missing_requirements"]


def test_unpinned_bundle_is_not_a_review(monkeypatch):
    bundle, _ = module._review()
    monkeypatch.setattr(module, "_review", lambda: (bundle, False))
    assert g.check_metatheorem("lob", {"hbl_conditions": True})["status"] == "UNKNOWN"


@pytest.mark.parametrize(
    "assumptions",
    [
        {"classical_first_order": False},
        {"D2": False},
        {"hbl_conditions": False},
        {"consistent": False, "omega_consistent": True},
    ],
)
def test_inconsistent_declared_context_is_explicit(assumptions):
    assert g.check_metatheorem("lob", assumptions)["status"] == "INCONSISTENT_CONTEXT"


def test_definition_record_cannot_be_promoted_to_metatheorem(monkeypatch):
    original = module.lookup_statement

    def wrong_kind(id):
        record = original(id)
        record["evidence"]["kind"] = "DEFINITION"
        return record

    monkeypatch.setattr(module, "lookup_statement", wrong_kind)
    assert g.check_metatheorem("lob", {})["status"] == "UNKNOWN"


def test_review_references_hash_actual_installed_resource_bytes(monkeypatch, tmp_path):
    from importlib.resources import files

    destination = tmp_path / "resources"
    destination.mkdir()
    for name in (
        "provability_representation.json",
        "pa_proof_representation.json",
        "substitution_representation.json",
    ):
        payload = files("goedel").joinpath("resources/" + name).read_bytes()
        (destination / name).write_bytes(payload)
    monkeypatch.setattr(module, "files", lambda package: tmp_path)
    assert module._review()[1]
    dependency = destination / "pa_proof_representation.json"
    dependency.write_bytes(dependency.read_bytes() + b"\n")
    assert not module._review()[1]  # even an equivalent JSON spelling has a new source identity
