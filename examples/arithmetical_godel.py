"""Construct a concrete fixed point; --godel uses the packaged PA provability formula."""

from __future__ import annotations

import argparse
import hashlib
import json

import goedel as g


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--godel", action="store_true", help="Use not Pr_PA(x); codes may have millions of digits"
    )
    args = parser.parse_args()
    result = g.godel_sentence() if args.godel else g.fixed_point(g.arithmetic_dag(g.parse_formula("x = 0")))
    witness = result["witness"]
    assert witness["checked_proof"]["status"] == "ESTABLISHED"
    assert result["details"]["code_equation_checked"]
    assert not g.validate_arithmetic_dag(witness["G"])["free_variables"]
    print(
        json.dumps(
            {
                "status": result["status"],
                "claim": result["claim"],
                "G_sha256": g.dag_fingerprint(witness["G"]),
                "q_digits": len(witness["q"]),
                "m_digits": len(witness["m"]),
                "m_sha256": hashlib.sha256(witness["m"].encode("ascii")).hexdigest(),
                "trusted_premise_count": len(witness["trusted_premises"]),
                "unprovability_asserted": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
