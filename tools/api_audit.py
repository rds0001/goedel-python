"""Check documented exports against examples and direct test references."""
import ast
import inspect
from pathlib import Path

import goedel

ROOT = Path(__file__).resolve().parents[1]
docs = (ROOT / "docs/API.md").read_text()
references = set()
for path in [*(ROOT / "tests").glob("*.py"), *(ROOT / "examples").glob("*.py")]:
    tree = ast.parse(path.read_text())
    references.update(node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "g")
for name in goedel.__all__:
    assert callable(getattr(goedel, name)), name
    assert inspect.getdoc(getattr(goedel, name)), name
    assert "## " + name + "\n" in docs, name
    assert name in references, name
print({"status": "PASS", "exports": len(goedel.__all__)})
