#!/usr/bin/env python3
"""Inspect all publication candidates, excluding only local Git internals/caches."""
from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPORT_PACKAGE = "goedel"
FORBIDDEN_DIRS = {"goedel-scaffold", "transformation", "scaffold", "unterlagen", "intern", "archiv", "downloads", "downloaded-documents"}
FORBIDDEN_SUFFIXES = {".pdf", ".doc", ".docx", ".odt", ".zip"}
LOCAL_ONLY = {".git", ".venv", ".cache", ".pytest_cache", ".ruff_cache", "__pycache__", ".hypothesis"}
REQUIRED = {"README.md", "LICENSE", "NOTICE", "pyproject.toml",
            f"src/{IMPORT_PACKAGE}/__init__.py", f"src/{IMPORT_PACKAGE}/py.typed"}


def main():
    if IMPORT_PACKAGE.startswith("__"):
        raise AssertionError("Source validator still contains scaffold placeholders")
    failures = []
    resources = ROOT / "src/goedel/resources"
    resource_manifest = json.loads((resources / "resource_manifest.json").read_text())
    actual = {p.name for p in resources.iterdir() if p.is_file()}
    expected = set(resource_manifest["files"]) | {"resource_manifest.json"}
    if actual != expected:
        failures.append("Unapproved resource files")
    def scan(value):
        if isinstance(value, dict):
            if any(key in value for key in ("private_locator", "never_publish", "current_authorization", "scaffold_version")):
                failures.append("Private metadata in public resource")
            for item in value.values():
                scan(item)
        elif isinstance(value, list):
            for item in value:
                scan(item)
    for name, digest in resource_manifest["files"].items():
        data = (resources / name).read_bytes()
        if sha256(data).hexdigest() != digest:
            failures.append("Resource hash mismatch: " + name)
        scan(json.loads(data))
    reproduction = ROOT / "tools/reproduction"
    reproduction_manifest = json.loads((reproduction / "manifest.json").read_text())
    expected_reproduction = set(reproduction_manifest["files_sha256"]) | {"manifest.json"}
    observed_reproduction = {p.name for p in reproduction.iterdir() if p.is_file()}
    if observed_reproduction != expected_reproduction:
        failures.append("Unapproved reproduction files")
    for name, digest in reproduction_manifest["files_sha256"].items():
        if Path(name).name != name or sha256((reproduction / name).read_bytes()).hexdigest() != digest:
            failures.append("Reproduction source hash mismatch: " + name)
    count = 0
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        parts = {part.lower() for part in relative.parts}
        if parts & LOCAL_ONLY:
            continue
        if path.is_symlink():
            failures.append(relative.as_posix() + ": symlink requires explicit publication review")
        if parts & FORBIDDEN_DIRS or relative.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(relative.as_posix())
        if path.is_file():
            count += 1
    # Build output is never a source input. Run this gate before building.
    for name in ("build", "dist"):
        if (ROOT / name).exists():
            failures.append(name)
    missing = sorted(name for name in REQUIRED if not (ROOT / name).is_file())
    if failures or missing:
        print({"forbidden": sorted(set(failures)), "missing": missing}, file=sys.stderr)
        return 1
    print({"files": count, "status": "ok"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
