"""Typed conditional catalogue inference with independent witness replay."""

from __future__ import annotations

import copy
import hashlib
import json
from importlib.resources import files
from typing import Any

from .catalogue import _catalogue, catalogue_manifest, theory_context
from .proof import _result
from .syntax import _error

_LIMIT = (
    "Conditional catalogue inference; declarations and literature premises are not proved by this replay."
)


def _rules():
    raw = files("goedel").joinpath("resources/inference_rules.json").read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def inference_context(
    theory: str,
    assumptions: dict[str, bool] | None = None,
    metatheory: str = "ordinary_classical_metamathematics",
    predicate_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind declarations to explicit theory, metatheory and optional predicate identities."""
    declared = theory_context(theory, assumptions)
    if not isinstance(metatheory, str) or not metatheory or len(metatheory) > 128:
        _error("Metatheory must be a nonempty label of at most 128 characters")
    if predicate_identity is not None and not isinstance(predicate_identity, dict):
        _error("Predicate identity must be an explicit record or None")
    return {
        "schema_version": "1.0",
        "theory_id": theory,
        "metatheory_id": metatheory,
        "level": "META",
        "assumptions": declared["assumptions"],
        "predicate_identity": copy.deepcopy(predicate_identity),
    }


def _context(context):
    keys = {"schema_version", "theory_id", "metatheory_id", "level", "assumptions", "predicate_identity"}
    if (
        not isinstance(context, dict)
        or set(context) != keys
        or context["schema_version"] != "1.0"
        or context["level"] != "META"
    ):
        _error("Invalid inference context or object/metatheory level")
    return inference_context(
        context["theory_id"], context["assumptions"], context["metatheory_id"], context["predicate_identity"]
    )


def _fact(prop, value, context):
    if not isinstance(prop, str) or not prop or len(prop) > 128 or type(value) is not bool:
        _error("A property label and boolean polarity are required")
    return {
        "property": prop,
        "value": value,
        "level": "META",
        "theory_id": context["theory_id"],
        "metatheory_id": context["metatheory_id"],
        "predicate_identity": context["predicate_identity"],
    }


def _predicate_reviewed(context):
    identity = context["predicate_identity"]
    if identity is None:
        return False
    # The pinned mathematical review is separate from user declarations.
    from .metatheorems import _review
    from .pa_provability import provability_identity

    try:
        resource, pinned = _review()
    except FileNotFoundError:
        return False
    hbl = resource.get("hbl_review", {})
    return (
        pinned
        and context["theory_id"] == identity.get("theory_id")
        and identity == resource.get("identity") == provability_identity()
        and resource.get("review", {}).get("status") == "INDEPENDENTLY_CHECKED"
        and resource.get("review", {}).get("hbl_schemas_reviewed") is True
        and hbl.get("status") == "INDEPENDENTLY_CHECKED"
        and hbl.get("predicate_identity") == identity
        and all(
            hbl.get("conditions", {}).get(name, {}).get("status") == "INDEPENDENTLY_CHECKED"
            for name in ("D1", "D2", "D3")
        )
    )


def _usable(rule, context):
    if rule.get("statement_id") is not None:
        catalogue, _ = _catalogue()
        statements = [s for s in catalogue["statements"] if s["id"] == rule["statement_id"]]
        if len(statements) != 1:
            return False
        statement = statements[0]
        evidence = statement.get("evidence", {})
        if (
            statement.get("active", True) is not True
            or evidence.get("kind") != "LITERATURE_RESULT"
            or evidence.get("review_status") != "REVIEWED"
            or evidence.get("verification_status") not in {"INDEPENDENTLY_CHECKED", "FORMALLY_VERIFIED"}
            or any(rule["premises"].get(name) is not True for name in statement["requirements"])
        ):
            return False
    return (
        rule["active"] is True
        and rule["review_status"] == "REVIEWED"
        and rule.get("verification_status") in {"INDEPENDENTLY_CHECKED", "FORMALLY_VERIFIED"}
        and (not rule["requires_predicate"] or _predicate_reviewed(context))
    )


def list_inference_rules() -> list[dict[str, Any]]:
    """List rules with hypotheses, polarity, provenance and review status."""
    data, _ = _rules()
    return copy.deepcopy(sorted(data["rules"], key=lambda r: r["id"]))


def _result_for(status, context, witness, details, dependencies=()):
    return _result(
        status,
        "CATALOGUE_INFERENCE",
        "Conditional typed catalogue consequence",
        context["assumptions"],
        [],
        [_LIMIT],
        witness,
        details,
        context=context,
        dependencies=list(dependencies),
    )


def check_derivation(witness: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Independently replay rule applications and identity/hash-bound premises."""
    required = {"schema_version", "context", "catalogue_sha256", "rules_sha256", "steps", "goal"}
    if not isinstance(witness, dict) or set(witness) != required or witness["schema_version"] != "1.0":
        _error("Malformed catalogue derivation envelope")
    stored = _context(witness["context"])
    checked = stored if context is None else _context(context)

    def fail(reason, index=None):
        return _result_for("REFUTED", checked, None, {"reason": reason, "invalid_step": index})

    if stored != checked:
        return fail("CONTEXT_IDENTITY_MISMATCH")
    data, rule_hash = _rules()
    if witness["catalogue_sha256"] != catalogue_manifest()["sha256"] or witness["rules_sha256"] != rule_hash:
        return fail("STALE_RESOURCE_HASH")
    steps = witness["steps"]
    if not isinstance(steps, list) or len(steps) > 4096:
        _error(
            "Derivation requires at most 4096 steps",
            "RESOURCE_LIMIT" if isinstance(steps, list) else "INVALID_INPUT",
        )
    goal = witness["goal"]
    if type(goal) is not int or not 1 <= goal <= len(steps):
        return fail("INVALID_GOAL_REFERENCE")
    rules = {r["id"]: r for r in data["rules"]}
    established = {}
    dependencies = []
    for index, step in enumerate(steps, 1):
        if not isinstance(step, dict) or set(step) != {"fact", "source", "rule", "premises"}:
            _error("Malformed derivation step")
        fact = step["fact"]
        if not isinstance(fact, dict) or set(fact) != {
            "property",
            "value",
            "level",
            "theory_id",
            "metatheory_id",
            "predicate_identity",
        }:
            _error("Malformed typed fact")
        if fact != _fact(fact["property"], fact["value"], checked):
            return fail("FACT_CONTEXT_OR_LEVEL_MISMATCH", index)
        refs = step["premises"]
        if not isinstance(refs, list) or any(type(r) is not int or not 1 <= r < index for r in refs):
            return fail("INVALID_PREMISE_REFERENCE", index)
        prop, value = fact["property"], fact["value"]
        if prop in established and established[prop] != value:
            return _result_for(
                "INCONSISTENT_CONTEXT", checked, None, {"reason": "CONTRADICTORY_FACTS", "property": prop}
            )
        if step["source"] == "DECLARATION":
            if step["rule"] is not None or refs or checked["assumptions"].get(prop) is not value:
                return fail("UNDECLARED_PREMISE", index)
            dependencies.append({"property": prop, "value": value, "source": "DECLARED_NOT_VERIFIED"})
        elif step["source"] == "RULE":
            if not isinstance(step["rule"], str):
                return fail("RULE_UNAVAILABLE_OR_UNREVIEWED", index)
            rule = rules.get(step["rule"])
            if rule is None or not _usable(rule, checked):
                return fail("RULE_UNAVAILABLE_OR_UNREVIEWED", index)
            if rule["conclusion"] != {"property": prop, "value": value}:
                return fail("RULE_CONCLUSION_MISMATCH", index)
            required_names = sorted(rule["premises"])
            if len(refs) != len(required_names):
                return fail("RULE_PREMISES_MISMATCH", index)
            for name, ref in zip(required_names, refs):
                expected = _fact(name, rule["premises"][name], checked)
                if steps[ref - 1]["fact"] != expected:
                    return fail("RULE_PREMISES_MISMATCH", index)
        else:
            return fail("UNKNOWN_STEP_SOURCE", index)
        established[prop] = value
    return _result_for(
        "ESTABLISHED",
        checked,
        copy.deepcopy(witness),
        {"reason": "VALID_CONDITIONAL_DERIVATION", "conclusion": steps[goal - 1]["fact"]},
        dependencies,
    )


def infer(property: str, value: bool, context: dict[str, Any], max_steps: int = 256) -> dict[str, Any]:
    """Find a finite typed rule chain; failure means UNKNOWN, never unprovability."""
    checked = _context(context)
    goal = _fact(property, value, checked)
    if type(max_steps) is not int or not 1 <= max_steps <= 4096:
        _error("max_steps must be an integer from 1 to 4096")
    data, rule_hash = _rules()
    rules = sorted(data["rules"], key=lambda r: r["id"])
    steps = []
    known = {}

    def admit(prop, polarity, source, rule=None, premises=()):
        if prop in known and steps[known[prop] - 1]["fact"]["value"] != polarity:
            return False
        if prop not in known:
            known[prop] = len(steps) + 1
            steps.append(
                {
                    "fact": _fact(prop, polarity, checked),
                    "source": source,
                    "rule": rule,
                    "premises": list(premises),
                }
            )
        return True

    for prop, polarity in sorted(checked["assumptions"].items()):
        if len(steps) >= max_steps:
            return _result_for("UNKNOWN", checked, None, {"reason": "BOUND_EXHAUSTED"})
        admit(prop, polarity, "DECLARATION")
    progress = True
    while progress:
        progress = False
        for rule in rules:
            if not _usable(rule, checked):
                continue
            if not all(
                p in known and steps[known[p] - 1]["fact"]["value"] is v for p, v in rule["premises"].items()
            ):
                continue
            prop, polarity = rule["conclusion"]["property"], rule["conclusion"]["value"]
            if prop in known:
                if steps[known[prop] - 1]["fact"]["value"] != polarity:
                    return _result_for(
                        "INCONSISTENT_CONTEXT",
                        checked,
                        None,
                        {"reason": "CONTRADICTORY_FACTS", "property": prop},
                    )
                continue
            if len(steps) >= max_steps:
                return _result_for("UNKNOWN", checked, None, {"reason": "BOUND_EXHAUSTED"})
            admit(prop, polarity, "RULE", rule["id"], [known[p] for p in sorted(rule["premises"])])
            progress = True
    if property not in known or steps[known[property] - 1]["fact"] != goal:
        return _result_for(
            "UNKNOWN",
            checked,
            None,
            {
                "reason": "NO_SUPPORTED_DERIVATION",
                "unavailable_rules": [r["id"] for r in rules if not _usable(r, checked)],
            },
        )
    witness = {
        "schema_version": "1.0",
        "context": checked,
        "catalogue_sha256": catalogue_manifest()["sha256"],
        "rules_sha256": rule_hash,
        "steps": steps,
        "goal": known[property],
    }
    return check_derivation(witness, checked)


def explain_derivation(witness: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validated step explanations, retaining unverified declaration labels."""
    result = check_derivation(witness)
    if result["status"] != "ESTABLISHED":
        _error("Cannot explain an invalid or obsolete derivation")
    rules = {r["id"]: r for r in list_inference_rules()}
    return [
        {
            "step": i,
            "fact": copy.deepcopy(s["fact"]),
            "premises": s["premises"],
            "explanation": "User declaration; not independently verified."
            if s["source"] == "DECLARATION"
            else rules[s["rule"]]["argument"],
        }
        for i, s in enumerate(witness["steps"], 1)
    ]


def catalogue_topics() -> list[dict[str, Any]]:
    """Return the twelve-family inventory, distinguishing coverage from verification."""
    data, _ = _catalogue()
    return copy.deepcopy(data.get("topics", []))


def search_catalogue(query: str, topic: str | None = None) -> list[dict[str, Any]]:
    """Search record text and optional topic using deterministic ASCII case folding."""
    if not isinstance(query, str) or len(query) > 256:
        _error("Search query must be text of at most 256 characters")
    if topic is not None and topic not in {r["id"] for r in catalogue_topics()}:
        _error("Unknown catalogue topic")

    def fold(text):
        return text.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))

    needle = fold(query)
    data, _ = _catalogue()
    out = []
    for family in ("definitions", "statements"):
        for record in data[family]:
            if topic is not None and topic not in record.get("topic_ids", []):
                continue
            if needle in fold(json.dumps(record, sort_keys=True, ensure_ascii=True, separators=(",", ":"))):
                out.append(
                    {
                        "id": record["id"],
                        "kind": family[:-1],
                        "title": record.get("title", record.get("name")),
                        "topic_ids": record.get("topic_ids", []),
                        "review_status": record.get("evidence", record)["review_status"],
                    }
                )
    return sorted(out, key=lambda r: (r["kind"], r["id"]))


def catalogue_graph(adapter: str = "records"):
    """Export typed data; optional NetworkX conversion preserves all attributes."""
    if adapter not in {"records", "networkx"}:
        _error("Supported graph adapters are records and networkx", "NOT_SUPPORTED")
    data, _ = _catalogue()
    nodes = []
    for family in ("definitions", "statements"):
        for record in data[family]:
            nodes.append(
                {
                    "id": family[:-1] + ":" + record["id"],
                    "kind": family[:-1],
                    "title": record.get("title", record.get("name")),
                    "level": "META",
                    "topic_ids": record.get("topic_ids", []),
                }
            )
    edges = [
        {
            "id": r["id"],
            "source": "statement:" + r["premise"],
            "target": "statement:" + r["conclusion"],
            "kind": r["kind"],
            "requirements": r["requirements"],
            "review_status": r["evidence"]["review_status"],
        }
        for r in data["relations"]
    ]
    for rule in list_inference_rules():
        rule_id = "rule:" + rule["id"]
        nodes.append({"id": rule_id, "kind": "rule", "title": rule["id"], "level": "META", "topic_ids": []})
        for prop in sorted(set(rule["premises"]) | {rule["conclusion"]["property"]}):
            node_id = "property:" + prop
            if not any(n["id"] == node_id for n in nodes):
                nodes.append(
                    {"id": node_id, "kind": "property", "title": prop, "level": "META", "topic_ids": []}
                )
        for prop, value in sorted(rule["premises"].items()):
            edges.append(
                {
                    "id": rule["id"] + ":premise:" + prop,
                    "source": "property:" + prop,
                    "target": rule_id,
                    "kind": "RULE_PREMISE",
                    "value": value,
                    "review_status": rule["review_status"],
                }
            )
        edges.append(
            {
                "id": rule["id"] + ":conclusion",
                "source": rule_id,
                "target": "property:" + rule["conclusion"]["property"],
                "kind": "RULE_CONCLUSION",
                "value": rule["conclusion"]["value"],
                "review_status": rule["review_status"],
            }
        )
    graph = {
        "nodes": sorted(nodes, key=lambda n: n["id"]),
        "edges": sorted(edges, key=lambda e: e["id"]),
        "catalogue_sha256": catalogue_manifest()["sha256"],
        "rules_sha256": _rules()[1],
    }
    if adapter == "records":
        return graph
    try:
        import networkx as nx
    except ImportError:
        _error("Install the optional graph dependency networkx", "NOT_SUPPORTED")
    result = nx.MultiDiGraph(catalogue_sha256=graph["catalogue_sha256"], rules_sha256=graph["rules_sha256"])
    for node in graph["nodes"]:
        result.add_node(node["id"], **copy.deepcopy(node))
    for edge in graph["edges"]:
        result.add_edge(edge["source"], edge["target"], key=edge["id"], **copy.deepcopy(edge))
    return result
