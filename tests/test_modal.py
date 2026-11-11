"""Independent finite modal countermodels and exhaustive small-frame checks."""

import itertools

import pytest

import goedel as g


def loeb():
    p = g.modal_atom("p")
    return g.modal_implication(g.modal_box(g.modal_implication(g.modal_box(p), p)), g.modal_box(p))


def test_loeb_reflexive_singleton_countermodel():
    model = g.kripke_model(["0"], [["0", "0"]], {"p": []})
    assert g.frame_check(model) == {
        "reflexive": True,
        "irreflexive": False,
        "transitive": True,
        "acyclic": False,
    }
    assert g.evaluate_modal(loeb(), model, "0")["status"] == "REFUTED"
    assert g.validate_modal_frame(loeb(), ["0"], [["0", "0"]])["witness"] == {
        "world": "0",
        "valuation": {"p": []},
    }


def test_transitivity_is_essential_and_all_eight_valuations():
    path = [["0", "1"], ["1", "2"]]
    closure = path + [["0", "2"]]
    nontransitive = g.kripke_model(["0", "1", "2"], path, {"p": []})
    assert not g.frame_check(nontransitive)["transitive"]
    assert g.evaluate_modal(loeb(), nontransitive, "0")["status"] == "REFUTED"
    result = g.validate_modal_frame(loeb(), ["0", "1", "2"], closure)
    assert result["status"] == "ESTABLISHED"
    assert result["details"] == {"valuations_checked": 8, "worlds_checked": 24}
    # Independent direct truth calculation from the definition of box.
    worlds = ["0", "1", "2"]
    for bits in itertools.product([False, True], repeat=3):
        truth = dict(zip(worlds, bits))
        box_p = {w: all(truth[v] for u, v in closure if u == w) for w in worlds}
        for w in worlds:
            antecedent = all((not box_p[v]) or truth[v] for u, v in closure if u == w)
            assert (not antecedent) or box_p[w]


def test_modal_connectives_and_vacuous_modalities():
    model = g.kripke_model(["w"], [], {"p": []})
    p = g.modal_atom("p")
    examples = [
        (g.modal_box(p), True),
        (g.modal_diamond(p), False),
        (g.modal_negate(p), True),
        (g.modal_disjunction(p, g.modal_negate(p)), True),
        (g.modal_conjunction(p, g.modal_negate(p)), False),
        (g.modal_bottom(), False),
    ]
    for formula, expected in examples:
        assert g.evaluate_modal(formula, model, "w")["details"]["value"] is expected


def test_modal_validation_errors_and_limits():
    assert g.ModalExpr("atom", "p") == g.modal_atom("p")
    for args in [
        (["w", "w"], [], {}),
        (["w"], [["w", "outside"]], {}),
        (["w"], [["w", "w"], ["w", "w"]], {}),
        (["w"], [], {"p": ["outside"]}),
    ]:
        with pytest.raises(g.GoedelError):
            g.kripke_model(*args)
    with pytest.raises(g.GoedelError):
        g.evaluate_modal(g.modal_atom("p"), g.kripke_model(["w"], []), "w")
    with pytest.raises(g.GoedelError) as caught:
        g.validate_modal_frame(loeb(), ["0", "1", "2"], [], max_valuations=4)
    assert caught.value.code == "RESOURCE_LIMIT"
    with pytest.raises(g.GoedelError) as caught:
        g.evaluate_modal(loeb(), g.kripke_model(["w"], [["w", "w"]], {"p": []}), "w", max_steps=1)
    assert caught.value.code == "RESOURCE_LIMIT"
