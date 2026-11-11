"""Executable public example covering every exported callable."""
import goedel as g

x, y = g.variable("x"), g.variable("y")
zero = g.constant("zero")
successor = g.function_term("S", [x])
atom = g.predicate("P", [successor])
assert isinstance(atom, g.Expr)
assert g.validate_expr(g.equal(x, zero))
assert g.validate_expr(g.negate(g.bottom()))
assert g.validate_expr(g.disjunction(g.predicate("A"), g.predicate("B")))
assert g.validate_expr(g.exists("x", atom))
formula = g.forall("y", g.predicate("R", [x, y]))
assert g.bound_variables(formula) == ["y"]
changed = g.substitute(formula, "x", y)
assert g.free_variables(changed) == ["y"]
assert g.alpha_equal(changed, g.normalize(changed))
assert g.deserialize(g.serialize(changed)) == changed
assert g.decode(g.encode(changed)) == changed
assert len(g.fingerprint(changed)) == 64
assert g.numbering()["max_bytes"] == 1024
p, q = g.predicate("P"), g.predicate("Q")
assumptions = [g.conjunction(p, g.implication(p, q))]
result = g.bounded_proof_search(q, assumptions)
assert result["status"] == "ESTABLISHED"
assert g.check_proof(result["witness"], assumptions, conclusion=q)["status"] == "ESTABLISHED"
assert g.list_statements() and g.list_definitions()
assert g.lookup_statement("rosser")["id"] == "rosser"
assert g.definition(g.list_definitions()[0])["id"] == g.list_definitions()[0]
assert g.check_applicability("rosser", g.theory_context("PA"))["status"] == "UNKNOWN"
assert g.relation_graph()["nodes"] == g.list_statements()
assert g.catalogue_manifest()["catalogue_version"] == "0.1.0"
try:
    g.decode("0")
except g.GoedelError as error:
    assert error.code == "INVALID_INPUT"
else:
    raise AssertionError("Invalid code accepted")
print("goedel example passed")
