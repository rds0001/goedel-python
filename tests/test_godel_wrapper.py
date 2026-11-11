"""Composition only: the full PA Goedel fixed point is not computed by this test.

The real built-in provability graph and wrapper negation execute. Only the
expensive generic constructor is replaced; its sentinel is not a proof result.
"""

import hashlib
import json

import pytest

import goedel as g
from goedel import metatheorems as module

_PREDICATE_SHA256 = "58fcc5492a6ef053c6176075570f1486859c7cdb6cc765812d01f72bdb3ce2ad"


def _syntax_hashes(graph):
    """Exact rooted syntax oracle, insensitive to sharing but not binder names."""
    hashes = []
    for node in graph["nodes"]:
        record = [node["op"], node["name"], [hashes[index] for index in node["args"]]]
        hashes.append(hashlib.sha256(json.dumps(record, separators=(",", ":")).encode("ascii")).hexdigest())
    return hashes


def test_godel_wrapper_binds_real_negated_predicate_and_propagates_result_and_limit(monkeypatch):
    predicate = g.provability_formula()
    assert g.dag_fingerprint(predicate) == _PREDICATE_SHA256
    expected = _syntax_hashes(predicate)[predicate["root"]]
    calls = []
    sentinel = object()  # Deliberately not a mathematical result or proof witness.

    def capture(phi):
        calls.append(phi)
        return sentinel

    monkeypatch.setattr(module, "fixed_point", capture)
    assert g.godel_sentence() is sentinel
    assert len(calls) == 1
    phi = calls.pop()
    assert g.validate_arithmetic_dag(phi)["free_variables"] == ["x1"]
    root = phi["nodes"][phi["root"]]
    assert root["op"] == "not" and root["name"] == "" and len(root["args"]) == 1
    assert _syntax_hashes(phi)[root["args"][0]] == expected

    exhausted = g.GoedelError("RESOURCE_LIMIT", "test-only constructor resource limit")

    def fail(phi):
        calls.append(phi)
        raise exhausted

    monkeypatch.setattr(module, "fixed_point", fail)
    with pytest.raises(g.GoedelError) as caught:
        g.godel_sentence()
    assert caught.value is exhausted
    assert caught.value.code == "RESOURCE_LIMIT"
    assert len(calls) == 1
    assert calls[0] == phi
