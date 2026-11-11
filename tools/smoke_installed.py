"""Run outside the source tree using an isolated installed Python interpreter."""
import importlib.metadata
import json
import sysconfig
from pathlib import Path

import goedel as g

origin = Path(g.__file__).resolve()
assert any(origin.is_relative_to(Path(sysconfig.get_path(k)).resolve()) for k in ("purelib", "platlib"))
x, y = g.variable("x"), g.variable("y")
changed = g.substitute(g.forall("y", g.predicate("R", [x, y])), "x", y)
assert changed == g.forall("v0", g.predicate("R", [y, g.variable("v0")]))
assert g.decode(g.encode(changed)) == changed
p, q = g.predicate("P"), g.predicate("Q")
assumptions = [p, g.implication(p, q)]
result = g.bounded_proof_search(q, assumptions)
assert result["status"] == "ESTABLISHED"
assert g.check_proof(result["witness"], assumptions, conclusion=q)["status"] == "ESTABLISHED"
assert g.check_applicability("rosser", g.theory_context("PA"))["status"] == "UNKNOWN"
assert g.catalogue_manifest()["catalogue_version"] == "0.2.0"
induction = g.induction_axiom(g.equal(g.add(x, y), g.add(y, x)), "x")
assert g.is_axiom(g.arithmetic_theory("PA"), induction)
assert not g.is_axiom(g.arithmetic_theory("Q"), induction)
assert g.sequence_decode(g.sequence_encode(["0", "9007199254740993"])) == ["0", "9007199254740993"]
dag = g.arithmetic_dag(g.equal(x, x))
assert g.check_scoped_dag_proof([{"rule": "eq_refl", "formula": dag, "premises": [], "scope": []}])["status"] == "ESTABLISHED"
modal_p = g.modal_atom("p")
loeb = g.modal_implication(g.modal_box(g.modal_implication(g.modal_box(modal_p), modal_p)), g.modal_box(modal_p))
assert g.evaluate_modal(loeb, g.kripke_model(["w"], [["w", "w"]], {"p": []}), "w")["status"] == "REFUTED"

structure = g.finite_structure(["a"], {"zero": "a"})
assert g.evaluate_formula(g.equal(g.zero(), g.zero()), structure)["status"] == "ESTABLISHED"
identity_proof = [
    {"rule": "assume", "formula": p, "premises": [], "scope": [1]},
    {"rule": "imp_intro", "formula": g.implication(p, p), "premises": [1], "scope": [], "discharge": [1]},
]
assert g.check_scoped_proof(identity_proof)["status"] == "ESTABLISHED"
transport = g.encode_proof(g.proof_object(identity_proof))
assert g.check_proof_code(transport)["status"] == "ESTABLISHED"
context = g.inference_context("T", {"classical_first_order": True, "extends_pa": True, "omega_consistent": True})
chain = g.infer("consistent", True, context)
assert chain["status"] == "ESTABLISHED"
assert g.check_derivation(chain["witness"], context)["status"] == "ESTABLISHED"
pa_axiom_code = g.arithmetic_dag_encode(g.hilbert_q_axiom(4))
pa_proof = g.pa_proof_encode([{"rule": 14, "formula": pa_axiom_code, "aux_a": "0", "aux_b": "0"}])
assert g.check_pa_proof(pa_proof, pa_axiom_code)["status"] == "ESTABLISHED"
assert g.check_metatheorem("godel_second_hbl", {})["status"] == "UNKNOWN"
assert g.check_metatheorem("godel_second_hbl", {"consistent": True})["status"] == "ESTABLISHED"
assert g.check_metatheorem("lob", {})["status"] == "ESTABLISHED"
# Installation smoke checks stay small; full arithmetic fixed points are opt-in.
assert len(g.validate_arithmetic_dag(dag)["free_variables"]) == 1
print(json.dumps({"status": "PASS", "version": importlib.metadata.version("goedel"), "origin": str(origin), "large_fixedpoint": "NOT_RUN"}))
