"""Literal lexical counterexamples for DAG alpha comparison."""

import copy

import pytest

import goedel as g


@pytest.mark.parametrize(
    "left,right,expected",
    [
        ("forall x. exists x. x = y", "forall x. exists x. x = y", True),
        ("forall x. exists x. x = y", "forall a. exists b. b = y", True),
        ("forall x. exists x. x = y", "forall a. exists b. a = y", False),
        ("forall x. x = y", "forall y. y = y", False),
        ("forall x. exists y. x = y", "forall x. exists y. x = x", False),
    ],
)
def test_literal_binding_and_shadowing(left, right, expected):
    left_dag = g.arithmetic_dag(g.parse_formula(left))
    right_dag = g.arithmetic_dag(g.parse_formula(right))
    assert g.dag_alpha_equal(left_dag, right_dag) is expected


def test_irrelevant_prefix_changes_preserve_denoted_syntax():
    first = {
        "schema_version": "1.0",
        "nodes": [
            {"op": "zero", "name": "", "args": []},
            {"op": "var", "name": "x0", "args": []},
            {"op": "eq", "name": "", "args": [1, 1]},
        ],
        "root": 2,
    }
    different = copy.deepcopy(first)
    different["nodes"][0] = {"op": "num", "name": "7", "args": []}
    shorter = {
        "schema_version": "1.0",
        "nodes": [
            {"op": "var", "name": "x0", "args": []},
            {"op": "eq", "name": "", "args": [0, 0]},
        ],
        "root": 1,
    }
    assert g.dag_alpha_equal(first, different)
    assert g.dag_alpha_equal(first, shorter)
    assert g.dag_alpha_equal(first, copy.deepcopy(first))


def test_identical_invalid_graphs_are_still_rejected():
    invalid = {
        "schema_version": "1.0",
        "nodes": [{"op": "succ", "name": "", "args": [0]}],
        "root": 0,
    }
    with pytest.raises(g.GoedelError):
        g.dag_alpha_equal(invalid, invalid)
